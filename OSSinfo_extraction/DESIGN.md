# 设计文档 (DESIGN.md)

本文档详细说明 OSS Information Extraction Tool 的核心设计逻辑、架构和模块说明。

## 目录

- [整体架构](#整体架构)
- [执行流程](#执行流程)
- [License提取设计](#license提取设计)
- [Copyright处理逻辑](#copyright处理逻辑)
- [参数处理逻辑](#参数处理逻辑)
- [嵌套目录检测](#嵌套目录检测)
- [模块详解](#模块详解)

---

## 整体架构

```mermaid
┌─────────────────────────────────────────────────────────────┐
│                        main.py (主入口)                      │
│                   参数解析 + 流程协调 + 错误处理               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ prerequisite  │    │    extract    │    │   scancode    │
│   环境检查    │    │   源码解压    │    │   扫描执行    │
└───────────────┘    └───────────────┘    └───────────────┘
                                                  │
        ┌─────────────────────────────────────────┤
        ▼                                         ▼
┌───────────────────┐                  ┌───────────────────┐
│ parse_and_        │                  │ license_          │
│ duplication       │                  │ extraction        │
│ Copyright处理     │                  │ License处理       │
└───────────────────┘                  └───────────────────┘
        │                                         │
        └─────────────────────┬───────────────────┘
                              ▼
                    ┌───────────────────┐
                    │ readme_opensource │
                    │   输出文件生成    │
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     cleanup       │
                    │   临时文件清理    │
                    └───────────────────┘
```

---

## 执行流程

```
输入参数解析
    │
    ▼
环境检查（scancode --version）
    │
    ▼
解压源码包（如需要）
    │
    ▼
嵌套目录检测
    │
    ▼
ScanCode扫描
    │
    ▼
Copyright提取 + 去重
    │
    ▼
License提取/校验
    │
    ▼
生成Readme.opensource
    │
    ▼
清理临时文件
```

---

## License提取设计

License提取是工具的核心功能，涉及文件识别、误匹配过滤和路径优先级处理三个关键环节。

### 1. License文件识别规则

工具首先需要识别哪些文件是潜在的license文件。

#### 文件名模式匹配

由 `is_license_file()` 函数实现，使用正则表达式匹配以下文件名模式：
- 通用模式：`LICENSE`, `COPYING`, `COPYRIGHT`, `NOTICE` 及其变体
- 许可证特定模式：`MIT`, `Apache`, `BSD`, `GPL`, `LGPL` 等

#### 目录识别

由 `is_license_directory()` 函数实现：
- 根目录下包含 "license" 字样的目录（如 `LICENSES/`, `license-texts/`）
- 该目录下的所有文件都被视为潜在的license文件

#### 扩展名过滤

支持的扩展名包括：
- 文档格式：`.txt`, `.md`, `.rst`, `.html`, `.asciidoc`
- 许可证特定：`.license`, `.header`, `.lesser`, `.gpl`, `.apache`, `.mit`
- 空扩展名：无扩展名的文件（如 `LICENSE`）

### 2. 误匹配过滤机制

工具采用两层保护机制过滤误匹配，确保只提取有效的license信息。

#### 第一层：路径有效性检查

由 `_is_valid_license_path()` 函数实现，只接受以下路径：
- 项目根目录下的license文件（如 `project/LICENSE`, `project/LICENSE.MIT`）
- 根目录下LICENSES目录中的文件（如 `project/LICENSES/MIT.txt`）

有效路径示例：
- `json-develop/LICENSE` ✓ 根目录下license文件
- `json-develop/LICENSE.MIT` ✓ 根目录下license文件
- `json-develop/LICENSES/CC0-1.0.txt` ✓ LICENSES目录下文件

无效路径示例：
- `json-develop/src/main.py` ✗ 非license文件
- `json-develop/docs/LICENSE` ✗ 非根目录或LICENSES目录
- `json-develop/subdir/LICENSES/xxx` ✗ LICENSES不是一级子目录

#### 第二层：匹配质量检查

由 `_find_license_by_path()` 函数实现：
1. 检查是否为 `.LICENSE` 规则匹配（ScanCode标识的完整license文本匹配）
2. 如果非 `.LICENSE` 规则匹配，检查匹配长度是否 >= 20字符
3. 不满足条件的判定为误匹配，返回None

有效匹配示例：
- LICENSE文件 + .LICENSE规则匹配 → 有效
- LICENSE文件 + 匹配长度 >= 20 → 有效

无效匹配示例：
- Makefile + 匹配长度 = 2 → 误匹配（第一层已过滤）
- 代码文件 + 匹配长度 = 200 → 误匹配（第一层已过滤）

#### 为什么两层保护是必要的？

第二层主要处理用户指定路径的场景。虽然第一层会检查用户指定的路径是否有效，但两层保护提供了双重保障：
1. 防止未来代码修改导致的漏洞
2. 提供更精确的匹配质量评估

### 3. License路径优先级处理

当项目中有多个相同类型的license文件时，工具按路径优先级自动选择。

由 `_get_license_path_priority()` 函数实现：

| 优先级 | 路径类型 | 示例 |
|--------|----------|------|
| 1（最高） | 根目录下的license文件 | `LICENSE.MIT` |
| 2 | LICENSES目录下的文件 | `LICENSES/MIT.txt` |
| 3（最低） | 其他目录的文件 | `docs/LICENSE` |

---

## Copyright处理逻辑

### 去重机制

由 `extract_and_duplicate_copyright()` 函数实现：
1. 从ScanCode扫描结果中提取所有copyright信息
2. 使用集合（Set）去除重复的copyright声明
3. 过滤掉文档文件（`.md`, `.rst`, `.txt`, `.adoc`, `.markdown`）中的copyright信息

### 过滤原因

文档文件通常是代码文件的衍生品，其中的copyright信息与代码文件中的声明相同。过滤文档文件可以：
- 减少重复信息
- 提高提取效率
- 保持输出的简洁性

### 关键字验证

只保留包含 "copyright" 关键字的声明，有效过滤无效或误识别的信息。

---

## 参数处理逻辑

### License参数组合处理

由 `process_license_params()` 函数实现：

| License名称 | License路径 | 处理逻辑 |
|-------------|-------------|----------|
| 未填写 | 未填写 | 执行完整license提取，输出所有检测到的license |
| 已填写 | 未填写 | 查找与指定名称匹配的license文件路径 |
| 未填写 | 已填写 | 从指定路径提取license名称 |
| 已填写 | 已填写 | 跳过license提取，直接使用填入的参数并进行一致性校验 |

### 一致性校验流程

当同时指定license名称和路径时：

1. **文件存在性检查**：验证指定的license文件路径是否存在
2. **license一致性检查**：验证指定路径的文件是否与指定的license名称匹配
3. **不匹配处理**：如果不匹配，输出警告提示用户人工核对，但仍使用用户提供的参数继续执行

---

## 嵌套目录检测

### 问题背景

源码包解压后可能出现嵌套目录结构：
```
package.zip-extract/
└── package-1.0.0/
    ├── LICENSE
    ├── src/
    └── ...
```

如果直接使用 `package.zip-extract` 作为根目录，会导致license文件路径识别错误。

### 解决方案

在 `main.py` 的 `main()` 函数中实现：检测解压根目录下是否只有一个子目录：
- 如果是，则使用该子目录作为真正的项目根目录
- 否则，使用解压根目录作为项目根目录

---

## 模块详解

### main.py - 主入口模块

工具主入口，负责：
- 解析命令行参数
- 协调整个提取流程
- 处理嵌套目录检测
- 错误处理和清理

**核心函数：**
- `parse_args()`：解析命令行参数
- `print_guide()`：打印详细使用指南
- `main()`：主流程入口

---

### prerequisite.py - 环境检查模块

环境检查模块，使用 `scancode --version` 命令验证运行环境是否具备运行条件。

**核心函数：**
- `check_scancode_available()`：检查scancode是否可用

---

### extract.py - 源码包解压模块

源码包解压模块，使用scancode-toolkit中的extractcode功能对源码包进行提取。如被测目标已经是源码目录，会自动跳过提取环节。

**核心函数：**
- `run_extractcode(target_path)`：执行源码包解压

**支持的压缩格式：**
- `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`

---

### scancode.py - 扫描模块

扫描模块，调用scancode工具对项目中全量copyright和license信息进行扫描，生成JSON格式的扫描结果。

**核心函数：**
- `run_scancode(target_path, output_json, scan_license)`：执行扫描

---

### parse_and_duplication.py - Copyright处理模块

Copyright处理模块，负责：
- 从扫描结果中提取copyright信息
- 去除重复的copyright声明
- 过滤文档文件中的copyright信息

**核心函数：**
- `extract_and_duplicate_copyright(result_json, output_txt)`：提取并去重copyright信息

---

### license_extraction.py - License处理模块

License处理模块，是工具的核心模块之一。

**核心功能：**
- 自动提取：从根目录下license相关文件中提取license信息
- 按名称查找：根据用户提供的license名称查找对应的文件路径
- 按路径提取：根据用户提供的文件路径提取license名称
- 误匹配过滤：两层保护机制过滤非完整license文本的误报
- 参数校验：验证用户提供的license名称和路径是否一致

**核心函数：**
- `is_license_file(filename)`：判断文件名是否是license相关文件
- `is_license_directory(dirname)`：判断目录名是否包含license字样
- `get_license_files_from_root(root_path)`：获取项目根目录下的license相关文件
- `extract_licenses(result_json, output_txt, root_path)`：从scancode结果中提取license信息
- `process_license_params(result_json, root_path, license_name, license_path)`：根据用户参数处理license
- `write_license_report(output_txt, software_name, software_version, license_records)`：写入license报告

---

### readme_opensource.py - 输出模块

输出模块，生成标准格式的Readme.opensource文件，包含软件名称、版本、copyright声明和完整license文本。

**核心函数：**
- `write_readme_opensource(output_path, software_name, software_version, copyright_records, license_records, root_path)`：生成Readme.opensource文件

---

### cleanup.py - 清理模块

清理模块，自动删除工具执行过程中产生的过程文件。

**核心函数：**
- `cleanup_extract_dir(extract_dir)`：清理解压目录

**清理策略：**
- 正常执行完成后自动清理
- 执行出错时保留临时文件以便调试

---

### logger.py - 日志模块

日志模块，提供分级日志输出功能。

**日志级别：**
| 级别 | 说明 |
|------|------|
| DEBUG | 调试信息 |
| INFO | 一般信息 |
| OK | 成功信息 |
| WARN | 警告信息 |
| ERROR | 错误信息 |

**环境变量控制：**
- `LOG_LEVEL=DEBUG`：显示全部日志
- `LOG_LEVEL=QUIET`：只显示ERROR日志
- 默认：显示INFO, OK, WARN, ERROR

---

### __init__.py - 包初始化

工具包初始化文件，定义包版本信息。

---

### __main__.py - 命令行入口

支持通过 `python -m ossinfo_extraction` 方式运行工具。
