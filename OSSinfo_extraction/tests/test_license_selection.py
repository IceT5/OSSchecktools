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

"""license记录选择（process_license_params）的场景矩阵单元测试。

通过构造ScanCode结果dict（不依赖真实扫描）确定性覆盖：
- 嵌套同名文件遮蔽（#384）：docs/LICENSE / LICENSES/LICENSE / third_party/*/LICENSE
- 显式子路径选择、前导斜杠与Windows分隔符
- 短文本误匹配过滤、记录顺序无关性
- -l模糊匹配、-l+-p一致性校验、各fallback路径
- 全量提取的路径优先级与跨文件引用（from_file_self）
- 独立调用（root_path=None）时从扫描结果headers自取扫描根目录
"""

from pathlib import Path

import pytest

from ossinfo_extraction.license_extraction import process_license_params

SIM_ROOT = "X:/sim/pkg-1.0"


def rec(path, spdx, detected=None, rule_suffix=".LICENSE", matched_len=300,
        matched_text="MATCHED TEXT", from_file=None):
    """构造一条scancode文件记录。

    rule_suffix=".LICENSE" 表示完整license文本匹配（有效）；
    rule_suffix=".RULE" 且 matched_len<20 表示短文本引用（会被过滤）。
    """
    return {
        "path": path,
        "detected_license_expression_spdx": spdx,
        "detected_license_expression": detected or spdx,
        "license_detections": [{
            "matches": [dict(
                rule_identifier=f"{spdx.lower()}{rule_suffix}",
                matched_length=matched_len,
                matched_text=matched_text,
                **({"from_file": from_file} if from_file else {}),
            )],
        }],
    }


def scan_data(files, root=SIM_ROOT):
    """构造带headers的扫描结果（headers.input供root_path=None时自取）。"""
    return {"headers": [{"options": {"input": [root]}}], "files": files}


def one(records):
    assert len(records) == 1, f"expected single record, got {records}"
    return records[0]


ROOT_REC = rec("pkg-1.0/LICENSE", "Apache-2.0", matched_text="ROOT LICENSE TEXT")
DOCS_REC = rec("pkg-1.0/docs/LICENSE", "BSD-3-Clause", matched_text="DOCS LICENSE TEXT")
SHADOW = [DOCS_REC, ROOT_REC]  # 嵌套同名记录排在前面（#384顺序敏感场景）


def short_rec(path, spdx="MIT"):
    """短文本引用记录：说明文档里提到license名，不构成有效检出。"""
    return rec(path, spdx, rule_suffix=".RULE", matched_len=3, matched_text="MIT")


