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

"""license名称二次识别（rescan_license_records）的单元测试。

覆盖：GBK文件转UTF-8副本后重扫并修正名称、UTF-8文件跳过、
解码不精确跳过、用户-l优先、pass2无检出/异常时保留原结果、
多记录指向同一文件、临时文件内容为UTF-8。
"""

import pytest

from ossinfo_extraction import license_rescan
from ossinfo_extraction.license_rescan import rescan_license_records


def record(file_path, spdx="LicenseRef-scancode-old", expression="old"):
    return {
        "file": file_path,
        "spdx_identifier": spdx,
        "license_expression": expression,
        "matched_text": "",
    }


def write_gbk(root, name="LICENSE", text="木兰宽松许可证，第2版\n版权所有\n"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("gbk"))
    return path


def fake_pass2(spdx="MulanPSL-2.0", expression="mulanpsl-2.0", path="f0000/LICENSE"):
    def _run(scan_target, result_json, **kwargs):
        return {"files": [{
            "path": path,
            "detected_license_expression_spdx": spdx,
            "detected_license_expression": expression,
        }]}
    return _run


def test_gbk_file_rescanned_and_name_corrected(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    write_gbk(root)
    records = [record("proj/LICENSE")]
    calls = {}

    def run(scan_target, result_json, **kwargs):
        calls["target"] = scan_target
        calls["kwargs"] = kwargs
        temp_file = scan_target / "f0000" / "LICENSE"
        # 临时副本必须是UTF-8，且中文正确
        assert temp_file.read_text(encoding="utf-8") == "木兰宽松许可证，第2版\n版权所有\n"
        return fake_pass2()(scan_target, result_json, **kwargs)

    monkeypatch.setattr(license_rescan, "run_scancode", run)
    rescan_license_records(records, root)

    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"
    assert records[0]["license_expression"] == "mulanpsl-2.0"
    assert calls["kwargs"]["scan_license"] is True
    assert calls["kwargs"]["scan_copyright"] is False


def test_utf8_file_skipped(tmp_path, monkeypatch):
    root = tmp_path
    (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    records = [record("LICENSE", spdx="MIT", expression="mit")]

    def fail(*args, **kwargs):
        raise AssertionError("UTF-8 file should not be re-scanned")

    monkeypatch.setattr(license_rescan, "run_scancode", fail)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MIT"
    assert records[0]["license_expression"] == "mit"


def test_user_license_name_skips_rescan(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE", spdx="MulanPSL-2.0", expression="mulanpsl-2.0")]

    def fail(*args, **kwargs):
        raise AssertionError("user -l should skip re-scan")

    monkeypatch.setattr(license_rescan, "run_scancode", fail)
    rescan_license_records(records, root, user_license_name="MulanPSL-2.0")
    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"


def test_lossy_decode_skipped(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(
        license_rescan, "_decode_license_text_with_status", lambda raw: ("bad�", False)
    )

    def fail(*args, **kwargs):
        raise AssertionError("lossy file should not be re-scanned")

    monkeypatch.setattr(license_rescan, "run_scancode", fail)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"


def test_missing_file_skipped(tmp_path, monkeypatch):
    records = [record("LICENSE")]
    monkeypatch.setattr(
        license_rescan, "run_scancode",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("missing file should not be scanned")),
    )
    rescan_license_records(records, tmp_path)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"


def test_pass2_no_detection_keeps_first_pass(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode",
                        lambda *a, **k: {"files": [{"path": "f0000/LICENSE"}]})
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"
    assert records[0]["license_expression"] == "old"


def test_pass2_failure_keeps_first_pass(tmp_path, monkeypatch, capsys):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]

    def fail(*args, **kwargs):
        raise RuntimeError("scancode failed")

    monkeypatch.setattr(license_rescan, "run_scancode", fail)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"
    assert "License re-scan failed" in capsys.readouterr().out


def test_multiple_records_same_file_both_corrected(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE"), record("LICENSE", spdx="LicenseRef-other", expression="other")]
    monkeypatch.setattr(license_rescan, "run_scancode", fake_pass2())
    rescan_license_records(records, root)
    assert [r["spdx_identifier"] for r in records] == ["MulanPSL-2.0", "MulanPSL-2.0"]
    assert [r["license_expression"] for r in records] == ["mulanpsl-2.0", "mulanpsl-2.0"]
