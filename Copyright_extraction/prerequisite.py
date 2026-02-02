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

def check_scancode_available():
    """
    Check whether scancode command is available.
    """
    try:
        result = subprocess.run(["scancode","--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        raise RuntimeError(
            "scancode command not found.\n"
            "Please install dependencies first:\n"
            " pip install -r requirements.txt\n"
            "or\n"
            " pip install ."
        )
    
    if result.returncode != 0:
        raise RuntimeError(
            "scancode command exists but is not working properly.\n"
            f"stderr: {result.stderr}"
        )

    print(f"[OK] Scancode available: {result.stdout.strip()}")