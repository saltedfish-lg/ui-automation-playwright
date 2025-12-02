"""
browser_fixtures.py
-------------------
该模块定义了与 Playwright 浏览器相关的 pytest fixture。

设计要点：
1. 使用 session 级别的 Playwright 实例（避免重复启动底层服务）；
2. 每个用例 function 级别创建 browser/context/page，确保用例之间隔离；
3. browser 类型、headless 等从配置中读取，方便 Jenkins 等环境切换；
4. 所有用例只需要注入 page fixture 即可，不必关心底层如何启动浏览器。
"""
import os
import time
from typing import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from framework.core.config_loader import get_config
from framework.core.logger import get_logger

logger = get_logger()

@pytest.fixture(scope="session")
def config() -> dict:
    """
    session 级别的配置 fixture，整个测试进程只读取一次配置文件。

    :return: 配置字典
    """
    cfg = get_config()
    logger.info(f"[配置] 当前环境: {cfg.get('env')}")
    return cfg


@pytest.fixture(scope="session")
def playwright_instance():
    """
    session 级别的 Playwright 实例。

    使用 sync_playwright() 上下文管理 Playwright 的生命周期。
    """
    logger.info("[Playwright] 启动 Playwright 服务")
    with sync_playwright() as playwright:
        yield playwright
    logger.info("[Playwright] 关闭 Playwright 服务")

@pytest.fixture(scope="function")
def browser(playwright_instance, config) -> Generator[Browser, None, None]:
    """
    function 级别的 Browser fixture。

    每个用例独立一个 Browser 实例，保证隔离性。
    你也可以根据需要将 scope 改为 class 或 module 级别以提升执行速度。

    :param playwright_instance: session 级别的 Playwright 实例
    :param config: 配置字典
    :return: Browser 实例
    """
    browser_config = config.get("browser", {})
    browser_type = browser_config.get("type", "chromium")
    headless = browser_config.get("headless", True)
    slow_mo = browser_config.get("slow_mo", 0)

    logger.info(
        f"[Browser] 启动浏览器: type={browser_type}, headless={headless}, slow_mo={slow_mo}"
    )

    if browser_type == "chromium":
        browser = playwright_instance.chromium.launch(
            headless=headless, slow_mo=slow_mo
        )
    elif browser_type == "firefox":
        browser = playwright_instance.firefox.launch(
            headless=headless, slow_mo=slow_mo
        )
    elif browser_type == "webkit":
        browser = playwright_instance.webkit.launch(
            headless=headless, slow_mo=slow_mo
        )
    else:
        raise ValueError(f"不支持的浏览器类型: {browser_type}")

    yield browser

    logger.info("[Browser] 关闭浏览器实例")
    browser.close()

@pytest.fixture(scope="function")
def page(browser: Browser, config: dict) -> Generator[Page, None, None]:
    """
    function 级别的 Page fixture。

    增强点：
    1. 每个用例新建独立的 BrowserContext 和 Page；
    2. 为每个用例启动 Playwright tracing，记录执行过程；
    3. 可选：通过环境变量开启视频录制 / HAR 采集；
    4. 上层 pytest hook 会在用例失败时停止 tracing 并输出 trace 文件。

    环境变量开关：
    - UI_RECORD_VIDEO=true    开启视频录制，输出到 reports/videos
    - UI_RECORD_HAR=true      开启 HAR 记录，输出到 reports/har

    :param browser: Browser 实例
    :param config: 配置字典
    :return: Page 实例
    """
    app_config = config.get("app", {})
    base_url = app_config.get("base_url", "")

    logger.info(f"[Context] 创建浏览器上下文, base_url={base_url}")

    # ====== 这里开始是可选的视频 / HAR 配置 ======
    record_video = os.getenv("UI_RECORD_VIDEO", "false").lower() == "true"
    record_har = os.getenv("UI_RECORD_HAR", "false").lower() == "true"

    # 统一用一个字典收集 new_context 的参数
    context_args: dict = {
        "base_url": base_url,
    }

    if record_video:
        video_dir = "reports/videos"
        os.makedirs(video_dir, exist_ok=True)
        context_args["record_video_dir"] = video_dir
        logger.info(f"[Context] 启用视频录制, 目录: {video_dir}")

    if record_har:
        har_dir = "reports/har"
        os.makedirs(har_dir, exist_ok=True)
        har_path = os.path.join(
            har_dir, f"har_{int(time.time() * 1000)}.har"
        )
        context_args["record_har_path"] = har_path
        context_args["record_har_mode"] = "minimal"  # 或 "full"
        logger.info(f"[Context] 启用 HAR 记录, 文件: {har_path}")

    # ====== 在这里用解包参数创建 BrowserContext ======
    context: BrowserContext = browser.new_context(**context_args)

    # 启动 tracing，记录本用例的执行轨迹
    context.tracing.start(
        screenshots=True,  # 记录截屏，方便回放
        snapshots=True,    # 记录 DOM 快照
        sources=True,      # 记录源码，便于调试
    )

    page: Page = context.new_page()

    # 统一设置一个默认超时时间（使用配置中的 medium）
    timeout_cfg = config.get("timeout", {})
    default_timeout = timeout_cfg.get("medium", 5000)

    # 设置上下文和页面的默认超时（毫秒）
    context.set_default_timeout(default_timeout)
    page.set_default_timeout(default_timeout)

    yield page

    logger.info("[Context] 关闭浏览器上下文")
    # 用例结束时如果还没 stop tracing，这里兜底停掉
    try:
        context.tracing.stop()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[Tracing] 停止 tracing 时发生异常（可能已提前停止）: {e}")

    context.close()

@pytest.fixture(scope="function")
def auth_page(browser: Browser, config: dict) -> Generator[Page, None, None]:
    """
    带有“已登录状态”的 Page fixture。

    使用方式：
        def test_xxx(auth_page: Page):
            # 这里打开的第一页，就已经是登录后的状态了

    实现思路：
    - 依赖事先生成好的 storage_state.json；
    - 创建 BrowserContext 时传入 storage_state 参数；
    - 让用例直接在已登录的上下文中执行，避免每条用例重复走登录流程。

    注意：
    - storage_state.json 建议用工具脚本生成；
    - 登录态过期时，重新生成即可。
    """
    app_cfg = config.get("app", {})
    base_url = app_cfg.get("base_url", "")

    # 登录状态文件路径（要和生成工具脚本里的路径一致）
    storage_state_path = os.path.join("artifacts", "storage_state.json")

    if not os.path.exists(storage_state_path):
        raise FileNotFoundError(
            f"未找到登录状态文件: {storage_state_path}，"
            f"请先运行 tools/generate_storage_state.py 生成。"
        )

    logger.info(
        f"[Context] 创建带登录态的浏览器上下文, "
        f"base_url={base_url}, storage_state={storage_state_path}"
    )

    # 核心：创建 context 时指定 storage_state
    context: BrowserContext = browser.new_context(
        base_url=base_url,
        storage_state=storage_state_path,
    )
    page: Page = context.new_page()

    yield page

    logger.info("[Context] 关闭带登录态的浏览器上下文")
    context.close()