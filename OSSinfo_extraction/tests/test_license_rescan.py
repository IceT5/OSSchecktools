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

from pathlib import Path

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


def fail_scan(*args, **kwargs):
    raise AssertionError("re-scan should not be called")


def test_empty_records_returns_without_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(license_rescan, "run_scancode", fail_scan)
    records = []
    assert rescan_license_records(records, tmp_path) is records


def test_root_none_returns_without_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(license_rescan, "run_scancode", fail_scan)
    records = [record("LICENSE")]
    assert rescan_license_records(records, None) is records
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"


@pytest.mark.parametrize("bad_record", [{}, {"file": ""}, {"file": None}])
def test_record_without_file_skipped(tmp_path, monkeypatch, bad_record):
    monkeypatch.setattr(license_rescan, "run_scancode", fail_scan)
    rescan_license_records([dict(bad_record)], tmp_path)


def test_read_oserror_skips_file(tmp_path, monkeypatch, capsys):
    root = tmp_path
    blocked = write_gbk(root)
    records = [record("LICENSE")]
    original_read_bytes = Path.read_bytes

    def fake_read_bytes(self):
        if self == blocked:
            raise PermissionError("denied")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    monkeypatch.setattr(license_rescan, "run_scancode", fail_scan)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"


def test_decode_exception_skips_file(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]

    def boom(raw):
        raise ValueError("decode failed")

    monkeypatch.setattr(license_rescan, "_decode_license_text_with_status", boom)
    monkeypatch.setattr(license_rescan, "run_scancode", fail_scan)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"


def test_decoded_text_with_nul_skipped(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(
        license_rescan, "_decode_license_text_with_status", lambda raw: ("abc\x00def", True)
    )
    monkeypatch.setattr(license_rescan, "run_scancode", fail_scan)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"


def test_pass2_path_with_scan_root_prefix(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode",
                        fake_pass2(path="files/f0000/LICENSE"))
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"


def test_pass2_path_with_backslash(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode",
                        fake_pass2(path="files\\f0000\\LICENSE"))
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"


def test_expression_only_updates_both_fields(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode",
                        fake_pass2(spdx="", expression="mulanpsl-2.0"))
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "mulanpsl-2.0"
    assert records[0]["license_expression"] == "mulanpsl-2.0"


def test_spdx_only_updates_both_fields(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode",
                        fake_pass2(spdx="MulanPSL-2.0", expression=""))
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"
    assert records[0]["license_expression"] == "MulanPSL-2.0"


def test_multiple_different_files_mapped_independently(tmp_path, monkeypatch):
    root = tmp_path
    (root / "a").mkdir()
    (root / "b").mkdir()
    (root / "a" / "LICENSE").write_bytes("木兰许可证\n".encode("gbk"))
    (root / "b" / "LICENSE").write_bytes("木兰许可证\n".encode("gbk"))
    records = [record("a/LICENSE"), record("b/LICENSE")]

    def run(scan_target, result_json, **kwargs):
        assert (scan_target / "f0000" / "LICENSE").is_file()
        assert (scan_target / "f0001" / "LICENSE").is_file()
        return {"files": [
            {"path": "files/f0000/LICENSE",
             "detected_license_expression_spdx": "MIT",
             "detected_license_expression": "mit"},
            {"path": "files/f0001/LICENSE",
             "detected_license_expression_spdx": "Apache-2.0",
             "detected_license_expression": "apache-2.0"},
        ]}

    monkeypatch.setattr(license_rescan, "run_scancode", run)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MIT"
    assert records[1]["spdx_identifier"] == "Apache-2.0"


def test_run_scancode_empty_dict_keeps_records(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode", lambda *a, **k: {})
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"


def test_unmapped_result_path_skipped(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode", lambda *a, **k: {"files": [
        {"path": "unrelated/LICENSE",
         "detected_license_expression_spdx": "MIT",
         "detected_license_expression": "mit"},
        {},
    ]})
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"


def test_run_scancode_none_warns_and_keeps_records(tmp_path, monkeypatch, capsys):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode", lambda *a, **k: None)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"
    assert "returned no result" in capsys.readouterr().out


def test_temp_write_failure_keeps_records(tmp_path, monkeypatch, capsys):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", boom)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"
    assert "License re-scan failed" in capsys.readouterr().out


