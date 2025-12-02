# framework/core/base_flow.py
# -*- coding: utf-8 -*-
"""
base_flow.py
------------
业务流程（Flow）基类。

设计目的：
1. 为所有 Flow 提供统一的结构和基础能力；
2. 封装通用的日志能力和常用辅助方法；
3. 让具体的 Flow（例如 LoginFlow / OrderFlow）专注于业务步骤本身。
"""

from playwright.sync_api import Page

from framework.core.logger import get_logger

logger = get_logger()


class BaseFlow:
    """
    Flow 层基类。

    属性：
        page: Playwright Page 实例，用于在浏览器中执行页面操作。
    """

    def __init__(self, page: Page):
        """
        初始化 Flow 基类。

        :param page: pytest fixture 提供的 Page 实例
        """
        self.page = page

    def step(self, description: str) -> None:
        """
        Flow 中的“步骤”记录工具方法。

        用法示例：
            self.step("打开登录页面")
            self.step("输入用户名和密码")

        好处：
        - 在日志中可以清晰看到每一步的业务含义；
        - 未来需要时可以扩展为记录到测试报告、Allure 步骤等。
        """
        logger.info(f"[Flow Step] {description}")

    def wait_page_stable(self, state: str = "networkidle") -> None:
        """
        等待页面稳定的通用方法。

        :param state: Playwright 的 load state，常用值：
                      - "load": 页面 load 事件触发
                      - "domcontentloaded": DOMContentLoaded 事件触发
                      - "networkidle": 网络空闲（适合 SPA / 接口较多页面）
        """
        logger.info(f"[Flow] 等待页面状态稳定: state={state}")
        self.page.wait_for_load_state(state)
