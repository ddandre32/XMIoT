# -*- coding: utf-8 -*-
"""
小米IoT CLI工具 - 符合CLI设计规范

设计特性:
- 双用户兼容: TTY环境（人类）默认table，非TTY（Agent）默认json
- 统一JSON输出格式: {success, data/error, timestamp}
- 标准化错误码: 包含code, message, suggestion
- 配置层级: 命令行 > 环境变量 > 配置文件 > 默认
- 管道友好: 支持Unix管道，输出到stdout，错误到stderr

原子能力分类:
- 内容发现: device list, scene list, scene search
- 内容获取: device get, device spec
- 内容处理: device prop get/set, device action, scene run
- 内容导出: 所有命令支持--format/--json选项
"""

__version__ = "1.0.0"

# 导出核心类型和函数
from .formatter import (
    ErrorCode,
    OutputFormat,
    format_output,
    get_default_format,
    is_tty,
    print_error,
    print_success,
    ProgressReporter,
    with_progress,
)
from .config import CLIConfig

__all__ = [
    "ErrorCode",
    "OutputFormat",
    "format_output",
    "get_default_format",
    "is_tty",
    "print_error",
    "print_success",
    "ProgressReporter",
    "with_progress",
    "CLIConfig",
]
