# -*- coding: utf-8 -*-
"""
path_utils.py
-------------
路径相关工具函数，主要用于统一管理截图、报告等输出路径。
"""

import os
from datetime import datetime

from framework.core.config_loader import get_config


def ensure_dir(path: str) -> None:
    """
    确保目录存在，如不存在则递归创建。

    :param path: 目录路径
    """
    os.makedirs(path, exist_ok=True)


def get_screenshot_path(test_name: str) -> str:
    """
    根据测试用例名生成截图路径。

    :param test_name: 测试用例名称（一般来自 request.node.name）
    :return: 截图文件的绝对路径
    """
    config = get_config()
    report_cfg = config.get("report", {})
    screenshot_dir = report_cfg.get("screenshot_dir", "reports/screenshots")

    ensure_dir(screenshot_dir)

    # 使用时间戳避免重名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{test_name}_{timestamp}.png"

    return os.path.join(screenshot_dir, filename)

def get_trace_path(test_name: str) -> str:
    """
    根据测试用例名生成 trace 文件路径（.zip）。

    :param test_name: 测试用例名称（来自 request.node.name）
    :return: trace 文件的绝对路径
    """
    config = get_config()
    report_cfg = config.get("report", {})
    trace_dir = report_cfg.get("trace_dir", "reports/traces")

    ensure_dir(trace_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{test_name}_{timestamp}.zip"

    return os.path.join(trace_dir, filename)
