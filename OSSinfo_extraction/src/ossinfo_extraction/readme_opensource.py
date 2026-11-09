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

"""
Readme.opensource 文件生成模块

生成格式示例：
    Software: 软件名称 版本号
    Copyright Notice(s):
    copyright信息1
    copyright信息2
    ...
    License: MIT
    Full License Text:
    MIT License内容...
    License: Apache-2.0
    Full License Text:
    Apache License内容...
"""

from pathlib import Path
from typing import List, Dict, Any

import chardet

from .logger import info, debug

# chardet判定为这些多字节编码且严格解码成功时，解码结果才视为可信；
# 单字节猜测编码（latin-1/windows-125x/koi8等）对任意字节总能"严格
# 成功"，不代表编码判断正确（GBK字节被判成Windows-1252时中文已乱码），
# 调用方（如license重扫）不应据此覆盖第一遍结果。
_TRUSTED_MULTIBYTE_ENCODINGS = {
    "gb2312",
    "gbk",
    "gb18030",
    "big5",
    "big5-hkscs",
    "euc-jp",
    "shift-jis",
    "iso-2022-jp",
    "euc-kr",
    "uhc",
    "johab",
    "utf-16",
    "utf-16be",
    "utf-16le",
    "utf-32",
    "utf-32be",
    "utf-32le",
}


def _is_trusted_decoding(encoding: str) -> bool:
    """判断chardet识别出的编码是否足以信任解码结果。"""
    return encoding.lower().replace("_", "-") in _TRUSTED_MULTIBYTE_ENCODINGS


def _decode_license_text_with_status(raw: bytes):
    """
    解码license文件内容，并返回解码是否精确。

    Returns:
        tuple[str, bool]: (解码文本, 解码结果是否可信)。替换解码、或
        chardet仅给出单字节猜测编码（对任意字节都能"严格成功"，不代表
        编码正确）时为False，调用方据此判断能否信任该文本（例如重扫
        license）。
    """
    text = None
    exact = False
    # 无BOM的UTF-16字节常含NUL，此时跳过UTF-8快路径
    if b"\x00" not in raw:
        try:
            text = raw.decode("utf-8-sig")
            exact = True
        except UnicodeDecodeError:
            pass

    if text is None:
        detected = chardet.detect(raw).get("encoding") or "utf-8"
        candidates = [detected]
        if detected.lower() in ("gb2312", "gbk"):
            candidates.append("gb18030")

        # 记录最后一个可用的编码，严格解码失败时用它做替换解码，
        # 避免整份非UTF-8文件被当作UTF-8而全部变成替换符
        last_valid = "utf-8"
        for encoding in candidates:
            try:
                text = raw.decode(encoding)
                exact = _is_trusted_decoding(encoding)
                break
            except UnicodeDecodeError:
                last_valid = encoding
            except LookupError:
                continue
        else:
            text = raw.decode(last_valid, errors="replace")
            exact = False

    return text.replace("\r\n", "\n").replace("\r", "\n"), exact


def _decode_license_text(raw: bytes) -> str:
    """
    自动识别license文件编码并解码。

    优先按UTF-8（含BOM）严格解码，避免chardet把以ASCII为主、仅含少量
    非ASCII字符的UTF-8文本误判为Latin-1/Windows-1252。UTF-8快路径未成功
    （解码失败或内容含NUL）时交给chardet识别；GB2312/GBK结果再尝试其超集
    GB18030。全部严格解码失败时，用最后识别到的编码做替换解码，尽量保留
    可读内容，最后退回UTF-8替换模式。解码后统一换行为LF。

    已知限制：无BOM的UTF-16、极短的GBK扩展字文本可能被chardet误判。

    Args:
        raw: license文件原始字节

    Returns:
        str: 解码并统一换行后的文本
    """
    return _decode_license_text_with_status(raw)[0]


def _read_license_text(full_license_path: Path):
    """
    读取license文件全文。

    Args:
        full_license_path: license文件完整路径

    Returns:
        str或None: 文件全文；读取失败时返回None
    """
    try:
        return _decode_license_text(full_license_path.read_bytes())
    except Exception as e:
        debug(f"Failed to read license file {full_license_path}: {e}")
        return None


def _write_license_file_content(f, license_file_path: str, root_path: Path) -> bool:
    """
    尝试从root_path读取license文件全文并写入。

    Args:
        f: 已打开的输出文件对象
        license_file_path: license文件相对路径
        root_path: 项目根目录路径

    Returns:
        bool: 是否成功读取并写入了license文件内容
    """
    license_content_found = False
    if not (license_file_path and root_path):
        return license_content_found

    # 清理路径：去掉可能存在的扫描前缀目录
    # scancode路径可能类似: json-develop.zip-extract/json-develop/LICENSES/xxx.txt
    # 我们需要提取实际的相对路径部分
    cleaned_license_path = _clean_license_path(license_file_path, root_path)

    # 尝试多种路径组合
    possible_paths = _get_possible_license_paths(root_path, cleaned_license_path)

    for full_license_path in possible_paths:
        debug(f"Trying license file path: {full_license_path}")
        if not (full_license_path.exists() and full_license_path.is_file()):
            debug(f"Path does not exist or is not a file: {full_license_path}")
            continue
        license_content = _read_license_text(full_license_path)
        if license_content is None:
            continue
        f.write(license_content)
        if not license_content.endswith("\n"):
            f.write("\n")
        f.write("\n")  # 添加空行，改善多个license时的阅读体验
        license_content_found = True
        debug(f"Successfully read license file: {full_license_path}")
        break

    return license_content_found


