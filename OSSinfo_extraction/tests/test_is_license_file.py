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

"""license文件名判定（is_license_file）的单元测试。

覆盖：标准命名、英式拼写、SPDX版本后缀、精确关键词豁免、
非license文件与近名干扰文件的拒绝。
期望值均以当前实现的实际行为为准（含豁免等特殊规则）。
"""

import pytest

from ossinfo_extraction.license_extraction import is_license_file


@pytest.mark.parametrize("filename,expected", [
    # 标准命名与大小写
    ("LICENSE", True),
    ("license", True),
    ("License", True),
    ("LICENSE.txt", True),
    ("LICENSE.md", True),
    ("LICENSE.TXT", True),
    ("LICENSE.MIT", True),
    ("LICENSE-MIT", True),
    # COPYING / COPYRIGHT 系列
    ("COPYING", True),
    ("COPYING.LESSER", True),
    ("COPYING-3.0", True),
    ("COPYRIGHT.md", True),
    # SPDX标识风格命名（文件名即SPDX标识）
    ("MIT.txt", True),
    ("MIT-0", True),
    ("Apache-2.0", True),           # ".0"曾被视为扩展名而误拒
    ("apache-2.0", True),
    ("GPL-3.0-only", True),         # ".0-only"
    ("GPL-3.0-or-later", True),
    ("LPPL-1.3c", True),            # 数字后带字母尾
    ("Apache-2.0-with-exceptions", True),
    # 英式拼写（tqdm场景）
    ("LICENCE", True),
    ("licence", True),
    ("LICENCE.txt", True),
    ("LICENCE-MIT", True),
    ("LICENCE.md", True),
    # stem精确关键词豁免：stem为LICENSE等关键词时跳过扩展名检查
    ("LICENSE.bak", True),
    ("LICENSE.exe", True),
    # 应当拒绝：非license文件
    ("readme.md", False),
    ("main.py", False),
    ("mit.py", False),              # stem不在精确关键词豁免范围
    ("NOTICE", False),
    ("notice", False),
    # 近名干扰
    ("unlicence", False),           # un前缀不得因licence模式误收
    ("UNLICENCE", False),
    ("licences.h", False),
    ("LICENSE2", False),
    ("my-license.txt", False),      # license不是文件名开头
    # unlicense有专门模式，是合法license命名（非licence模式的误收）
    ("UNLICENSE", True),
    ("unlicense.txt", True),
])
def test_is_license_file(filename, expected):
    assert is_license_file(filename) is expected
