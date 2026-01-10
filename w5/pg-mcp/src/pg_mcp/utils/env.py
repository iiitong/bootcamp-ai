import os


def get_env[T](key: str, default: T | None = None) -> str | T | None:
    """获取环境变量

    Args:
        key: 环境变量名
        default: 默认值

    Returns:
        环境变量值或默认值
    """
    return os.environ.get(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """获取布尔类型环境变量

    Args:
        key: 环境变量名
        default: 默认值

    Returns:
        布尔值（true/1/yes 为 True，其他为 False）
    """
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def get_env_int(key: str, default: int = 0) -> int:
    """获取整数类型环境变量

    Args:
        key: 环境变量名
        default: 默认值

    Returns:
        整数值

    Raises:
        ValueError: 如果值不能转换为整数
    """
    value = os.environ.get(key)
    if value is None:
        return default
    return int(value)


def get_env_float(key: str, default: float = 0.0) -> float:
    """获取浮点数类型环境变量

    Args:
        key: 环境变量名
        default: 默认值

    Returns:
        浮点数值

    Raises:
        ValueError: 如果值不能转换为浮点数
    """
    value = os.environ.get(key)
    if value is None:
        return default
    return float(value)


def require_env(key: str) -> str:
    """获取必需的环境变量

    Args:
        key: 环境变量名

    Returns:
        环境变量值

    Raises:
        EnvironmentError: 如果环境变量未设置
    """
    value = os.environ.get(key)
    if value is None:
        raise OSError(f"Required environment variable '{key}' is not set")
    return value
