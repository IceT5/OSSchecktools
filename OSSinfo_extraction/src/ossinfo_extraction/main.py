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

import sys
import os
import argparse
from pathlib import Path

from .logger import info, ok, warn, error, debug, has_error, error_exit, register_cleanup_callback, set_software_info
from .prerequisite import check_scancode_available
from .extract import run_extractcode
from .scancode import run_scancode
from .parse_and_duplication import extract_and_duplicate_copyright
from .license_extraction import extract_licenses, process_license_params, write_license_report
from .readme_opensource import write_readme_opensource
from .cleanup import cleanup_extract_dir


def print_guide():
    """打印详细使用指南"""
    guide = """
                    OSS information Extraction Tool
                      版权与许可证信息提取工具使用指南

【工具简介 / Tool Introduction】
本工具用于从源代码压缩包或目录中提取版权信息和许可证信息，生成标准化的
Readme.opensource文件。

This tool extracts copyright and license information from source code archives
or directories and generates a standardized Readme.opensource file.

--------------------------------------------------------------------------------
【必填参数 / Required Parameters】
--------------------------------------------------------------------------------
  -t, --target      目标文件或目录路径
                    Target file or directory path
                    示例: -t package.zip 或 -t /path/to/source

  -n, --name        软件名称
                    Software name
                    示例: -n "json" 或 -n "Apache Commons"

  -v, --version     软件版本号
                    Software version
                    示例: -v "3.11.3" 或 -v "2.0.0"

--------------------------------------------------------------------------------
【可选参数 / Optional Parameters】
--------------------------------------------------------------------------------
  -l, --license     许可证名称（SPDX标识符）
                    License name (SPDX identifier)
                    示例: -l "MIT", -l "Apache-2.0", -l "GPL-3.0-only"
                    说明: 如果不提供，工具将自动检测许可证

  -p, --license-path 许可证文件相对路径
                      License file relative path
                      示例: -p "LICENSE", -p "LICENSES/MIT.txt"
                      说明: 如果不提供，工具将自动查找许可证文件

  -o, --output-dir   输出目录
                      Output directory
                      示例: -o "./output"
                      说明: 默认输出到目标文件所在目录

--------------------------------------------------------------------------------
【使用场景 / Usage Scenarios】
--------------------------------------------------------------------------------

场景1: 完全自动提取
  cret -t package.zip -n "MyLib" -v "1.0.0"
  
  说明: 工具自动扫描并提取所有版权和许可证信息
  Note: Tool automatically scans and extracts all copyright and license info

场景2: 指定许可证名称
  cret -t package.zip -n "MyLib" -v "1.0.0" -l "MIT"
  
  说明: 当已知许可证名称时，可指定以获得更准确的结果
  Note: Specify license name when known for more accurate results

场景3: 指定许可证文件路径
  cret -t package.zip -n "MyLib" -v "1.0.0" -p "LICENSE"
  
  说明: 当已知许可证文件位置时，可指定路径
  Note: Specify license file path when known

场景4: 同时指定许可证名称和路径 (推荐 / Recommended)
  cret -t package.zip -n "MyLib" -v "1.0.0" -l "MIT" -p "LICENSE"
  
  说明: 同时提供名称和路径，跳过自动检测，结果最准确
  Note: Provide both to skip automatic detection, most accurate results

--------------------------------------------------------------------------------
【输出文件 / Output Files】
--------------------------------------------------------------------------------
  Readme.opensource    - 最终输出的许可证声明文件
                         Final license declaration file

  *_copyright          - 版权信息提取报告
                         Copyright extraction report

  *_license            - 许可证信息提取报告
                         License extraction report

  result.json          - ScanCode扫描原始结果（调试用）
                         Raw ScanCode scan results (for debugging)

--------------------------------------------------------------------------------
【注意事项 / Important Notes】
--------------------------------------------------------------------------------
  1. 许可证文件仅接受以下位置:
     License files are only accepted from:
     - 项目根目录 / Project root directory
     - 根目录下的LICENSES目录 / LICENSES directory under root

  2. 当未同时提供许可证名称和路径时，工具会提示人工核对结果
     When license name and path are not both provided, manual verification
     is recommended

  3. 支持的压缩格式: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .tbz2
     Supported archive formats: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .tbz2

--------------------------------------------------------------------------------
【常见许可证SPDX标识符 / Common SPDX Identifiers】
--------------------------------------------------------------------------------
  MIT              - MIT License
  Apache-2.0       - Apache License 2.0
  BSD-3-Clause     - BSD 3-Clause License
  BSD-2-Clause     - BSD 2-Clause License
  GPL-3.0-only     - GNU General Public License v3.0 only
  GPL-3.0-or-later - GNU General Public License v3.0 or later
  LGPL-3.0         - GNU Lesser General Public License v3.0
  MPL-2.0          - Mozilla Public License 2.0
  CC0-1.0          - Creative Commons Zero v1.0 Universal

--------------------------------------------------------------------------------
【日志级别控制 / Log Level Control】
--------------------------------------------------------------------------------
  工具支持通过环境变量 LOG_LEVEL 控制日志输出级别：

  默认模式 (INFO):
    显示 INFO, OK, WARN, ERROR 级别日志
    示例: cret -t package.zip -n "MyLib" -v "1.0.0"

  调试模式 (DEBUG):
    显示全部日志，包括 DEBUG 调试信息
    示例: LOG_LEVEL=DEBUG cret -t package.zip -n "MyLib" -v "1.0.0"

  静默模式 (QUIET):
    只显示 ERROR 错误信息
    示例: LOG_LEVEL=QUIET cret -t package.zip -n "MyLib" -v "1.0.0"

  Log level control via LOG_LEVEL environment variable:
    (default)  - INFO, OK, WARN, ERROR logs
    DEBUG       - All logs including DEBUG
    QUIET       - ERROR logs only

"""
    print(guide)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Extract copyright and license information from source code archives. "
                    "\n提取源代码压缩包中的版权和许可证信息。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples / 示例:
  cret -t package.zip -n "MySoftware" -v "1.0.0"
  cret -t package.zip -n "MySoftware" -v "1.0.0" -l "MIT"
  cret -t package.zip -n "MySoftware" -v "1.0.0" -p "LICENSES/MIT.txt"
  cret -t package.zip -n "MySoftware" -v "1.0.0" -l "MIT" -p "LICENSES/MIT.txt"

