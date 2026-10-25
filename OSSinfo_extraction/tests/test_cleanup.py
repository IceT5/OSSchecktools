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

"""cleanup_extract_dir的安全护栏单元测试。

该函数负责删除extractcode解压目录，其中“目录名必须以-extract结尾”
的校验是防止误删任意目录的安全栏，回归会静默扩大删除范围。
"""

from ossinfo_extraction.cleanup import cleanup_extract_dir


def test_removes_extract_dir(tmp_path):
    target = tmp_path / "pkg.zip-extract"
    target.mkdir()
    (target / "file.txt").write_text("x", encoding="utf-8")
    cleanup_extract_dir(target)
    assert not target.exists()


def test_missing_dir_is_noop(tmp_path):
    cleanup_extract_dir(tmp_path / "never-existed-extract")  # 不应抛异常


def test_plain_file_is_not_deleted(tmp_path):
    target = tmp_path / "file.zip-extract"
    target.write_text("i am a file", encoding="utf-8")
    cleanup_extract_dir(target)
    assert target.exists()  # 非目录跳过


def test_dir_without_extract_suffix_is_not_deleted(tmp_path):
    target = tmp_path / "important-data"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="utf-8")
    cleanup_extract_dir(target)
    assert target.exists() and (target / "keep.txt").exists()


def test_rmtree_failure_does_not_raise(tmp_path, monkeypatch):
    target = tmp_path / "pkg.tar.gz-extract"
    target.mkdir()

    def broken_rmtree(path, *args, **kwargs):
        raise OSError("simulated lock")

    monkeypatch.setattr("ossinfo_extraction.cleanup.shutil.rmtree", broken_rmtree)
    cleanup_extract_dir(target)  # 失败仅告警，不中断
