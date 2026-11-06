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

"""对最终选定的非UTF-8 license文件做二次识别，修正license名称。

ScanCode按原始字节识别license，非UTF-8文件（如GBK）会被内部按Latin-1
误解码，导致识别出的SPDX标识错误或不完整（例如中文/英文双语木兰许可证
被判成LicenseRef-scancode-mulanpsl-2.0-en而不是MulanPSL-2.0）。

本模块只处理最终要输出的license记录：把对应文件严格解码后转成UTF-8
临时副本，再用ScanCode单独识别一次，用结果替换记录中的SPDX/表达式。
全文输出仍由readme_opensource从原文件读取解码，不受影响。
"""

import tempfile
from pathlib import Path

from .logger import debug, info, warn
from .readme_opensource import (
    _clean_license_path,
    _decode_license_text_with_status,
    _get_possible_license_paths,
)
from .scancode import run_scancode


def _is_utf8(raw: bytes) -> bool:
    """判断字节是否是合法UTF-8文本（含BOM；含NUL的按非文本处理）。"""
    if b"\x00" in raw:
        return False
    try:
        raw.decode("utf-8-sig")
        return True
    except UnicodeDecodeError:
        return False


def _resolve_license_file(file_path: str, root_path: Path):
    """
    把ScanCode记录中的路径还原为磁盘文件；找不到返回None。
    """
    if not file_path or root_path is None:
        return None
    cleaned = _clean_license_path(file_path, root_path)
    for candidate in _get_possible_license_paths(root_path, cleaned):
        if candidate.is_file():
            return candidate
    return None


def rescan_license_records(
    license_records: list,
    root_path: Path,
    jobs: int = 4,
    max_in_memory: int = 2000,
    user_license_name: str = None,
) -> list:
    """
    修正最终license记录中因编码导致的错误名称。

    只处理最终记录的file字段对应的文件，且只处理严格解码成功的非UTF-8
    文件；UTF-8文件、解码不精确的文件、找不到的文件都跳过。用户显式提供
    的license名称优先，不做覆盖。二次识别失败时保留第一遍结果并告警。

    Args:
        license_records: process_license_params返回的最终记录（原地修改）
        root_path: 扫描根目录
        jobs: ScanCode并行任务数
        max_in_memory: ScanCode内存缓存文件数
        user_license_name: 用户显式-l指定的名称，非空时跳过重扫

    Returns:
        list: 传入的license_records（可能已被修正）
    """
    if not license_records or user_license_name or root_path is None:
        return license_records

    path_to_indices = {}
    for idx, record in enumerate(license_records):
        full_path = _resolve_license_file(record.get("file", ""), root_path)
        if full_path is None:
            continue
        path_to_indices.setdefault(full_path.resolve(), []).append(idx)

    candidates = []
    for full_path in path_to_indices:
        try:
            raw = full_path.read_bytes()
        except OSError as e:
            debug(f"Failed to read license file for re-scan {full_path}: {e}")
            continue
        if _is_utf8(raw):
            continue
        try:
            text, exact = _decode_license_text_with_status(raw)
        except Exception as e:
            # 解码异常不能影响主流程，保留第一遍结果
            debug(f"Failed to decode license file for re-scan {full_path}: {e}")
            continue
        if not exact or "\x00" in text:
            debug(f"Skipped lossy/non-text license file for re-scan: {full_path}")
            continue
        candidates.append((full_path, text))

    if not candidates:
        return license_records

    try:
        with tempfile.TemporaryDirectory(prefix="ossinfo-license-rescan-") as temp_dir:
            base = Path(temp_dir)
            scan_dir = base / "files"
            scan_dir.mkdir()
            rel_to_path = {}
            for i, (full_path, text) in enumerate(candidates):
                rel_path = f"f{i:04d}/{full_path.name}"
                temp_file = scan_dir / rel_path
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                temp_file.write_text(text, encoding="utf-8")
                rel_to_path[rel_path] = full_path

            data = run_scancode(
                scan_dir,
                base / "result.json",
                jobs=jobs,
                scan_license=True,
                max_in_memory=max_in_memory,
                scan_copyright=False,
            )
            if not isinstance(data, dict):
                warn("License re-scan returned no result, keeping first-pass results")
                return license_records

            updated = 0
            for file_info in data.get("files", []):
                raw_rel_path = file_info.get("path", "").replace("\\", "/")
                # ScanCode返回的路径可能带扫描根目录名（如 files/f0000/LICENSE），
                # 同时兼容已去除前缀的形式
                cleaned_rel_path = _clean_license_path(raw_rel_path, scan_dir)
                full_path = rel_to_path.get(raw_rel_path) or rel_to_path.get(cleaned_rel_path)
                if full_path is None:
                    continue
                detected_spdx = file_info.get("detected_license_expression_spdx", "")
                detected_expression = file_info.get("detected_license_expression", "")
                # 两个字段保持一致的名称：只有其一时互相回填，避免Readme
                # 取spdx_identifier、license报告取expression导致两份输出不一致
                new_spdx = detected_spdx or detected_expression
                new_expression = detected_expression or detected_spdx
                if not new_spdx and not new_expression:
                    continue
                for idx in path_to_indices.get(full_path, []):
                    record = license_records[idx]
                    record["spdx_identifier"] = new_spdx
                    record["license_expression"] = new_expression
                    updated += 1

            if updated:
                info(
                    f"Re-scanned {len(candidates)} non-UTF-8 license file(s); "
                    f"corrected {updated} license record(s)"
                )
    except Exception as e:
        warn(f"License re-scan failed, keeping first-pass results: {e}")

    return license_records
