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

"""Readme.opensource写出（write_readme_opensource）的单元测试。

覆盖输出格式逐段断言、license文件定位与全文读取、matched_text回退、
无license记录的占位输出、非UTF-8文件容错。
"""

import pytest
from pathlib import Path

from ossinfo_extraction.readme_opensource import write_readme_opensource


@pytest.fixture
def project(tmp_path) -> Path:
    """模拟项目根：带顶层目录名（与扫描记录路径前缀一致）。"""
    root = tmp_path / "samplelib-1.2.3"
    (root / "LICENSES").mkdir(parents=True)
    (root / "LICENSE").write_text("MIT License\nline2\n", encoding="utf-8")
    (root / "LICENSES" / "Apache-2.0.txt").write_text("Apache License\n", encoding="utf-8")
    (root / "latin.txt").write_bytes(b"Copyright (c) \xc9lastique\n")  # latin-1字节
    return root


def read(out: Path) -> str:
    return out.read_text(encoding="utf-8")


def test_full_output_format(project, tmp_path):
    out = tmp_path / "Readme.opensource"
    records = [{"file": "samplelib-1.2.3/LICENSE", "spdx_identifier": "MIT",
                "license_expression": "MIT", "matched_text": "should not be used"}]
    write_readme_opensource(out, "samplelib", "1.2.3",
                            ["Copyright (c) 2024 Dev"], records, project)
    text = read(out)
    assert text.startswith("Software: samplelib 1.2.3\n")
    assert "Copyright Notice(s):\nCopyright (c) 2024 Dev\n" in text
    assert "License: MIT\nFull License Text:\nMIT License\nline2\n" in text
    assert "should not be used" not in text  # 文件读取成功时不回退matched_text


def test_matched_text_fallback_when_file_missing(project, tmp_path):
    out = tmp_path / "Readme.opensource"
    records = [{"file": "samplelib-1.2.3/GONE", "spdx_identifier": "MIT",
                "license_expression": "MIT", "matched_text": "fall back text"}]
    write_readme_opensource(out, "samplelib", "1.2.3", [], records, project)
    text = read(out)
    assert "fall back text" in text
    assert "[No license text available]" not in text


def test_no_text_available_placeholder(project, tmp_path):
    out = tmp_path / "Readme.opensource"
    records = [{"file": "", "spdx_identifier": "MIT",
                "license_expression": "MIT", "matched_text": ""}]
    write_readme_opensource(out, "samplelib", "1.2.3", [], records, project)
    assert "[No license text available]" in read(out)


def test_no_license_records_placeholder(project, tmp_path):
    out = tmp_path / "Readme.opensource"
    write_readme_opensource(out, "samplelib", "1.2.3", [], [], project)
    text = read(out)
    assert "License: No license information found.\n" in text
    assert "[No license text available]" in text


def test_no_copyright_notice(project, tmp_path):
    out = tmp_path / "Readme.opensource"
    write_readme_opensource(out, "samplelib", "1.2.3", [], [], project)
    assert "No copyright information found." in read(out)


def test_multiple_licenses_layout(project, tmp_path):
    out = tmp_path / "Readme.opensource"
    records = [
        {"file": "samplelib-1.2.3/LICENSE", "spdx_identifier": "MIT",
         "license_expression": "MIT", "matched_text": ""},
        {"file": "samplelib-1.2.3/LICENSES/Apache-2.0.txt", "spdx_identifier": "Apache-2.0",
         "license_expression": "Apache-2.0", "matched_text": ""},
    ]
    write_readme_opensource(out, "samplelib", "1.2.3", [], records, project)
    text = read(out)
    mit_pos = text.index("License: MIT\n")
    apache_pos = text.index("License: Apache-2.0\n")
    assert 0 < mit_pos < apache_pos
    assert "Apache License\n" in text


def test_latin1_file_does_not_crash(project, tmp_path):
    """非UTF-8编码的license文件按errors=replace容错读入。"""
    out = tmp_path / "Readme.opensource"
    records = [{"file": "samplelib-1.2.3/latin.txt", "spdx_identifier": "Unknown",
                "license_expression": "Unknown", "matched_text": ""}]
    write_readme_opensource(out, "samplelib", "1.2.3", [], records, project)
    text = read(out)
    assert "lastique" in text  # 可读部分保留


def test_license_text_without_trailing_newline_normalized(project, tmp_path):
    """license全文无结尾换行时补换行再加空行分隔。"""
    (project / "LICENSE").write_text("MIT text no newline", encoding="utf-8")
    out = tmp_path / "Readme.opensource"
    records = [{"file": "samplelib-1.2.3/LICENSE", "spdx_identifier": "MIT",
                "license_expression": "MIT", "matched_text": ""}]
    write_readme_opensource(out, "samplelib", "1.2.3", [], records, project)
    assert "MIT text no newline\n\n" in read(out)


def test_matched_text_without_trailing_newline_normalized(project, tmp_path):
    """matched_text回退时无结尾换行同样补齐。"""
    out = tmp_path / "Readme.opensource"
    records = [{"file": "samplelib-1.2.3/GONE", "spdx_identifier": "MIT",
                "license_expression": "MIT", "matched_text": "raw fallback"}]
    write_readme_opensource(out, "samplelib", "1.2.3", [], records, project)
    assert "raw fallback\n\n" in read(out)


def test_single_subdir_fallback_locates_license(tmp_path):
    """记录无根名前缀时，根下唯一子目录的回退组合可命中文件。"""
    root = tmp_path / "wrapper"
    inner = root / "samplelib-1.2.3"
    inner.mkdir(parents=True)
    (inner / "LICENSE").write_text("inner license\n", encoding="utf-8")
    out = tmp_path / "Readme.opensource"
    records = [{"file": "LICENSE", "spdx_identifier": "MIT",
                "license_expression": "MIT", "matched_text": ""}]
    write_readme_opensource(out, "sw", "1", [], records, root)
    assert "inner license\n" in read(out)


def test_blank_copyright_entries_skipped(project, tmp_path):
    out = tmp_path / "Readme.opensource"
    write_readme_opensource(out, "sw", "1", ["(c) 2020 A", "   ", ""], [], project)
    text = read(out)
    assert "(c) 2020 A" in text
    assert "\n\n\n" not in text  # 空白条目不产生空行
