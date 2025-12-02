# tests/login/test_login_success.py
# -*- coding: utf-8 -*-
"""
test_login_success.py
---------------------
示例用例：验证登录成功。

设计要点：
1. 用例层只关心“业务流程 + 断言”；
2. 前置步骤调用 LoginFlow 完成登录；
3. 断言基于页面上的“登录成功提示”或首页特征元素。
"""

from playwright.sync_api import Page

from framework.core.logger import get_logger
from flows.login_flow import LoginFlow
from pages.login_page import LoginPage

logger = get_logger()


def test_login_success(page: Page):
    """
    测试用例：使用默认账号登录系统，验证登录成功。

    :param page: 来自 pytest fixture 的 Playwright Page 实例
    """
    logger.info("[用例] test_login_success 开始执行")

    # 1. 通过 Flow 执行登录流程
    flow = LoginFlow(page)
    flow.login_with_default_account()

    # 2. 等页面网络请求和渲染稳定，避免刚跳转就断言导致不稳定
    page.wait_for_load_state("networkidle")

    # 3. 断言：登录成功提示可见（也可以换成首页特征元素）
    login_page = LoginPage(page)
    assert login_page.is_logged_in(), "登录成功提示未出现，疑似登录失败"

    logger.info("[用例] test_login_success 执行完成")
