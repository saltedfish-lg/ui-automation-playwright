# pages/login_page.py
# -*- coding: utf-8 -*-
"""
login_page.py
-------------
登录页面的 Page Object（PO 层）。

设计要点：
1. 尽量使用 Playwright 自带的 get_by_xxx 系列 API，代码更语义化、可读性更好；
2. URL 打开逻辑与 config.yaml 中的 base_url + login_path 保持一致；
3. 成功/失败提示封装成方法，供 Flow 层和用例层复用。
"""

from playwright.sync_api import Locator

from framework.core.base_page import BasePage
from framework.core.config_loader import get_config


class LoginPage(BasePage):
    """
    登录页 Page 对象，继承 BasePage。

    说明：
    - 输入框、按钮用 Locator 封装（Playwright 原生 API），
      优先使用 placeholder、role 等更稳定的属性；
    - 成功/失败提示暂时用 XPath，后续可以和前端约定 data-testid 再替换。
    """

    # ========== 成功 / 失败提示定位（可以根据你实际页面调整） ==========
    # 登录成功提示元素的 XPath
    SUCCESS_MESSAGE = "//p[.//text()='登录成功']"
    USER_NAME_LABEL = ".userName"
    # 登录失败错误提示元素的 XPath
    # 1. 全局错误：账号或密码错误
    GLOBAL_ERROR_MESSAGE = "//p[.//text()='账号或密码错误']"
    # 2. 用户名为空的校验提示
    USERNAME_REQUIRED_MESSAGE = "//div[text()='请输入账号']"
    # 3. 密码为空的校验提示
    PASSWORD_REQUIRED_MESSAGE = "//div[text()='请输入密码']"

    # ========== URL 打开逻辑 ==========

    def open_login_page(self) -> None:
        """
        打开登录页面。

        兼容两种配置方式：
        1）登录页就是 base_url 本身：
            app:
              base_url: "http://vat.dev.dev.usaeu.com:8088"
              login_path: ""
        2）登录页是 base_url + login_path：
            app:
              base_url: "http://vat.dev.dev.usaeu.com:8088"
              login_path: "/login"

        不管哪种写法，这里都会算出一个完整 URL，然后用 BasePage.open 打开。
        """
        config = get_config()
        app_cfg = config.get("app", {})

        base_url = app_cfg.get("base_url", "").rstrip("/")
        login_path = (app_cfg.get("login_path") or "").strip()

        # 情况 1：login_path 为空，直接用 base_url
        if not login_path:
            full_url = base_url

        # 情况 2：login_path 是绝对 URL（以 http 开头），直接用它
        elif login_path.startswith("http"):
            full_url = login_path

        # 情况 3：login_path 是相对路径，拼接 base_url 和 path
        else:
            full_url = f"{base_url}/{login_path.lstrip('/')}"

        self.open(full_url)


    # ========== 内部 Locator 获取方法 ==========

    def _username_input(self) -> Locator:
        """
        内部方法：返回用户名输入框的 Locator 对象。

        这里使用 get_by_placeholder，依赖于 input 的 placeholder 文案：
        <input placeholder="请输入账号" ...>
        """
        return self.page.get_by_placeholder("请输入账号")

    def _password_input(self) -> Locator:
        """
        内部方法：返回密码输入框的 Locator 对象。

        依赖于密码输入框的 placeholder 文案：
        <input placeholder="请输入密码" ...>
        """
        return self.page.get_by_placeholder("请输入密码")

    def _login_button(self) -> Locator:
        """
        内部方法：返回“登录”按钮的 Locator 对象。

        这里通过按钮的语义角色 + 文案来定位：
        <button>登录</button>
        """
        return self.page.get_by_role("button", name="登录", exact=True)

    # ========== 对外操作方法（供 Flow 层调用） ==========

    def input_username(self, username: str) -> None:
        """
        在“用户名”输入框中输入文本。

        :param username: 要输入的用户名/账号
        """
        # 直接用 Locator.fill，Playwright 会自动等待元素可交互
        self._username_input().fill(username)

    def input_password(self, password: str) -> None:
        """
        在“密码”输入框中输入文本。

        :param password: 要输入的密码
        """
        self._password_input().fill(password)

    def click_login_button(self) -> None:
        """
        点击“登录”按钮。
        """
        self._login_button().click()

    # ========== 成功 / 失败状态封装（供用例层断言） ==========

    def get_error_message(self) -> str:
        """
        获取登录失败时的错误提示文本。

        :return: 错误文案（例如：'账号或密码错误'）
        """
        return self.get_text(self.GLOBAL_ERROR_MESSAGE)

    def is_error_message_visible(self) -> bool:
        """
        判断登录失败错误提示是否可见。

        :return: True 表示错误提示元素在页面上可见
        """
        return self.is_visible(self.GLOBAL_ERROR_MESSAGE)

    def get_success_message(self) -> str:
        """
        获取登录成功时的提示文本。

        :return: 成功文案（例如：'登录成功'）
        """
        return self.get_text(self.SUCCESS_MESSAGE)

    def is_logged_in(self) -> bool:
        """
        判断登录成功提示是否可见。

        :return: True 表示成功提示元素在页面上可见
        """
        return self.is_visible(self.USER_NAME_LABEL)

    def is_global_error_visible(self) -> bool:
        """是否出现全局错误提示：账号或密码错误"""
        return self.is_visible(self.GLOBAL_ERROR_MESSAGE)

    def is_username_required_visible(self) -> bool:
        """是否出现“请输入账号”的表单校验错误"""
        return self.is_visible(self.USERNAME_REQUIRED_MESSAGE)

    def is_password_required_visible(self) -> bool:
        """是否出现“请输入密码”的表单校验错误"""
        return self.is_visible(self.PASSWORD_REQUIRED_MESSAGE)
