"""
日志配置模块
"""

import logging
import sys
from typing import Optional
from ..config import get_config


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    enable_console: bool = True
) -> logging.Logger:
    """
    设置日志配置
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 日志格式
        enable_console: 是否启用控制台输出
    
    Returns:
        配置好的logger实例
    """
    config = get_config()
    
    # 确定日志级别
    if log_level is None:
        log_level = config.log_level
    
    # 设置日志格式
    if log_format is None:
        if config.debug:
            log_format = (
                '%(asctime)s - %(name)s - %(levelname)s - '
                '%(filename)s:%(lineno)d - %(funcName)s - %(message)s'
            )
        else:
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 创建根logger
    logger = logging.getLogger('enhanced_lineage_agent')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有的handlers
    logger.handlers.clear()
    
    # 添加控制台handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 防止重复日志
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger
    
    Args:
        name: logger名称
    
    Returns:
        logger实例
    """
    return logging.getLogger(f'enhanced_lineage_agent.{name}')


class ContextualLogger:
    """
    上下文感知的日志记录器
    """
    
    def __init__(self, logger: logging.Logger, context_id: Optional[str] = None):
        self.logger = logger
        self.context_id = context_id
    
    def _format_message(self, message: str) -> str:
        """格式化消息，添加上下文信息"""
        if self.context_id:
            return f"[{self.context_id}] {message}"
        return message
    
    def debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        self.logger.debug(self._format_message(message), **kwargs)
    
    def info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        self.logger.info(self._format_message(message), **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        self.logger.warning(self._format_message(message), **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录ERROR级别日志"""
        self.logger.error(self._format_message(message), **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录CRITICAL级别日志"""
        self.logger.critical(self._format_message(message), **kwargs)
    
    def exception(self, message: str, **kwargs):
        """记录异常信息"""
        self.logger.exception(self._format_message(message), **kwargs)


def get_contextual_logger(name: str, context_id: Optional[str] = None) -> ContextualLogger:
    """
    获取上下文感知的logger
    
    Args:
        name: logger名称
        context_id: 上下文ID
    
    Returns:
        ContextualLogger实例
    """
    logger = get_logger(name)
    return ContextualLogger(logger, context_id)