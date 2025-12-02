# tests/login/test_login_negative.py
# -*- coding: utf-8 -*-
"""
test_login_negative.py
----------------------
登录失败场景测试用例集合。

设计要点：
1. 通过 pytest.mark.parametrize 参数化多种错误输入场景；
2. 使用 LoginFlow 执行登录动作；
3. 使用 LoginPage 断言错误提示是否出现；
4. 通过这种方式，快速覆盖常见的登录校验逻辑。
"""

import pytest
from playwright.sync_api import Page

from framework.core.logger import get_logger
from flows.login_flow import LoginFlow
from pages.login_page import LoginPage

logger = get_logger()


@pytest.mark.parametrize(
    "username,password,case_desc",
    [
        ("guang", "wrong_password", "密码错误"),
        ("not_exist", "Aa123456", "账号不存在"),
        ("", "Aa123456", "账号为空"),
        ("guang", "", "密码为空"),
    ],
)
def test_login_fail_cases(page: Page, username: str, password: str, case_desc: str):
    flow = LoginFlow(page)
    flow.login_should_fail(username=username, password=password)

@pytest.mark.debug
def test_debug_fail(page):
    assert False, "故意失败看报告附件"