class TestPathSelectsExactRecord:
    """-p模式：精确匹配指定文件，不被嵌套同名记录遮蔽（#384）。"""

    def test_root_license_not_shadowed_by_docs(self):
        got = one(process_license_params(scan_data(SHADOW), Path(SIM_ROOT), None, "LICENSE"))
        assert got["file"] == "pkg-1.0/LICENSE"
        assert got["spdx_identifier"] == "Apache-2.0"
        assert got["matched_text"] == "ROOT LICENSE TEXT"

    def test_order_independent(self):
        """精确匹配的价值：无论扫描记录顺序如何，结果一致（修复前顺序敏感）。"""
        flipped = one(process_license_params(
            scan_data(list(reversed(SHADOW))), Path(SIM_ROOT), None, "LICENSE"))
        assert flipped["file"] == "pkg-1.0/LICENSE"

    def test_licenses_dir_license_not_shadowed(self):
        files = [rec("pkg-1.0/LICENSES/LICENSE", "GPL-3.0-only"),
                 rec("pkg-1.0/LICENSE", "Apache-2.0")]
        got = one(process_license_params(scan_data(files), Path(SIM_ROOT), None, "LICENSE"))
        assert got["file"] == "pkg-1.0/LICENSE"

    def test_third_party_license_not_shadowed(self):
        files = [rec("pkg-1.0/third_party/forked/golang/LICENSE", "GPL-2.0"),
                 rec("pkg-1.0/LICENSE", "MIT")]
        got = one(process_license_params(scan_data(files), Path(SIM_ROOT), None, "LICENSE"))
        assert got["file"] == "pkg-1.0/LICENSE"

    def test_explicit_subpath_selects_nested_file(self):
        """显式指定嵌套文件时仍可选中它（#384预期行为保留）。"""
        got = one(process_license_params(scan_data(SHADOW), Path(SIM_ROOT), None, "docs/LICENSE"))
        assert got["file"] == "pkg-1.0/docs/LICENSE"
        assert got["spdx_identifier"] == "BSD-3-Clause"

    def test_subpath_licenses_dir(self):
        got = one(process_license_params(
            scan_data(SHADOW), Path(SIM_ROOT), None, "LICENSES/Apache-2.0.txt"))
        # 合成数据未含LICENSES记录，此处仅验证无匹配fallback路径
        assert got["spdx_identifier"] == "Unknown"

    def test_leading_slash_and_backslash(self):
        """前导斜杠与Windows分隔符由路径补算归一。"""
        for user_path in ("/LICENSE", "LICENSE", ".\\LICENSE"):
            got = one(process_license_params(scan_data(SHADOW), Path(SIM_ROOT), None, user_path))
            assert got["file"] == "pkg-1.0/LICENSE"

    def test_extract_prefix_record_resolved(self):
        """-extract包装前缀的扫描记录可还原匹配。"""
        files = [rec("v1.0.zip-extract/pkg-1.0/LICENSE", "Apache-2.0")]
        root = Path("X:/sim/v1.0.zip-extract/pkg-1.0")
        got = one(process_license_params(scan_data(files, root=str(root)),
                                         root, None, "LICENSE"))
        assert got["file"] == "v1.0.zip-extract/pkg-1.0/LICENSE"

    def test_short_match_does_not_shadow_real_file(self):
        """短文本引用（如README提及MIT）不遮蔽真实文件。"""
        files = [short_rec("pkg-1.0/README"), rec("pkg-1.0/LICENSE", "MIT")]
        got = one(process_license_params(scan_data(files), Path(SIM_ROOT), None, "LICENSE"))
        assert got["file"] == "pkg-1.0/LICENSE"

    def test_no_match_falls_back_to_unknown(self):
        got = one(process_license_params(scan_data(SHADOW), Path(SIM_ROOT), None, "NOT-EXIST"))
        assert got["spdx_identifier"] == "Unknown"
        assert got["file"] == "NOT-EXIST"

    def test_root_path_none_resolved_from_headers(self):
        """独立库调用root_path=None时从headers.input自取扫描根目录。"""
        got = one(process_license_params(scan_data(SHADOW), None, None, "LICENSE"))
        assert got["file"] == "pkg-1.0/LICENSE"


class TestNameSelect:
    """-l模式：按license名称匹配。"""

    def test_exact_name(self):
        records = process_license_params(scan_data(SHADOW), Path(SIM_ROOT), "Apache-2.0", None)
        assert any(r["spdx_identifier"] == "Apache-2.0" for r in records)

    def test_partial_case_insensitive(self):
        records = process_license_params(scan_data(SHADOW), Path(SIM_ROOT), "apache", None)
        assert any(r["spdx_identifier"] == "Apache-2.0" for r in records)

    def test_no_match_falls_back_to_user_name(self):
        got = one(process_license_params(scan_data(SHADOW), Path(SIM_ROOT), "Zlib", None))
        assert got["spdx_identifier"] == "Zlib"
        assert got["file"] == ""


class TestValidateNameAndPath:
    """-l+-p模式：名称与路径文件检出的一致性校验。"""

    def test_match(self):
        got = one(process_license_params(
            scan_data(SHADOW), Path(SIM_ROOT), "Apache-2.0", "LICENSE"))
        assert got["file"] == "pkg-1.0/LICENSE"
        assert got["spdx_identifier"] == "Apache-2.0"

    def test_mismatch_keeps_user_name_and_detected_text(self):
        got = one(process_license_params(
            scan_data(SHADOW), Path(SIM_ROOT), "GPL-2.0", "LICENSE"))
        assert got["spdx_identifier"] == "GPL-2.0"          # 保留用户名称
        assert got["matched_text"] == "ROOT LICENSE TEXT"    # 保留实际检出的文本

    def test_path_without_detection_falls_back(self):
        got = one(process_license_params(
            scan_data(SHADOW), Path(SIM_ROOT), "MIT", "NOT-EXIST"))
        assert got["spdx_identifier"] == "MIT"


