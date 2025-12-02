# tools/generate_storage_state.py
# -*- coding: utf-8 -*-
"""
一个小工具脚本：
1. 启动浏览器
2. 执行一次登录
3. 保存登录后的 storage_state 到文件

后面所有 UI 用例都可以基于这个状态启动浏览器，跳过重复登录。
"""

import os

from playwright.sync_api import sync_playwright

from framework.core.config_loader import get_config
from flows.login_flow import LoginFlow


def main():
    config = get_config()
    app_cfg = config.get("app", {})
    browser_cfg = config.get("browser", {})

    base_url = app_cfg.get("base_url", "")
    browser_type = browser_cfg.get("type", "chromium")
    headless = browser_cfg.get("headless", True)
    slow_mo = browser_cfg.get("slow_mo", 0)

    # 存储登录状态的文件路径
    storage_state_path = os.path.join("artifacts", "storage_state.json")
    os.makedirs("artifacts", exist_ok=True)

    with sync_playwright() as p:
        if browser_type == "chromium":
            browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)
        elif browser_type == "firefox":
            browser = p.firefox.launch(headless=headless, slow_mo=slow_mo)
        else:
            browser = p.webkit.launch(headless=headless, slow_mo=slow_mo)

        # 创建带 base_url 的 context
        context = browser.new_context(base_url=base_url)
        page = context.new_page()

        # 复用你已有的登录流程
        flow = LoginFlow(page)
        flow.login_with_default_account()

        # 如果有需要，可以再等一下页面稳定
        page.wait_for_load_state("networkidle")

        # 核心：保存登录后的 storage_state
        context.storage_state(path=storage_state_path)
        print(f"已保存登录状态到: {storage_state_path}")

        browser.close()


if __name__ == "__main__":
    main()
