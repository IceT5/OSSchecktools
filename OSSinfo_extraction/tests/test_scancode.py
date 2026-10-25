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

覆盖部分结果容错的四个分支与命令行组装契约（-l插入位置、
-j/--max-in-memory映射），不依赖真实scancode。
"""

import json

import pytest

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

    def test_nonzero_exit_without_partial_raises(self, tmp_path, monkeypatch):
        result_json = tmp_path / "r.json"  # 不存在部分结果

        def fake_run(cmd, stdout=None, stderr=None):
            class R:
                returncode = 2

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        with pytest.raises(RuntimeError):
            run_scancode(tmp_path / "target", result_json)

    def test_nonzero_exit_with_partial_continues(self, tmp_path, monkeypatch, capsys):
        result_json = tmp_path / "r.json"
        result_json.write_text(json.dumps({"files": [{"path": "a"}]}), encoding="utf-8")

        def fake_run(cmd, stdout=None, stderr=None):
            class R:
                returncode = 1

            return R()

        monkeypatch.setattr("ossinfo_extraction.scancode.subprocess.run", fake_run)
        data = run_scancode(tmp_path / "target", result_json)
        assert data["files"] == [{"path": "a"}]