def _write_license_record(f, record: Dict[str, Any], root_path: Path) -> None:
    """
    写入单条license记录（License名称 + Full License Text）。

    优先读取license文件全文；读取失败时回退使用matched_text。

    Args:
        f: 已打开的输出文件对象
        record: license记录
        root_path: 项目根目录路径（用于读取license文件内容）
    """
    license_name = record.get("spdx_identifier", "Unknown")
    license_file_path = record.get("file", "")

    # 输出License名称
    f.write(f"License: {license_name}\n")

    # 输出Full License Text
    f.write("Full License Text:\n")

    # 尝试读取license文件内容
    if _write_license_file_content(f, license_file_path, root_path):
        return

    # 如果文件读取失败，尝试使用matched_text
    matched_text = record.get("matched_text", "")
    if matched_text:
        f.write(matched_text)
        if not matched_text.endswith("\n"):
            f.write("\n")
        f.write("\n")  # 添加空行，改善多个license时的阅读体验
    else:
        f.write("[No license text available]\n")
        f.write("\n")  # 添加空行，改善多个license时的阅读体验


def _write_copyright_section(f, copyright_records: List[str]) -> None:
    """
    写入Copyright Notice(s)段落。

    Args:
        f: 已打开的输出文件对象
        copyright_records: copyright记录列表
    """
    f.write("Copyright Notice(s):\n")
    if not copyright_records:
        f.write("No copyright information found.\n")
        return
    for copyright_text in copyright_records:
        cleaned_text = copyright_text.strip()
        if cleaned_text:
            f.write(f"{cleaned_text}\n")


def write_readme_opensource(
    output_path: Path,
    software_name: str,
    software_version: str,
    copyright_records: List[str],
    license_records: List[Dict[str, Any]],
    root_path: Path,
) -> None:
    """
    生成Readme.opensource文件。

    文件格式：
    - Software: 软件名称 版本号
    - Copyright Notice(s):
    - [copyright信息列表]
    - License: License名称
    - Full License Text:
    - [license文件内容]
    - （多个license重复上述两步）

    Args:
        output_path: 输出文件路径
        software_name: 软件名称
        software_version: 软件版本
        copyright_records: copyright记录列表
        license_records: license记录列表，每项包含：
            - file: license文件路径
            - spdx_identifier: license SPDX标识
            - license_expression: license表达式
            - matched_text: 匹配文本（可选）
        root_path: 项目根目录路径（用于读取license文件内容）
    """
    with output_path.open("w", encoding="utf-8") as f:
        # 第一步：输出软件名称和版本
        f.write(f"Software: {software_name} {software_version}\n")

        # 第二步：输出Copyright Notice(s)
        _write_copyright_section(f, copyright_records)

        # 第三步：输出License信息（每个license重复）
        if license_records:
            for record in license_records:
                _write_license_record(f, record, root_path)
        else:
            f.write("License: No license information found.\n")
            f.write("Full License Text:\n")
            f.write("[No license text available]\n")

    info(f"Readme.opensource written to {output_path}")


def _clean_license_path(license_file_path: str, root_path: Path) -> str:
    """
    清理license文件路径，移除扫描前缀目录。

    路径标准化处理：
    1. 统一使用正斜杠作为路径分隔符
    2. 移除解压根目录前缀

    Args:
        license_file_path: 原始license文件路径
        root_path: 根目录路径

    Returns:
        str: 清理后的相对路径
    """
    # 标准化路径分隔符（统一使用正斜杠）
    normalized_path = license_file_path.replace("\\", "/")
    path_parts = normalized_path.split("/")

    # 过滤空部分
    path_parts = [p for p in path_parts if p]

    if not path_parts:
        return ""

    # 获取root_path的标准化名称（用于匹配）
    root_name = root_path.name

    # 尝试找到root_path名称在路径中的位置
    for i, part in enumerate(path_parts):
        if part == root_name:
            # 返回该位置之后的路径
            return "/".join(path_parts[i + 1 :])

    # 如果没找到，尝试查找常见的解压目录模式
    start_idx = 0
    for i, part in enumerate(path_parts):
        # 跳过 xxx-extract 这类目录
        if "-extract" in part.lower():
            start_idx = i + 1
            continue

    # 返回清理后的路径
    return "/".join(path_parts[start_idx:])


def _get_possible_license_paths(root_path: Path, relative_path: str) -> List[Path]:
    """
    生成可能的license文件完整路径列表。

    匹配规则（按优先级）：
    1. 直接拼接路径
    2. 处理嵌套目录结构（根目录只有一个子目录的情况）

    注意：不做递归查找，避免误匹配其他目录下的同名文件

    Args:
        root_path: 根目录路径
        relative_path: 相对路径

    Returns:
        List[Path]: 可能的完整路径列表
    """
    possible_paths = []

    # 1. 直接拼接
    possible_paths.append(root_path / relative_path)

    # 2. 检查是否是嵌套目录结构
    try:
        items = list(root_path.iterdir())
        if len(items) == 1 and items[0].is_dir():
            possible_paths.append(items[0] / relative_path)
    except Exception:
        pass

    # 注意：移除了递归查找逻辑，避免误匹配
    # 例如：避免将 docs/LICENSE 或 third_party/lib/LICENSE 误匹配为根目录的 LICENSE

    return possible_paths
