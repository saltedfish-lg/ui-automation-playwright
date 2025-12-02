# framework/core/base_page.py
# -*- coding: utf-8 -*-
"""
base_page.py
------------
所有 Page Object 的基类，对 Playwright 的 Page 做一层抽象封装。

改进点：
1. 从配置中读取统一的超时时间配置（short/medium/long）；
2. 对外方法支持传入自定义 timeout，未传则使用默认 medium；
3. 方便在不同环境下集中调整等待时间，而不是在代码里硬编码 5000。
"""

from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from framework.core.config_loader import get_config
from framework.core.logger import get_logger

logger = get_logger()


class BasePage:
    """
    Page Object 基类，所有页面类都应该继承该类。

    属性：
        page: Playwright 中的 Page 实例，表示当前浏览器标签页；
        _short_timeout / _medium_timeout / _long_timeout:
            从配置中读取的统一超时时间，单位毫秒。
    """

    def __init__(self, page: Page):
        """
        初始化 BasePage。

        :param page: Playwright Page 实例，由 pytest fixture 传入
        """
        self.page = page

        # 读取全局配置，用于初始化各类默认超时时间
        config = get_config()
        timeout_cfg = config.get("timeout", {})

        # 提供合理的默认值，避免配置缺失导致报错
        self._short_timeout: int = timeout_cfg.get("short", 3000)
        self._medium_timeout: int = timeout_cfg.get("medium", 5000)
        self._long_timeout: int = timeout_cfg.get("long", 10000)

    # ========== 基础导航方法 ==========

    def open(self, url: str, wait_until: str = "load") -> None:
        """
        打开指定 URL 页面。

        :param url: 目标地址，可以是完整 URL，也可以是相对路径（依赖 base_url）
        :param wait_until: 等待页面加载完成的条件（load/domcontentloaded/networkidle）
        """
        logger.info(f"[导航] 打开页面: {url}")
        self.page.goto(url, wait_until=wait_until)

    # ========== 元素操作封装 ==========

    def click(self, locator: str, timeout: int | None = None) -> None:
        """
        点击元素（带自动等待）。

        :param locator: 元素定位字符串（CSS / XPath / text 等）
        :param timeout: 超时时间（毫秒），未传则使用默认中等时长
        """
        effective_timeout = timeout or self._medium_timeout
        logger.info(f"[操作] 点击元素: {locator}, timeout={effective_timeout}ms")
        try:
            self.page.click(locator, timeout=effective_timeout)
        except PlaywrightTimeoutError:
            logger.error(f"[超时] 点击元素超时: {locator}")
            raise

    def fill(self, locator: str, value: str, timeout: int | None = None) -> None:
        """
        在输入框中输入文本（会先清空原有内容）。

        :param locator: 元素定位字符串
        :param value: 要输入的文本
        :param timeout: 超时时间（毫秒），未传则使用默认中等时长
        """
        effective_timeout = timeout or self._medium_timeout
        logger.info(
            f"[操作] 输入文本: locator={locator}, value={value}, timeout={effective_timeout}ms"
        )
        try:
            # 先等待元素可见，再进行输入，调试更友好
            element = self.page.locator(locator)
            element.wait_for(state="visible", timeout=effective_timeout)
            element.fill(value)
        except PlaywrightTimeoutError:
            logger.error(f"[超时] 输入文本超时: {locator}")
            raise

    def get_text(self, locator: str, timeout: int | None = None) -> str:
        """
        获取元素文本内容。

        :param locator: 元素定位字符串
        :param timeout: 超时时间（毫秒），未传则使用默认中等时长
        :return: 元素的文本内容
        """
        effective_timeout = timeout or self._medium_timeout
        logger.info(f"[获取文本] 元素: {locator}, timeout={effective_timeout}ms")
        try:
            element = self.page.locator(locator)
            element.wait_for(state="visible", timeout=effective_timeout)
            text = element.inner_text()
            logger.info(f"[获取文本] 内容: {text}")
            return text
        except PlaywrightTimeoutError:
            logger.error(f"[超时] 获取文本超时: {locator}")
            raise

    def is_visible(self, locator: str, timeout: int | None = None) -> bool:
        """
        判断元素是否在页面可见。

        :param locator: 元素定位字符串
        :param timeout: 超时时间（毫秒），未传则使用默认中等时长
        :return: True 表示可见，False 表示不可见或超时
        """
        effective_timeout = timeout or self._medium_timeout
        logger.info(f"[校验] 判断元素是否可见: {locator}, timeout={effective_timeout}ms")
        try:
            element = self.page.locator(locator)
            element.wait_for(state="visible", timeout=effective_timeout)
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"[不可见或超时] 元素: {locator}")
            return False

    # ========== 断言封装 ==========

    def assert_text_equal(
        self,
        locator: str,
        expected_text: str,
        timeout: int | None = None,
        msg: str | None = None,
    ) -> None:
        """
        断言元素文本等于预期值。

        :param locator: 元素定位字符串
        :param expected_text: 期望文本
        :param timeout: 超时时间（毫秒），未传则使用默认中等时长
        :param msg: 自定义断言失败信息
        """
        effective_timeout = timeout or self._medium_timeout
        actual = self.get_text(locator, timeout=effective_timeout)
        logger.info(
            f"[断言] 文本相等: expected={expected_text}, actual={actual}, locator={locator}"
        )
        if actual != expected_text:
            error_msg = msg or f"元素文本不匹配，期望: {expected_text}，实际: {actual}"
            logger.error(error_msg)
            raise AssertionError(error_msg)

    def assert_true(self, condition: Any, msg: str = "断言失败：条件为 False") -> None:
        """
        通用布尔断言方法。

        :param condition: 需要判断的条件
        :param msg: 断言失败信息
        """
        logger.info(f"[断言] 条件判断，结果: {condition}")
        if not condition:
            logger.error(msg)
            raise AssertionError(msg)
