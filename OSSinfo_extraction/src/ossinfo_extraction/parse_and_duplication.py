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

from pathlib import Path

from .logger import info
from .config import COPYRIGHT_IGNORED_SUFFIXES

def extract_and_duplicate_copyright(
    data: dict,
    output_txt: Path,
) -> list:
    """
    从scancode结果中提取copyright信息并写入文件。

    Args:
        data: scancode输出的JSON数据（已解析的字典）
        output_txt: 输出文件路径

    Returns:
        list: 提取的copyright记录列表
    """

    unique_records = set()
    duplicated_results = []

    for file_info in data.get("files", []):
        file_path = file_info.get("path", "")
        suffix = Path(file_path).suffix.lower()

        if suffix in COPYRIGHT_IGNORED_SUFFIXES:
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

    info(f"Extracted {len(duplicated_results)} unique records")
    info(f"Output written to {output_txt}")

    return duplicated_results
