# flows/login_flow.py
# -*- coding: utf-8 -*-
"""
login_flow.py
-------------
登录业务流程（Flow 层）。
"""

import os

from playwright.sync_api import Page

from framework.core.base_flow import BaseFlow
from framework.core.config_loader import get_config
from framework.core.logger import get_logger
from pages.login_page import LoginPage

logger = get_logger()


class LoginFlow(BaseFlow):
    """
    登录业务流程类。

    继承 BaseFlow，复用 step()、wait_page_stable() 等通用能力。
    """

    def __init__(self, page: Page):
        """
        初始化登录流程对象。

        :param page: pytest fixture 提供的 Page 实例
        """
        # 调用父类构造函数，初始化 page
        super().__init__(page)
        # 构建本流程使用到的页面对象
        self.login_page = LoginPage(page)

    def _get_default_account(self) -> tuple[str, str]:
        """
        获取默认登录账号（用户名、密码）。

        优先级：
        1. 环境变量 UI_ACCOUNT_USERNAME / UI_ACCOUNT_PASSWORD；
        2. configs/config.yaml 中 account 节点。
        """
        config = get_config()
        account_cfg = config.get("account", {})

        username = os.getenv("UI_ACCOUNT_USERNAME") or account_cfg.get("username")
        password = os.getenv("UI_ACCOUNT_PASSWORD") or account_cfg.get("password")

        if not username or not password:
            raise ValueError(
                "默认登录账号未配置，请设置环境变量 "
                "UI_ACCOUNT_USERNAME / UI_ACCOUNT_PASSWORD 或在配置文件 account 下配置用户名和密码。"
            )

        return username, password

    def login_with_default_account(self) -> None:
        username, password = self._get_default_account()
        logger.info(f"[流程] 使用默认账号登录: username={username}")
        self.login(username=username, password=password)

    def login(self, username: str, password: str) -> None:
        """
        使用指定账号执行登录流程（只做操作，不做断言）。

        :param username: 登录用户名
        :param password: 登录密码
        """
        self.step("打开登录页面")
        self.login_page.open_login_page()

        self.step(f"输入用户名：{username}")
        self.login_page.input_username(username)

        self.step("输入密码")
        self.login_page.input_password(password)

        self.step("点击登录按钮")
        self.login_page.click_login_button()

        self.step("等待登录后的页面稳定")
        self.wait_page_stable(state="networkidle")

        logger.info("[流程] 登录操作已完成（是否成功由上层用例断言）")

    def login_should_success(
        self,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """
        带断言的“登录应当成功”流程。

        - 如果传了 username/password：用你传的账号密码；
        - 如果没传：自动用默认账号（环境变量 / 配置文件）。
        """
        if username is None or password is None:
            username, password = self._get_default_account()
            logger.info(f"[流程] 使用默认账号执行 login_should_success: username={username}")
        else:
            logger.info(f"[流程] 使用自定义账号执行 login_should_success: username={username}")

        # 1. 执行登录操作（不含断言）
        self.login(username=username, password=password)

        # 2. 等待页面稳定
        self.wait_page_stable("networkidle")

        # 3. 断言：登录成功标识出现
        login_page = LoginPage(self.page)
        assert login_page.is_success_message_visible(), "期望登录成功，但未检测到成功标识。"

    def login_should_fail(self, username: str, password: str) -> None:
        """
        带断言的“登录应当失败”流程。

        - 账号/密码由调用方传入（一般是参数化测试数据）；
        - 断言：错误提示出现。
        """
        logger.info(f"[流程] 执行 login_should_fail, username={username}")
        self.login(username=username, password=password)
        self.wait_page_stable("networkidle")

        login_page = LoginPage(self.page)

        if not username and password:
            # 用户名为空的场景
            assert login_page.is_username_required_visible(), "期望出现“请输入账号”的错误提示，但未检测到。"
        elif username and not password:
            # 密码为空的场景
            assert login_page.is_password_required_visible(), "期望出现“请输入密码”的错误提示，但未检测到。"
        else:
            # 其他失败场景：账号或密码错误
            assert login_page.is_global_error_visible(), "期望出现“账号或密码错误”的全局错误提示，但未检测到。"