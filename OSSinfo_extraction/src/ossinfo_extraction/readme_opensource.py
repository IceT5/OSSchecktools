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

from .logger import info, debug


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
        f.write("Copyright Notice(s):\n")

        if copyright_records:
            for copyright_text in copyright_records:
                # 清理每行并写入
                cleaned_text = copyright_text.strip()
                if cleaned_text:
                    f.write(f"{cleaned_text}\n")
        else:
            f.write("No copyright information found.\n")

        # 第三步：输出License信息（每个license重复）
        if license_records:
            for record in license_records:
                license_name = record.get("spdx_identifier", "Unknown")
                license_file_path = record.get("file", "")

                # 输出License名称
                f.write(f"License: {license_name}\n")

                # 输出Full License Text
                f.write("Full License Text:\n")

                # 尝试读取license文件内容
                license_content_found = False

                if license_file_path and root_path:
                    # 清理路径：去掉可能存在的扫描前缀目录
                    # scancode路径可能类似: json-develop.zip-extract/json-develop/LICENSES/xxx.txt
                    # 我们需要提取实际的相对路径部分
                    cleaned_license_path = _clean_license_path(license_file_path, root_path)

                    # 尝试多种路径组合
                    possible_paths = _get_possible_license_paths(root_path, cleaned_license_path)

                    for full_license_path in possible_paths:
                        debug(f"Trying license file path: {full_license_path}")
                        if full_license_path.exists() and full_license_path.is_file():
                            try:
                                with full_license_path.open("r", encoding="utf-8", errors="replace") as lf:
                                    license_content = lf.read()
                                    f.write(license_content)
                                    if not license_content.endswith("\n"):
                                        f.write("\n")
                                    f.write("\n")  # 添加空行，改善多个license时的阅读体验
                                    license_content_found = True
                                    debug(f"Successfully read license file: {full_license_path}")
                                    break
                            except Exception as e:
                                debug(f"Failed to read license file {full_license_path}: {e}")
                        else:
                            debug(f"Path does not exist or is not a file: {full_license_path}")

                # 如果文件读取失败，尝试使用matched_text
                if not license_content_found:
                    matched_text = record.get("matched_text", "")
                    if matched_text:
                        f.write(matched_text)
                        if not matched_text.endswith("\n"):
                            f.write("\n")
                        f.write("\n")  # 添加空行，改善多个license时的阅读体验
                    else:
                        f.write("[No license text available]\n")
                        f.write("\n")  # 添加空行，改善多个license时的阅读体验
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
            return "/".join(path_parts[i+1:])

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