class TestFullExtraction:
    """无参数：全量提取的优先级与过滤。"""

    def test_priority_root_over_licenses_over_docs(self):
        files = [
            rec("pkg-1.0/docs/MIT.txt", "MIT"),
            rec("pkg-1.0/LICENSES/MIT.txt", "MIT"),
            rec("pkg-1.0/LICENSE.MIT", "MIT"),
        ]
        records = process_license_params(scan_data(files), Path(SIM_ROOT), None, None)
        assert [r["file"] for r in records] == ["pkg-1.0/LICENSE.MIT"]

    def test_multiple_licenses_extracted(self):
        files = [
            rec("pkg-1.0/LICENSE", "MIT"),
            rec("pkg-1.0/LICENSES/Apache-2.0.txt", "Apache-2.0"),
            rec("pkg-1.0/third_party/x/BSD", "BSD-3-Clause"),
        ]
        records = process_license_params(scan_data(files), Path(SIM_ROOT), None, None)
        # 全量提取只接受根目录与LICENSES目录；其他目录的license文件
        # （third_party/x/BSD）不在自动提取范围，需-p显式指定
        assert {r["spdx_identifier"] for r in records} == {"MIT", "Apache-2.0"}
        assert "pkg-1.0/third_party/x/BSD" not in {r["file"] for r in records}

    def test_cross_file_reference_ranked_after_self(self):
        """同SPDX时，自身包含全文的记录优先于跨文件引用。"""
        referenced = rec("pkg-1.0/LICENSES/GPL-2.0.txt", "GPL-2.0",
                         from_file="pkg-1.0/COPYING")
        self_contained = rec("pkg-1.0/COPYING", "GPL-2.0")
        records = process_license_params(
            scan_data([referenced, self_contained]), Path(SIM_ROOT), None, None)
        assert [r["file"] for r in records] == ["pkg-1.0/COPYING"]

    def test_root_overrides_from_file_self(self):
        """路径优先级高于from_file_self（路径优先，再按引用状态排序）。"""
        files = [
            rec("pkg-1.0/LICENSES/MIT.txt", "MIT", from_file="pkg-1.0/OTHER"),
            rec("pkg-1.0/docs/MIT.txt", "MIT"),
        ]
        records = process_license_params(scan_data(files), Path(SIM_ROOT), None, None)
        assert [r["file"] for r in records] == ["pkg-1.0/LICENSES/MIT.txt"]

    def test_flat_archive_root_license_accepted(self):
        """扁平压缩包（无顶层目录）：扫描根目录名即项目根，清理规则保留
        该段不剥离，根文件记录形如 xxx-extract/LICENSE（深度2，与规范包
        的 pkg-1.0/LICENSE 同构），按既有根文件逻辑接受。"""
        files = [rec("v1.zip-extract/LICENSE", "MIT"),
                 rec("v1.zip-extract/COPYING.LESSER", "LGPL-2.1")]
        root = Path("X:/sim/v1.zip-extract")
        records = process_license_params(scan_data(files, root=str(root)), root, None, None)
        assert {r["file"] for r in records} == {"v1.zip-extract/LICENSE",
                                                "v1.zip-extract/COPYING.LESSER"}

    def test_flat_root_and_subdir_different_spdx_both_kept(self):
        """扁平包根与子目录license不同SPDX时各自保留（子目录记录剥包装层
        后深度为2，按既有规则同样接受）。"""
        files = [rec("v1.zip-extract/docs/LICENSE", "BSD-3-Clause"),
                 rec("v1.zip-extract/LICENSE", "MIT")]
        root = Path("X:/sim/v1.zip-extract")
        records = process_license_params(scan_data(files, root=str(root)), root, None, None)
        assert {r["file"] for r in records} == {"v1.zip-extract/LICENSE",
                                                "v1.zip-extract/docs/LICENSE"}

    def test_flat_licenses_dir_accepted(self):
        files = [rec("v1.zip-extract/LICENSES/GPL-3.0-only.txt", "GPL-3.0-only"),
                 rec("v1.zip-extract/LICENSE", "MIT")]
        root = Path("X:/sim/v1.zip-extract")
        records = process_license_params(scan_data(files, root=str(root)), root, None, None)
        assert {r["file"] for r in records} == {"v1.zip-extract/LICENSE",
                                                "v1.zip-extract/LICENSES/GPL-3.0-only.txt"}

    def test_nested_root_license_accepted_unchanged(self):
        """规范嵌套包（主流形态）：清理行为不变，根文件照常接受。"""
        files = [rec("pkg-1.0/LICENSE", "MIT"),
                 rec("pkg-1.0/docs/LICENSE", "BSD-3-Clause")]
        root = Path("X:/sim/pkg-1.0")
        records = process_license_params(scan_data(files), root, None, None)
        assert [r["file"] for r in records] == ["pkg-1.0/LICENSE"]

    def test_no_license_records(self):
        records = process_license_params(scan_data([]), Path(SIM_ROOT), None, None)
        assert records == []

    def test_same_spdx_different_expressions_both_kept(self):
        """同SPDX不同表达式（如带例外条款）分组键不同，应各自保留。"""
        files = [
            rec("pkg-1.0/LICENSE", "GPL-2.0-only"),
            rec("pkg-1.0/LICENSE.exception", "GPL-2.0-only",
                detected="GPL-2.0-only WITH Classpath-exception-2.0"),
        ]
        records = process_license_params(scan_data(files), Path(SIM_ROOT), None, None)
        assert len(records) == 2

    def test_from_file_self_equal_to_self_counts_as_self(self):
        """from_file等于自身路径时视为自包含。"""
        files = [
            rec("pkg-1.0/LICENSES/A.txt", "MIT", from_file="pkg-1.0/LICENSES/A.txt"),
            rec("pkg-1.0/LICENSE.MIT", "MIT"),
        ]
        records = process_license_params(scan_data(files), Path(SIM_ROOT), None, None)
        assert [r["file"] for r in records] == ["pkg-1.0/LICENSE.MIT"]


