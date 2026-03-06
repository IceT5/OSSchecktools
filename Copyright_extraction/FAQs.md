# 常见问题 (FAQs)

本文档收集了 Copyright & License Extraction Tool 使用过程中的常见问题及解答。

## 安装与环境

### Q: 工具支持哪些操作系统？
A: 工具开发和测试环境为 `Ubuntu 22.04`，使用 `Python 3.10/3.11`。在 Windows 环境运行时，可能会出现自动生成的临时目录路径过长，导致自动删除临时目录失败。如确需在 Windows 环境使用，建议修改系统参数配置启用长路径支持。

### Q: 如何安装工具？
A: 进入 Copyright_extraction 目录后，执行：
```bash
pip install -e .
```
安装完成后会生成 `cret` 命令。

### Q: 安装时提示 scancode 相关错误怎么办？
A: 工具依赖 ScanCode Toolkit，请确保环境满足 ScanCode 的运行要求。详见 [ScanCode 官方文档](https://scancode-toolkit.readthedocs.io/en/stable/getting-started/installation/index.html#installation-prerequisites)。

## License 识别问题

### Q: 为什么我的 license 没有被识别？
A: 请检查以下几点：
1. **文件位置**：license 文件是否在根目录或 LICENSES 目录下
2. **文件命名**：license 文件命名是否符合规范（如 LICENSE, LICENSE.MIT 等）
3. **文件格式**：文件是否为文本格式，非二进制文件
4. **调试模式**：使用 `LOG_LEVEL=DEBUG` 查看详细日志，了解扫描过程中的具体信息

### Q: 工具支持识别哪些许可证？
A: 工具的许可证识别能力基于 ScanCode Toolkit 的许可证数据库，支持 MIT、Apache-2.0、BSD、GPL、LGPL 等常用开源许可证。运行以下命令查看 ScanCode 支持的所有许可证：
```bash
scancode --list-licenses
```

### Q: 如何处理工具不支持的许可证？
A: 推荐使用 `-l` 和 `-p` 参数同时指定许可证名称和文件路径：
```bash
cret -t package.zip -n "MySoftware" -v "1.0.0" -l "Custom-License" -p "LICENSE"
```
这样可以跳过自动检测，直接使用您提供的参数。

### Q: 为什么 LGPL-3.0 许可证识别失败？
A: ScanCode Toolkit 不支持 `LGPL-3.0-only` 和 `LGPL-3.0-or-later` 这两种 SPDX 标识符，只支持 `LGPL-3.0`。请使用：
```bash
cret -t package.zip -n "MySoftware" -v "1.0.0" -l "LGPL-3.0"
```

### Q: Makefile 被误识别为 MIT 许可证怎么办？
A: 工具已内置误匹配过滤机制，会自动过滤此类误报。如果仍遇到问题，请使用 `-l` 和 `-p` 参数明确指定许可证信息。

## 参数使用问题

### Q: 什么时候应该同时指定 `-l` 和 `-p` 参数？
A: 当您明确知道软件的许可证名称和许可证文件位置时，建议同时指定这两个参数。这样可以：
- 跳过自动检测，结果最准确
- 避免潜在的误识别
- 工具会进行一致性校验，确保参数正确

### Q: 只指定 `-l` 参数会发生什么？
A: 工具会在项目根目录和 LICENSES 目录中查找与指定名称匹配的 license 文件，并提取对应的 license 信息。

### Q: 只指定 `-p` 参数会发生什么？
A: 工具会从指定路径的文件中提取 license 名称和内容。路径必须是相对于项目根目录的相对路径。

### Q: 为什么会出现"请人工核对"的警告？
A: 当工具无法完全确认 license 信息的准确性时，会提示用户人工核对。常见场景包括：
- 未同时提供 license 名称和路径
- 提供的 license 名称与文件内容不匹配
- 自动检测到多个 license

建议使用 `-l` 和 `-p` 参数同时指定 license 名称和路径以获得最准确的结果。

## 多许可证问题

### Q: 如何处理多许可证项目？
A: 工具会自动检测并输出所有检测到的 license。每个 license 会单独列在 Readme.opensource 文件中。如果不指定 `-l` 和 `-p` 参数，工具会执行完整 license 提取，输出所有检测到的 license。

### Q: 项目有多个 LICENSE 文件，工具如何处理？
A: 工具会：
1. 识别根目录下的所有 license 文件
2. 识别 LICENSES 目录下的所有文件
3. 对每个文件提取 license 信息
4. 在 Readme.opensource 中分别列出每个 license

## 输出问题

### Q: 输出文件有哪些？
A: 工具运行完成后会生成以下文件：
- `Readme.opensource`：最终输出的许可证声明文件（标准格式）
- `{被测目标名}_copyright`：copyright 信息文本
- `{被测目标名}_license`：license 信息文本
- `result.json`：ScanCode 扫描原始结果（调试用）

### Q: Readme.opensource 文件的格式是什么？
A: 文件格式如下：
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

### Q: 为什么 copyright 信息为空？
A: 可能的原因：
1. 源代码中没有 copyright 声明
2. copyright 声明格式不标准，ScanCode 无法识别
3. 所有 copyright 信息都在文档文件中，被过滤掉了

使用 `LOG_LEVEL=DEBUG` 查看详细日志以了解具体情况。

## 错误处理

### Q: Windows 环境下删除临时目录失败怎么办？
A: Windows 系统可能因路径过长导致删除失败。建议：
1. 修改系统注册表启用长路径支持
2. 或手动删除临时目录（通常位于目标文件同目录下，名称类似 `xxx-extract`）

### Q: 执行过程中断，临时文件在哪里？
A: 如果执行过程中断，临时文件会保留以便调试：
- 解压的源码目录：通常位于目标文件同目录下，名称类似 `xxx-extract`
- 扫描结果文件：`result.json`

### Q: 如何查看详细的调试信息？
A: 使用 `LOG_LEVEL=DEBUG` 环境变量：
```bash
LOG_LEVEL=DEBUG cret -t package.zip -n "MySoftware" -v "1.0.0"
```

### Q: 如何只显示错误信息？
A: 使用 `LOG_LEVEL=QUIET` 环境变量：
```bash
LOG_LEVEL=QUIET cret -t package.zip -n "MySoftware" -v "1.0.0"
```

## 其他问题

### Q: 工具支持哪些压缩格式？
A: 支持的格式包括：`.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`

### Q: 可以直接扫描 git clone 后的目录吗？
A: 可以。直接指定目录路径即可：
```bash
cret -t ./source_dir -n "MySoftware" -v "1.0.0"
```

### Q: 如何查看详细的使用指南？
A: 运行以下命令查看详细使用指南：
```bash
cret --guide
```

### Q: 遇到其他问题怎么办？
A: 1. 使用 `LOG_LEVEL=DEBUG` 查看详细日志
2. 查看 [DESIGN.md](DESIGN.md) 了解工具的设计逻辑
3. 向项目提交 Issue，附上详细的错误信息和日志