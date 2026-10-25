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

"""合成真实软件包构造器。

构造一个虚构但高度仿真的开源软件包 samplelib，用于端到端测试：
- 覆盖license文件的各种真实命名与位置（根目录/LICENSES目录/嵌套子目录）
- 覆盖版权声明的各种真实书写形式（Copyright (c)/(c)/copr./Copyright (C)）
- 支持多种压缩格式与多种目录嵌套形态，模拟真实世界的发行包

license全文取自ScanCode licensedcode数据（tests/data/licenses/），
保证扫描引擎能够真实检出对应SPDX标识。
"""

import io
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

LICENSES_DATA = Path(__file__).parent / "data" / "licenses"


def license_text(spdx_name: str) -> str:
    """读取tests/data/licenses下的真实license全文。"""
    return (LICENSES_DATA / f"{spdx_name}.txt").read_text(encoding="utf-8")


@dataclass
class Entry:
    """包内单个文件条目。seq控制写入顺序（用于构造扫描记录顺序敏感的场景）。"""

    path: str
    content: str
    seq: int = 0

    def encoded(self) -> bytes:
        return self.content.encode("utf-8")


PKG_ROOT = "samplelib-1.2.3"

C_SAMPLELIB = """/* samplelib - a tiny sample library */
#include "samplelib.h"

/*
 * Copyright (c) 2007-2024 SampleLib Dev Team
 * SPDX-License-Identifier: MIT
 */

int samplelib_version(void) { return 0x010203; }
"""

C_UTILS = """/* utils for samplelib */
#include "utils.h"

/* (c) 2025 Helper Corp. All rights reserved. */

int util_add(int a, int b) { return a + b; }
"""

C_VENDOR = """/* vendored code, do not edit */
#include "vendor.h"

/*
 * copr. 2019 Vendor GmbH
 * Licensed under the Apache License, Version 2.0
 */

int vendor_lookup(int id) { return id; }
"""

H_BANNER = """/* banner.h - build information */
#ifndef BANNER_H
#define BANNER_H

/* Copyright (C) 2021-2024 Acme Systems, Inc. */

#define SAMPLELIB_BUILD "release"
#endif
"""

C_TINYLIB = """/* tinylib - vendored third-party helper */
#include <stddef.h>

/* Copyright (c) 2018 TinyLib Authors */

size_t tiny_strlen(const char *s);
"""

README = """# samplelib

A sample project used by OSSinfo_extraction end-to-end tests.

This package intentionally mixes several license file locations and
copyright statement styles that occur in real-world distributions.
"""

SETUP_PY = """from setuptools import setup

setup(name="samplelib", version="1.2.3", packages=["samplelib"])
"""

NOTICE = """samplelib 1.2.3
This product includes software developed by the SampleLib Dev Team.
Third-party components are listed under third_party/.
"""


