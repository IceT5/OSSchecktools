# Copyright (c) 2026 IceT5. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
统一日志模块

提供统一的日志输出格式:
- [INFO] 普通信息
- [OK] 成功信息
- [WARN] 警告信息
- [ERROR] 错误信息
- [DEBUG] 调试信息 (默认隐藏)
- [CMD] 命令信息

日志级别控制:
- DEBUG: 显示所有日志 (包括DEBUG)
- INFO: 显示 INFO, OK, WARN, ERROR (默认)
- QUIET: 只显示 ERROR
"""

import os
import sys

# 日志级别常量
DEBUG = 0
INFO = 1
QUIET = 2

# 默认日志级别 (可通过环境变量 LOG_LEVEL 控制)
# DEBUG=0 显示所有, INFO=1 显示常规日志, QUIET=2 只显示错误
_log_level = INFO

# 错误计数器
_error_count = 0

# 清理回调函数（在main.py中注册）
_cleanup_callback = None

# 软件信息（在main.py中设置）
_software_name = ""
_software_version = ""


def register_cleanup_callback(callback) -> None:
    """
    注册清理回调函数。
    
    Args:
        callback: 清理函数，无参数，在error退出时调用
    """
    global _cleanup_callback
    _cleanup_callback = callback


def set_software_info(name: str, version: str) -> None:
    """
    设置软件名称和版本信息。
    
    Args:
        name: 软件名称
        version: 软件版本
    """
    global _software_name, _software_version
    _software_name = name
    _software_version = version


def set_log_level(level: int) -> None:
    """
    设置日志级别。
    
    Args:
        level: 日志级别常量 (DEBUG, INFO, QUIET)
    """
    global _log_level
    _log_level = level


def get_log_level() -> int:
    """
    获取当前日志级别。
    
    Returns:
        int: 当前日志级别
    """
    return _log_level


def _init_log_level() -> None:
    """从环境变量初始化日志级别"""
    global _log_level
    env_level = os.environ.get("LOG_LEVEL", "").upper()
    if env_level == "DEBUG":
        _log_level = DEBUG
    elif env_level == "QUIET":
        _log_level = QUIET
    else:
        _log_level = INFO


# 初始化日志级别
_init_log_level()


def info(message: str) -> None:
    """输出普通信息日志"""
    if _log_level <= INFO:
        print(f"[INFO] {message}")


def ok(message: str) -> None:
    """输出成功信息日志"""
    if _log_level <= INFO:
        print(f"[OK] {message}")


def warn(message: str) -> None:
    """输出警告信息日志"""
    if _log_level <= INFO:
        print(f"[WARN] {message}")


def error(message: str) -> None:
    """输出错误信息日志"""
    global _error_count
    _error_count += 1
    # ERROR始终显示
    print(f"[ERROR] {message}")


def error_exit(message: str, exit_code: int = 1) -> None:
    """
    输出错误日志并立即退出程序。
    
    如果注册了清理回调函数，会在退出前执行清理。
    
    Args:
        message: 错误信息
        exit_code: 退出码，默认为1
    """
    global _error_count
    _error_count += 1
    print(f"[ERROR] {message}")
    
    # 输出包含软件名称和版本的失败提示
    if _software_name and _software_version:
        print(f"[ERROR] {_software_name} {_software_version} Readme.opensource生成失败，请修改完成后重新执行")
        print(f"[ERROR] {_software_name} {_software_version} Readme.opensource generation failed. Please fix the issue and try again.")
    else:
        print(f"[ERROR] Readme.opensource生成失败，请修改完成后重新执行")
        print(f"[ERROR] Readme.opensource generation failed. Please fix the issue and try again.")
    
    # 执行清理回调
    if _cleanup_callback is not None:
        try:
            _cleanup_callback()
        except Exception as e:
            print(f"[ERROR] Cleanup failed: {e}")
    
    sys.exit(exit_code)


def has_error() -> bool:
    """
    检查是否有过错误日志。
    
    Returns:
        bool: 是否有过错误
    """
    return _error_count > 0


def reset_error_count() -> None:
    """重置错误计数器"""
    global _error_count
    _error_count = 0


def debug(message: str) -> None:
    """输出调试信息日志 (默认隐藏)"""
    if _log_level <= DEBUG:
        print(f"[DEBUG] {message}")


def cmd(command: str) -> None:
    """输出命令信息日志"""
    if _log_level <= DEBUG:
        print(f"[CMD] {command}")