# utils/api_client.py
# -*- coding: utf-8 -*-
"""
api_client.py
-------------
基于 Playwright 的 APIRequestContext 做的一层轻量封装。

设计目标：
1. 统一管理常用的 HTTP 请求头（headers），包括：
   - Content-Type
   - 业务方要求的自定义头（如 X-Request-ID、X-Tenant-Id 等）
   - 鉴权头（如 Authorization: Bearer xxx）

2. 提供更易用的 GET / POST / PUT / DELETE 方法：
   - 自动拼接默认 headers；
   - 自动对 HTTP 状态码做断言，失败时带上详细日志；
   - 自动尝试解析 JSON，并提供“通用业务成功断言”（如 code == 0 或 success == True）。

3. 对上层屏蔽 Playwright 的 APIRequestContext 细节：
   - 上层只关心：ApiClient.get/post 返回的 JSON 数据；
   - 不需要每次都手写 status_code 检查。

注意：
- 这里的“业务成功判断逻辑”是通用模板，可以按你自家系统约定调整：
  比如很多后端约定：{"code": 0, "msg": "ok", "data": {...}}
  也有约定：{"success": true, "message": "xxx", "data": {...}}
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from playwright.sync_api import APIRequestContext, APIResponse

from framework.core.logger import get_logger

logger = get_logger()


class ApiClient:
    """
    ApiClient
    =========
    对 Playwright 的 APIRequestContext 做简单包装。

    使用方式示例（伪代码）：
    ----------------------------------------------------------------------
    def test_some_api(api_client: ApiClient):
        # 1. 直接发 GET 请求并断言 HTTP + 业务成功
        data = api_client.get("/api/user/profile")

        # 2. 发 POST 请求，期望 HTTP 201，且业务 code == 0
        payload = {"name": "张三", "age": 18}
        data = api_client.post("/api/user", json=payload, expected_status=201)

        # 3. 自定义 header / 不使用业务成功断言：
        resp = api_client.get(
            "/api/raw",
            headers={"X-Debug": "1"},
            check_business=False,
        )
    ----------------------------------------------------------------------
    """

    def __init__(
        self,
        request_context: APIRequestContext,
        default_headers: Optional[Dict[str, str]] = None,
        enable_business_check: bool = True,
    ) -> None:
        """
        初始化 ApiClient。

        :param request_context: Playwright 的 APIRequestContext 实例（由 fixture 创建）
        :param default_headers: 默认请求头，会自动合并到每次请求中
        :param enable_business_check: 是否默认对返回 JSON 做业务成功断言
        """
        self._request_context = request_context
        # 默认头可以为空，实际使用时再按需补充
        self._default_headers: Dict[str, str] = default_headers or {}
        # 是否开启通用业务成功断言
        self._enable_business_check = enable_business_check
        # 存放鉴权相关的信息（比如 Bearer Token）
        self._auth_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Header / 鉴权相关辅助方法
    # ------------------------------------------------------------------
    def set_bearer_token(self, token: str) -> None:
        """
        设置 Bearer Token 鉴权头。

        调用后，所有请求会自动带上：
            Authorization: Bearer <token>
        """
        self._auth_token = token
        logger.info("[API] 设置 Bearer Token 鉴权头")

    def set_common_header(self, key: str, value: str) -> None:
        """
        设置一个长期生效的公共请求头。

        例如：
            client.set_common_header("X-Tenant-Id", "10001")
        """
        self._default_headers[key] = value
        logger.info(f"[API] 设置默认请求头: {key}={value}")

    def _merge_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        内部方法：合并默认头 + 鉴权头 + 本次请求头。

        合并规则：
        - 以“本次请求头”为最高优先级（同名 key 会覆盖默认头）；
        - 如果设置了 auth_token，会自动注入 Authorization 头；
        """
        final_headers: Dict[str, str] = dict(self._default_headers)

        # 注入 Bearer Token 鉴权头（如果有）
        if self._auth_token:
            final_headers["Authorization"] = f"Bearer {self._auth_token}"

        # 本次请求自定义 header 覆盖默认值
        if headers:
            final_headers.update(headers)

        return final_headers

    # ------------------------------------------------------------------
    # 核心 HTTP 调用方法（GET / POST / PUT / DELETE）
    # ------------------------------------------------------------------
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
        check_business: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        发送 GET 请求。

        :param url: 请求路径，可以是相对路径（推荐）或绝对路径
        :param params: Query 参数字典
        :param headers: 额外请求头（会覆盖默认头同名字段）
        :param expected_status: 期望的 HTTP 状态码，默认 200
        :param check_business: 是否执行业务成功断言；
                               None 表示沿用对象级默认开关（enable_business_check）
        :return: 解析后的 JSON 数据（dict），如果非 JSON 会抛异常
        """
        final_headers = self._merge_headers(headers)
        logger.info(f"[API] GET {url}, params={params}, headers={final_headers}")

        response: APIResponse = self._request_context.get(
            url,
            params=params,
            headers=final_headers,
        )

        return self._handle_response(
            response,
            expected_status=expected_status,
            check_business=check_business,
        )

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
        check_business: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        发送 POST 请求。

        :param url: 请求路径
        :param json: JSON 请求体（常用）
        :param data: 表单请求体（application/x-www-form-urlencoded 或 multipart）
        :param headers: 额外请求头
        :param expected_status: 期望 HTTP 状态码
        :param check_business: 是否执行业务成功断言
        :return: 解析后的 JSON 数据（dict）
        """
        final_headers = self._merge_headers(headers)
        logger.info(
            f"[API] POST {url}, json={json}, data={data}, headers={final_headers}"
        )

        response: APIResponse = self._request_context.post(
            url,
            json=json,
            data=data,
            headers=final_headers,
        )

        return self._handle_response(
            response,
            expected_status=expected_status,
            check_business=check_business,
        )

    def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
        check_business: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        发送 PUT 请求。
        用法和 POST 类似。
        """
        final_headers = self._merge_headers(headers)
        logger.info(f"[API] PUT {url}, json={json}, data={data}, headers={final_headers}")

        response: APIResponse = self._request_context.put(
            url,
            json=json,
            data=data,
            headers=final_headers,
        )

        return self._handle_response(
            response,
            expected_status=expected_status,
            check_business=check_business,
        )

    def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200,
        check_business: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        发送 DELETE 请求。
        一般用于删除资源。
        """
        final_headers = self._merge_headers(headers)
        logger.info(f"[API] DELETE {url}, headers={final_headers}")

        response: APIResponse = self._request_context.delete(
            url,
            headers=final_headers,
        )

        return self._handle_response(
            response,
            expected_status=expected_status,
            check_business=check_business,
        )

    # ------------------------------------------------------------------
    # 底层响应处理与通用断言
    # ------------------------------------------------------------------
    def _handle_response(
        self,
        response: APIResponse,
        expected_status: int,
        check_business: Optional[bool],
    ) -> Dict[str, Any]:
        """
        内部方法：统一处理 HTTP 响应。

        步骤：
        1. 断言 HTTP 状态码是否等于 expected_status；
        2. 尝试解析 JSON，如果失败则抛异常；
        3. 根据 check_business（或默认开关）决定是否做业务成功断言；
        4. 返回解析后的 JSON 数据。
        """
        # 1）HTTP 状态码断言
        self._assert_status(response, expected_status)

        # 2）解析 JSON
        try:
            data = response.json()
        except Exception as e:  # noqa: BLE001
            # 如果后端不是 JSON 格式，直接给出详细错误信息
            text = response.text()
            logger.error(
                f"[API] 响应非 JSON 格式，status={response.status}，text={text}"
            )
            raise ValueError(f"响应非 JSON 格式，无法解析。原始异常: {e}") from e

        logger.info(f"[API] 响应 JSON: {data}")

        # 3）业务成功断言（可选）
        if check_business is None:
            # None 表示沿用对象默认策略
            check_business = self._enable_business_check

        if check_business:
            self._assert_business_success(data)

        # 4）返回 JSON 数据
        return data

    @staticmethod
    def _assert_status(response: APIResponse, expected_status: int) -> None:
        """
        断言 HTTP 状态码是否符合预期。

        如果不符合：
        - 打印响应头和部分响应体，方便排查；
        - 抛出 AssertionError。
        """
        actual_status = response.status
        if actual_status != expected_status:
            # 尽量给出更多上下文信息
            text_preview = response.text()
            if len(text_preview) > 500:
                text_preview = text_preview[:500] + "...(截断)"

            raise AssertionError(
                f"HTTP 状态码不符合预期，期望={expected_status}，实际={actual_status}，"
                f"响应内容预览={text_preview}"
            )

    @staticmethod
    def _assert_business_success(data: Dict[str, Any]) -> None:
        """
        通用“业务成功”断言。

        默认约定（可根据你们后端约定自行修改）：
        1）如果有 "code" 字段：
            - 认为 0 / "0" / "SUCCESS" / "OK" 等是成功；
        2）否则，如果有 "success" 字段：
            - 认为 True 是成功；
        3）两者都没有，则不做业务判断，直接放过。

        如果被判断为“业务失败”，会抛出 AssertionError。
        """
        # 1）优先看 code 字段
        if "code" in data:
            code = data.get("code")
            # 常见一堆成功值
            success_codes = {0, "0", "SUCCESS", "SUCCESSFUL", "OK"}
            if code not in success_codes:
                msg = data.get("msg") or data.get("message") or ""
                raise AssertionError(f"业务返回失败，code={code}, msg={msg}, data={data}")
            return

        # 2）其次看 success 字段
        if "success" in data:
            success = data.get("success")
            if success is not True:
                msg = data.get("message") or data.get("msg") or ""
                raise AssertionError(
                    f"业务返回失败，success={success}, msg={msg}, data={data}"
                )
            return

        # 3）既没有 code，也没有 success，认为无法判定业务状态，直接通过
        logger.warning(
            "[API] 响应中未发现 'code' 或 'success' 字段，跳过业务成功断言。"
        )

