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

import os
import shutil
import tempfile
import sys
import subprocess
from pathlib import Path

def run_extractcode(target: str) -> Path:
    """
    When target is an archive, execute this function.
    Run extractcode --shallow.
    extractcode will create <archive_name>-extract directory automatically.
    """
    archive = Path(target).resolve()

    custom_tmp = Path(tempfile.mkdtemp(prefix="scancode_tmp_", dir=str(archive.parent)))
    env = os.environ.copy()
    env['TMP'] = str(custom_tmp)
    env['TEMP'] = str(custom_tmp)

    cmd = [
        "extractcode",
        "--shallow",
        str(archive),
    ]

    print("Running extractcode:")
    print(" ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"extractcode failed with exit code {result.returncode}")

    extract_dir = archive.parent / f"{archive.name}-extract"

    if not extract_dir.exists():
        raise RuntimeError(
            f"Expected extract directory not found: {extract_dir}"
        )
    
    shutil.rmtree(custom_tmp)
    return extract_dir
