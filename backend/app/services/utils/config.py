"""
配置管理工具模块
"""
import yaml
import os
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器类"""

    def __init__(self, config_file: str = "./utils/config.yaml"):
        """
        初始化配置管理器

        Args:
            config_file (str): 配置文件路径
        """
        self.config_file = config_file
        self.config_data = {}
        self.load_config()

    def load_config(self):
        """
        加载配置文件
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self.config_data = {}
        else:
            print(f"配置文件不存在: {self.config_file}")
            self.config_data = {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项的值

        Args:
            key_path (str): 配置项路径，使用点号分隔，如 "database.url"
            default (Any): 默认值

        Returns:
            Any: 配置项的值
        """
        keys = key_path.split('.')
        value = self.config_data

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any):
        """
        设置配置项的值

        Args:
            key_path (str): 配置项路径，使用点号分隔，如 "database.url"
            value (Any): 要设置的值
        """
        keys = key_path.split('.')
        config = self.config_data

        # 遍历到倒数第二个键，创建必要的嵌套字典
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # 设置最后一个键的值
        config[keys[-1]] = value

    def save_config(self):
        """
        保存配置到文件
        """
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if config_dir:  # 只有当目录路径不为空时才创建目录
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def reload_config(self):
        """
        重新加载配置文件
        """
        self.load_config()

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置

        Returns:
            Dict[str, Any]: 所有配置数据
        """
        return self.config_data.copy()


# 全局配置管理器实例
config_manager = None


def get_config_manager(config_file: str = "./utils/config.yaml") -> ConfigManager:
    """
    获取配置管理器实例

    Args:
        config_file (str): 配置文件路径

    Returns:
        ConfigManager: 配置管理器实例
    """
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager(config_file)
    return config_manager


def get_config(key_path: str, default: Any = None) -> Any:
    """
    获取配置项的值

    Args:
        key_path (str): 配置项路径，使用点号分隔，如 "database.url"
        default (Any): 默认值

    Returns:
        Any: 配置项的值
    """
    return get_config_manager().get(key_path, default)


def set_config(key_path: str, value: Any):
    """
    设置配置项的值

    Args:
        key_path (str): 配置项路径，使用点号分隔，如 "database.url"
        value (Any): 要设置的值
    """
    get_config_manager().set(key_path, value)


def save_config():
    """
    保存配置到文件
    """
    get_config_manager().save_config()