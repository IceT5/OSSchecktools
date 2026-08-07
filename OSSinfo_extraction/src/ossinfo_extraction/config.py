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

"""
项目配置常量
"""

# ScanCode 版本要求
EXPECTED_SCANCODE_VERSION = "32.5.0"

# 常见的 license 文件名模式（不包含扩展名）
LICENSE_FILE_PATTERNS = [
    # 通用 license 文件名
    r"^license$",           # LICENSE, license
    r"^license[-_.].*",     # LICENSE-MIT, LICENSE.APACHE, LICENSE.MIT, license.txt
    r"^copying$",           # COPYING, copying
    r"^copying[-_.].*",     # COPYING.LESSER, COPYING.GPL, COPYING-3.0
    r"^copyright$",         # COPYRIGHT, copyright
    r"^copyright[-_.].*",   # COPYRIGHT.txt, COPYRIGHT.md

    # 按许可证名称匹配（支持SPDX标识符格式）
    # MIT 系列
    r"^mit$",               # MIT.txt
    r"^mit[-_.].*",         # MIT-License, MIT.txt, MIT-0

    # Apache 系列
    r"^apache$",            # Apache.txt
    r"^apache[-_.].*",      # Apache-2.0, Apache-License, Apache.txt

    # BSD 系列
    r"^bsd$",               # BSD.txt
    r"^bsd[-_.].*",         # BSD-2-Clause, BSD-3-Clause, BSD-4-Clause, BSD.txt

    # GPL 系列
    r"^gpl$",               # GPL.txt
    r"^gpl[-_.].*",         # GPL-3.0, GPL-2.0, GPL-3.0-only, GPL-3.0-or-later

    # LGPL 系列
    r"^lgpl$",              # LGPL.txt
    r"^lgpl[-_.].*",        # LGPL-3.0, LGPL-2.1, LGPL.txt

    # AGPL 系列
    r"^agpl$",              # AGPL.txt
    r"^agpl[-_.].*",        # AGPL-3.0, AGPL-3.0-only

    # MPL 系列
    r"^mpl$",               # MPL.txt
    r"^mpl[-_.].*",         # MPL-2.0, MPL.txt

    # EPL (Eclipse Public License) 系列
    r"^epl$",               # EPL.txt
    r"^epl[-_.].*",         # EPL-1.0, EPL-2.0, EPL.txt

    # Creative Commons 系列
    r"^cc0$",               # CC0.txt
    r"^cc0[-_.].*",         # CC0-1.0, CC0.txt
    r"^cc[-_.].*",          # CC-BY, CC-BY-SA, CC-BY-4.0

    # ISC License
    r"^isc$",               # ISC.txt
    r"^isc[-_.].*",         # ISC-License

    # Unlicense
    r"^unlicense$",         # UNLICENSE
    r"^unlicense[-_.].*",   # UNLICENSE.txt

    # zlib License
    r"^zlib$",              # zlib.txt
    r"^zlib[-_.].*",        # zlib-license

    # PostgreSQL License
    r"^postgresql$",        # PostgreSQL.txt
    r"^postgresql[-_.].*",  # PostgreSQL-License

    # Open Font License
    r"^ofl$",               # OFL
    r"^ofl[-_.].*",         # OFL.txt, OFL-1.1

    # Artistic License
    r"^artistic$",          # Artistic.txt
    r"^artistic[-_.].*",    # Artistic-2.0, Artistic-License

    # 0BSD (Zero-Clause BSD)
    r"^0bsd$",              # 0BSD.txt

    # Boost Software License
    r"^bsl$",               # BSL.txt
    r"^bsl[-_.].*",         # BSL-1.0
    r"^boost[-_.].*",       # Boost-1.0, Boost-License

    # EUPL (European Union Public License)
    r"^eupl$",              # EUPL.txt
    r"^eupl[-_.].*",        # EUPL-1.1, EUPL-1.2

    # CDDL (Common Development and Distribution License)
    r"^cddl$",              # CDDL.txt
    r"^cddl[-_.].*",        # CDDL-1.0, CDDL-1.1

    # Eclipse Distribution License
    r"^edl$",               # EDL.txt
    r"^edl[-_.].*",         # EDL-1.0

    # LaTeX Project Public License
    r"^lppl$",              # LPPL.txt
    r"^lppl[-_.].*",        # LPPL-1.3c

    # Microsoft Public License
    r"^ms[-_]?pl$",         # MS-PL, MSPL

    # Mozilla Public License (alternate naming)
    r"^mozilla[-_.].*",     # Mozilla-Public-License

    # OpenSSL License
    r"^openssl$",           # OpenSSL.txt

    # PHP License
    r"^php[-_.].*",         # PHP-3.0, PHP-License

    # Python License
    r"^python[-_.].*",      # Python-2.0, Python-License

    # SIL Open Font License (alternate naming)
    r"^sil[-_.].*",         # SIL-OFL-1.1

    # Vim License
    r"^vim$",               # Vim.txt

    # W3C License
    r"^w3c$",               # W3C.txt
    r"^w3c[-_.].*",         # W3C-License

    # WTFPL (Do What The Fuck You Want To Public License)
    r"^wtfpl$",             # WTFPL.txt

    # Zope Public License
    r"^zpl$",               # ZPL.txt
    r"^zpl[-_.].*",         # ZPL-2.1
]

# 常见的 license 文件扩展名
LICENSE_EXTENSIONS = {
    "", ".txt", ".md", ".rst", ".html", ".htm",
    ".xml", ".json", ".yaml", ".yml", ".asciidoc",
    ".adoc", ".markdown", ".license", ".header",
    ".lesser", ".gpl", ".apache",
    ".mit", ".bsd", ".lgpl",
    ".mpl", ".ofl", ".unlicense",
    ".artistic", ".cc0",
}

# Copyright 提取时忽略的文件扩展名（文档类文件）
COPYRIGHT_IGNORED_SUFFIXES = {
    ".md",
    ".rst",
    ".txt",
    ".adoc",
    ".markdown",
}