class TestNameDedup:
    """-l模式下同SPDX多记录按路径优先级去重。"""

    def test_root_wins_across_locations(self):
        files = [
            rec("pkg-1.0/docs/MIT.txt", "MIT"),
            rec("pkg-1.0/LICENSES/MIT.txt", "MIT"),
            rec("pkg-1.0/LICENSE.MIT", "MIT"),
        ]
        records = process_license_params(scan_data(files), Path(SIM_ROOT), "MIT", None)
        assert len(records) == 1
        assert records[0]["file"] == "pkg-1.0/LICENSE.MIT"


class TestUserOverride:
    """-p的用户意志优先：显式指定的文件不受自动识别规则（文件名模式、
    根目录/LICENSES目录位置限制）约束，一律按用户输入处理。"""

    def test_filename_outside_license_patterns(self):
        """文件名不符合license命名模式（如NOTICE）时，显式-p仍选中该记录。"""
        files = [rec("pkg-1.0/third_party/NOTICE", "BSD-3-Clause"),
                 rec("pkg-1.0/LICENSE", "Apache-2.0")]
        got = one(process_license_params(
            scan_data(files), Path(SIM_ROOT), None, "third_party/NOTICE"))
        assert got["file"] == "pkg-1.0/third_party/NOTICE"
        assert got["spdx_identifier"] == "BSD-3-Clause"

    def test_non_top_level_licenses_dir(self):
        """二级LICENSES目录（自动识别仅认一级）中的文件，显式-p仍选中。"""
        files = [rec("pkg-1.0/vendor/lib/LICENSES/custom.txt", "MIT"),
                 rec("pkg-1.0/LICENSE", "Apache-2.0")]
        got = one(process_license_params(
            scan_data(files), Path(SIM_ROOT), None, "vendor/lib/LICENSES/custom.txt"))
        assert got["file"] == "pkg-1.0/vendor/lib/LICENSES/custom.txt"

    def test_arbitrary_name_with_detection(self):
        """任意命名的文件（README含完整license文本的变体场景），显式-p选中。"""
        files = [rec("pkg-1.0/docs/README", "GPL-3.0-only"),
                 rec("pkg-1.0/LICENSE", "Apache-2.0")]
        got = one(process_license_params(
            scan_data(files), Path(SIM_ROOT), None, "docs/README"))
        assert got["file"] == "pkg-1.0/docs/README"
        assert got["spdx_identifier"] == "GPL-3.0-only"

    def test_override_does_not_leak_into_auto_extraction(self):
        """对照：不指定-p时，上述非规范位置的记录不进入自动提取。"""
        files = [rec("pkg-1.0/third_party/NOTICE", "BSD-3-Clause"),
                 rec("pkg-1.0/vendor/lib/LICENSES/custom.txt", "MIT"),
                 rec("pkg-1.0/LICENSE", "Apache-2.0")]
        records = process_license_params(scan_data(files), Path(SIM_ROOT), None, None)
        assert [r["file"] for r in records] == ["pkg-1.0/LICENSE"]


