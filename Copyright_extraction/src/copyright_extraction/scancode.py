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
import subprocess
from pathlib import Path

def run_scancode(scan_target: Path, result_json: Path, jobs: int = 8):
    """
    Run ScanCode Toolkit.
    """
    cmd = [
        "scancode",
        "-c",
        "--filter-clues",
        "--only-findings",
        "--json-pp",
        str(result_json),
        str(scan_target),
        "-n",
        str(jobs),
    ]

    print("[INFO] Running scancode:")
    print(" ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ScanCode failed with exit code {result.returncode}")
