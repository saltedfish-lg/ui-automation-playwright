"""
network_utils.py
----------------
基于 Playwright 的简单接口 mock 工具示例。

主要能力：
1. 拦截指定 URL 的请求；
2. 返回自定义的 mock 响应；
3. 适合在前端 UI 自动化中屏蔽不稳定的后端依赖，或制造特殊数据场景。
"""

from typing import Any, Dict
import json
from playwright.sync_api import Page


def mock_get(
    page: Page,
    url_substring: str,
    mock_json: Dict[str, Any],
    status: int = 200,
) -> None:
    """
    拦截并 mock 某个 GET 请求。

    :param page: 当前用例的 Page 实例
    :param url_substring: URL 关键字（包含这个片段的请求都会被拦截）
    :param mock_json: 要返回的 JSON 数据
    :param status: HTTP 状态码，默认 200
    """
    def _handler(route, request):
        # 仅拦截 GET 请求，且 URL 中包含指定关键字
        if request.method == "GET" and url_substring in request.url:
            route.fulfill(
                status=status,
                content_type="application/json",
                body=json.dumps(mock_json, ensure_ascii=False),
            )
        else:
            # 其他请求正常放行
            route.fallback()
    # 在当前 page 上设置路由拦截规则
    page.route("**/*", _handler)
