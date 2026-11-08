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

"""扁平压缩包根选择与路径清理的边界用例。

锁定已确认但尚未修复的卡点：

- 解压目录顶层混有 README、__MACOSX、pax_global_header 等归档元数据时，
  `_detect_nested_root` 的“唯一子项”条件不成立，不再下钻到真正的项目
  目录，导致 `pkg/LICENSE` 被当成深度 3 的子目录文件而丢失。
- 无根名锚定的 legacy 分支会剥离路径中任意位置的 `-extract` 段，而不是
  只处理开头的包装层。

这些用例按期望行为断言；修复前会失败，用于锁定问题。
"""

from pathlib import Path

import pytest

from ossinfo_extraction.license_extraction import _clean_scancode_path
from ossinfo_extraction.main import _detect_nested_root, _prepare_scan_target


def make_tree(root: Path, entries: list[str]) -> Path:
    """在 root 下创建文件树；每个 entry 是相对路径，内容无关。"""
    for entry in entries:
        path = root / entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")
    return root


class TestNestedRootWithArchiveMetadata:
    """解压目录顶层混有归档元数据时，仍应找到唯一项目目录。"""

    @pytest.mark.parametrize(
        "extra",
        [
            "README.txt",
            "README.md",
            ".DS_Store",
            "pax_global_header",
        ],
    )
    def test_single_project_dir_with_top_level_file(self, tmp_path, extra):
        root = make_tree(
            tmp_path / "pkg-mixed.tar.gz-extract", ["pkg/LICENSE", extra]
        )
        assert _detect_nested_root(root) == root / "pkg"

    def test_single_project_dir_with_macos_metadata_dir(self, tmp_path):
        root = make_tree(
            tmp_path / "pkg-mixed.tar.gz-extract",
            ["pkg/LICENSE", "__MACOSX/._LICENSE"],
        )
        assert _detect_nested_root(root) == root / "pkg"

    def test_single_project_dir_with_multiple_metadata_entries(self, tmp_path):
        root = make_tree(
            tmp_path / "pkg-mixed.tar.gz-extract",
            [
                "pkg/LICENSE",
                "README.txt",
                "__MACOSX/._LICENSE",
                "pax_global_header",
            ],
        )
        assert _detect_nested_root(root) == root / "pkg"


class TestNestedRootGuards:
    """修复混合包装包时，不得破坏既有根选择行为。"""

    def test_flat_project_root_is_kept(self, tmp_path):
        root = make_tree(
            tmp_path / "pkg.zip-extract",
            ["LICENSE", "README.md", "src/main.c"],
        )
        assert _detect_nested_root(root) == root

    def test_single_child_wrapper_still_descends(self, tmp_path):
        root = make_tree(tmp_path / "pkg.zip-extract", ["pkg-1.0/LICENSE"])
        assert _detect_nested_root(root) == root / "pkg-1.0"

    def test_multiple_project_dirs_are_kept(self, tmp_path):
        root = make_tree(
            tmp_path / "pkg.zip-extract", ["a/LICENSE", "b/LICENSE"]
        )
        assert _detect_nested_root(root) == root


class TestPrepareScanTarget:
    """混合包装包的根选择应反映到实际扫描根。"""

    def test_mixed_wrapper_scan_target_is_project_dir(
        self, tmp_path, monkeypatch
    ):
        root = make_tree(
            tmp_path / "pkg-mixed.tar.gz-extract",
            ["pkg/LICENSE", "README.txt", "__MACOSX/._LICENSE"],
        )
        target = tmp_path / "pkg-mixed.tar.gz"
        target.write_bytes(b"placeholder")

        monkeypatch.setattr(
            "ossinfo_extraction.main.run_extractcode", lambda _target: root
        )
        extract_dir, scan_target = _prepare_scan_target(target)
        assert extract_dir == root
        assert scan_target == root / "pkg"


class TestCleanScancodePath:
    """根名锚定与 legacy `-extract` 剥离的边界。"""

    @pytest.mark.parametrize(
        ("record", "root_name"),
        [
            ("Text-Extract/LICENSE", "text-extract"),
            ("text-extract/LICENSE", "TEXT-EXTRACT"),
            ("Project.zip-extract/LICENSE", "project.zip-extract"),
        ],
    )
    def test_root_anchor_is_case_insensitive(self, record, root_name):
        assert _clean_scancode_path(record, root_name) == record

    def test_leading_extract_wrapper_is_stripped(self):
        assert (
            _clean_scancode_path("pkg.zip-extract/pkg/LICENSE")
            == "pkg/LICENSE"
        )

    def test_inner_extract_directory_is_not_stripped(self):
        path = "pkg/src/foo-extract/LICENSE"
        assert _clean_scancode_path(path) == path

    def test_inner_extract_directory_is_not_stripped_with_other_root(self):
        path = "pkg/src/foo-extract/LICENSE"
        assert _clean_scancode_path(path, "other-root") == path
