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
import os
from pathlib import Path

from .prerequisite import check_scancode_available
from .extract import run_extractcode
from .scancode import run_scancode
from .parse_and_duplication import extract_and_duplicate_copyright
from .cleanup import cleanup_extract_dir



def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <target>")
        sys.exit(1)

    target = Path(sys.argv[1]).resolve()
    result_json = target.parent / "result.json"
    output_txt = target.parent / f"{target.name}_copyright"
    
    check_scancode_available()

    extract_dir = None
    scan_target = target

    try:
        if target.is_file():
            extract_dir = run_extractcode(target)
            scan_target = extract_dir
        
        run_scancode(scan_target, result_json)
        
        extract_and_duplicate_copyright(result_json, output_txt)

    except Exception as e:
        print("[ERROR] Pipeline failed, extracted directory will be kept for debugging.")
        print(e)
        raise

    else:
        if extract_dir:
            cleanup_extract_dir(extract_dir)
        os.remove(result_json)

if __name__ == "__main__":
    main()
    
