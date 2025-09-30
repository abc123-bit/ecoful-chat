"""
日志工具模块
"""
import logging
import os
from pathlib import Path
from loguru import logger
import sys


class Logger:
    """日志工具类"""

    def __init__(self, config=None):
        """
        初始化日志工具

        Args:
            config (dict, optional): 日志配置
        """
        # 移除默认的日志处理器
        logger.remove()

        # 默认配置
        self.config = {
            "level": "INFO",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
            "file": "./logs/system.log"
        }

        # 更新配置
        if config:
            self.config.update(config)

        # 确保日志目录存在
        log_file = Path(self.config["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 添加文件日志处理器
        logger.add(
            self.config["file"],
            level=self.config["level"],
            format=self.config["format"],
            rotation="100 MB",
            retention="30 days",
            compression="zip"
        )

        # 添加控制台日志处理器
        logger.add(
            sys.stdout,
            level=self.config["level"],
            format=self.config["format"]
        )

    def debug(self, message):
        """记录调试信息"""
        logger.debug(message)

    def info(self, message):
        """记录一般信息"""
        logger.info(message)

    def warning(self, message):
        """记录警告信息"""
        logger.warning(message)

    def error(self, message):
        """记录错误信息"""
        logger.error(message)

    def critical(self, message):
        """记录严重错误信息"""
        logger.critical(message)


# 创建全局日志实例
log_manager = None


def get_logger(config=None):
    """
    获取日志管理器实例

    Args:
        config (dict, optional): 日志配置

    Returns:
        Logger: 日志管理器实例
    """
    global log_manager
    if log_manager is None:
        log_manager = Logger(config)
    return log_manager


def debug(message):
    """记录调试信息"""
    get_logger().debug(message)


def info(message):
    """记录一般信息"""
    get_logger().info(message)


def warning(message):
    """记录警告信息"""
    get_logger().warning(message)


def error(message):
    """记录错误信息"""
    get_logger().error(message)


def critical(message):
    """记录严重错误信息"""
    get_logger().critical(message)