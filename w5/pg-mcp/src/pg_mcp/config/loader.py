import os
import re
from pathlib import Path
from typing import Any

import yaml

from pg_mcp.config.models import AppConfig


def expand_env_vars(value: str) -> str:
    """展开环境变量

    支持 ${VAR_NAME} 和 ${VAR_NAME:-default} 语法
    """
    pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        if default is not None:
            return default
        return match.group(0)  # 保持原样

    return re.sub(pattern, replacer, value)


def process_config_dict(config: dict[str, Any]) -> dict[str, Any]:
    """递归处理配置字典，展开所有环境变量"""
    result: dict[str, Any] = {}
    for key, value in config.items():
        if isinstance(value, str):
            result[key] = expand_env_vars(value)
        elif isinstance(value, dict):
            result[key] = process_config_dict(value)
        elif isinstance(value, list):
            result[key] = [
                process_config_dict(item) if isinstance(item, dict)
                else expand_env_vars(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """加载配置

    配置来源优先级（从高到低）：
    1. 环境变量 PG_MCP_*
    2. 配置文件（如果指定）
    3. 默认值

    Args:
        config_path: 配置文件路径，如果为 None 则从环境变量 PG_MCP_CONFIG 读取

    Returns:
        AppConfig: 应用配置

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    # 确定配置文件路径
    if config_path is None:
        config_path = os.environ.get("PG_MCP_CONFIG")

    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        if not isinstance(raw_config, dict):
            raise ValueError(f"Invalid config file format: expected dict, got {type(raw_config)}")

        # 展开环境变量
        config_dict = process_config_dict(raw_config)

        return AppConfig(**config_dict)

    # 从环境变量构建配置
    return _load_from_env()


def _load_from_env() -> AppConfig:
    """从环境变量构建配置

    环境变量格式：
    - PG_MCP_DATABASES__0__NAME=main
    - PG_MCP_DATABASES__0__HOST=localhost
    - PG_MCP_OPENAI__API_KEY=sk-xxx
    """
    # 收集所有 PG_MCP_ 开头的环境变量
    prefix = "PG_MCP_"
    env_vars = {
        k[len(prefix):]: v
        for k, v in os.environ.items()
        if k.startswith(prefix)
    }

    if not env_vars:
        raise ValueError(
            "No configuration found. Either set PG_MCP_CONFIG environment variable "
            "to point to a config file, or set PG_MCP_* environment variables."
        )

    # 构建配置字典
    config: dict[str, Any] = {}

    for key, value in env_vars.items():
        parts = key.lower().split("__")
        current = config

        for i, part in enumerate(parts[:-1]):
            # 检查是否是数组索引
            if part.isdigit():
                idx = int(part)
                parent_key = parts[i - 1] if i > 0 else None
                if parent_key and parent_key in current:
                    while len(current[parent_key]) <= idx:
                        current[parent_key].append({})
                    current = current[parent_key][idx]
                continue

            if part not in current:
                # 检查下一个部分是否是数字（数组）
                next_part = parts[i + 1] if i + 1 < len(parts) else None
                if next_part and next_part.isdigit():
                    current[part] = []
                else:
                    current[part] = {}
            current = current[part]

        # 设置最终值
        final_key = parts[-1]
        if not final_key.isdigit():
            current[final_key] = value

    return AppConfig(**config)
