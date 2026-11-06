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

"""copyright提取（extract_and_duplicate_copyright）的单元测试。

核心行为：只做来源上下文判断，不做内容判断。提供root_path时，用pygments
（scancode-toolkit自带依赖）对检出所在源文件做词法分析——检出区间完全落在
注释/文档字符串内视为有效声明，落在代码上下文（如C宏``#define``行）视为
误报丢弃；判定只应用于显式支持的语言白名单（COPYRIGHT_CONTEXT_LEXER_CLASSES，
均为编程语言），数据格式/证书/未知语言一律保留；任何不确定情形（无词法器、
读取失败、文件过大、行号缺失、pygments缺失）一律保留。不提供root_path时
透传全部非空声明。

其余既有行为不变：statement回退、copyright字段优先、去重保持首次顺序、
文档类后缀与生成物后缀跳过。
"""

import pytest

from ossinfo_extraction import parse_and_duplication
from ossinfo_extraction.parse_and_duplication import extract_and_duplicate_copyright


def fcopy(path, *statements):
    return {"path": path, "copyrights": [{"copyright": s} for s in statements]}


def fline(path, start, end, statement):
    return {"path": path, "copyrights": [
        {"copyright": statement, "start_line": start, "end_line": end}
    ]}


def write(tmp_path, rel, content):
    full = tmp_path / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- 透传（无root_path）

def test_all_statement_forms_preserved(tmp_path):
    """不提供root_path时透传：声明内容不做任何判断。"""
    data = {"files": [
        fcopy("a.c", "Copyright (c) 2007-2024 SampleLib Dev Team"),
        fcopy("b.c", "(c) 2025 Helper Corp. All rights reserved."),
        fcopy("c.c", "copr. 2019 Vendor GmbH"),
        fcopy("d.h", "Copyright (C) 2021-2024 Acme Systems, Inc."),
    ]}
    out = tmp_path / "copyright.txt"
    records = extract_and_duplicate_copyright(data, out)
    assert records == [
        "Copyright (c) 2007-2024 SampleLib Dev Team",
        "(c) 2025 Helper Corp. All rights reserved.",
        "copr. 2019 Vendor GmbH",
        "Copyright (C) 2021-2024 Acme Systems, Inc.",
    ]
    assert out.read_text(encoding="utf-8") == "".join(r + "\n" for r in records)


