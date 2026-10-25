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

"""license提取报告（write_license_report）的单元测试。"""

from ossinfo_extraction.license_extraction import write_license_report


def test_empty_records_placeholder(tmp_path):
    out = tmp_path / "r.txt"
    write_license_report(out, "sw", "1.0", [])
    text = out.read_text(encoding="utf-8")
    assert "No license information found." in text
    assert "Software Name: sw" in text


def test_record_sections(tmp_path):
    out = tmp_path / "r.txt"
    records = [{"file": "pkg-1.0/LICENSE", "spdx_identifier": "MIT",
                "license_expression": "MIT", "matched_text": "hello"}]
    write_license_report(out, "sw", "1.0", records)
    text = out.read_text(encoding="utf-8")
    assert "Total unique licenses found: 1" in text
    assert "--- License #1 ---" in text
    assert "File: pkg-1.0/LICENSE" in text
    assert "SPDX Identifier: MIT" in text
    assert "License Expression: MIT" in text
    assert "Matched Text:\nhello\n" in text


def test_matched_text_truncated_at_500(tmp_path):
    out = tmp_path / "r.txt"
    records = [{"file": "f", "spdx_identifier": "MIT",
                "license_expression": "MIT", "matched_text": "x" * 600}]
    write_license_report(out, "sw", "1.0", records)
    text = out.read_text(encoding="utf-8")
    assert "x" * 500 + "..." in text
    assert "x" * 501 not in text


def test_missing_optional_fields_use_na(tmp_path):
    out = tmp_path / "r.txt"
    records = [{"file": "f"}]
    write_license_report(out, "sw", "1.0", records)
    text = out.read_text(encoding="utf-8")
    assert "SPDX Identifier: N/A" in text
    assert "License Expression: N/A" in text
    assert "Matched Text:" not in text  # 无matched_text时不输出该段
