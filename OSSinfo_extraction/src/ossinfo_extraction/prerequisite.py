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

import subprocess

from .config import EXPECTED_SCANCODE_VERSION
from .logger import ok, warn


def check_scancode_available():
    """
    Check whether scancode command is available and check version.

    检查 scancode 命令是否可用，如果版本不匹配则告警但不阻止运行。
    """
    try:
        result = subprocess.run(
            ["scancode", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except FileNotFoundError:
        raise RuntimeError(
            "scancode command not found.\n"
            "Please install scancode-toolkit:\n"
            "  pip install scancode-toolkit==32.5.0"
        )

    version_output = result.stdout.strip()

    # 检查版本是否匹配，不匹配告警但不阻止运行
    if EXPECTED_SCANCODE_VERSION not in version_output:
        warn(
            f"scancode version mismatch: expected {EXPECTED_SCANCODE_VERSION}, "
            f"got {version_output}. This may cause unexpected behavior."
        )
    else:
        ok(f"Scancode available: {version_output}")
