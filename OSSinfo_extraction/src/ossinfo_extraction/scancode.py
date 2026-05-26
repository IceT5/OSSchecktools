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

import sys
import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .logger import info, warn, cmd as log_cmd


def _is_binary_file(fpath: str) -> bool:
    """
    检查文件是否为二进制文件（应跳过扫描）。
    
    读取文件前 8000 字节，如果包含 NUL 字节（\\x00）则判定为二进制文件。
    这是 git 用来区分文本和二进制文件的标准方法。
    二进制文件不包含 license/copyright 文本，跳过扫描不影响结果。
    
    Args:
        fpath: 文件路径字符串
    
    Returns:
        bool: 是否应跳过该文件
    """
    try:
        with open(fpath, "rb") as f:
            chunk = f.read(8000)
            return b"\x00" in chunk
    except (OSError, IOError):
        return True


def _collect_and_detect_binary(scan_target: Path, workers: int = 8) -> tuple:
    """
    使用 os.walk 快速遍历 + 多线程并行检测二进制文件。
    
    os.walk 比 Path.rglob 快 4 倍以上，ThreadPoolExecutor 并行检测
    将 118K 文件的检测时间从 10+ 分钟降到 ~4 分钟。
    
    Args:
        scan_target: 扫描目标路径
        workers: 并行线程数
    
    Returns:
        tuple: (binary_files set, text_files set, binary_count, text_count)
        其中 binary_files 和 text_files 存储相对路径字符串
    """
    # Phase 1: os.walk 快速收集所有文件路径
    all_files = []
    for dirpath, _, filenames in os.walk(str(scan_target)):
        for fname in filenames:
            all_files.append(os.path.join(dirpath, fname))
    
    info(f"Collected {len(all_files)} files for binary detection")
    
    # Phase 2: 多线程并行检测
    binary_set = set()
    text_set = set()
    
    def check_and_classify(fpath):
        rel = os.path.relpath(fpath, str(scan_target))
        if _is_binary_file(fpath):
            return (rel, True)
        return (rel, False)
    
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(check_and_classify, all_files)
    
    binary_count = 0
    text_count = 0
    for rel_path, is_binary in results:
        if is_binary:
            binary_set.add(rel_path)
            binary_count += 1
        else:
            text_set.add(rel_path)
            text_count += 1
    
    info(f"Binary detection done: {binary_count} binary, {text_count} text files")
    return binary_set, text_set, binary_count, text_count


def _create_text_only_scan_dir(scan_target: Path, workers: int = 8) -> Path:
    """
    创建只包含文本文件的临时扫描目录。
    
    使用多线程并行检测二进制文件，排除后将文本文件拷贝到临时目录，
    保持原有目录结构。
    
    Args:
        scan_target: 原始扫描目标路径
        workers: 二进制检测的并行线程数
    
    Returns:
        Path: 只包含文本文件的临时目录路径
    """
    text_dir = Path(tempfile.mkdtemp(prefix="ossinfo_text_"))
    
    binary_set, _, binary_count, text_count = _collect_and_detect_binary(scan_target, workers)
    
    # 拷贝文本文件到临时目录
    scan_target_str = str(scan_target)
    for dirpath, dirnames, filenames in os.walk(scan_target_str):
        for fname in filenames:
            src_fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(src_fpath, scan_target_str)
            if rel in binary_set:
                continue
            dst_fpath = os.path.join(str(text_dir), rel)
            os.makedirs(os.path.dirname(dst_fpath), exist_ok=True)
            shutil.copy2(src_fpath, dst_fpath)
    
    info(f"Binary files skipped: {binary_count}, text files copied: {text_count}")
    return text_dir


def cleanup_text_dir(text_dir: Path) -> None:
    """
    清理临时文本文件目录。
    
    Args:
        text_dir: 临时目录路径
    """
    if text_dir and text_dir.exists():
        try:
            shutil.rmtree(text_dir)
        except OSError:
            pass


def run_scancode(scan_target: Path, result_json: Path, jobs: int = 4, scan_license: bool = False, max_in_memory: int = 2000, timeout: int = 60):
    """
    Run ScanCode Toolkit.
    
    直接调用 scancode 命令进行扫描。
    
    Args:
        scan_target: 要扫描的目标路径
        result_json: 输出JSON文件路径
        jobs: 并行任务数
        scan_license: 是否扫描license信息
        max_in_memory: 内存中缓存的文件扫描详情数量
        timeout: 单文件扫描超时时间（秒），超时文件将被跳过
    
    Returns:
        dict: 解析后的ScanCode JSON结果数据
    
    Raises:
        RuntimeError: ScanCode执行失败且无法生成有效结果
    """
    cmd = [
        "scancode",
        "-c",  # 扫描copyright
        "--only-findings",
        "--json-pp",
        str(result_json),
        str(scan_target),
        "-n",
        str(jobs),
        "--max-in-memory",
        str(max_in_memory),
        "--timeout",
        str(timeout),
    ]
    
    # 添加license扫描参数
    if scan_license:
        cmd.insert(1, "-l")  # 扫描license

    info("Running scancode:")
    log_cmd(" ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if result.returncode != 0:
        # ScanCode返回非零退出码，尝试读取已生成的结果文件
        if result_json.exists():
            try:
                with result_json.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                file_count = len(data.get("files", []))
                if file_count > 0:
                    warn(f"ScanCode reported errors (exit code {result.returncode}), "
                         f"but produced valid results with {file_count} files scanned. Continuing.")
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        
        raise RuntimeError(f"ScanCode failed with exit code {result.returncode}")
    
    # 正常退出，读取结果
    with result_json.open("r", encoding="utf-8") as f:
        return json.load(f)