# 概述
本工具主要包含5个模块：安装scancode、提取源代码、扫描copyright、copyright信息去重以及安全删除过程文件，工具的输入为 开源软件源码包，输出为 copyright文本。

## 环境准备
工具依托scancode-toolkit的copyright提取功能，所以需要确保环境满足scancode-toolkit运行要求，详见[官方文档](https://scancode-toolkit.readthedocs.io/en/stable/getting-started/installation/index.html#installation-prerequisites)
本工具开发和测试的环境为：Ubuntu 22.04 python3.10-3.11

## 物料准备
从开源软件的官方仓库下载源代码包，当前版本仅支持对源代码包进行扫描（即zip或tar文件）
（后续功能拆分后，可支持直接对项目目录执行扫描，例如git clone后的目录）

## 安装scancode
通过pip install安装，安装前先校验本地是否已经安装，安装完成后，使用scancode --version命令验证是否安装成功

## 提取源代码
使用scancode-toolkit自带的extractcode插件，对源代码包进行提取

## 扫描copyright
执行scancode命令，对项目中全量copyright信息进行采集

## copyright信息去重
去除重复的copyright信息，同时对工具的一些误报进行处理，如文档中的copyright描述信息等

## 安全删除过程文件
工具执行过程中会产生过程文件，如源代码包提取后的代码文件等

## 输出
工具运行完成后，会在源代码包同级目录中，生成以 {源代码包名}_copyright 命名的文本文件