def test_statement_field_fallback(tmp_path):
    """copyright字段缺失时回退statement字段。"""
    data = {"files": [
        {"path": "a.c", "copyrights": [{"statement": "(c) 2020 Foo"}]},
    ]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt")
    assert records == ["(c) 2020 Foo"]


def test_empty_values_dropped(tmp_path):
    data = {"files": [
        {"path": "a.c", "copyrights": [{"copyright": ""}, {"copyright": "   "}, {}]},
    ]}
    assert extract_and_duplicate_copyright(data, tmp_path / "o.txt") == []


def test_dedup_keeps_first_order(tmp_path):
    data = {"files": [
        fcopy("a.c", "(c) 2020 Foo"),
        fcopy("b.c", "(c) 2020 Foo", "(c) 2021 Bar"),
        fcopy("c.c", "(c) 2020 foo"),  # 精确字符串不同，视为不同记录
    ]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt")
    assert records == ["(c) 2020 Foo", "(c) 2021 Bar", "(c) 2020 foo"]


def test_doc_suffixes_skipped(tmp_path):
    """文档类后缀（全集）中的声明跳过，含大写后缀。"""
    suffixes = [".md", ".rst", ".txt", ".adoc", ".markdown"]
    data = {"files": [
        fcopy(f"doc{suffix}", f"(c) 2020 Doc {suffix}") for suffix in suffixes
    ] + [fcopy("UPPER.MD", "(c) 2020 Upper Doc"), fcopy("src/code.c", "(c) 2020 Code Writer")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt")
    assert records == ["(c) 2020 Code Writer"]


def test_generated_suffixes_skipped(tmp_path):
    """生成物/二进制后缀（.pyc/.so等）中的声明跳过。"""
    data = {"files": [
        fcopy("pkg/__pycache__/mod.pyc", "(c) 2020 From Pyc"),
        fcopy("lib/native.so", "(c) 2020 From So"),
        fcopy("src/code.c", "(c) 2020 Code Writer"),
    ]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt")
    assert records == ["(c) 2020 Code Writer"]


def test_copyright_field_wins_over_statement(tmp_path):
    """copyright与statement同时存在时优先copyright字段。"""
    data = {"files": [
        {"path": "a.c", "copyrights": [
            {"copyright": "Copyright (c) 2020 Foo", "statement": "statement text"}]},
    ]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt")
    assert records == ["Copyright (c) 2020 Foo"]


def test_whitespace_stripped(tmp_path):
    data = {"files": [fcopy("a.c", "   (c) 2020 Foo   ")]}
    assert extract_and_duplicate_copyright(data, tmp_path / "o.txt") == ["(c) 2020 Foo"]


def test_without_root_path_code_noise_kept(tmp_path):
    """不提供root_path时没有上下文信息，代码噪声也保留（fail-open契约）。"""
    data = {"files": [fcopy("src/secinput.h", "(c) (c) L")]}
    assert extract_and_duplicate_copyright(data, tmp_path / "o.txt") == ["(c) (c) L"]


# ---------------------------------------------------------------- 上下文判断

C_HEADER = """/*
 * Copyright (c) 2014-2020 Sample Corp.
 * SPDX-License-Identifier: MIT
 */
#include <stdio.h>

#define IS_SPACE(c) (((c) == L' ') || ((c) == L'\\t'))

int f(int c) { return IS_SPACE(c); }
"""


def test_macro_in_define_dropped_header_comment_kept(tmp_path):
    """C宏行中的检出丢弃，块注释头中的检出保留。"""
    write(tmp_path, "proj/src/a.h", C_HEADER)
    data = {"files": [
        fline("proj/src/a.h", 2, 2, "Copyright (c) 2014-2020 Sample Corp."),
        fline("proj/src/a.h", 7, 7, "(c) (c) L"),
    ]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["Copyright (c) 2014-2020 Sample Corp."]


def test_block_comment_multiline_statement_kept(tmp_path):
    """跨多行的块注释声明整段保留。"""
    write(tmp_path, "proj/a.c", "/*\n * Copyright (c) 2019 Multi Corp.\n * All rights reserved.\n */\n")
    data = {"files": [fline("proj/a.c", 2, 3, "Copyright (c) 2019 Multi Corp. All rights reserved.")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["Copyright (c) 2019 Multi Corp. All rights reserved."]


PY_FILE = '''# Copyright (c) 2020 Py Corp
import re
_MARKER = r"(?i)\\(c\\)|copr."
'''


def test_python_comment_kept_code_line_dropped(tmp_path):
    """Python注释中的声明保留，代码行字符串中的检出丢弃。"""
    write(tmp_path, "proj/a.py", PY_FILE)
    data = {"files": [
        fline("proj/a.py", 1, 1, "Copyright (c) 2020 Py Corp"),
        fline("proj/a.py", 3, 3, "(c) copr."),
    ]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["Copyright (c) 2020 Py Corp"]


def test_docstring_notice_kept(tmp_path):
    """Python文档字符串中的license声明保留（按注释类词法单元处理）。"""
    write(tmp_path, "proj/a.py", '"""(c) 2020 Doc Corp\nlicense note\n"""\ndef f():\n    pass\n')
    data = {"files": [fline("proj/a.py", 1, 2, "(c) 2020 Doc Corp")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["(c) 2020 Doc Corp"]


def test_trailing_comment_on_code_line_dropped(tmp_path):
    """已知限制：与代码同行的行尾注释中的声明按代码上下文丢弃。"""
    write(tmp_path, "proj/a.c", "int x; /* (c) 2020 Tail Corp */\n")
    data = {"files": [fline("proj/a.c", 1, 1, "(c) 2020 Tail Corp")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == []


# ---------------------------------------------------------------- fail-open

def test_unknown_extension_kept(tmp_path):
    """无对应词法器（如.pem）时无法判断，保留。"""
    write(tmp_path, "proj/a.pem", "Copyright (c) 2020 Pem Corp\n")
    data = {"files": [fline("proj/a.pem", 1, 1, "Copyright (c) 2020 Pem Corp")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["Copyright (c) 2020 Pem Corp"]


def test_data_file_without_comments_kept(tmp_path):
    """证书等数据文件即使有词法器也不产生注释单元，整体豁免保留。"""
    pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "Certificate:\n"
        "    Data:\n"
        "        (c) 1999 Entrust.net Limited\n"
        "-----END CERTIFICATE-----\n"
    )
    write(tmp_path, "proj/cacert.pem", pem)
    data = {"files": [fline("proj/cacert.pem", 4, 4, "(c) 1999 Entrust.net Limited")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["(c) 1999 Entrust.net Limited"]


def test_data_format_file_kept(tmp_path):
    """TOML等数据格式不在语言白名单内，字段中的版权声明保留。"""
    toml = 'version = 1\n\n[[annotations]]\npriority = "lowest"\nSPDX-FileCopyrightText = "Copyright 2017 FSFE"\n'
    write(tmp_path, "proj/REUSE.toml", toml)
    data = {"files": [fline("proj/REUSE.toml", 6, 6, "Copyright 2017 FSFE")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["Copyright 2017 FSFE"]


def test_missing_source_file_kept(tmp_path):
    """源文件不存在时无法判断，保留。"""
    data = {"files": [fline("proj/ghost.c", 1, 1, "(c) 2020 Ghost")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["(c) 2020 Ghost"]


def test_missing_line_numbers_kept(tmp_path):
    """检出缺行号时无法判断，保留。"""
    write(tmp_path, "proj/a.c", "#define X(c) ((c) == L' ')\n")
    data = {"files": [fcopy("proj/a.c", "(c) (c) L")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["(c) (c) L"]


def test_pygments_unavailable_keeps_everything(tmp_path, monkeypatch):
    """pygments缺失时退化为透传。"""
    write(tmp_path, "proj/a.c", "#define X(c) ((c) == L' ')\n")
    monkeypatch.setattr(parse_and_duplication, "_PYGMENTS_AVAILABLE", False)
    data = {"files": [fline("proj/a.c", 1, 1, "(c) (c) L")]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt", root_path=tmp_path / "proj")
    assert records == ["(c) (c) L"]
