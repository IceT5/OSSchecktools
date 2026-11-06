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

"""copyright提取：保留注释上下文中的声明，丢弃代码上下文中的误报。

ScanCode的版权检测基于文本行，不区分代码与注释，C宏中的 ``(c) == L`` 会被
误识别为 ``(c) (c) L``。真实的版权声明写在注释或文档字符串里，因此对检出
所在源文件做词法分析（pygments，scancode-toolkit自带依赖）判断来源上下文：
完全落在注释内视为有效声明，落在代码上下文视为误报丢弃。

"注释/代码"的区分只对编程语言有意义，因此判定只应用于显式支持并经真实
语料验证的语言白名单（config.COPYRIGHT_CONTEXT_LEXER_CLASSES）；数据格式
（JSON/TOML）、证书（.pem）、未知语言一律保留。

不做任何基于声明内容的判断（字母数、关键词、拼写形式）：任何不确定情形
（pygments缺失、词法器不在白名单、读取或分析失败、文件过大、行号越界）
一律保留，宁可误留，不可误删。
"""

from pathlib import Path

from .logger import debug, info
from .config import (
    COPYRIGHT_CONTEXT_LEXER_CLASSES,
    COPYRIGHT_IGNORED_GENERATED_SUFFIXES,
    COPYRIGHT_IGNORED_SUFFIXES,
)
from .readme_opensource import _clean_license_path

# pygments是scancode-toolkit的自带依赖；缺失时退化为不做来源判断（全部保留）
try:
    from pygments import lex as _pygments_lex
    from pygments.lexers import get_lexer_for_filename as _get_lexer_for_filename
    from pygments.token import Comment as _TokenComment
    from pygments.token import Literal as _TokenLiteral
    from pygments.token import Text as _TokenText

    _PYGMENTS_AVAILABLE = True
except ImportError:  # pragma: no cover - 依赖由scancode-toolkit提供
    _PYGMENTS_AVAILABLE = False

# 超过该大小的文件不做词法分析：版权头不会出现在超大文件的深处，
# 而对超大文件做全量词法分析会拖慢流水线
_MAX_LEX_FILE_BYTES = 2 * 1024 * 1024


def _is_comment_token(ttype) -> bool:
    """
    判断pygments词法单元是否属于注释或文档字符串。

    Comment.Preproc（#define/#pragma/#include等预处理指令）属于代码而非
    注释；C宏 ``(c) == L`` 的误报正来自预处理指令行，必须排除。
    """
    if ttype in _TokenComment.Preproc:
        return False
    return ttype in _TokenComment or ttype in _TokenLiteral.String.Doc


def _lines_in_comment_context(full_path: Path, start_line: int, end_line: int) -> bool:
    """
    判断[start_line, end_line]是否完全落在注释或文档字符串内。

    规则只有一条：检出区间的每一行都必须只含注释类词法单元（空白不算
    代码）；任一行含代码单元即视为误报。任何不确定情形一律返回True。

    Args:
        full_path: 检出所在的源文件路径
        start_line: 检出起始行（1-based）
        end_line: 检出结束行（1-based）

    Returns:
        bool: True表示保留该检出（在注释内或无法判定），False表示丢弃
    """
    if not _PYGMENTS_AVAILABLE:
        return True
    try:
        raw = full_path.read_bytes()
        if len(raw) > _MAX_LEX_FILE_BYTES:
            return True
        # 词法分析只依赖代码结构，个别字节解码失败不影响注释判定
        text = raw.decode("utf-8", errors="replace")
        lexer = _get_lexer_for_filename(full_path.name)
    except Exception:
        return True

    # 只有显式支持（并经真实语料验证）的编程语言才做注释/代码判定；
    # 数据格式、证书、未知语言的"代码/注释"概念无意义，整体保留
    if type(lexer).__name__ not in COPYRIGHT_CONTEXT_LEXER_CLASSES:
        return True

    line_has_comment = {}
    line_has_code = {}
    current = 1
    try:
        for ttype, value in _pygments_lex(text, lexer):
            # 换行符是所在行的终止符：以\n结尾的token，其最后一个\n不占用新行
            newline_count = value.count("\n")
            occupied_end = current + newline_count - (1 if value.endswith("\n") else 0)
            if _is_comment_token(ttype):
                for line_no in range(current, occupied_end + 1):
                    line_has_comment[line_no] = True
            elif ttype in _TokenText or not value.strip():
                # 空白与纯换行不参与判定，避免注释行被换行token误判为代码
                pass
            else:
                for line_no in range(current, occupied_end + 1):
                    line_has_code[line_no] = True
            current = current + newline_count
    except Exception:
        return True

    for line_no in range(start_line, end_line + 1):
        if line_has_code.get(line_no, False):
            return False
        if not line_has_comment.get(line_no, False):
            # 行号超出词法结果（空文件等），无法判定，按保留处理
            return True
    return True


def _find_scanned_file(root_path, file_path):
    """
    把ScanCode记录的路径还原为磁盘上的源文件。

    ScanCode路径可能带解压根目录名或 -extract 前缀，依次尝试多种组合；
    找不到返回None（调用方按保留处理）。
    """
    candidates = []
    if root_path is not None:
        candidates.append(root_path / file_path)
        cleaned = _clean_license_path(file_path, root_path)
        if cleaned:
            candidates.append(root_path / cleaned)
        candidates.append(root_path.parent / file_path)
    candidates.append(Path(file_path))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def extract_and_duplicate_copyright(
    data: dict,
    output_txt: Path,
    root_path=None,
) -> list:
    """
    从scancode结果中提取copyright信息并写入文件。

    只保留来自注释/文档字符串上下文的声明；root_path为None时跳过上下文
    判断，保留全部非空声明。提取结果去重并保持首次出现顺序。

    Args:
        data: scancode输出的JSON数据（已解析的字典）
        output_txt: 输出文件路径
        root_path: 扫描根目录，用于读取检出所在源文件做来源上下文判断

    Returns:
        list: 提取的copyright记录列表
    """
    unique_records = set()
    duplicated_results = []
    dropped = 0

    for file_info in data.get("files", []):
        file_path = file_info.get("path", "")
        suffix = Path(file_path).suffix.lower()

        if suffix in COPYRIGHT_IGNORED_SUFFIXES or suffix in COPYRIGHT_IGNORED_GENERATED_SUFFIXES:
            continue

        source_file = _find_scanned_file(root_path, file_path) if root_path else None

        for copyright_info in file_info.get("copyrights", []):
            value = (
                copyright_info.get("copyright")
                or copyright_info.get("statement")
            )
            if not value:
                continue

            value_stripped = value.strip()

            if not value_stripped:
                continue

            if source_file is not None:
                start_line = copyright_info.get("start_line")
                end_line = copyright_info.get("end_line")
                if start_line is not None and end_line is not None:
                    if not _lines_in_comment_context(source_file, start_line, end_line):
                        dropped += 1
                        debug(
                            f"Dropped copyright outside comment context: "
                            f"{file_path}:{start_line}-{end_line} {value_stripped!r}"
                        )
                        continue

            if value_stripped not in unique_records:
                unique_records.add(value_stripped)
                duplicated_results.append(value_stripped)

    with output_txt.open("w", encoding="utf-8") as f:
        for item in duplicated_results:
            f.write(item.strip() + "\n")

    info(f"Extracted {len(duplicated_results)} unique records")
    if dropped:
        info(f"Filtered {dropped} copyright detections outside comment context")
    info(f"Output written to {output_txt}")

    return duplicated_results
