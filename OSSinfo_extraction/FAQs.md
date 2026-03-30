# 常见问题 (FAQs)

本文档收集了 OSS Information Extraction Tool 使用过程中的常见问题、故障排查步骤及解决方案。

## 目录

- [故障排查流程](#故障排查流程)
- [安装与环境问题](#安装与环境问题)
- [License相关问题](#license相关问题)
- [Copyright相关问题](#copyright相关问题)
- [输出相关问题](#输出相关问题)
- [其他问题](#其他问题)

---

## 故障排查流程

遇到问题时，建议按以下步骤排查：

```
1. 启用调试日志
   LOG_LEVEL=DEBUG cret -t ...
   │
   ▼
2. 查看日志输出
   - 是否有 ERROR 级别错误？
   - 是否有 WARN 级别警告？
   │
   ▼
3. 根据错误类型定位问题
   - 安装错误 → 查看[安装与环境问题](#安装与环境问题)
   - License识别问题 → 查看[License相关问题](#license相关问题)
   - Copyright提取问题 → 查看[Copyright相关问题](#copyright相关问题)
   │
   ▼
4. 问题仍未解决？
   - 查看 [DESIGN.md](DESIGN.md) 了解设计逻辑
   - 向项目提交 Issue
```

---

## 安装与环境问题

### Q: 工具支持哪些操作系统？

**A:** 
- **推荐**：Ubuntu 22.04，Python 3.10/3.11
- **Windows**：可能出现临时目录路径过长导致删除失败的问题

**Windows 用户解决方案：**
- 修改系统注册表启用长路径支持
- 或手动删除临时目录（位于目标文件同目录下，名称类似 `xxx-extract`）

### Q: 安装时提示 scancode 相关错误怎么办？

**A:** 工具依赖 ScanCode Toolkit，请确保环境满足其运行要求。

**排查步骤：**
1. 检查 scancode 是否正确安装：
   ```bash
   scancode --version
   ```
2. 如未安装或报错，请参考 [ScanCode 官方文档](https://scancode-toolkit.readthedocs.io/en/stable/getting-started/installation/index.html#installation-prerequisites)

### Q: 如何安装工具？

**A:** 
```bash
cd OSSinfo_extraction
pip install -e .
```
安装完成后会生成 `cret` 命令。

---

## License相关问题

### Q: 为什么 license 没有被识别？

**A:** 请按以下顺序排查：

| 检查项 | 要求 | 说明 |
|--------|------|------|
| 文件位置 | 根目录或 LICENSES 目录 | 不支持其他目录 |
| 文件命名 | 符合规范 | 如 LICENSE, LICENSE.MIT, COPYING |
| 文件格式 | 文本格式 | 不支持二进制文件 |
| 文件内容 | 完整许可证文本 | 片段声明可能被过滤 |

**调试方法：**
```bash
LOG_LEVEL=DEBUG cret -t package.zip -n "Software" -v "1.0.0"
```

### Q: 为什么 LGPL-3.0 许可证识别失败？

**A:** ScanCode Toolkit 不支持 `LGPL-3.0-only` 和 `LGPL-3.0-or-later`，只支持 `LGPL-3.0`。

**解决方案：**
```bash
cret -t package.zip -n "Software" -v "1.0.0" -l "LGPL-3.0"
```

### Q: 使用 `-l` 参数时提示许可证未找到？

**A:** 
1. **确认使用 SPDX 标识符**：必须使用标准短名称，如 `MIT`、`Apache-2.0`、`GPL-3.0-only`
2. **查看 ScanCode 支持的许可证列表**：
   ```bash
   scancode --list-licenses
   ```
3. **使用 `-l` 和 `-p` 同时指定**：跳过自动检测

### Q: 指定了 license 名称和路径，但提示"请人工核对"？

**A:** 这表示工具检测到名称与文件内容可能不匹配。请检查：
- 指定的 license 名称是否正确
- 指定的文件路径是否正确
- 文件内容是否确实包含该许可证

### Q: 如何处理工具不支持的许可证？

**A:** 使用 `-l` 和 `-p` 参数同时指定，跳过自动检测：
```bash
cret -t package.zip -n "Software" -v "1.0.0" -l "Custom-License" -p "LICENSE"
```

### Q: 项目有多个 LICENSE 文件，工具如何处理？

**A:** 工具会按优先级处理：
1. 识别根目录下的所有 license 文件
2. 识别 LICENSES 目录下的所有文件
3. 按路径优先级选择（根目录 > LICENSES 目录 > 其他目录）
4. 在 Readme.opensource 中分别列出每个 license

### Q: 什么时候应该同时指定 `-l` 和 `-p` 参数？

**A:** 
- ✅ 明确知道许可证名称和文件位置时
- ✅ 需要最准确的结果时
- ✅ 自动检测出现问题需要覆盖时

---

## Copyright相关问题

### Q: 为什么 copyright 信息为空？

**A:** 可能原因及解决方案：

| 原因 | 解决方案 |
|------|----------|
| 源代码中没有 copyright 声明 | 检查源文件，补充版权声明 |
| 声明格式不标准 | 使用标准格式：`Copyright (c) 年份 作者` |
| 只存在于文档文件中 | 文档中的 copyright 默认被过滤 |
| 不包含 "copyright" 关键字 | 工具只保留包含关键字的信息 |

**调试方法：**
```bash
LOG_LEVEL=DEBUG cret -t package.zip -n "Software" -v "1.0.0"
# 查看 result.json 中的 copyright 扫描结果
```

### Q: copyright 信息重复怎么办？

**A:** 工具已内置去重机制。如仍有重复：
1. 检查是否有多个文件包含相同的 copyright 声明
2. 使用 `LOG_LEVEL=DEBUG` 查看原始扫描结果
3. 人工核对并删除 `Readme.opensource` 中的重复项

---

## 输出相关问题

### Q: 输出文件有哪些？

**A:** 
| 文件 | 说明 |
|------|------|
| `Readme.opensource` | 最终许可证声明文件 |
| `{target}_copyright` | copyright 信息文本 |
| `{target}_license` | license 信息文本 |
| `result.json` | ScanCode 原始扫描结果（调试用） |

### Q: Readme.opensource 格式是什么？

**A:** 
```
Software: 软件名称 版本号
Copyright Notice(s):
copyright信息1
copyright信息2
...
License: MIT
Full License Text:
MIT License内容...
```

### Q: 执行过程中断，临时文件在哪里？

**A:** 
- 解压目录：目标文件同目录下，名称类似 `xxx-extract`
- 扫描结果：`result.json`
- 出错时临时文件会保留以便调试

---

## 其他问题

### Q: 工具支持哪些压缩格式？

**A:** `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`

### Q: 可以直接扫描目录吗？

**A:** 可以，直接指定目录路径：
```bash
cret -t ./source_dir -n "Software" -v "1.0.0"
```

### Q: 如何查看详细使用指南？

**A:** 
```bash
cret --guide
```

### Q: Windows 环境下删除临时目录失败？

**A:** 
1. 修改系统注册表启用长路径支持
2. 或手动删除 `xxx-extract` 目录

### Q: 如何自定义 License 文件匹配规则？

**A:** 工具的配置常量集中在 `config.py` 模块中，可以根据需要修改：

| 配置常量 | 说明 |
|----------|------|
| `LICENSE_FILE_PATTERNS` | License 文件名匹配模式（正则表达式列表） |
| `LICENSE_EXTENSIONS` | License 文件扩展名集合 |
| `COPYRIGHT_IGNORED_SUFFIXES` | Copyright 提取时忽略的文件扩展名 |

**示例：添加新的 license 文件名模式**
```python
# 在 config.py 中添加
LICENSE_FILE_PATTERNS = [
    # ... 现有模式
    r"^my-custom-license$",  # 添加自定义模式
]
```

### Q: 遇到其他问题怎么办？

**A:** 
1. 使用 `LOG_LEVEL=DEBUG` 查看详细日志
2. 查看 `result.json` 了解扫描原始结果
3. 查看 [DESIGN.md](DESIGN.md) 了解设计逻辑
4. 向项目提交 Issue，附上：
   - 详细的错误信息
   - 调试日志输出
   - 目标文件/目录的基本信息
