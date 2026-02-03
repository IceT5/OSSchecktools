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

import json
from pathlib import Path

def extract_and_duplicate_copyright(
    result_json: Path,
    output_txt: Path,
):
    ignored_suffixes = {
        ".md",
        ".rst",
        ".txt",
        ".adoc",
        ".markdown",
    }
    with result_json.open("r", encoding="utf-8") as f:
        data = json.load(f)

    unique_records = set()
    duplicated_results = []

    for file_info in data.get("files", []):
        file_path = file_info.get("path", "")
        suffix = Path(file_path).suffix.lower()

        if suffix in ignored_suffixes:
            continue

        for copyright_info in file_info.get("copyrights", []):
            value = (
                copyright_info.get("copyright")
                or copyright_info.get("statement")
            )
            if not value:
                continue
            
            value_stripped = value.strip()

            if "copyright" not in value_stripped.lower():
                continue

            if value_stripped not in unique_records:
                unique_records.add(value_stripped)
                duplicated_results.append(value_stripped)

    with output_txt.open("w", encoding="utf-8") as f:
        for item in duplicated_results:
            f.write(item.strip() + "\n")

    print(f"Extracted {len(duplicated_results)} unique records")
    print(f"Output written to {output_txt}")