def samplelib_entries(
    top: str = PKG_ROOT,
    license_filename: str = "LICENSE",
    include_root_license: bool = True,
    shadow_order: bool = False,
) -> list:
    """生成samplelib标准布局的条目列表。

    Args:
        top: 包内顶层目录；空串表示无顶层目录（文件直接位于包根）
        license_filename: 根目录license文件名（LICENSE/LICENCE等）
        include_root_license: 是否包含根目录license文件
        shadow_order: True时docs/LICENSE条目先于根license条目写入，
            用于复现“扫描记录顺序导致嵌套同名文件遮蔽根文件”的场景

    Returns:
        list[Entry]: 按写入顺序排列的条目
    """
    def rel(path: str) -> str:
        return f"{top}/{path}" if top else path

    root_license_seq = 0
    entries = []
    if shadow_order:
        # docs/LICENSE 先写入（seq=0），模拟扫描记录中嵌套同名文件排在前面
        entries.append(Entry(rel("docs/LICENSE"), license_text("BSD-3-Clause"), seq=0))
        root_license_seq = 1

    if include_root_license:
        entries.append(Entry(rel(license_filename), license_text("MIT"), seq=root_license_seq))
        entries.append(Entry(rel("LICENSES/Apache-2.0.txt"), license_text("Apache-2.0"), seq=2))
        entries.append(Entry(rel("LICENSES/GPL-3.0-only.txt"), license_text("GPL-3.0-only"), seq=3))
        # LICENSES目录内允许任意命名的license文件（宽松接受策略）
        entries.append(Entry(rel("LICENSES/custom-exception.md"),
                             "Custom exception clause for samplelib.\n", seq=4))

    docs_entries = [] if shadow_order else [Entry(rel("docs/LICENSE"),
                                                  license_text("BSD-3-Clause"), seq=5)]
    entries.extend(docs_entries + [
        Entry(rel("docs/manual.md"), "# samplelib manual\n\nUsage notes.\n", seq=6),
        Entry(rel("third_party/tinylib/LICENSE"), license_text("Apache-2.0"), seq=7),
        Entry(rel("third_party/tinylib/tiny.c"), C_TINYLIB, seq=8),
        Entry(rel("src/samplelib.c"), C_SAMPLELIB, seq=9),
        Entry(rel("src/utils.c"), C_UTILS, seq=10),
        Entry(rel("src/vendor.c"), C_VENDOR, seq=11),
        Entry(rel("src/banner.h"), H_BANNER, seq=12),
        Entry(rel("NOTICE"), NOTICE, seq=13),
        Entry(rel("COPYING.LESSER"), license_text("LGPL-2.1"), seq=14),
        Entry(rel("README.md"), README, seq=15),
        Entry(rel("setup.py"), SETUP_PY, seq=16),
    ])
    entries.sort(key=lambda e: e.seq)
    return entries


def spdx_suffix_entries(top: str = "spdxpkg-0.9") -> list:
    """生成“文件名以SPDX版本后缀结尾”的包。

    Apache-2.0 的 Path().suffix 是 ".0"、GPL-3.0-only 是 ".0-only"，
    这类文件名曾被扩展名白名单误拒（LicenseIdentifierSuffix修复的靶点）。
    """
    def rel(path: str) -> str:
        return f"{top}/{path}"

    return [
        Entry(rel("Apache-2.0"), license_text("Apache-2.0"), seq=0),
        Entry(rel("GPL-3.0-only"), license_text("GPL-3.0-only"), seq=1),
        Entry(rel("main.c"), "/* (c) 2024 SpdxPkg Authors */\nint main(void){return 0;}\n", seq=2),
        Entry(rel("README"), "spdx suffix package\n", seq=3),
    ]


def no_license_entries(top: str = "barelib-0.1") -> list:
    """生成不含任何license文件的包。"""
    def rel(path: str) -> str:
        return f"{top}/{path}"

    return [
        Entry(rel("bare.c"), "/* barelib */\nint bare(void){return 0;}\n", seq=0),
        Entry(rel("README.md"), "no license inside\n", seq=1),
    ]


def british_entries(top: str = "tqdmlike-4.66") -> list:
    """生成英式拼写LICENCE的包（tqdm场景：sdist中license文件名为LICENCE）。"""
    def rel(path: str) -> str:
        return f"{top}/{path}"

    return [
        Entry(rel("LICENCE"), license_text("Apache-2.0"), seq=0),
        Entry(rel("core.py"), "# core\n# Copyright (c) 2024 BritishPkg Authors\n", seq=1),
        Entry(rel("README.md"), "british spelling package\n", seq=2),
    ]


def deep_nested_entries() -> list:
    """生成双层顶层目录的包（wrapper目录再套项目目录）。"""
    return samplelib_entries(top=f"release-1.2.3/{PKG_ROOT}")


def empty_dir_entries() -> list:
    """生成仅含一个占位文件的包（提取后接近空目录的边界形态）。"""
    return [Entry(f"{PKG_ROOT}/.placeholder", "\n", seq=0)]


