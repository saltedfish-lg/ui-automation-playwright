# -*- coding: utf-8 -*-
"""
config_loader.py
----------------
该模块负责统一加载项目配置，提供一个全局可用的配置字典对象。

设计要点：
1. 配置文件统一放在 configs 目录下；
2. 支持多环境（如：config_dev.yaml / config_test.yaml）；
3. 通过懒加载 + 单例方式，避免在每个模块中重复读取文件；
4. 对外暴露 get_config() 函数，其他模块只关心读取，不关心实现细节。
"""

import os
from functools import lru_cache
from typing import Any, Dict

import yaml


def _load_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    内部工具函数：读取 YAML 文件并返回字典。

    :param file_path: YAML 配置文件的绝对路径
    :return: YAML 解析后的字典结果
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"配置文件不存在: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        # yaml.safe_load 会将 YAML 内容解析为 Python 字典
        data = yaml.safe_load(f) or {}
    return data


@lru_cache(maxsize=1)
def get_config() -> Dict[str, Any]:
    """
    对外暴露的配置获取函数（单例模式）。

    逻辑说明：
    1. 首先加载 configs/config.yaml 作为默认配置；
    2. 再根据环境（env 字段或环境变量）决定是否加载其他覆盖配置；
    3. 将覆盖配置递归合并到默认配置中；
    4. 使用 lru_cache 装饰器，保证全局只加载一次配置。

    :return: 合并后的配置字典
    """
    # 获取项目根目录（当前文件 -> framework/core -> 项目根）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))

    # 默认配置文件路径
    default_config_path = os.path.join(project_root, "configs", "config.yaml")
    config = _load_yaml_file(default_config_path)

    # 通过环境变量 UI_AUTOMATION_ENV 覆盖 env 字段（方便 Jenkins 等外部控制）
    env_from_env = os.getenv("UI_AUTOMATION_ENV")
    if env_from_env:
        config["env"] = env_from_env

    # 根据 env 字段决定是否加载对应的环境配置文件
    env_name = config.get("env")
    if env_name and env_name != "default":
        env_config_path = os.path.join(
            project_root, "configs", f"config_{env_name}.yaml"
        )
        if os.path.exists(env_config_path):
            env_config = _load_yaml_file(env_config_path)
            # 将环境配置合并到默认配置中（浅合并，简单够用）
            config = _merge_dicts(config, env_config)

    return config


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归地合并两个字典，override 中的值会覆盖 base 中的同名键。

    :param base: 基础配置字典
    :param override: 覆盖配置字典
    :return: 合并后的新字典
    """
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            # 如果两个值都是 dict，则递归合并
            result[key] = _merge_dicts(result[key], value)
        else:
            # 否则，直接覆盖
            result[key] = value
    return result
