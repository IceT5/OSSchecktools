# 概述
本工具主要包含5个模块：检运行环境、提取源代码、扫描copyright、copyright信息去重以及安全清除过程文件，工具的输入为 开源软件源码包，输出为 copyright文本。

## 环境准备
工具依托scancode-toolkit的copyright提取功能，所以需要确保环境满足scancode-toolkit运行要求，详见[官方文档](https://scancode-toolkit.readthedocs.io/en/stable/getting-started/installation/index.html#installation-prerequisites)

本工具开发和测试的环境为：Ubuntu 22.04 python3.10-3.11 ，在windows环境运行时，可能会出现自动生成的临时目录路径过长，导致自动删除临时目录失败，如确需在windows环境使用，建议修改系统参数配置。

## 输入
从开源软件的官方仓库下载源代码包，当前版本仅支持对源代码包进行扫描（即zip或tar文件）
（后续功能拆分后，可支持直接对项目目录执行扫描，例如git clone后的目录）

## 运行
`pip install -r requirments.txt`

`python Copyright_extraction.main {archive}` 

或 

`python Copyright_extraction.main {path}`

## 输出
工具运行完成后，会在源代码包同级目录中，生成以 {源代码包名}_copyright 命名的文本文件

## 模块简介
### main.py
工具主入口，接收传入的被测目标

### prerequisite.py
使用scancode --version
命令查看运行环境是否具备运行条件

### extract.py
使用scancode-toolkit工具中的extractcode功能，对源码包进行提取。如被测目标已经是源码目录，会自动跳过提取环节

### scancode.py
调用scancode工具，对项目中全量copyright信息进行扫描

### parse_and_duplication.py
去除重复的copyright信息，并对已知的误报场景进行优化

### cleanup.py
自动删除工具执行过程中会产生的过程文件，如源代码包提取后的代码文件等

