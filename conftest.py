"""
全局 Pytest 配置与钩子：
1. 注册 fixtures 模块；
2. 失败用例自动截图 + 导出 trace；
3. 将截图 / trace 挂到 pytest-html 报告中。
"""

from typing import Any
from pathlib import Path

import pytest
import pytest_html
from playwright.sync_api import Page

from framework.core.logger import get_logger
from utils.path_utils import get_screenshot_path, get_trace_path

logger = get_logger()

# 插件方式引入 fixtures
pytest_plugins = [
    "framework.fixtures.browser_fixtures",  # 这里面有 config / playwright_instance / browser / page / auth_page
    "framework.fixtures.api_fixtures",
]

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> None:
    """
    用例执行阶段结束后被调用的钩子。

    作用：
    1. 拿到 pytest 生成的 TestReport；
    2. 如果是执行阶段（when == "call"）且失败，则：
        - 自动截图；
        - 导出 Playwright trace；
        - 将截图 / trace 作为 extras 挂到 pytest-html 报告中。

    注意：
    - 只对实际执行阶段（call）做处理，setup/teardown 暂不处理；
    - 同时兼容 page / auth_page 两种 fixture。
    """
    # 1）先让 pytest 和其他插件先处理这个 hook
    outcome = yield

    # 2）再拿到 TestReport
    report = outcome.get_result()

    # 只关心用例执行阶段
    if report.when != "call":
        return

    # 确保 report 上有 extra 属性（pytest-html 用来存放附件）
    extra = getattr(report, "extra", [])

    # 只有失败的用例我们才去截图 / trace
    if report.failed:
        logger.error(f"[失败] 用例失败，准备自动截图和保存 trace: {report.nodeid}")

        # 优先 page，其次 auth_page
        page: Page | None = item.funcargs.get("page") or item.funcargs.get("auth_page")

        if not page:
            logger.warning(
                "[失败] 用例中未注入 page/auth_page fixture，无法截图和保存 trace"
            )
            report.extra = extra
            return

        # ===== 1. 生成失败截图并挂到报告 =====
        screenshot_path = get_screenshot_path(item.name)
        try:
            # 实际截屏
            page.screenshot(path=screenshot_path, full_page=True)
            logger.error(f"[截图] 已保存失败截图: {screenshot_path}")

            # 将截图路径转换为相对 reports 目录的路径，方便 HTML 引用
            report_root = Path("reports")
            screenshot_rel = Path(screenshot_path)
            try:
                # 如果是类似 "reports/screenshots/xxx.png"，relative_to 后就是 "screenshots/xxx.png"
                screenshot_rel = screenshot_rel.relative_to(report_root)
            except ValueError:
                # 不在 reports 目录下，就直接用原路径
                pass

            # 添加到 pytest-html 的 extras 中
            extra.append(
                pytest_html.extras.image(
                    screenshot_rel.as_posix(),  # 统一用 / 作为分隔符
                    mime_type="image/png",
                )
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"[截图失败] 保存截图时发生异常: {e}")

        # ===== 2. 导出 trace 并挂到报告 =====
        trace_path = get_trace_path(item.name)
        try:
            page.context.tracing.stop(path=trace_path)
            logger.error(f"[Tracing] 已保存失败 trace 文件: {trace_path}")

            report_root = Path("reports")
            trace_rel = Path(trace_path)
            try:
                trace_rel = trace_rel.relative_to(report_root)
            except ValueError:
                pass

            # 用一个 HTML 超链接的形式挂到报告中
            trace_link_html = (
                f'<a href="{trace_rel.as_posix()}" target="_blank">'
                f"下载 Playwright trace</a>"
            )
            extra.append(pytest_html.extras.html(trace_link_html))
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Tracing] 保存 trace 时发生异常: {e}")

    # 不管失败 / 通过，都要把 extra 回写到 report 上
    report.extra = extra
