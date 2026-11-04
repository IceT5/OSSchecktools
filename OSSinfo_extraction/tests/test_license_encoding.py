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

"""license文件编码解码（_decode_license_text/_read_license_text）单元测试。

覆盖BOM编码、UTF-8、GBK/GB18030（含扩展字符）、多语种单/多字节编码、
换行归一化、二进制内容容错、探测失败兜底以及文件读取失败路径。
编码识别以真实长度的license文本为准：极短字节序列的编码本身存在歧义，
不做确定性断言。
"""

import codecs

import pytest

from ossinfo_extraction import readme_opensource
from ossinfo_extraction.readme_opensource import _decode_license_text, _read_license_text

MULTILINGUAL_SAMPLES = [
    ("simplified_chinese_gbk", "gbk",
     "本软件根据开放源代码许可证条款分发。版权所有，保留所有权利。"),
    ("traditional_chinese_big5", "big5",
     "本軟體依開放原始碼授權條款散布。版權所有，保留所有權利。"),
    ("japanese_shift_jis", "shift_jis",
     "このソフトウェアはオープンソースライセンスに基づいて配布されます。"),
    ("japanese_euc_jp", "euc_jp",
     "このソフトウェアはオープンソースライセンスに基づいて配布されます。"),
    ("korean_cp949", "cp949",
     "이 소프트웨어는 오픈 소스 라이선스에 따라 배포됩니다."),
    ("russian_koi8_r", "koi8_r",
     "Это программное обеспечение распространяется по лицензии с открытым исходным кодом."),
    ("russian_cp1251", "cp1251",
     "Это программное обеспечение распространяется по лицензии с открытым исходным кодом."),
    ("russian_iso8859_5", "iso8859_5",
     "Это программное обеспечение распространяется по лицензии с открытым исходным кодом."),
    ("arabic_cp1256", "cp1256",
     "يتم توزيع هذا البرنامج بموجب ترخيص مفتوح المصدر."),
    ("greek_iso8859_7", "iso8859_7",
     "Αυτό το λογισμικό διανέμεται υπό άδεια ανοιχτού κώδικα."),
    ("hebrew_cp1255", "cp1255",
     "תוכנה זו מופצת תחת רישיון קוד פתוח."),
    ("thai_tis620", "tis_620",
     "ซอฟต์แวร์นี้เผยแพร่ภายใต้สัญญาอนุญาตโอเพนซอร์ส"),
    ("western_cp1252", "cp1252",
     "Ce logiciel est distribué sous licence open source. Éàçùôï."),
    ("central_european_iso8859_2", "iso8859_2",
     "Ten program jest rozpowszechniany na licencji open source. ĄĆĘŁŃÓŚŹŻ."),
    ("turkish_iso8859_9", "iso8859_9",
     "Bu yazılım açık kaynak lisansı altında dağıtılır. ĞİŞÇÖÜ."),
]


@pytest.mark.parametrize("bom, encoding", [
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
])
def test_bom_encoded_text_decoded(bom, encoding):
    """带BOM的UTF-8/16/32文本按BOM解码，且BOM不进入结果。"""
    text = "木兰许可证\n"
    assert _decode_license_text(bom + text.encode(encoding)) == text


def test_utf8_text_unchanged():
    text = "MIT License\nCopyright (c) 2024\n"
    assert _decode_license_text(text.encode("utf-8")) == text


def test_gbk_chinese_decoded():
    text = "木兰宽松许可证，第2版\n\n版权所有，保留所有权利。\n"
    assert _decode_license_text(text.encode("gbk")) == text


def test_gb18030_four_byte_character_decoded():
    text = "木兰宽松许可证，第2版\n" * 10 + "扩展字符𠀀\n"
    assert _decode_license_text(text.encode("gb18030")) == text


def test_latin1_text_preserved():
    """拉丁单字节编码的ASCII部分保持可读（重音字符编码存在检测歧义）。"""
    text = "Copyright (c) Élastique\n"
    assert "lastique" in _decode_license_text(text.encode("latin-1"))


@pytest.mark.parametrize("text, encoding", [
    ("LICENSE\r\nline2\r\n", "utf-8"),
    ("LICENSE\r\n版权所有\r\n", "gbk"),
])
def test_crlf_normalized_to_lf(text, encoding):
    """与原文本模式读取一致：CRLF/CR统一为LF，避免污染Readme输出。"""
    assert _decode_license_text(text.encode(encoding)) == text.replace("\r\n", "\n")


def test_binary_content_does_not_crash():
    """含NUL的二进制内容走UTF-8替换模式，不参与中文编码猜测。"""
    decoded = _decode_license_text(b"\x00\x01\xff\xfe")
    assert isinstance(decoded, str)
    assert "�" in decoded


def test_empty_content():
    assert _decode_license_text(b"") == ""


def test_read_license_text_decodes_gbk_file(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.write_bytes("木兰许可证\n".encode("gbk"))
    assert _read_license_text(license_file) == "木兰许可证\n"


def test_read_license_text_returns_none_when_missing(tmp_path):
    assert _read_license_text(tmp_path / "MISSING") is None


@pytest.mark.parametrize(
    "name, encoding, text",
    MULTILINGUAL_SAMPLES,
    ids=[sample[0] for sample in MULTILINGUAL_SAMPLES],
)
def test_multilingual_text_decoded(name, encoding, text):
    """真实长度的多语种license文本应识别原编码并正确往返。"""
    assert _decode_license_text(text.encode(encoding)) == text


@pytest.mark.parametrize("text, encoding", [
    ("line1\rline2\r", "utf-8"),
    ("第一行\r第二行\r", "gbk"),
])
def test_cr_normalized_to_lf(text, encoding):
    """单独的CR也统一为LF。"""
    assert _decode_license_text(text.encode(encoding)) == text.replace("\r", "\n")


def test_detection_none_falls_back_to_utf8_replace(monkeypatch):
    """chardet识别不到编码时退回UTF-8替换模式。"""
    monkeypatch.setattr(readme_opensource.chardet, "detect", lambda raw: {"encoding": None})
    assert "�" in _decode_license_text("版权".encode("gbk"))


def test_unknown_detected_encoding_falls_back_to_utf8_replace(monkeypatch):
    """chardet返回不存在的编码时退回UTF-8替换模式。"""
    monkeypatch.setattr(
        readme_opensource.chardet, "detect", lambda raw: {"encoding": "not-a-real-codec"}
    )
    assert "�" in _decode_license_text(b"\xff\xfe")


def test_undecodable_detected_encoding_falls_back(monkeypatch):
    """探测到的编码无法解码时退回UTF-8替换模式。"""
    monkeypatch.setattr(readme_opensource.chardet, "detect", lambda raw: {"encoding": "ascii"})
    assert "�" in _decode_license_text("版权".encode("gbk"))


def test_read_license_text_decodes_utf16_file(tmp_path):
    license_file = tmp_path / "LICENSE"
    text = "木兰许可证\n"
    license_file.write_bytes(codecs.BOM_UTF16_LE + text.encode("utf-16-le"))
    assert _read_license_text(license_file) == text
