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
from pathlib import Path
from typing import Set, List, Dict, Any, Optional

from .logger import info, ok, warn, error, debug, error_exit
from .config import LICENSE_FILE_PATTERNS, LICENSE_EXTENSIONS

# SPDX版本后缀文法：数字版本号 + 可选字母尾（如.3c）+ 可选SPDX限定符
# （only/or-later/with-例外名，均为SPDX规范定义的封闭集合）。
# 用于识别被误认为文件扩展名的版本限定符，
# 如 Apache-2.0 中的 ".0"、GPL-3.0-only 中的 ".0-only"、LPPL-1.3c 中的 ".3c"。
SPDX_VERSION_SUFFIX = re.compile(
    r"\.[0-9]+[a-z]?(?:-(?:only|or-later|with-[a-z0-9]+(?:-[a-z0-9]+)*))?$",
    re.IGNORECASE,
)


def _is_exact_license_keyword(stem: str) -> bool:
    """
    判断stem是否精确匹配license关键词（不带后缀修饰）。

    当stem精确匹配 license/copying/copyright 等关键词时，
    文件名中的后缀部分（如 COPYING.GPL2 中的 .GPL2）是license类型限定符，
    而非文件格式扩展名，因此应跳过扩展名白名单检查。

    例如：
    - COPYING.GPL2 → stem='copying' → True（.GPL2是license类型限定符）
    - COPYING.md   → stem='copying' → True（.md虽然也是扩展名，但不应阻止匹配）
    - license_1_0  → stem='license_1_0' → False（有后缀修饰，走正常扩展名检查）

    Args:
        stem: 文件名（不含扩展名）的小写形式

    Returns:
        bool: 是否是精确的license关键词
    """
    exact_keyword_patterns = [
        r"^license$",
        r"^copying$",
        r"^copyright$",
    ]
    for pattern in exact_keyword_patterns:
        if re.match(pattern, stem, re.IGNORECASE):
            return True
    return False


def is_license_file(filename: str) -> bool:
    """
    判断文件名是否是license相关文件。

    检查规则：
    1. 文件名（不含扩展名）必须匹配已知的license模式
    2. 扩展名必须在允许列表中，以下情况跳过此检查：
       - stem精确匹配license关键词（此时后缀是license类型限定符而非文件格式扩展名）
       - "扩展名"实为SPDX版本限定符后缀（如 Apache-2.0 的 .0、GPL-3.0-only 的 .0-only），
         此时用完整文件名重新匹配license模式确认

    注意：此函数仅检查文件名是否符合规范，不检查路径。
    对于LICENSES目录下命名不规范的文件，由_is_valid_license_path函数处理。

    Args:
        filename: 文件名（不含路径）

    Returns:
        bool: 是否是license文件
    """
    # 获取不含扩展名的文件名
    stem = Path(filename).stem.lower()
    ext = Path(filename).suffix.lower()

    # 检查文件名是否匹配license模式
    matched_pattern = None
    for pattern in LICENSE_FILE_PATTERNS:
        if re.match(pattern, stem, re.IGNORECASE):
            matched_pattern = pattern
            break

    if not matched_pattern:
        return False

    # 当stem精确匹配license关键词（如 COPYING.GPL2 中的 copying）时，
    # 后缀部分是license类型限定符而非文件格式扩展名，跳过扩展名检查
    if _is_exact_license_keyword(stem):
        return True

    # 其他情况：检查扩展名是否在允许列表中（空扩展名始终允许）
    if ext and ext not in LICENSE_EXTENSIONS:
        # 不在白名单的"扩展名"可能是SPDX版本限定符被误认为扩展名
        # （如 Apache-2.0 的 Path().suffix 是 ".0"），此时用完整文件名
        # 重新匹配license模式确认；其余扩展名仍然拒绝
        if SPDX_VERSION_SUFFIX.fullmatch(ext):
            full_name = filename.lower()
            if not any(re.match(p, full_name, re.IGNORECASE)
                       for p in LICENSE_FILE_PATTERNS):
                return False
        else:
            return False

    return True


