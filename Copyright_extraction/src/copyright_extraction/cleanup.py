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

import shutil
from pathlib import Path

def cleanup_extract_dir(extract_dir: Path):
    """
    Safety delete extractcode path, if target is not archive, skip this function
    """
    if not extract_dir.exists():
        print(f"[INFO] Extracted directory not found, skip cleanup: {extract_dir}")
        return

    if not extract_dir.is_dir():
        print(f"[WARN] Path is not a directory, skip cleanup: {extract_dir}")
        return

    # 额外安全校验：目录名必须以 -extract 结尾
    if not extract_dir.name.endswith("-extract"):
        print(f"[WARN] Directory name does not end with '-extract', skip cleanup: {extract_dir}")
        return

    try:
        shutil.rmtree(extract_dir)
        print(f"[OK] Cleaned up extracted directory: {extract_dir}")
    except Exception as e:
        print(f"[WARN] Failed to cleanup extracted directory: {extract_dir}")
        print(f"       Reason: {e}")
