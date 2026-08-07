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
import subprocess
from pathlib import Path

from .logger import info, warn, cmd as log_cmd


def run_scancode(scan_target: Path, result_json: Path, jobs: int = 4, scan_license: bool = False, max_in_memory: int = 2000):
    """
    Run ScanCode Toolkit.

    直接调用 scancode 命令进行扫描。

    Args:
        scan_target: 要扫描的目标路径
        result_json: 输出JSON文件路径
        jobs: 并行任务数
        scan_license: 是否扫描license信息
        max_in_memory: 内存中缓存的文件扫描详情数量

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
