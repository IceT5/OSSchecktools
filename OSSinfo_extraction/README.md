# OSS information Extraction Tool

# 概述
本工具用于从开源软件源码包中自动提取版权信息（copyright）和许可证信息（license），生成标准化的 `Readme.opensource` 文件。工具基于 [ScanCode Toolkit](https://github.com/nexB/scancode-toolkit) 的扫描能力，并针对实际使用场景进行了多项优化。

## 环境准备
工具依托scancode-toolkit的copyright提取功能，所以需要确保环境满足scancode-toolkit运行要求，详见[官方文档](https://scancode-toolkit.readthedocs.io/en/stable/getting-started/installation/index.html#installation-prerequisites)

本工具开发和测试的环境为：`Ubuntu 22.04` `python3.10&python3.11` `pip 25.2` ，在windows环境运行时，可能会出现自动生成的临时目录路径过长，导致自动删除临时目录失败，如确需在windows环境使用，建议修改系统参数配置。

## 输入
支持对开源软件源码包（一般为zip或tar文件）以及源码目录（如git clone后的目录）执行扫描。

支持的压缩格式：`.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`

## 运行
进入OSSinfo_extraction目录后，执行`pip install -e .`；
安装完成后，会生成cret命令，执行以下格式运行：

### 命令格式
```bash
cret -t <target> -n <software_name> -v <software_version> [可选参数]
```

### 必填参数
| 参数 | 长参数 | 说明 |
|------|--------|------|
| `-t` | `--target` | 被测目标文件或目录路径（如：package.zip 或 ./source_dir） |
| `-n` | `--name` | 软件名称 |
| `-v` | `--version` | 软件版本 |

### 可选参数
| 参数 | 长参数 | 说明 |
|------|--------|------|
| `-l` | `--license` | License名称，**必须使用SPDX许可证标识符**（如：MIT, Apache-2.0） |
| `-p` | `--license-path` | License文件相对路径（相对于代码根目录） |
| `-o` | `--output-dir` | 输出目录，默认为被测目标同级目录 |
| `-j` | `--jobs` | ScanCode并行进程数，默认4（内存不足时可降低） |
| | `--max-in-memory` | ScanCode内存缓存文件数，默认2000；设为0表示不限制内存使用（禁用磁盘缓存）；设为-1表示仅使用磁盘缓存（最小化内存占用） |
| | `--timeout` | 单文件扫描超时时间（秒），默认60（超时文件将被跳过） |
| `--guide` | | 显示详细使用指南 |

### ⚠️ 重要提示：License名称必须使用SPDX标识符

使用 `-l` 参数指定license名称时，**必须使用符合 [SPDX (Software Package Data Exchange)](https://spdx.org/licenses/) 标准的许可证标识符**。SPDX标识符是开源许可证的标准化短名称，确保许可证识别的准确性和一致性。

例如：
- ✅ 正确：`-l "MIT"`、`-l "Apache-2.0"`、`-l "GPL-3.0-only"`
- ❌ 错误：`-l "mit license"`、`-l "Apache License 2.0"`、`-l "GNU GPL v3"`

### 使用示例
```bash
# 场景1：完全自动提取
cret -t package.zip -n "MySoftware" -v "1.0.0"

# 场景2：指定license名称，自动查找对应的license文件路径
cret -t package.zip -n "MySoftware" -v "1.0.0" -l "MIT"

# 场景3：指定license文件路径，自动提取license名称
cret -t package.zip -n "MySoftware" -v "1.0.0" -p "LICENSES/MIT.txt"

# 场景4：同时指定license名称和路径（推荐）
# 此模式跳过license提取，直接使用用户提供的参数，结果最准确
cret -t package.zip -n "MySoftware" -v "1.0.0" -l "MIT" -p "LICENSE"

# 指定输出目录
cret -t package.zip -n "MySoftware" -v "1.0.0" -o "./output"

# 调整ScanCode性能参数（适用于大项目或内存有限的机器）
cret -t package.zip -n "MySoftware" -v "1.0.0" -j 2 --max-in-memory 1000 --timeout 30

# 显示详细使用指南
cret --guide
```

### License参数组合说明
| License名称 | License路径 | 行为 |
|-------------|-------------|------|
| 未填写 | 未填写 | 执行完整license提取，输出所有检测到的license |
| 已填写 | 未填写 | 查找与指定名称匹配的license文件路径 |
| 未填写 | 已填写 | 从指定路径提取license名称 |
| 已填写 | 已填写 | 跳过license提取，直接使用填入的参数并进行一致性校验 |

### License参数校验
当同时指定license名称和路径时，工具会进行以下校验：

1. **文件存在性检查**：验证指定的license文件路径是否存在
2. **license一致性检查**：验证指定路径的文件是否与指定的license名称匹配
3. **不匹配提示**：如果检测到不匹配，会输出警告提示用户人工核对

```bash
# 示例：指定license名称和路径
cret -t package.zip -n "MySoftware" -v "1.0.0" -l "MIT" -p "LICENSE"

# 如果LICENSE文件实际包含Apache-2.0许可证，会输出警告：
# [WARN] License name 'MIT' does not match the license detected in file 'LICENSE'
# [WARN] Please verify the license name and file path are correct
# [WARN] 请人工核对许可证信息是否准确 / Please manually verify the license information is accurate
```

### 日志级别控制
工具支持通过环境变量控制日志输出级别：

| 环境变量值 | 显示内容 | 说明 |
|------------|----------|------|
| (默认) | INFO, OK, WARN, ERROR | 常规日志输出 |
| `LOG_LEVEL=DEBUG` | 全部日志 | 包含DEBUG调试信息，用于问题排查 |
| `LOG_LEVEL=QUIET` | 仅ERROR | 静默模式，只输出错误信息 |

```bash
# 默认模式运行
cret -t package.zip -n "MySoftware" -v "1.0.0"

# 显示调试日志
LOG_LEVEL=DEBUG cret -t package.zip -n "MySoftware" -v "1.0.0"

# 静默模式（只显示错误）
LOG_LEVEL=QUIET cret -t package.zip -n "MySoftware" -v "1.0.0"
```

## 支持的许可证

本工具的许可证识别能力基于 [ScanCode Toolkit](https://github.com/nexB/scancode-toolkit) 的许可证数据库。使用 `-l` 参数时，**必须使用SPDX许可证标识符**。

### 完整SPDX许可证标识符列表

以下是常用的SPDX许可证标识符，按类型分类：

#### 宽松许可证 (Permissive Licenses)

| 许可证名称 | SPDX标识符 |
|------------|------------|
| MIT License | `MIT` |
| ISC License | `ISC` |
| Zero-Clause BSD | `0BSD` |
| Unlicense | `Unlicense` |

#### Apache 许可证系列

| 许可证名称 | SPDX标识符 |
|------------|------------|
| Apache License 1.0 | `Apache-1.0` |
| Apache License 1.1 | `Apache-1.1` |
| Apache License 2.0 | `Apache-2.0` |

#### BSD 许可证系列

| 许可证名称 | SPDX标识符 |
|------------|------------|
| BSD 2-Clause "Simplified" License | `BSD-2-Clause` |
| BSD 2-Clause FreeBSD License | `BSD-2-Clause-FreeBSD` |
| BSD 2-Clause NetBSD License | `BSD-2-Clause-NetBSD` |
| BSD 3-Clause "New" or "Revised" License | `BSD-3-Clause` |
| BSD 3-Clause Attribution License | `BSD-3-Clause-Attribution` |
| BSD 3-Clause Clear License | `BSD-3-Clause-Clear` |
| BSD 3-Clause LBNL License | `BSD-3-Clause-LBNL` |
| BSD 4-Clause "Original" License | `BSD-4-Clause` |

#### GPL 许可证系列

| 许可证名称 | SPDX标识符 |
|------------|------------|
| GNU General Public License v2.0 only | `GPL-2.0-only` |
| GNU General Public License v2.0 or later | `GPL-2.0-or-later` |
| GNU General Public License v3.0 only | `GPL-3.0-only` |
| GNU General Public License v3.0 or later | `GPL-3.0-or-later` |
| GNU General Public License v1.0 only | `GPL-1.0-only` |
| GNU General Public License v1.0 or later | `GPL-1.0-or-later` |

> **注意**：ScanCode 可能也识别为 `GPL-2.0` 或 `GPL-3.0`（不带后缀），建议使用完整标识符。

#### LGPL 许可证系列

| 许可证名称 | SPDX标识符 |
|------------|------------|
| GNU Lesser General Public License v2.0 only | `LGPL-2.0-only` |
| GNU Lesser General Public License v2.0 or later | `LGPL-2.0-or-later` |
| GNU Lesser General Public License v2.1 only | `LGPL-2.1-only` |
| GNU Lesser General Public License v2.1 or later | `LGPL-2.1-or-later` |
| GNU Lesser General Public License v3.0 only | `LGPL-3.0-only` |
| GNU Lesser General Public License v3.0 or later | `LGPL-3.0-or-later` |
| GNU Library General Public License v2 only | `LGPL-2.0` |
| GNU Library General Public License v2 or later | `LGPL-2.0+` |
| GNU Library General Public License v2.1 only | `LGPL-2.1` |
| GNU Library General Public License v2.1 or later | `LGPL-2.1+` |

#### AGPL 许可证系列

| 许可证名称 | SPDX标识符 |
|------------|------------|
| GNU Affero General Public License v3.0 only | `AGPL-3.0-only` |
| GNU Affero General Public License v3.0 or later | `AGPL-3.0-or-later` |

#### MPL 许可证系列

| 许可证名称 | SPDX标识符 |
|------------|------------|
| Mozilla Public License 1.0 | `MPL-1.0` |
| Mozilla Public License 1.1 | `MPL-1.1` |
| Mozilla Public License 2.0 | `MPL-2.0` |
| Mozilla Public License 2.0 (no copyleft exception) | `MPL-2.0-no-copyleft-exception` |

#### Eclipse 许可证系列

| 许可证名称 | SPDX标识符 |
|------------|------------|
| Eclipse Public License 1.0 | `EPL-1.0` |
| Eclipse Public License 2.0 | `EPL-2.0` |
| Eclipse Distribution License 1.0 | `EDL-1.0` |
| Eclipse Public License 2.0 | `EPL-2.0` |

#### Creative Commons 许可证系列

| 许可证名称 | SPDX标识符 |
|------------|------------|
| Creative Commons Zero v1.0 Universal | `CC0-1.0` |
| Creative Commons Attribution 4.0 International | `CC-BY-4.0` |
| Creative Commons Attribution Share Alike 4.0 International | `CC-BY-SA-4.0` |
| Creative Commons Attribution Non Commercial 4.0 International | `CC-BY-NC-4.0` |
| Creative Commons Attribution No Derivatives 4.0 International | `CC-BY-ND-4.0` |
| Creative Commons Attribution Non Commercial Share Alike 4.0 International | `CC-BY-NC-SA-4.0` |
| Creative Commons Attribution Non Commercial No Derivatives 4.0 International | `CC-BY-NC-ND-4.0` |

#### 其他常用许可证

| 许可证名称 | SPDX标识符 |
|------------|------------|
| Artistic License 2.0 | `Artistic-2.0` |
| PostgreSQL License | `PostgreSQL` |
| zlib License | `Zlib` |
| Boost Software License 1.0 | `BSL-1.0` |
| SIL Open Font License 1.1 | `OFL-1.1` |
| Universal Permissive License v1.0 | `UPL-1.0` |
| Do What The F*ck You Want To Public License | `WTFPL` |
| Fair License | `Fair` |
| ISC License | `ISC` |
| NTP License | `NTP` |
| NTP License (legal text) | `NTP-0` |
| SQLite Blessing | `blessing` |
| SQLite Public Domain | `SQLite-PD` |

#### 专有/商业许可证

| 许可证名称 | SPDX标识符 |
|------------|------------|
| Proprietary | `Proprietary` |
| Commercial | `Commercial` |
| Other / Non-Standard | `NOASSERTION` |

### 特别说明

**关于 LGPL-3.0 的特殊处理：**

ScanCode Toolkit 不支持 `LGPL-3.0-only` 和 `LGPL-3.0-or-later` 这两种 SPDX 标识符，只支持 `LGPL-3.0`。如果您的项目使用 LGPL-3.0 许可证，请使用 `-l LGPL-3.0` 参数。

```bash
# 正确用法
cret -t package.zip -n "MySoftware" -v "1.0.0" -l "LGPL-3.0"

# 不支持的标识符（会导致匹配失败）
# -l "LGPL-3.0-only"
# -l "LGPL-3.0-or-later"
```

### 如何处理不支持的许可证

如果您发现工具无法识别某些许可证，可以采取以下方式：

1. **手动指定许可证信息（推荐）**

   使用 `-l` 和 `-p` 参数同时指定许可证名称和文件路径，跳过自动检测：
   ```bash
   cret -t package.zip -n "MySoftware" -v "1.0.0" -l "Custom-License" -p "LICENSE"
   ```

2. **查看 ScanCode 支持的完整许可证列表**

   运行以下命令查看 ScanCode 支持的所有许可证：
   ```bash
   scancode --list-licenses
   ```

3. **提交许可证支持请求**

   如果您认为某个许可证应该被支持，可以：
   - 向 [ScanCode Toolkit](https://github.com/nexB/scancode-toolkit) 提交 Issue 或 PR


## 输出
工具运行完成后，会在被测目标的同级目录（或指定的输出目录）中，生成以下文件：
- `Readme.opensource`：最终输出的许可证声明文件（标准格式）
- `{被测目标名}_copyright`：copyright信息文本
- `{被测目标名}_license`：license信息文本
- `result.json`：ScanCode扫描原始结果（调试用）

### Readme.opensource 文件格式
```
Software: 软件名称 版本号
Copyright Notice(s):
copyright信息1
copyright信息2
...
License: MIT
Full License Text:
MIT License内容...
License: Apache-2.0
Full License Text:
Apache License内容...
```

### License文件提取规则
License信息仅从以下文件中提取：
1. 根目录下包含"license"、"copying"、"copyright"、"notice"等关键字的文件
2. 根目录下包含"license"字样目录中的所有文件

支持的license文件名模式：
- `LICENSE`, `LICENSE.txt`, `LICENSE.md`
- `LICENSE-MIT`, `LICENSE_APACHE`
- `COPYING`, `COPYING.LESSER`, `COPYING-GPL`
- `NOTICE`, `NOTICE.txt`
- 以及其他常见的license文件命名格式

### 输出示例
```
============================================================
LICENSE INFORMATION EXTRACTION REPORT
============================================================

Software Name: nlohmann-json
Software Version: 3.11.3

Total unique licenses found: 6

--- License #1 ---
File: json-develop/LICENSE.MIT
SPDX Identifier: MIT
License Expression: mit

--- License #2 ---
File: json-develop/LICENSES/Apache-2.0.txt
SPDX Identifier: Apache-2.0
License Expression: apache-2.0
...
```

## 项目结构

```
OSSinfo_extraction/
├── src/ossinfo_extraction/
│   ├── __init__.py          # 包初始化
│   ├── __main__.py          # 命令行入口
│   ├── main.py              # 主入口模块
│   ├── config.py            # 配置模块（集中管理常量）
│   ├── prerequisite.py      # 环境检查模块
│   ├── extract.py           # 源码解压模块
│   ├── scancode.py          # 扫描模块
│   ├── parse_and_duplication.py  # Copyright处理模块
│   ├── license_extraction.py     # License处理模块
│   ├── readme_opensource.py      # 输出生成模块
│   ├── cleanup.py           # 清理模块
│   └── logger.py            # 日志模块
├── DESIGN.md                # 设计文档
├── FAQs.md                  # 常见问题
├── README.md                # 本文档
├── pyproject.toml           # 项目配置
└── requirements.txt         # 依赖列表
```

## 更多文档

- [设计文档 (DESIGN.md)](DESIGN.md) - 详细设计逻辑和模块说明
- [常见问题 (FAQs.md)](FAQs.md) - 常见问题及故障排查

## 许可证

本项目采用 Apache License 2.0 许可证。

