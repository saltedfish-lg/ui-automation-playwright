# -*- coding: utf-8 -*-
"""
logger.py
---------
统一日志封装模块。

设计要点：
1. 使用 loguru 简化日志配置；
2. 日志输出到控制台 + 文件（按天切割）；
3. 对外暴露 get_logger()，避免每个模块重复配置；
4. 日志路径从配置文件读取，保持统一管理。
"""

import os
from functools import lru_cache

from loguru import logger

from framework.core.config_loader import get_config


@lru_cache(maxsize=1)
def get_logger():
    """
    获取全局日志记录器实例（loguru.logger）。

    使用 lru_cache 保证只初始化一次，避免重复添加 handler。
    """
    config = get_config()

    # 从配置中读取日志目录
    report_config = config.get("report", {})
    log_dir = report_config.get("log_dir", "reports/logs")

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 清除默认 handler（避免重复配置）
    logger.remove()

    # 添加控制台输出 handler
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level="INFO",
        enqueue=True,  # 多线程安全
    )

    # 添加文件输出 handler（按时间轮转）
    log_file_path = os.path.join(log_dir, "ui_automation_{time:YYYYMMDD}.log")
    logger.add(
        log_file_path,
        rotation="00:00",  # 每天 0 点新建日志文件
        retention="10 days",
        encoding="utf-8",
        level="INFO",
        enqueue=True,
    )

    return logger