class TestMalformedRecords:
    """异常扫描数据的容错。"""

    def test_missing_path_ignored_in_full_extraction(self):
        data = scan_data([{"detected_license_expression_spdx": "MIT"}])
        assert process_license_params(data, Path(SIM_ROOT), None, None) == []

    def test_missing_detections_ignored(self):
        data = scan_data([{"path": "pkg-1.0/LICENSE",
                           "detected_license_expression_spdx": "MIT"}])
        assert process_license_params(data, Path(SIM_ROOT), None, None) == []

    def test_empty_matches_ignored(self):
        r = rec("pkg-1.0/LICENSE", "MIT")
        r["license_detections"][0]["matches"] = []
        assert process_license_params(scan_data([r]), Path(SIM_ROOT), None, None) == []

    def test_long_rule_match_is_valid(self):
        """无.LICENSE规则但匹配长度>=20属有效检出。"""
        r = rec("pkg-1.0/LICENSE", "MIT", rule_suffix=".RULE", matched_len=50)
        records = process_license_params(scan_data([r]), Path(SIM_ROOT), None, None)
        assert len(records) == 1

    def test_short_rule_match_rejected(self):
        """无.LICENSE规则且匹配长度<20属短文本引用，拒绝。"""
        r = short_rec("pkg-1.0/LICENSE")
        assert process_license_params(scan_data([r]), Path(SIM_ROOT), None, None) == []

    def test_invalid_filename_rejected_even_with_long_match(self):
        """文件名不是license（如NOTICE.txt）时即使检出有效也拒绝。"""
        r = rec("pkg-1.0/NOTICE.txt", "MIT", rule_suffix=".RULE", matched_len=50)
        assert process_license_params(scan_data([r]), Path(SIM_ROOT), None, None) == []

    def test_missing_detections_falls_back_in_path_mode(self):
        data = scan_data([{"path": "pkg-1.0/LICENSE",
                           "detected_license_expression_spdx": "MIT"}])
        got = one(process_license_params(data, Path(SIM_ROOT), None, "LICENSE"))
        assert got["spdx_identifier"] == "Unknown"

    def test_empty_headers_list_does_not_crash(self):
        data = {"headers": [], "files": [rec("pkg-1.0/LICENSE", "MIT")]}
        records = process_license_params(data, Path(SIM_ROOT), None, None)
        assert len(records) == 1

    def test_no_headers_with_root_none_degrades(self):
        """无headers且root_path=None：按深度启发式仍可提取深度2合法文件名记录。"""
        data = {"files": [rec("pkg-1.0/LICENSE", "MIT")]}
        records = process_license_params(data, None, None, None)
        assert [r["file"] for r in records] == ["pkg-1.0/LICENSE"]