Run 'cret --guide' for detailed usage instructions.
运行 'cret --guide' 查看详细使用指南。
        """
    )
    
    # 必填参数
    parser.add_argument(
        "-t", "--target",
        required=True,
        help="Target file or directory to analyze / 目标文件或目录路径 (e.g., package.zip)"
    )
    parser.add_argument(
        "-n", "--name",
        required=True,
        help="Software name / 软件名称 (required)"
    )
    parser.add_argument(
        "-v", "--version",
        required=True,
        help="Software version / 软件版本号 (required)"
    )
    
    # 可选参数
    parser.add_argument(
        "-l", "--license",
        dest="license_name",
        default=None,
        help="License name (SPDX identifier) / 许可证名称，如 MIT, Apache-2.0"
    )
    parser.add_argument(
        "-p", "--license-path",
        dest="license_path",
        default=None,
        help="Relative path to license file / 许可证文件相对路径"
    )
    parser.add_argument(
        "-o", "--output-dir",
        dest="output_dir",
        default=None,
        help="Output directory for results / 输出目录 (default: same as target)"
    )
    parser.add_argument(
        "--guide",
        action="store_true",
        help="Show detailed usage guide / 显示详细使用指南"
    )
    
    # 先检查是否只是要显示指南（在解析必填参数之前）
    if "--guide" in sys.argv or "-g" in sys.argv:
        print_guide()
        sys.exit(0)
    
    args = parser.parse_args()
    
    return args


def main():
    args = parse_args()
    
    # 解析目标路径
    target = Path(args.target).resolve()
    if not target.exists():
        error_exit(f"Target does not exist: {target}")
    
    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = target.parent if target.is_file() else target
    
    # 输出文件路径
    result_json = output_dir / "result.json"
    output_copyright = output_dir / f"{target.stem}_copyright"
    output_license = output_dir / f"{target.stem}_license"
    output_readme = output_dir / "Readme.opensource"
    
    # 用于清理的变量
    extract_dir = None
    scan_target = target
    
    # 定义清理函数
    def cleanup():
        """清理过程文件和临时目录"""
        # 删除已生成的过程文件
        if result_json.exists():
            result_json.unlink()
        if output_copyright.exists():
            output_copyright.unlink()
        if output_license.exists():
            output_license.unlink()
        if output_readme.exists():
            output_readme.unlink()
        # 清理临时目录
        nonlocal extract_dir
        if extract_dir:
            cleanup_extract_dir(extract_dir)
    
    # 注册清理回调
    register_cleanup_callback(cleanup)
    
    # 软件信息
    software_name = args.name
    software_version = args.version
    license_name = args.license_name
    license_path = args.license_path
    
    # 设置软件信息（用于错误日志输出）
    set_software_info(software_name, software_version)
    
    info(f"Software Name: {software_name}")
    info(f"Software Version: {software_version}")
    info(f"License Name: {license_name or 'Not provided'}")
    info(f"License Path: {license_path or 'Not provided'}")
    
    try:
        if target.is_file():
            extract_dir = run_extractcode(target)
            # 检测嵌套目录：如果解压根目录下只有一个子目录，进入该目录作为真正的根目录
            scan_target = extract_dir
            try:
                items = list(extract_dir.iterdir())
                if len(items) == 1 and items[0].is_dir():
                    scan_target = items[0]
                    info(f"Detected nested directory, using as root: {scan_target}")
            except Exception:
                pass
        
        # 验证用户提供的license路径是否存在
        if license_path:
            # 标准化路径：移除前导斜杠，统一路径分隔符
            # 避免 /LICENSES/MIT.txt 被解析为绝对路径
            normalized_license_path = license_path.lstrip("/").replace("\\", "/")
            license_full_path = scan_target / normalized_license_path
            if not license_full_path.exists():
                error_exit(f"License file not found: {license_path}")
            
            # 标准化后的路径用于后续处理
            license_path = normalized_license_path
        
        # 执行scancode扫描（始终扫描license，用于校验用户提供的参数）
        check_scancode_available()
        run_scancode(scan_target, result_json, scan_license=True)
        
        # 提取copyright信息
        copyright_records = extract_and_duplicate_copyright(result_json, output_copyright)
        
        # 处理license信息（始终调用process_license_params以执行校验）
        license_records = process_license_params(
            result_json=result_json,
            root_path=scan_target,
            license_name=license_name,
            license_path=license_path,
        )
        
        # 检查是否有错误发生（用于非error_exit方式的错误）
        if has_error():
            error_exit("Errors occurred during processing, aborting.")
        
        # 写入license报告
        write_license_report(
            output_txt=output_license,
            software_name=software_name,
            software_version=software_version,
            license_records=license_records,
        )
        
        # 生成Readme.opensource文件
        write_readme_opensource(
            output_path=output_readme,
            software_name=software_name,
            software_version=software_version,
            copyright_records=copyright_records,
            license_records=license_records,
            root_path=scan_target,
        )

    except Exception as e:
        error("Pipeline failed, extracted directory will be kept for debugging.")
        print(e)
        raise

    else:
        if extract_dir:
            cleanup_extract_dir(extract_dir)
        # 暂时保留result.json用于调试
        # os.remove(result_json)
        debug(f"Result JSON kept at: {result_json}")

if __name__ == "__main__":
    main()