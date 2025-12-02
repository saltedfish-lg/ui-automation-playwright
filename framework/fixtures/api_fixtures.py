"""
基于 Playwright 的 APIRequestContext + ApiClient 封装的 pytest fixture。

作用：
    提供一个 session 级别的 ApiClient 实例，用于：
    - 在 UI 自动化前后通过接口造数 / 清理数据；
    - 执行独立的接口自动化场景（配合 pytest 标记使用）。

设计要点：
    1. base_url 复用 app.base_url（也可以在 configs 中单独配置 api.base_url）；
    2. 提供一组默认 headers（Content-Type 等），后续可在 configs 中扩展；
    3. 如需鉴权，可在：
        - 用例 / Flow 中调用 client.set_bearer_token("xxx");
        - 或扩展这里，开局先调用登录接口拿 Token。
"""

from typing import Generator

import pytest
from playwright.sync_api import APIRequestContext

from framework.core.config_loader import get_config
from framework.core.logger import get_logger
from utils.api_client import ApiClient

logger = get_logger()


@pytest.fixture(scope="session")
def api_client(playwright_instance) -> Generator[ApiClient, None, None]:
    """
    session 级别的 ApiClient fixture。

    - 在整个测试 session 中共享一个 APIRequestContext；
    - 一般用于造数场景，避免重复创建 HTTP 连接；
    - UI / API 混合场景时，既可以在 UI 前后调用接口，又可以写纯接口用例。

    :param playwright_instance: 来自 browser_fixtures 的 session 级别 Playwright 实例
    :return: 包装后的 ApiClient 实例
    """
    config = get_config()

    app_cfg = config.get("app", {})
    # 如果以后在 configs/config.yaml 中单独加 api.base_url，可优先使用
    api_cfg = config.get("api", {})

    base_url = api_cfg.get("base_url") or app_cfg.get("base_url", "")

    # 默认请求头（可以在 configs 中扩展 api.default_headers，然后这里优先从配置读取）
    default_headers = api_cfg.get("default_headers") or {
        "Content-Type": "application/json;charset=utf-8",
    }

    logger.info(f"[API] 创建 ApiClient, base_url={base_url}, headers={default_headers}")

    # 创建 Playwright 的 APIRequestContext（后续所有请求共用此上下文）
    request_context: APIRequestContext = playwright_instance.request.new_context(
        base_url=base_url,
        extra_http_headers=default_headers,
    )

    client = ApiClient(
        request_context=request_context,
        default_headers=default_headers,
        enable_business_check=True,  # 默认开启“code/success”业务断言
    )

    try:
        # 这里可以按需做“开局鉴权”，例如调用登录接口获取 token：
        #
        # login_resp = client.post(
        #     "/api/auth/login",
        #     json={"username": "...", "password": "..."},
        #     check_business=False,  # 登录接口的返回结构可能和统一格式不同
        # )
        # token = login_resp.get("token")
        # client.set_bearer_token(token)
        #
        # 当前项目如果暂时不需要，这块先留注释，后续要用再填坑。
        yield client
    finally:
        logger.info("[API] 关闭 ApiClient / APIRequestContext")
        request_context.dispose()