def test_jobs_passthrough_and_temp_result_outside_scan_dir(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    seen = {}

    def run(scan_target, result_json, **kwargs):
        seen["target"] = scan_target
        seen["result"] = result_json
        seen["kwargs"] = kwargs
        return fake_pass2()(scan_target, result_json, **kwargs)

    monkeypatch.setattr(license_rescan, "run_scancode", run)
    rescan_license_records(records, root, jobs=7, max_in_memory=300)
    assert seen["kwargs"]["jobs"] == 7
    assert seen["kwargs"]["max_in_memory"] == 300
    assert seen["kwargs"]["scan_license"] is True
    assert seen["kwargs"]["scan_copyright"] is False
    assert seen["result"].parent == seen["target"].parent
    assert not str(seen["result"]).startswith(str(seen["target"]) + "/")
    assert not seen["target"].parent.exists()  # 临时目录已清理


def test_utf8_bom_and_ascii_skipped(tmp_path, monkeypatch):
    root = tmp_path
    (root / "LICENSE").write_bytes(b"\xef\xbb\xbfMIT License\n")
    (root / "COPYING").write_bytes(b"MIT License\n")
    records = [record("LICENSE", "MIT", "mit"), record("COPYING", "MIT", "mit")]
    monkeypatch.setattr(license_rescan, "run_scancode", fail_scan)
    rescan_license_records(records, root)
    assert [r["spdx_identifier"] for r in records] == ["MIT", "MIT"]


def test_nul_containing_utf16_bytes_not_treated_as_utf8():
    assert license_rescan._is_utf8("MIT License".encode("utf-16-le")) is False


def test_latin1_file_rescanned(tmp_path, monkeypatch):
    root = tmp_path
    (root / "LICENSE").write_bytes("Copyright (c) Élastique\n".encode("latin-1"))
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode", fake_pass2(spdx="MIT", expression="mit"))
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MIT"


def test_gb18030_four_byte_char_rescanned(tmp_path, monkeypatch):
    root = tmp_path
    text = "木兰许可证\n" * 10 + "扩展字符𠀀\n"
    (root / "LICENSE").write_bytes(text.encode("gb18030"))
    records = [record("LICENSE")]

    def run(scan_target, result_json, **kwargs):
        temp_text = (scan_target / "f0000" / "LICENSE").read_text(encoding="utf-8")
        assert "𠀀" in temp_text
        return fake_pass2()(scan_target, result_json, **kwargs)

    monkeypatch.setattr(license_rescan, "run_scancode", run)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"


def test_empty_user_license_name_still_rescans(tmp_path, monkeypatch):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode", fake_pass2())
    rescan_license_records(records, root, user_license_name="")
    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"


def test_record_with_extract_prefix(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    write_gbk(root)
    records = [record("pkg.zip-extract/proj/LICENSE")]
    monkeypatch.setattr(license_rescan, "run_scancode", fake_pass2())
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"


def test_record_absolute_path(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    license_file = write_gbk(root)
    records = [record(str(license_file.resolve()))]
    monkeypatch.setattr(license_rescan, "run_scancode", fake_pass2())
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MulanPSL-2.0"


def test_same_file_different_spellings_single_scan(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    write_gbk(root)
    records = [record("LICENSE"), record("proj/LICENSE")]
    calls = []

    def run(scan_target, result_json, **kwargs):
        files = [p for p in scan_target.rglob("*") if p.is_file()]
        assert len(files) == 1
        calls.append(1)
        return fake_pass2()(scan_target, result_json, **kwargs)

    monkeypatch.setattr(license_rescan, "run_scancode", run)
    rescan_license_records(records, root)
    assert len(calls) == 1
    assert [r["spdx_identifier"] for r in records] == ["MulanPSL-2.0", "MulanPSL-2.0"]


def test_partial_multi_file_results_keep_other_record(tmp_path, monkeypatch):
    root = tmp_path
    (root / "a").mkdir()
    (root / "b").mkdir()
    (root / "a" / "LICENSE").write_bytes("木兰许可证\n".encode("gbk"))
    (root / "b" / "LICENSE").write_bytes("木兰许可证\n".encode("gbk"))
    records = [record("a/LICENSE"), record("b/LICENSE", spdx="LicenseRef-b", expression="b")]

    monkeypatch.setattr(license_rescan, "run_scancode", lambda *a, **k: {"files": [{
        "path": "files/f0000/LICENSE",
        "detected_license_expression_spdx": "MIT",
        "detected_license_expression": "mit",
    }]})
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "MIT"
    assert records[1]["spdx_identifier"] == "LicenseRef-b"


@pytest.mark.parametrize("exception", [ValueError, OSError])
def test_run_scancode_other_exceptions_keep_records(tmp_path, monkeypatch, capsys, exception):
    root = tmp_path
    write_gbk(root)
    records = [record("LICENSE")]

    def fail(*args, **kwargs):
        raise exception("boom")

    monkeypatch.setattr(license_rescan, "run_scancode", fail)
    rescan_license_records(records, root)
    assert records[0]["spdx_identifier"] == "LicenseRef-scancode-old"
    assert "License re-scan failed" in capsys.readouterr().out