def is_license_directory(dirname: str) -> bool:
    """
    判断目录名是否包含license字样。

    Args:
        dirname: 目录名

    Returns:
        bool: 是否是license相关目录
    """
    dirname_lower = dirname.lower()
    return "license" in dirname_lower


def get_license_files_from_root(root_path: Path) -> Set[str]:
    """
    获取项目根目录下的license相关文件的相对路径。

    root_path 已经是真正的项目根目录（在main.py中已处理嵌套目录检测）。
    返回相对于root_path的相对路径字符串集合。

    Args:
        root_path: 项目根目录路径

    Returns:
        Set[str]: license相关文件的相对路径集合
    """
    license_files = set()

    if not root_path.is_dir():
        return license_files

    try:
        for item in root_path.iterdir():
            if item.is_file():
                # 检查项目根目录下的文件是否是license文件
                if is_license_file(item.name):
                    license_files.add(item.name)
            elif item.is_dir():
                # 检查目录名是否包含license字样
                if is_license_directory(item.name):
                    # 收集该目录下的所有文件
                    for sub_item in item.rglob("*"):
                        if sub_item.is_file():
                            rel_path = sub_item.relative_to(root_path)
                            license_files.add(str(rel_path).replace("\\", "/"))
    except PermissionError:
        warn(f"Permission denied when accessing: {root_path}")

    return license_files


