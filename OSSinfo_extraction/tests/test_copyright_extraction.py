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

核心行为：保留ScanCode检出的有效版权声明（不按"copyright"关键字二次过滤），
含(c)/copr./Copyright (C)等真实书写形式；过滤仅有单字母/纯数字的明显误报
（如C宏中被误识别的 ``(c) (c) L``）；去重且保持首次出现顺序；文档类后缀跳过。
"""

import pytest

from ossinfo_extraction.parse_and_duplication import (
    _is_meaningful_copyright,
    extract_and_duplicate_copyright,
)


def fcopy(path, *statements):
    return {"path": path, "copyrights": [{"copyright": s} for s in statements]}


def test_all_statement_forms_preserved(tmp_path):
    """(c)/copr./Copyright (C)等不含copyright单词的声明不被过滤。"""
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


def test_macro_false_positive_dropped(tmp_path):
    """ScanCode把C宏中的(c)==L误识别为(c) (c) L，应被过滤。"""
    data = {"files": [fcopy(
        "src/secinput.h",
        "Copyright (c) Huawei Technologies Co., Ltd. 2014-2020",
        "(c) (c) L",
    )]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt")
    assert records == ["Copyright (c) Huawei Technologies Co., Ltd. 2014-2020"]


def test_valid_non_keyword_forms_kept(tmp_path):
    """不含copyright单词但holder有效的中文/英文/(c)/copr.声明保留。"""
    data = {"files": [fcopy(
        "a.c",
        "(c) 1999 Entrust.net Limited",
        "(c) Casper da Costa-Luis casperdcl (https://github.com/casperdcl)",
        "copr. 2019 Vendor GmbH",
        "版权所有",
        "(c) 2020 华为",
    )]}
    records = extract_and_duplicate_copyright(data, tmp_path / "o.txt")
    assert records == [
        "(c) 1999 Entrust.net Limited",
        "(c) Casper da Costa-Luis casperdcl (https://github.com/casperdcl)",
        "copr. 2019 Vendor GmbH",
        "版权所有",
        "(c) 2020 华为",
    ]


def test_meaningless_fragments_dropped(tmp_path):
    data = {"files": [fcopy("a.c", "(c) 2020", "(c) A", "(c) (c) L")]}
    assert extract_and_duplicate_copyright(data, tmp_path / "o.txt") == []


def test_copyright_keyword_kept_even_with_short_holder(tmp_path):
    data = {"files": [fcopy("a.c", "Copyright (c) A")]}
    assert extract_and_duplicate_copyright(data, tmp_path / "o.txt") == ["Copyright (c) A"]


def test_statement_field_noise_dropped(tmp_path):
    data = {"files": [{"path": "a.c", "copyrights": [{"statement": "(c) (c) L"}]}]}
    assert extract_and_duplicate_copyright(data, tmp_path / "o.txt") == []


def test_noise_filtered_before_dedup(tmp_path):
    data = {"files": [
        fcopy("a.c", "(c) (c) L", "(c) 2020 Foo"),
        fcopy("b.c", "(c) 2020 Foo"),
    ]}
    assert extract_and_duplicate_copyright(data, tmp_path / "o.txt") == ["(c) 2020 Foo"]


@pytest.mark.parametrize("value, expected", [
    ("(c) (c) L", False),
    ("(c) 2020", False),
    ("(c) A", False),
    ("", False),
    ("(c) 1999 Entrust.net Limited", True),
    ("(c) Casper da Costa-Luis", True),
    ("copr. 2019 Vendor GmbH", True),
    ("版权所有", True),
    ("(c) 2020 华为", True),
    ("Copyright (c) A", True),
    ("© 2020 Bar Corp", True),
    ("(c) HP", True),
])
def test_is_meaningful_copyright(value, expected):
    assert _is_meaningful_copyright(value) is expected
