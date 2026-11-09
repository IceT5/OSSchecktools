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

import re
import unicodedata
from pathlib import Path

from .logger import info
from .config import COPYRIGHT_IGNORED_SUFFIXES

_COPYRIGHT_MARKER = re.compile(r"(?i)\(c\)|©|copr\.?")
# 版权特征：对齐ScanCode 32.5.0 COPYRIGHT词元的全部关键字变体
# （copyright/Copyrighy/Copyirght/Cppyright/(c)opy*/opy*/copr），外加
# (c)/©标记、中文"版权/著作"和年份。不含任何特征的普通语句不应按
# 版权输出；ScanCode可检出的声明必然含其一。
_COPYRIGHT_FEATURE = re.compile(
    r"(?i)copyr(ight|ighy|irght)|cppyright|opyr|opyl|copr\.?"
    r"|\(c\)|©|版权|著作|(?:19|20)\d{2}"
)


def _has_meaningful_letters(text: str, minimum: int = 2) -> bool:
    """
    判断文本中是否至少包含 minimum 个Unicode字母。

    使用 unicodedata 的字母类别（L*）计数，覆盖拉丁、中日韩、西里尔、
    希腊、阿拉伯、泰、印地等文字；数字、空白、标点和组合符号不计入。
    """
    count = 0
    for char in text:
        if unicodedata.category(char).startswith("L"):
            count += 1
            if count >= minimum:
                return True
    return False


def _is_meaningful_copyright(value: str) -> bool:
    """
    判断ScanCode检出的copyright是否像有效声明。

    ScanCode的copyright检测基于文本行解析，不区分代码、注释和字符串，
    可能把C宏中的 ``(c) == L`` 误识别为 ``(c) (c) L``。先要求文本具备
    版权特征（copyright关键字、(c)/©/copr.标记、中文"版权/著作"、年份），
    不具备的直接排除，避免普通语句仅凭含2个字母就被当作版权声明；
    含copyright单词的声明直接保留；否则去掉(c)/©/copr.标记后，要求至少
    2个Unicode字母，过滤掉只有单字母、数字或纯符号的明显噪声。
    """
    if not _COPYRIGHT_FEATURE.search(value):
        return False
    if re.search(r"(?i)copyright", value):
        return True
    remainder = _COPYRIGHT_MARKER.sub(" ", value)
    return _has_meaningful_letters(remainder)


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
            value = copyright_info.get("copyright") or copyright_info.get("statement")
            if not value:
                continue

            value_stripped = value.strip()

            if not value_stripped:
                continue

            if not _is_meaningful_copyright(value_stripped):
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
