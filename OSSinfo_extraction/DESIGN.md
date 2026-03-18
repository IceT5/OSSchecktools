# 设计逻辑

本文档详细说明 OSS information Extraction Tool 的核心设计逻辑。

## 误匹配过滤设计

工具采用两层保护机制过滤误匹配：

### 第一层：路径有效性检查

在 `_is_valid_license_path` 函数中实现，只接受以下路径：
- 项目根目录下的license文件（如 `project/LICENSE`, `project/LICENSE.MIT`）
- 根目录下LICENSES目录中的文件（如 `project/LICENSES/MIT.txt`）

路径检查逻辑：
```
有效路径示例：
  json-develop/LICENSE          ✓ 根目录下license文件
  json-develop/LICENSE.MIT      ✓ 根目录下license文件
  json-develop/LICENSES/CC0-1.0.txt  ✓ LICENSES目录下文件

无效路径示例：
  json-develop/src/main.py      ✗ 非license文件
  json-develop/docs/LICENSE     ✗ 非根目录或LICENSES目录
  json-develop/subdir/LICENSES/xxx  ✗ LICENSES不是一级子目录
```

### 第二层：匹配质量检查

在 `_find_license_by_path` 函数中实现：
1. 检查是否为 `.LICENSE` 规则匹配（ScanCode标识的完整license文本匹配）
2. 如果非 `.LICENSE` 规则匹配，检查匹配长度是否 >= 20字符
3. 不满足条件的判定为误匹配，返回None

```
有效匹配示例：
  LICENSE文件 + .LICENSE规则匹配  → 有效
  LICENSE文件 + 匹配长度 >= 20    → 有效

无效匹配示例：
  Makefile + 匹配长度 = 2        → 误匹配（第一层已过滤）
  代码文件 + 匹配长度 = 200      → 误匹配（第一层已过滤）
```

### 为什么两层保护是必要的？

用户可能问：如果第一层已经过滤了非license文件，为什么还需要第二层？

答案：第二层主要处理用户指定路径的场景。虽然第一层会检查用户指定的路径是否有效，但两层保护提供了双重保障：
1. 防止未来代码修改导致的漏洞
2. 提供更精确的匹配质量评估

## 执行流程

```
输入参数解析
    ↓
环境检查（scancode --version）
    ↓
解压源码包（如需要）
    ↓
嵌套目录检测
    ↓
ScanCode扫描
    ↓
Copyright提取 + 去重
    ↓
License提取/校验
    ↓
生成Readme.opensource
    ↓
清理临时文件
```

## 参数处理逻辑

### License参数组合处理

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

## Copyright处理逻辑

### 去重机制

1. 从ScanCode扫描结果中提取所有copyright信息
2. 使用集合（Set）去除重复的copyright声明
3. 过滤掉文档文件（`.md`, `.rst`, `.txt`, `.adoc`, `.markdown`）中的copyright信息，避免重复

### 过滤原因

文档文件通常是代码文件的衍生品，其中的copyright信息与代码文件中的声明相同。过滤文档文件可以：
- 减少重复信息
- 提高提取效率
- 保持输出的简洁性

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

检测解压根目录下是否只有一个子目录：
- 如果是，则使用该子目录作为真正的项目根目录
- 否则，使用解压根目录作为项目根目录

## License文件识别规则

### 文件名模式匹配

工具使用正则表达式匹配以下文件名模式：
- 通用模式：`LICENSE`, `COPYING`, `COPYRIGHT`, `NOTICE` 及其变体
- 许可证特定模式：`MIT`, `Apache`, `BSD`, `GPL`, `LGPL` 等

### 目录识别

- 根目录下包含 "license" 字样的目录（如 `LICENSES/`, `license-texts/`）
- 该目录下的所有文件都被视为潜在的license文件

### 扩展名过滤

支持的扩展名包括：
- 文档格式：`.txt`, `.md`, `.rst`, `.html`, `.asciidoc`
- 许可证特定：`.license`, `.header`, `.lesser`, `.gpl`, `.apache`, `.mit`
- 空扩展名：无扩展名的文件（如 `LICENSE`）