def chinese_entries(top: str = "项目库-1.0") -> list:
    """生成中文目录/文件名的包（编码与嵌套检测的综合边界）。"""
    def rel(path: str) -> str:
        return f"{top}/{path}"

    return [
        Entry(rel("LICENSE"), license_text("MIT"), seq=0),
        Entry(rel("源码/主程序.c"), "/* Copyright (c) 2024 中文作者 */\nint main(){}\n", seq=1),
        Entry(rel("说明.md"), "# 项目说明\n", seq=2),
    ]


def mismatch_entries(top: str = "mismatch-1.0") -> list:
    """生成文件名与内容不一致、行尾/编码变体的包。

    - LICENSE文件名装Apache全文：提取以内容为准
    - crlf.txt：CRLF行尾（Windows打包常见）
    - bom.txt：UTF-8 BOM前缀
    - empty.txt：0字节
    """
    def rel(path: str) -> str:
        return f"{top}/{path}"

    apache = license_text("Apache-2.0")
    return [
        Entry(rel("LICENSE"), apache, seq=0),
        Entry(rel("crlf.txt"), apache.replace("\n", "\r\n"), seq=1),
        Entry(rel("bom.txt"), "﻿" + apache, seq=2),
        Entry(rel("empty.txt"), "", seq=3),
    ]


def spdx_only_entries(top: str = "spdxsrc-1.0") -> list:
    """生成无license文件、仅源码内SPDX声明行的包（现代项目形态）。"""
    def rel(path: str) -> str:
        return f"{top}/{path}"

    return [
        Entry(rel("src/a.c"), "// SPDX-License-Identifier: MIT\nint a(){}\n", seq=0),
        Entry(rel("src/b.c"), "// SPDX-License-Identifier: Apache-2.0\nint b(){}\n", seq=1),
        Entry(rel("README.md"), "spdx-only package\n", seq=2),
    ]


def make_corrupt_zip(dest: Path) -> Path:
    """损坏zip：非法数据（非空但无法解出任何内容）。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"PK" + b"\x00" * 100)
    return dest


def make_empty_zip(dest: Path) -> Path:
    """空zip：0个条目。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w"):
        pass
    return dest


def make_nested_archive(dest: Path) -> Path:
    """嵌套压缩包：tar.gz内封装zip（流水线以--shallow解压，内层zip
    不会被递归解开，用于固化内层license不提取的现状边界）。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("nestedlib-1.0/LICENSE", license_text("MIT"))
    with tarfile.open(dest, "w:gz") as t:
        data = inner.getvalue()
        info = tarfile.TarInfo(name="inner.zip")
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))
    return dest


def make_archive(entries: list, dest: Path) -> Path:
    """按dest后缀打包条目为真实压缩包。

    支持：.zip / .tar / .tar.gz / .tgz / .tar.bz2 / .tbz2

    Args:
        entries: Entry列表（按seq顺序写入，保证包内条目顺序可控）
        dest: 目标压缩包路径（后缀决定格式）

    Returns:
        Path: 生成的压缩包路径
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    name = dest.name
    if name.endswith(".zip"):
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for e in entries:
                zf.writestr(e.path, e.encoded())
    else:
        mode = "w"
        if name.endswith((".tar.gz", ".tgz")):
            mode = "w:gz"
        elif name.endswith((".tar.bz2", ".tbz2")):
            mode = "w:bz2"
        with tarfile.open(dest, mode) as tf:
            for e in entries:
                data = e.encoded()
                info = tarfile.TarInfo(name=e.path)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
    return dest


def write_tree(entries: list, root: Path) -> Path:
    """把条目写为真实目录树（目录形态输入用）。"""
    root.mkdir(parents=True, exist_ok=True)
    for e in entries:
        p = root / e.path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(e.encoded())
    return root
