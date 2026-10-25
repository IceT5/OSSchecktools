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

"""pytest共享配置与fixtures。

- 注入src路径，使测试无需安装即可导入ossinfo_extraction包
- 提供合成真实软件包的session级fixtures（目录/多种压缩格式）
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from package_builder import (  # noqa: E402
    PKG_ROOT,
    british_entries,
    deep_nested_entries,
    empty_dir_entries,
    make_archive,
    no_license_entries,
    samplelib_entries,
    spdx_suffix_entries,
    write_tree,
)

PKG_ROOT_NAME = PKG_ROOT

EXPECTED_SCANCODE_VERSION = "32.5.0"


def _scancode_version() -> str:
    try:
        out = subprocess.run(["scancode", "--version"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace",
                             timeout=60).stdout
    except Exception:
        return ""
    for token in out.replace("\n", " ").split():
        if token[0:1].isdigit():
            return token
    return ""


needs_scancode = pytest.mark.skipif(
    shutil.which("scancode") is None or shutil.which("extractcode") is None,
    reason="scancode/extractcode not on PATH",
)


@pytest.fixture(scope="session", autouse=True)
def _gate_scancode_version(request):
    """扫描类用例对scancode版本的检出行为有约定，版本不符时明确跳过。"""
    if shutil.which("scancode") is None:
        return
    version = _scancode_version()
    if version and not version.startswith(EXPECTED_SCANCODE_VERSION):
        pytest.skip(f"scancode {version} != {EXPECTED_SCANCODE_VERSION}: "
                    f"检出行为断言可能不适用")


@pytest.fixture(autouse=True)
def _clean_extract_residue(pkg_dir):
    """用例开始前清理session包目录下的*-extract残留。

    CLI失败路径会刻意保留解压目录，残留会污染复用同一压缩包的后续用例。
    """
    yield
    if pkg_dir.exists():
        for residue in pkg_dir.glob("*-extract"):
            shutil.rmtree(residue, ignore_errors=True)


@pytest.fixture(scope="session")
def sample_dir(tmp_path_factory) -> Path:
    """samplelib标准布局的目录形态（无顶层目录，文件直接散开）。"""
    root = tmp_path_factory.mktemp("pkg") / "samplelib-flat"
    return write_tree(samplelib_entries(top=""), root)


@pytest.fixture(scope="session")
def sample_dir_nested(tmp_path_factory) -> Path:
    """samplelib标准布局的目录形态（含samplelib-1.2.3顶层单目录）。"""
    root = tmp_path_factory.mktemp("pkg") / "samplelib-nested-src"
    return write_tree(samplelib_entries(), root / PKG_ROOT_NAME).parent


@pytest.fixture(scope="session")
def pkg_dir(tmp_path_factory) -> Path:
    """存放本次会话所有合成压缩包的目录。"""
    return tmp_path_factory.mktemp("archives")


@pytest.fixture(scope="session")
def sample_zip(pkg_dir) -> Path:
    """标准包zip形态（顶层单目录，标准sdist嵌套形态）。"""
    return make_archive(samplelib_entries(), pkg_dir / "samplelib-1.2.3.zip")


@pytest.fixture(scope="session")
def sample_tar_gz(pkg_dir) -> Path:
    return make_archive(samplelib_entries(), pkg_dir / "samplelib-1.2.3.tar.gz")


@pytest.fixture(scope="session")
def sample_tgz(pkg_dir) -> Path:
    return make_archive(samplelib_entries(), pkg_dir / "samplelib-1.2.3.tgz")


@pytest.fixture(scope="session")
def sample_tar_bz2(pkg_dir) -> Path:
    return make_archive(samplelib_entries(), pkg_dir / "samplelib-1.2.3.tar.bz2")


@pytest.fixture(scope="session")
def sample_tbz2(pkg_dir) -> Path:
    return make_archive(samplelib_entries(), pkg_dir / "samplelib-1.2.3.tbz2")


@pytest.fixture(scope="session")
def sample_tar(pkg_dir) -> Path:
    return make_archive(samplelib_entries(), pkg_dir / "samplelib-1.2.3.tar")


@pytest.fixture(scope="session")
def sample_zip_flat(pkg_dir) -> Path:
    """无顶层目录的zip（解压后文件直接散开）。"""
    return make_archive(samplelib_entries(top=""), pkg_dir / "samplelib-flat.zip")


@pytest.fixture(scope="session")
def sample_zip_deep(pkg_dir) -> Path:
    """双层顶层目录的zip（wrapper再套项目目录）。"""
    return make_archive(deep_nested_entries(), pkg_dir / "samplelib-deep.zip")


@pytest.fixture(scope="session")
def shadow_zip(pkg_dir) -> Path:
    """遮蔽包：docs/LICENSE条目先于根LICENSE写入（复现#384顺序敏感场景）。"""
    return make_archive(samplelib_entries(shadow_order=True), pkg_dir / "shadowlib.zip")


@pytest.fixture(scope="session")
def british_zip(pkg_dir) -> Path:
    """英式拼写LICENCE包（tqdm场景）。"""
    return make_archive(british_entries(), pkg_dir / "tqdmlike-4.66.zip")


@pytest.fixture(scope="session")
def spdx_zip(pkg_dir) -> Path:
    """SPDX版本后缀文件名包（Apache-2.0/GPL-3.0-only）。"""
    return make_archive(spdx_suffix_entries(), pkg_dir / "spdxpkg-0.9.zip")


@pytest.fixture(scope="session")
def bare_zip(pkg_dir) -> Path:
    """不含license文件的包。"""
    return make_archive(no_license_entries(), pkg_dir / "barelib-0.1.zip")


@pytest.fixture(scope="session")
def near_empty_zip(pkg_dir) -> Path:
    """仅含占位文件的包（近空目录边界形态）。"""
    return make_archive(empty_dir_entries(), pkg_dir / "emptylib.zip")


def run_cli(work_dir: Path, *args: str, env_extra: dict | None = None):
    """以子进程运行cret CLI，返回(subprocess.CompletedProcess)。

    通过PYTHONPATH指向被测源码，无需安装即可运行。
    固定子进程编码与日志级别，隔离运行环境的差异。
    """
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUTF8"] = "1"      # 工具输出含中文，避免非CJK代码页编码失败
    env["LOG_LEVEL"] = "INFO"    # 断言依赖[INFO]日志，隔离外部LOG_LEVEL
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, "-m", "ossinfo_extraction.main", *args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", cwd=work_dir, env=env, timeout=600)
    except subprocess.TimeoutExpired:
        raise AssertionError("CLI执行超时（>600s）：scancode子进程可能卡死")
