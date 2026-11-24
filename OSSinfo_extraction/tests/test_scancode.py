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

"""ScanCode调用层（run_scancode/_load_partial_result）的单元测试。

覆盖退出码语义（仅exit=1允许部分结果）、部分结果的四个分支与命令行
组装契约（-l插入位置、-j/--max-in-memory映射），不依赖真实scancode。
"""

import json
import os

import pytest

from conftest import run_cli
from ossinfo_extraction.scancode import _load_partial_result, run_scancode


class TestLoadPartialResult:
    def test_missing_file_returns_none(self, tmp_path):
        assert _load_partial_result(tmp_path / "nope.json", 1) is None

    def test_corrupt_json_returns_none(self, tmp_path):
        bad = tmp_path / "result.json"
        bad.write_text("{not json", encoding="utf-8")
        assert _load_partial_result(bad, 1) is None

    def test_empty_files_returns_none(self, tmp_path):
        empty = tmp_path / "result.json"
        empty.write_text(json.dumps({"files": []}), encoding="utf-8")
        assert _load_partial_result(empty, 1) is None

    def test_valid_partial_result_returned(self, tmp_path):
        ok = tmp_path / "result.json"
        ok.write_text(json.dumps({"files": [{"path": "a"}]}), encoding="utf-8")
        data = _load_partial_result(ok, 1)
        assert data == {"files": [{"path": "a"}]}


class TestCommandAssembly:
    def test_license_flag_inserted_after_scancode(self, tmp_path, monkeypatch):
        """-l插入在scancode之后第一个位置；-n/--max-in-memory按值映射。"""
        import sys

        result_json = tmp_path / "r.json"
        seen = {}

        def fake_run(cmd, stdout=None, stderr=None):
            seen["cmd"] = list(cmd)

            class R:
                returncode = 0

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        result_json.write_text(json.dumps({"files": []}), encoding="utf-8")
        run_scancode(tmp_path / "target", result_json, jobs=7,
                     scan_license=True, max_in_memory=300)
        cmd = seen["cmd"]
        assert cmd[0] == "scancode"
        assert cmd[1] == "-l"                       # scan_license=True插入位置
        assert "-c" in cmd                          # copyright扫描保留
        assert "--only-findings" in cmd
        n_index = cmd.index("-n")
        assert cmd[n_index + 1] == "7"
        mem_index = cmd.index("--max-in-memory")
        assert cmd[mem_index + 1] == "300"

    def test_no_license_flag_by_default(self, tmp_path, monkeypatch):
        result_json = tmp_path / "r.json"
        seen = {}

        def fake_run(cmd, stdout=None, stderr=None):
            seen["cmd"] = list(cmd)

            class R:
                returncode = 0

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        result_json.write_text(json.dumps({"files": []}), encoding="utf-8")
        run_scancode(tmp_path / "target", result_json)
        assert "-l" not in seen["cmd"]

    def test_copyright_flag_omitted_when_disabled(self, tmp_path, monkeypatch):
        """重扫license时只加-l，不加-c。"""
        result_json = tmp_path / "r.json"
        seen = {}

        def fake_run(cmd, stdout=None, stderr=None):
            seen["cmd"] = list(cmd)

            class R:
                returncode = 0

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        result_json.write_text(json.dumps({"files": []}), encoding="utf-8")
        run_scancode(tmp_path / "target", result_json,
                     scan_license=True, scan_copyright=False)
        assert seen["cmd"][1] == "-l"
        assert "-c" not in seen["cmd"]

    def test_exit_2_without_result_raises(self, tmp_path, monkeypatch):
        result_json = tmp_path / "r.json"  # 本次未生成结果

        def fake_run(cmd, stdout=None, stderr=None):
            class R:
                returncode = 2

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        with pytest.raises(RuntimeError):
            run_scancode(tmp_path / "target", result_json)

    def test_exit_2_with_stale_result_raises(self, tmp_path, monkeypatch):
        """issue A：exit=2时路径上的旧result.json绝不能作为本次结果。"""
        result_json = tmp_path / "r.json"
        result_json.write_text(json.dumps({"files": [{"path": "old"}]}), encoding="utf-8")

        def fake_run(cmd, stdout=None, stderr=None):
            class R:
                returncode = 2

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        with pytest.raises(RuntimeError):
            run_scancode(tmp_path / "target", result_json)

    def test_other_nonzero_with_stale_result_raises(self, tmp_path, monkeypatch):
        """除1/2外的非零码同样不使用旧结果。"""
        result_json = tmp_path / "r.json"
        result_json.write_text(json.dumps({"files": [{"path": "old"}]}), encoding="utf-8")

        def fake_run(cmd, stdout=None, stderr=None):
            class R:
                returncode = 3

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        with pytest.raises(RuntimeError):
            run_scancode(tmp_path / "target", result_json)

    def test_exit_1_without_result_raises(self, tmp_path, monkeypatch):
        result_json = tmp_path / "r.json"  # 本次未生成结果

        def fake_run(cmd, stdout=None, stderr=None):
            class R:
                returncode = 1

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        with pytest.raises(RuntimeError):
            run_scancode(tmp_path / "target", result_json)

    def test_exit_1_with_corrupt_result_raises(self, tmp_path, monkeypatch):
        result_json = tmp_path / "r.json"
        result_json.write_text("{not json", encoding="utf-8")

        def fake_run(cmd, stdout=None, stderr=None):
            class R:
                returncode = 1

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        with pytest.raises(RuntimeError):
            run_scancode(tmp_path / "target", result_json)

    def test_exit_1_with_partial_continues(self, tmp_path, monkeypatch):
        result_json = tmp_path / "r.json"
        result_json.write_text(json.dumps({"files": [{"path": "a"}]}), encoding="utf-8")

        def fake_run(cmd, stdout=None, stderr=None):
            class R:
                returncode = 1

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        data = run_scancode(tmp_path / "target", result_json)
        assert data["files"] == [{"path": "a"}]


@pytest.mark.skipif(os.name == "nt", reason="fake scancode uses a POSIX shell script")
def test_cli_aborts_on_cli_error_with_stale_result(tmp_path):
    """CLI级issue A：exit=2且输出目录有旧result.json时，流水线必须中断，
    不得用旧结果生成当前项目的报告。"""
    target = tmp_path / "pkg"
    target.mkdir()
    (target / "LICENSE").write_text("CURRENT PACKAGE LICENSE\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "result.json").write_text(
        json.dumps({"files": [{"path": "old/LICENSE",
                               "detected_license_expression_spdx": "MIT",
                               "detected_license_expression": "mit",
                               "copyrights": [{"copyright": "Copyright 2021 OLD AUTHOR"}],
                               "license_detections": [{"matches": [{
                                   "rule_identifier": "mit.LICENSE",
                                   "matched_length": 100,
                                   "matched_text": "OLD MIT LICENSE TEXT"}]}]}]}),
        encoding="utf-8",
    )
    bindir = tmp_path / "bin"
    bindir.mkdir()
    scanner = bindir / "scancode"
    scanner.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = "--version" ]; then echo "ScanCode version: 32.5.0"; exit 0; fi\n'
        'exit 2\n',
        encoding="utf-8",
    )
    scanner.chmod(0o755)

    result = run_cli(
        tmp_path,
        "-t", str(target), "-n", "CURRENT-SOFTWARE", "-v", "2.0", "-o", str(out),
        env_extra={"PATH": str(bindir) + os.pathsep + os.environ["PATH"]},
    )

    assert result.returncode != 0
    assert not (out / "Readme.opensource").exists()
