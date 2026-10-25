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

"""_normalize_license_path（-p入口校验）的单元测试。

覆盖：正常解析返回(相对路径, 绝对路径)元组、前导斜杠与Windows分隔符、
越界拒绝（../上跳/外部绝对路径/symlink逃逸）、目录与不存在路径拒绝、
..绕回目标内的合法形态、空参数直通。
"""

import os
from pathlib import Path

import pytest

from ossinfo_extraction.license_extraction import process_license_params  # noqa: F401
from ossinfo_extraction.main import _normalize_license_path


@pytest.fixture
def target(tmp_path) -> Path:
    """模拟扫描目标：根LICENSE与LICENSES/MIT.txt，另含一个子目录。"""
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (tmp_path / "LICENSES").mkdir()
    (tmp_path / "LICENSES" / "MIT.txt").write_text("MIT\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    return tmp_path


def test_normal_returns_relative_and_absolute(target):
    rel, full = _normalize_license_path(target, "LICENSE")
    assert rel == "LICENSE"
    assert full == (target / "LICENSE").resolve()
    assert full.is_absolute()


def test_licenses_subpath(target):
    rel, full = _normalize_license_path(target, "LICENSES/MIT.txt")
    assert rel == "LICENSES/MIT.txt"
    assert full == (target / "LICENSES" / "MIT.txt").resolve()


def test_leading_slash(target):
    rel, _ = _normalize_license_path(target, "/LICENSE")
    assert rel == "LICENSE"


def test_windows_separator(target):
    rel, full = _normalize_license_path(target, "LICENSES\\MIT.txt")
    assert rel == "LICENSES/MIT.txt"
    assert full == (target / "LICENSES" / "MIT.txt").resolve()


@pytest.mark.parametrize("user_path", ["../outside.txt", "docs/../../outside.txt"])
def test_parent_escape_rejected(target, tmp_path_factory, user_path):
    (tmp_path_factory.mktemp("outside") / "outside.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        _normalize_license_path(target, user_path)


def test_external_absolute_rejected(target):
    with pytest.raises(SystemExit):
        _normalize_license_path(target, str(target.parent / "elsewhere.txt"))


def test_symlink_escape_rejected(target, tmp_path):
    """链接位于目标内但指向外部文件：resolve展开后越界，拒绝。"""
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("external\n", encoding="utf-8")
    link = target / "sneaky"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform/account")
    with pytest.raises(SystemExit):
        _normalize_license_path(target, "sneaky")


def test_symlink_inside_target_accepted(target):
    """链接指向目标内文件：合法。"""
    link = target / "alias"
    try:
        os.symlink(target / "LICENSE", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform/account")
    rel, full = _normalize_license_path(target, "alias")
    assert full == (target / "LICENSE").resolve()


def test_dotdot_reentering_target_accepted(target):
    """..绕回目标内（docs/../LICENSE）：resolve后仍在目标内，接受。"""
    rel, full = _normalize_license_path(target, "docs/../LICENSE")
    assert rel == "docs/../LICENSE"  # 相对形式原样保留供日志与回退使用
    assert full == (target / "LICENSE").resolve()


def test_directory_rejected(target):
    with pytest.raises(SystemExit):
        _normalize_license_path(target, "LICENSES")


def test_missing_file_rejected(target):
    with pytest.raises(SystemExit):
        _normalize_license_path(target, "NOT-EXIST")


def test_none_passthrough(target):
    assert _normalize_license_path(target, None) == (None, None)
