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

"""重扫与报告输出的集成测试。

通过 main._write_reports 串起“参数组合 -> license记录 -> 重扫 -> 两个报告”，
验证四种参数组合的调用/跳过行为，以及 *_license 与 Readme.opensource
使用同一套名称。
"""

import re

import pytest

from ossinfo_extraction import license_rescan, main


def write_gbk(root, name="LICENSE"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes("木兰宽松许可证，第2版\n版权所有\n".encode("gbk"))
    return path


def make_record(spdx="LicenseRef-scancode-mulanpsl-2.0-en", expression="mulanpsl-2.0-en"):
    return {
        "file": "LICENSE",
        "spdx_identifier": spdx,
        "license_expression": expression,
        "matched_text": "",
    }


def read_names(output_files):
    """从license报告和Readme中提取名称集合。"""
    license_text = output_files[2].read_text(encoding="utf-8")
    readme_text = output_files[3].read_text(encoding="utf-8")
    report_names = set(re.findall(r"^SPDX Identifier: (.+)$", license_text, re.M))
    readme_names = set(re.findall(r"^License: (.+)$", readme_text, re.M))
    return report_names, readme_names


def run_write_reports(tmp_path, monkeypatch, record, license_name, license_path=("__unset__",),
                      fake_scan=None):
    root = tmp_path / "proj"
    root.mkdir()
    write_gbk(root)
    output_files = (
        tmp_path / "result.json",
        tmp_path / "proj_copyright",
        tmp_path / "proj_license",
        tmp_path / "Readme.opensource",
    )

    monkeypatch.setattr(main, "has_error", lambda: False)
    monkeypatch.setattr(main, "extract_and_duplicate_copyright",
                        lambda data, output: output.write_text("", encoding="utf-8") or [])
    monkeypatch.setattr(main, "process_license_params",
                        lambda data, root_path, license_name, license_path, license_full_path: [record])
    if fake_scan is not None:
        monkeypatch.setattr(license_rescan, "run_scancode", fake_scan)

    actual_path = None if license_path == "__unset__" else license_path
    main._write_reports(
        {"files": []}, root, ("sw", "1", license_name), output_files,
        actual_path, None, jobs=3, max_in_memory=200,
    )
    return output_files


def corrected_scan(counter=None):
    def run(scan_target, result_json, **kwargs):
        if counter is not None:
            counter.append(1)
        assert kwargs["scan_license"] is True
        assert kwargs["scan_copyright"] is False
        assert kwargs["jobs"] == 3
        assert kwargs["max_in_memory"] == 200
        temp_text = (scan_target / "f0000" / "LICENSE").read_text(encoding="utf-8")
        assert "木兰宽松许可证" in temp_text
        return {"files": [{
            "path": "files/f0000/LICENSE",
            "detected_license_expression_spdx": "MulanPSL-2.0",
            "detected_license_expression": "mulanpsl-2.0",
        }]}
    return run


def fail_scan(*args, **kwargs):
    raise AssertionError("re-scan should not be called")


def test_no_params_rescans_and_outputs_consistent(tmp_path, monkeypatch):
    calls = []
    outputs = run_write_reports(tmp_path, monkeypatch, make_record(),
                                license_name=None, fake_scan=corrected_scan(calls))
    assert len(calls) == 1
    report_names, readme_names = read_names(outputs)
    assert report_names == {"MulanPSL-2.0"}
    assert readme_names == report_names


def test_l_only_skips_rescan_and_user_name_wins(tmp_path, monkeypatch):
    outputs = run_write_reports(
        tmp_path, monkeypatch, make_record(spdx="GPL-2.0", expression="gpl-2.0"),
        license_name="GPL-2.0", fake_scan=fail_scan,
    )
    report_names, readme_names = read_names(outputs)
    assert report_names == {"GPL-2.0"}
    assert readme_names == report_names


def test_p_only_rescans(tmp_path, monkeypatch):
    calls = []
    outputs = run_write_reports(
        tmp_path, monkeypatch, make_record(),
        license_name=None, license_path="LICENSE",
        fake_scan=corrected_scan(calls),
    )
    assert len(calls) == 1
    report_names, readme_names = read_names(outputs)
    assert report_names == {"MulanPSL-2.0"}
    assert readme_names == report_names


def test_l_and_p_skips_rescan(tmp_path, monkeypatch):
    outputs = run_write_reports(
        tmp_path, monkeypatch, make_record(spdx="MulanPSL-2.0", expression="mulanpsl-2.0"),
        license_name="MulanPSL-2.0", license_path="LICENSE",
        fake_scan=fail_scan,
    )
    report_names, readme_names = read_names(outputs)
    assert report_names == {"MulanPSL-2.0"}
    assert readme_names == report_names


def test_p_only_unknown_record_corrected(tmp_path, monkeypatch):
    calls = []
    outputs = run_write_reports(
        tmp_path, monkeypatch, make_record(spdx="Unknown", expression="Unknown"),
        license_name=None, license_path="LICENSE",
        fake_scan=corrected_scan(calls),
    )
    assert len(calls) == 1
    report_names, readme_names = read_names(outputs)
    assert report_names == {"MulanPSL-2.0"}
    assert readme_names == report_names


def test_rescan_no_detection_outputs_consistent(tmp_path, monkeypatch):
    def no_detection(scan_target, result_json, **kwargs):
        return {"files": [{"path": "files/f0000/LICENSE"}]}

    outputs = run_write_reports(tmp_path, monkeypatch, make_record(),
                                license_name=None, fake_scan=no_detection)
    report_names, readme_names = read_names(outputs)
    assert report_names == {"LicenseRef-scancode-mulanpsl-2.0-en"}
    assert readme_names == report_names


def test_rescan_failure_outputs_consistent(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("scancode failed")

    outputs = run_write_reports(tmp_path, monkeypatch, make_record(),
                                license_name=None, fake_scan=fail)
    report_names, readme_names = read_names(outputs)
    assert report_names == {"LicenseRef-scancode-mulanpsl-2.0-en"}
    assert readme_names == report_names


def test_empty_records_no_rescan(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    write_gbk(root)
    output_files = (
        tmp_path / "result.json",
        tmp_path / "proj_copyright",
        tmp_path / "proj_license",
        tmp_path / "Readme.opensource",
    )
    monkeypatch.setattr(main, "has_error", lambda: False)
    monkeypatch.setattr(main, "extract_and_duplicate_copyright",
                        lambda data, output: output.write_text("", encoding="utf-8") or [])
    monkeypatch.setattr(main, "process_license_params",
                        lambda *args, **kwargs: [])
    monkeypatch.setattr(license_rescan, "run_scancode", fail_scan)
    main._write_reports({"files": []}, root, ("sw", "1", None), output_files,
                        None, None, jobs=3, max_in_memory=200)
    readme_text = output_files[3].read_text(encoding="utf-8")
    assert "License: No license information found." in readme_text


def test_l_no_match_empty_file_no_rescan(tmp_path, monkeypatch):
    rec = make_record(spdx="MulanPSL-2.0", expression="mulanpsl-2.0")
    rec["file"] = ""
    outputs = run_write_reports(tmp_path, monkeypatch, rec,
                                license_name="MulanPSL-2.0", fake_scan=fail_scan)
    report_names, readme_names = read_names(outputs)
    assert report_names == {"MulanPSL-2.0"}
    assert readme_names == report_names
