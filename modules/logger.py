"""
日志记录模块
提供统一的日志记录功能，支持不同的日志级别和格式化输出
"""
import logging
import os
import sys
from datetime import datetime
import colorama

# 初始化彩色输出
colorama.init()

# 日志级别颜色
LEVEL_COLORS = {
    'DEBUG': colorama.Fore.CYAN,
    'INFO': colorama.Fore.GREEN,
    'WARNING': colorama.Fore.YELLOW,
    'ERROR': colorama.Fore.RED,
    'CRITICAL': colorama.Fore.RED + colorama.Style.BRIGHT
}

# 模块颜色
MODULE_COLOR = colorama.Fore.BLUE

# 重置颜色
RESET_COLOR = colorama.Style.RESET_ALL


class ColoredFormatter(logging.Formatter):
    """
    带颜色的日志格式化器
    """
    def format(self, record):
        # 获取级别颜色
        level_color = LEVEL_COLORS.get(record.levelname, '')
        
        # 格式化模块名称
        module = f"{MODULE_COLOR}[{record.module}]{RESET_COLOR}" if hasattr(record, 'module') else ""
        
        # 计算运行时间
        levelname = f"{level_color}{record.levelname}{RESET_COLOR}"
        
        # 组装最终日志消息
        record.levelname = levelname
        record.module_colored = module
        
        # 调用原始格式化方法
        return super().format(record)


def get_logger(name=None, log_file=None, log_level=logging.INFO):
    """
    获取一个配置好的日志记录器
    
    Args:
        name: 日志记录器名称，默认为root
        log_file: 日志文件路径，默认不记录到文件
        log_level: 日志级别，默认为INFO
        
    Returns:
        配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    
    # 如果已配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    logger.setLevel(log_level)
    
    # 创建并配置控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # 创建彩色格式化器
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s %(levelname)-8s %(module_colored)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 如果指定了日志文件，也记录到文件
    if log_file:
        # 确保日志目录存在
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        
        # 创建并配置文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # 文件中不使用彩色
        file_formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] [%(module)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# 创建默认日志记录器
logger = get_logger('tofu')


def debug(msg, *args, **kwargs):
    """DEBUG级别日志"""
    logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """INFO级别日志"""
    logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """WARNING级别日志"""
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """ERROR级别日志"""
    logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    """CRITICAL级别日志"""
    logger.critical(msg, *args, **kwargs)


def set_log_level(level):
    """设置日志级别"""
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def add_file_handler(log_file):
    """添加文件处理器"""
    # 确保日志目录存在
    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
    
    # 创建并配置文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logger.level)
    
    # 文件中不使用彩色
    file_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] [%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return file_handler 