def process_license_params(
    data: dict,
    root_path: Path,
    license_name: Optional[str] = None,
    license_path: Optional[str] = None,
    license_full_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    根据用户提供的参数处理license信息。

    参数组合逻辑：
    - 只填license名称：提取与该名称对应的license文本路径
    - 只填license路径：提取该路径对应的license名称
    - 都不填：执行完整license提取

    Args:
        data: scancode输出的JSON数据（已解析的字典）
        root_path: 项目根目录路径
        license_name: 用户提供的license名称（可选）
        license_path: 用户提供的license文本相对路径（可选）
        license_full_path: license文件绝对路径，由命令入口规范化校验后传入（可选）

    Returns:
        List[Dict]: 提取的license信息列表
    """
    # 获取扫描的根目录
    scanned_root = (data.get("headers") or [{}])[0].get("options", {}).get("input") or [None]
    scanned_root = scanned_root[0]
    if root_path is None:
        root_path = Path(scanned_root) if scanned_root else None

    # 独立调用未传绝对路径时按相对路径补算；CLI入口已在main.py中完成校验
    if license_path and license_full_path is None and root_path is not None:
        relative_license_path = license_path.lstrip("/").replace("\\", "/")
        license_full_path = (root_path / relative_license_path).resolve()

    # 确定要检查的license文件集合
    target_license_files = set()
    if root_path:
        target_license_files = get_license_files_from_root(root_path)

    # 构建目标license文件的文件名集合
    target_license_filenames = set()
    for f in target_license_files:
        filename = Path(f).name.lower()
        target_license_filenames.add(filename)

    if license_name and not license_path:
        # 只填license名称：提取对应的license文本路径
        return _select_license_name_records(
            data, target_license_files, target_license_filenames, license_name
        )

    if license_path and not license_name:
        # 只填license路径：提取该路径对应的license名称
        return _select_license_path_record(
            data, target_license_files, license_path, root_path, license_full_path
        )

    if license_name and license_path:
        # 同时指定license名称和license文件路径：校验是否匹配
        return _validate_license_path_name(
            data, target_license_files, license_name, license_path, root_path, license_full_path
        )

    # 都不填：执行完整license提取
    info("Performing full license extraction")
    license_records = _extract_all_licenses(
        data, target_license_files, target_license_filenames
    )

    # 提示用户人工核对
    warn("请人工核对许可证信息是否准确 / Please manually verify the license information is accurate")
    return license_records


def _select_license_name_records(
    data: dict,
    target_license_files: Set[str],
    target_license_filenames: Set[str],
    license_name: str,
) -> List[Dict[str, Any]]:
    """
    只指定license名称时：提取与该名称对应的license记录。

    Args:
        data: scancode输出的JSON数据（已解析的字典）
        target_license_files: 目标license文件集合
        target_license_filenames: 目标license文件名集合
        license_name: 用户提供的license名称

    Returns:
        List[Dict]: 提取的license信息列表
    """
    info(f"Searching for license path matching name: {license_name}")

    matching_records = _find_license_by_name(
        data, target_license_files, target_license_filenames, license_name
    )

    if matching_records:
        license_records = matching_records
        info(f"Found {len(matching_records)} matching license record(s)")
    else:
        # 用户指定了license名称但未匹配到，输出警告但继续执行
        warn(f"No license file found matching name: {license_name}")
        warn("Please check if the license name is a valid SPDX identifier (e.g., MIT, Apache-2.0, GPL-3.0)")
        # 使用用户提供的license名称，继续生成Readme.opensource
        license_records = [{
            "file": "",
            "spdx_identifier": license_name,
            "license_expression": license_name,
            "matched_text": "",
        }]

    # 提示用户人工核对
    warn("请人工核对许可证信息是否准确 / Please manually verify the license information is accurate")
    return license_records


def _select_license_path_record(
    data: dict,
    target_license_files: Set[str],
    license_path: str,
    root_path: Optional[Path],
    license_full_path: Optional[Path],
) -> List[Dict[str, Any]]:
    """
    只指定license路径时：提取该路径对应的license记录。

    Args:
        data: scancode输出的JSON数据（已解析的字典）
        target_license_files: 目标license文件集合
        license_path: 用户提供的license文件相对路径
        root_path: 实际扫描根目录
        license_full_path: license文件绝对路径

    Returns:
        List[Dict]: 提取的license信息列表
    """
    info(f"Extracting license name from path: {license_path}")

    # 路径验证已在main.py中完成，这里不再重复验证

    matching_record = _find_license_by_path(
        data, target_license_files, license_path, root_path, license_full_path
    )

    if matching_record:
        license_records = [matching_record]
        info(f"Found license: {matching_record['spdx_identifier']}")
    else:
        # 用户指定了license路径但未检测到license信息，输出警告但继续执行
        warn(f"No license information found for path: {license_path}")
        warn(f"The file '{license_path}' may not be a valid license file")
        warn("Please check if the file contains complete license text")
        # 返回包含license_path的记录，让后续流程能从文件读取内容
        license_records = [{
            "file": license_path,
            "spdx_identifier": "Unknown",
            "license_expression": "Unknown",
            "matched_text": "",
        }]

    # 提示用户人工核对
    warn("请人工核对许可证信息是否准确 / Please manually verify the license information is accurate")
    return license_records


def _validate_license_path_name(
    data: dict,
    target_license_files: Set[str],
    license_name: str,
    license_path: str,
    root_path: Optional[Path],
    license_full_path: Optional[Path],
) -> List[Dict[str, Any]]:
    """
    同时指定license名称和路径时：校验名称与该路径文件检测结果是否匹配。

    Args:
        data: scancode输出的JSON数据（已解析的字典）
        target_license_files: 目标license文件集合
        license_name: 用户提供的license名称
        license_path: 用户提供的license文件相对路径
        root_path: 实际扫描根目录
        license_full_path: license文件绝对路径

    Returns:
        List[Dict]: 提取的license信息列表
    """
    info(f"Validating license name '{license_name}' against file path '{license_path}'")

    # 从路径提取license信息
    matching_record = _find_license_by_path(
        data, target_license_files, license_path, root_path, license_full_path
    )

    if matching_record:
        detected_spdx = matching_record.get("spdx_identifier", "")
        detected_license = matching_record.get("license_expression", "")

        # 检查是否匹配
        is_match = _license_name_matches(
            license_name.lower(), detected_spdx, detected_license
        )

        if is_match:
            info(f"License name '{license_name}' matches the license detected in file '{license_path}'")
            license_records = [matching_record]
        else:
            # 不匹配，输出警告但继续执行
            warn(f"License name '{license_name}' does not match the license detected in file '{license_path}'")
            warn("Please verify the license name and file path are correct")
            # 使用用户提供的名称，但保留检测到的matched_text
            license_records = [{
                "file": license_path,
                "spdx_identifier": license_name,
                "license_expression": license_name,
                "matched_text": matching_record.get("matched_text", ""),
            }]
    else:
        # 路径未识别出license信息，输出警告但继续执行
        warn(f"No license information found for path: {license_path}")
        warn(f"The file '{license_path}' may not be a valid license file")
        # 使用用户提供的license名称
        license_records = [{
            "file": license_path,
            "spdx_identifier": license_name,
            "license_expression": license_name,
            "matched_text": "",
        }]

    # 提示用户人工核对
    warn("请人工核对许可证信息是否准确 / Please manually verify the license information is accurate")
    return license_records


def _get_best_matched_text(file_info: dict) -> str:
    """
    从license_detections中获取最佳的matched_text。

    优先级规则：
    1. 优先选择 .LICENSE 规则（完整license文本匹配）
    2. 其次选择 matched_length 最长的匹配

    注意：scancode JSON中可能没有matched_text字段，此时返回空字符串。
    调用者应检查返回值是否为空，如果为空则需要从源文件读取。

    Args:
        file_info: scancode文件信息

    Returns:
        str: 最佳的matched_text，如果没有则返回空字符串
    """
    license_detections = file_info.get("license_detections", [])
    if not license_detections:
        return ""

    best_text = ""
    best_length = 0
    best_match = None
    has_license_rule = False

    for detection in license_detections:
        matches = detection.get("matches", [])
        for match in matches:
            rule_id = match.get("rule_identifier", "")
            matched_text = match.get("matched_text", "")
            matched_length = match.get("matched_length", len(matched_text) if matched_text else 0)

            # 优先选择 .LICENSE 规则
            if rule_id.endswith(".LICENSE"):
                if not has_license_rule or matched_length > best_length:
                    best_text = matched_text
                    best_length = matched_length
                    best_match = match
                    has_license_rule = True
            elif not has_license_rule:
                # 没有 .LICENSE 规则时，选择最长的匹配
                if matched_length > best_length:
                    best_text = matched_text
                    best_length = matched_length
                    best_match = match

    # 如果matched_text为空但有matched_length，说明JSON中没有存储matched_text
    # 此时返回空字符串，调用者需要从源文件读取
    return best_text


def get_best_match_info(file_info: dict) -> Dict[str, Any]:
    """
    从license_detections中获取最佳匹配的详细信息。

    用于判断匹配质量，决定是否需要从源文件读取完整license文本。

    Args:
        file_info: scancode文件信息

    Returns:
        Dict: 包含最佳匹配信息的字典：
            - has_license_rule: 是否有.LICENSE规则匹配
            - matched_length: 匹配长度
            - start_line: 匹配开始行
            - end_line: 匹配结束行
            - rule_identifier: 规则标识
    """
    license_detections = file_info.get("license_detections", [])
    if not license_detections:
        return {
            "has_license_rule": False,
            "matched_length": 0,
            "start_line": 0,
            "end_line": 0,
            "rule_identifier": "",
        }

    best_length = 0
    best_match = None
    has_license_rule = False

    for detection in license_detections:
        matches = detection.get("matches", [])
        for match in matches:
            rule_id = match.get("rule_identifier", "")
            matched_length = match.get("matched_length", 0)

            # 优先选择 .LICENSE 规则
            if rule_id.endswith(".LICENSE"):
                if not has_license_rule or matched_length > best_length:
                    best_match = match
                    best_length = matched_length
                    has_license_rule = True
            elif not has_license_rule:
                # 没有 .LICENSE 规则时，选择最长的匹配
                if matched_length > best_length:
                    best_match = match
                    best_length = matched_length

    if best_match:
        return {
            "has_license_rule": has_license_rule,
            "matched_length": best_match.get("matched_length", 0),
            "start_line": best_match.get("start_line", 0),
            "end_line": best_match.get("end_line", 0),
            "rule_identifier": best_match.get("rule_identifier", ""),
        }

    return {
        "has_license_rule": False,
        "matched_length": 0,
        "start_line": 0,
        "end_line": 0,
        "rule_identifier": "",
    }


def _is_valid_license_match(file_info: dict) -> bool:
    """
    判断ScanCode对文件的license匹配是否有效（非误匹配）。

    过滤规则：
    - 有 .LICENSE 规则匹配 → 有效（完整的license文本匹配）
    - 无 .LICENSE 规则但匹配长度 >= 20 → 有效（较长的片段匹配）
    - 无 .LICENSE 规则且匹配长度 < 20 → 无效（短文本引用，如说明文档中提到 "MIT"）

    Args:
        file_info: scancode文件信息

    Returns:
        bool: 是否是有效的license匹配
    """
    match_info = get_best_match_info(file_info)
    if not match_info["has_license_rule"]:
        if match_info["matched_length"] < 20:
            return False
    return True


def _mutually_contains(a: str, b: str) -> bool:
    """
    判断两个字符串是否互相包含（a含b 或 b含a）。

    Args:
        a: 字符串a（小写形式）
        b: 字符串b（小写形式）

    Returns:
        bool: 是否互相包含
    """
    return a in b or b in a


def _license_name_matches(license_name_lower: str,
                          detected_spdx: str,
                          detected_license: str) -> bool:
    """
    检查用户提供的license名称是否与检出结果模糊匹配（支持部分匹配和忽略大小写）。

    Args:
        license_name_lower: 用户提供的小写license名称
        detected_spdx: 检出的SPDX表达式
        detected_license: 检出的license表达式

    Returns:
        bool: 是否匹配
    """
    return (_mutually_contains(license_name_lower, detected_spdx.lower()) or
            _mutually_contains(license_name_lower, detected_license.lower()))


def _detect_from_file_self(file_info: dict, file_path: str) -> bool:
    """
    判断.LICENSE规则匹配是否来自文件自身。

    from_file_self=True 表示文件自身包含license全文；False表示
    license全文来自被引用的其他文件（跨文件引用）。

    Args:
        file_info: scancode文件信息
        file_path: 当前文件的路径

    Returns:
        bool: .LICENSE规则匹配是否来自文件自身
    """
    for det in file_info.get("license_detections", []):
        for m in det.get("matches", []):
            from_file = m.get("from_file", "")
            if (m.get("rule_identifier", "").endswith(".LICENSE")
                    and from_file and from_file != file_path):
                return False
    return True


def _build_license_record(file_info: dict, file_path: str,
                          detected_spdx: str,
                          detected_license: str) -> Dict[str, Any]:
    """
    由单个scancode文件信息构造license记录。

    Args:
        file_info: scancode文件信息
        file_path: 文件路径
        detected_spdx: 检出的SPDX表达式
        detected_license: 检出的license表达式

    Returns:
        Dict: license记录
    """
    # 获取最佳matched_text（优先.LICENSE规则）
    matched_text = _get_best_matched_text(file_info)
    return {
        "file": file_path,
        "spdx_identifier": detected_spdx,
        "license_expression": detected_license,
        "matched_text": matched_text,
        "from_file_self": _detect_from_file_self(file_info, file_path),
    }


def _filter_by_priority(groups: Dict[Any, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    对分组的license记录按优先级去重，每组只保留优先级最高的记录。

    优先级排序依据：
    1. 路径优先级（根目录(1) > LICENSES目录(2) > 其他目录(3)）
    2. from_file_self 优先（自身包含 license 全文 > 引用其他文件）

    Args:
        groups: 按SPDX标识或(spdx, license)组合分组的记录

    Returns:
        List[Dict]: 每组优先级最高的记录列表
    """
    filtered_records = []
    for key, records in groups.items():
        if len(records) == 1:
            filtered_records.extend(records)
            continue
        sorted_records = sorted(
            records,
            key=lambda r: (
                _get_license_path_priority(r["file"]),
                0 if r.get("from_file_self", True) else 1,
            )
        )
        # 只取优先级最高的（第一个）
        filtered_records.append(sorted_records[0])
        debug(f"Multiple {key} license files found, selected: {sorted_records[0]['file']}")
    return filtered_records


def _find_license_by_name(
    data: dict,
    target_license_files: Set[str],
    target_license_filenames: Set[str],
    license_name: str,
) -> List[Dict[str, Any]]:
    """
    根据license名称查找对应的license记录。

    仅接受根目录下或LICENSES目录下的license文件。

    当有多个相同license的文件时，按路径优先级筛选：
    - 根目录下的license文件优先 (如 LICENSE.MIT)
    - LICENSES目录下次之 (如 LICENSES/MIT.txt)
    - 其他目录最低

    Args:
        data: scancode JSON数据
        target_license_files: 目标license文件集合
        target_license_filenames: 目标license文件名集合
        license_name: 要查找的license名称

    Returns:
        List[Dict]: 匹配的license记录列表
    """
    license_name_lower = license_name.lower()
    matching_records = []
    seen = set()

    for file_info in data.get("files", []):
        file_path = file_info.get("path", "")

        # 使用严格的路径检查
        if not _is_valid_license_path(file_path, target_license_files):
            continue

        detected_spdx = file_info.get("detected_license_expression_spdx", "")
        detected_license = file_info.get("detected_license_expression", "")

        if not detected_spdx:
            continue

        # 检查是否匹配用户提供的license名称（支持部分匹配和忽略大小写）
        if not _license_name_matches(license_name_lower, detected_spdx, detected_license):
            continue

        # 初步去重：同一文件相同SPDX只添加一次
        unique_key = (detected_spdx, file_path)
        if unique_key in seen:
            continue
        seen.add(unique_key)
        matching_records.append(
            _build_license_record(file_info, file_path, detected_spdx, detected_license))

    # 按路径优先级去重：当有多个相同SPDX标识的license时，只保留优先级最高的
    if len(matching_records) > 1:
        spdx_groups: Dict[str, List[Dict[str, Any]]] = {}
        for record in matching_records:
            spdx_groups.setdefault(record["spdx_identifier"], []).append(record)
        matching_records = _filter_by_priority(spdx_groups)

    return matching_records


def _find_license_by_path(
    data: dict,
    target_license_files: Set[str],
    license_path: str,
    root_path: Optional[Path] = None,
    license_full_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    根据license文件路径查找对应的license名称。

    将扫描记录还原为绝对路径后与license_full_path精确比较，
    避免后缀匹配误选docs/LICENSE等嵌套同名文件。

    误匹配过滤：
    - 只有 .LICENSE 规则匹配才认为是有效的完整license匹配
    - 短文本规则匹配（如 mit_30.RULE 仅匹配2字符）会被过滤

    Args:
        data: scancode JSON数据
        target_license_files: 目标license文件集合（保留以兼容既有调用）
        license_path: 要查找的license文件相对路径
        root_path: 实际扫描根目录
        license_full_path: license文件绝对路径（命令入口已规范化校验）

    Returns:
        Optional[Dict]: 匹配的license记录，如果未找到或为误匹配则返回None
    """
    if root_path is None or license_full_path is None:
        return None

    for file_info in data.get("files", []):
        file_path = file_info.get("path", "").replace("\\", "/")

        # 扫描记录以扫描根目录名开头（如 json-3.11.3/LICENSE.MIT），
        # 剥离根名前缀后拼接还原为绝对路径再比较
        candidate = Path(_clean_scancode_path(file_path))
        if candidate.parts and candidate.parts[0].lower() == root_path.name.lower():
            candidate = Path(*candidate.parts[1:])
        if (root_path / candidate).resolve() != license_full_path:
            continue

        detected_spdx = file_info.get("detected_license_expression_spdx", "")
        detected_license = file_info.get("detected_license_expression", "")

        # 过滤误匹配（短文本引用，如说明文档中提到 license 名称）
        if not _is_valid_license_match(file_info):
            return None

        # 获取最佳matched_text（优先.LICENSE规则）
        matched_text = _get_best_matched_text(file_info)

        return {
            "file": file_path,
            "spdx_identifier": detected_spdx,
            "license_expression": detected_license,
            "matched_text": matched_text,
        }

    return None


def _is_valid_license_path(file_path: str, target_license_files: Set[str]) -> bool:
    """
    检查license文件路径是否有效。

    有效条件（满足其一即可）：
    1. 文件在target_license_files集合中
    2. 项目根目录下的一级LICENSES目录中的文件（如 project-name/LICENSES/xxx）
       - LICENSES目录下的文件，即使命名不规范，也会被接受
    3. 项目根目录下的license文件（如 project-name/LICENSE.MIT, project-name/MIT.txt）

    路径结构说明：
    - 路径格式通常为：项目根目录/文件 或 项目根目录/LICENSES/文件
    - 例如：json-develop/LICENSE.MIT, json-develop/LICENSES/CC0-1.0.txt
    - 不允许：json-develop/subdir/LICENSES/xxx（LICENSES必须是项目根目录下的一级子目录）

    Args:
        file_path: 文件路径
        target_license_files: 目标license文件集合

    Returns:
        bool: 是否是有效的license文件路径
    """
    # 直接匹配target_license_files集合
    if file_path in target_license_files:
        return True

    # 清理路径：移除解压根目录前缀（如 xxx-extract/project-name/ -> project-name/）
    cleaned_path = _clean_scancode_path(file_path)

    # 解析清理后的路径
    path_parts = Path(cleaned_path).parts

    # 过滤掉空的路径部分（如根目录）
    path_parts = [p for p in path_parts if p]

    if not path_parts:
        return False

    # 路径深度检查：
    # - 深度为1：清理规则保证记录首段（扫描根目录名）不会被剥离，
    #   该形态正常不会出现，保留为防御分支
    # - 深度为2：项目根目录下的文件（如 json-develop/LICENSE.MIT）
    # - 深度>=3：可能是 LICENSES 目录下的文件（如 json-develop/LICENSES/CC0-1.0.txt）

    if len(path_parts) == 1:
        return False
    elif len(path_parts) == 2:
        # 项目根目录下的文件（如 json-develop/LICENSE.MIT）
        # 检查文件名是否是license文件
        file_name = path_parts[-1]
        return is_license_file(file_name)
    else:
        # 深度>=3：检查是否是项目根目录下的一级LICENSES目录
        # path_parts[0] 是项目根目录名（如 json-develop）
        # path_parts[1] 必须是 LICENSES 目录
        # path_parts[2:] 是 LICENSES 目录下的文件路径
        if is_license_directory(path_parts[1]):
            # 是项目根目录下的一级LICENSES目录，接受任意深度的文件
            return True
        else:
            # 不是LICENSES目录，不允许
            return False


def _get_license_path_priority(file_path: str) -> int:
    """
    获取license文件路径的优先级。

    优先级规则：
    - 根目录下的license文件优先级最高 (1)
    - LICENSES目录下的文件优先级次之 (2)
    - 其他目录的文件优先级最低 (3)

    例如：
    - json-develop/LICENSE.MIT -> 1 (根目录)
    - json-develop/LICENSES/MIT.txt -> 2 (LICENSES目录)
    - json-develop/docs/LICENSE -> 3 (其他目录)

    Args:
        file_path: license文件路径

    Returns:
        int: 优先级数字（越小优先级越高）
    """
    # 清理路径
    cleaned_path = _clean_scancode_path(file_path)

    # 标准化路径分隔符
    path_parts = cleaned_path.replace("\\", "/").lower().split("/")

    # 过滤掉空部分
    path_parts = [p for p in path_parts if p]

    if not path_parts:
        return 3

    # 检查路径深度和结构
    # 路径格式：项目名/license文件 或 项目名/LICENSES/license文件

    if len(path_parts) == 1:
        # 与路径有效性检查一致：清理规则保证该形态正常不出现
        return 3
    elif len(path_parts) == 2:
        # 项目根目录下的文件（如 json-develop/LICENSE.MIT）
        # 这是最标准的位置，优先级最高
        return 1
    else:
        # 深度 >= 3
        # 检查是否是LICENSES目录（如 json-develop/LICENSES/MIT.txt）
        if path_parts[1] == "licenses":
            return 2
        else:
            # 其他目录，优先级最低
            return 3


def _clean_scancode_path(file_path: str) -> str:
    """
    清理scancode输出的路径，移除解压根目录前缀。

    例如：
    - json-develop.zip-extract/json-develop/LICENSE.MIT -> json-develop/LICENSE.MIT
    - json-develop/LICENSE.MIT -> json-develop/LICENSE.MIT（不变）

    Args:
        file_path: 原始文件路径

    Returns:
        str: 清理后的路径
    """
    # 标准化路径分隔符
    path_parts = file_path.replace("\\", "/").split("/")

    # 过滤掉空部分
    path_parts = [p for p in path_parts if p]

    if not path_parts:
        return file_path

    # 查找并跳过 -extract 目录。剥离条件：-extract段之后仍存在
    # “目录/文件”两级结构，说明它是extractcode的包装层；若其后仅剩
    # 单个文件，说明该-extract目录就是项目根本身（扁平压缩包：包内
    # 文件直接散落在解压根下），此时扫描记录首段即项目根名，保留
    # 不剥（记录形如 xxx-extract/LICENSE，与规范包的 pkg-1.0/LICENSE
    # 同构，深度2即项目根文件语义）。
    start_idx = 0
    for i, part in enumerate(path_parts):
        if "-extract" in part.lower():
            if len(path_parts) - (i + 1) >= 2:
                start_idx = i + 1
            break

    # 返回清理后的路径
    return "/".join(path_parts[start_idx:])


def _extract_all_licenses(
    data: dict,
    target_license_files: Set[str],
    target_license_filenames: Set[str],
) -> List[Dict[str, Any]]:
    """
    提取所有license信息。

    仅接受：
    1. 项目根目录下的license文件
    2. 根目录下LICENSES目录中的文件

    当有多个相同license的文件时，按路径优先级筛选：
    - 根目录下的license文件优先 (如 LICENSE.MIT)
    - LICENSES目录下次之 (如 LICENSES/MIT.txt)
    - 其他目录最低

    Args:
        data: scancode JSON数据
        target_license_files: 目标license文件集合
        target_license_filenames: 目标license文件名集合

    Returns:
        List[Dict]: 提取的license记录列表
    """
    license_records = []
    seen = set()

    for file_info in data.get("files", []):
        file_path = file_info.get("path", "")

        # 使用严格的路径检查
        if not _is_valid_license_path(file_path, target_license_files):
            continue

        detected_license = file_info.get("detected_license_expression", "")
        detected_spdx = file_info.get("detected_license_expression_spdx", "")

        if not detected_license:
            continue

        # 过滤误匹配（短文本引用，如说明文档中提到 license 名称）
        if not _is_valid_license_match(file_info):
            continue

        # 初步去重：同时考虑spdx、license和文件路径，避免同一文件重复添加
        unique_key = (detected_spdx, detected_license, file_path)
        if unique_key in seen:
            continue
        seen.add(unique_key)

        license_records.append(
            _build_license_record(file_info, file_path, detected_spdx, detected_license))

    # 按路径优先级去重：当有多个相同(spdx, license)组合的license时，只保留优先级最高的
    # 优先级：根目录(1) > LICENSES目录(2) > 其他目录(3)
    if len(license_records) > 1:
        spdx_license_groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for record in license_records:
            key = (record["spdx_identifier"], record["license_expression"])
            spdx_license_groups.setdefault(key, []).append(record)
        license_records = _filter_by_priority(spdx_license_groups)

    info(f"Extracted {len(license_records)} unique license records")
    return license_records


def write_license_report(
    output_txt: Path,
    software_name: str,
    software_version: str,
    license_records: List[Dict[str, Any]],
) -> None:
    """
    写入license报告。

    Args:
        output_txt: 输出文件路径
        software_name: 软件名称
        software_version: 软件版本
        license_records: license记录列表
    """
    with output_txt.open("w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("LICENSE INFORMATION EXTRACTION REPORT\n")
        f.write("=" * 60 + "\n\n")

        # 软件基本信息
        f.write(f"Software Name: {software_name}\n")
        f.write(f"Software Version: {software_version}\n\n")

        if not license_records:
            f.write("No license information found.\n")
        else:
            f.write(f"Total unique licenses found: {len(license_records)}\n\n")

            for i, record in enumerate(license_records, 1):
                f.write(f"--- License #{i} ---\n")
                f.write(f"File: {record.get('file', 'N/A')}\n")
                f.write(f"SPDX Identifier: {record.get('spdx_identifier', 'N/A')}\n")
                f.write(f"License Expression: {record.get('license_expression', 'N/A')}\n")
                if record.get('matched_text'):
                    # 限制matched_text的长度
                    text = record['matched_text']
                    if len(text) > 500:
                        text = text[:500] + "..."
                    f.write(f"Matched Text:\n{text}\n")
                f.write("\n")

    info(f"License report written to {output_txt}")
