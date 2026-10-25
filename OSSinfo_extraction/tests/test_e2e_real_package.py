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

"""端到端测试：合成真实软件包经由真实ScanCode扫描与CLI完整流水线。

L2（真实扫描断言产物）：
- 六种压缩格式的全量提取
- 目录/扁平/深嵌套/遮蔽/英式拼写/SPDX后缀/无license/近空包
- 版权声明多种书写形式的提取

L3（CLI行为）：
- -l/-p组合、-o输出目录、错误路径的退出码与提示
- --guide、缺参退出码、LOG_LEVEL

运行前提：PATH中存在scancode与extractcode（缺失时自动跳过）。
"""

import shutil

import pytest

from conftest import needs_scancode, run_cli

MIT_MARK = "Permission is hereby granted"
APACHE_MARK = "Apache License"
LGPL_MARK = "GNU LESSER GENERAL PUBLIC LICENSE"


def readme_of(out_dir):
    return (out_dir / "Readme.opensource").read_text(encoding="utf-8")


def run_extract(archive, out_dir, *extra):
    result = run_cli(out_dir, "-t", str(archive), "-n", "samplelib", "-v", "1.2.3",
                     "-o", str(out_dir), *extra)
    assert result.returncode == 0, result.stderr[-2000:] + result.stdout[-2000:]
    return result


@needs_scancode
class TestFullExtractionFormats:
    """六种压缩格式的全量提取（同一布局，验证解压链路）。"""

    def test_zip(self, sample_zip, tmp_path):
        run_extract(sample_zip, tmp_path)
        text = readme_of(tmp_path)
        assert "Software: samplelib 1.2.3\n" in text
        assert "License: MIT\n" in text and MIT_MARK in text
        assert "License: Apache-2.0\n" in text and APACHE_MARK in text
        # LGPL全文内含GPL引用段落，真实引擎检出复合表达式，断言宽松匹配
        assert "LGPL-2.1" in text and LGPL_MARK in text
        # 嵌套同名license（docs/、third_party/）不进入全量提取
        assert "License: BSD-3-Clause" not in text
        # 四种版权书写形式均被保留；引擎将(C)归一化输出为(c)
        assert "Copyright (c) 2007-2024 SampleLib Dev Team" in text
        copyright_txt = (tmp_path / "samplelib-1.2.3_copyright").read_text(encoding="utf-8")
        assert "(c) 2025 Helper Corp" in copyright_txt
        assert "copr. 2019 Vendor GmbH" in copyright_txt
        assert "Copyright (c) 2021-2024 Acme Systems" in copyright_txt

    def test_tar_gz(self, sample_tar_gz, tmp_path):
        run_extract(sample_tar_gz, tmp_path)
        assert "License: MIT\n" in readme_of(tmp_path)

    def test_tgz(self, sample_tgz, tmp_path):
        run_extract(sample_tgz, tmp_path)
        assert "License: MIT\n" in readme_of(tmp_path)

    def test_tar_bz2(self, sample_tar_bz2, tmp_path):
        run_extract(sample_tar_bz2, tmp_path)
        assert "License: MIT\n" in readme_of(tmp_path)

    def test_tbz2(self, sample_tbz2, tmp_path):
        run_extract(sample_tbz2, tmp_path)
        assert "License: MIT\n" in readme_of(tmp_path)

    def test_tar(self, sample_tar, tmp_path):
        run_extract(sample_tar, tmp_path)
        assert "License: MIT\n" in readme_of(tmp_path)


@needs_scancode
class TestPackageShapes:
    """目录形态与包布局变体。"""

    def test_dir_input(self, sample_dir, tmp_path):
        run_extract(sample_dir, tmp_path)
        assert "License: MIT\n" in readme_of(tmp_path)

    def test_flat_archive(self, sample_zip_flat, tmp_path):
        """无顶层目录的包：解压根即项目根（扫描记录带-extract前缀）。

        曾因清理规则误剥项目根段（首段恰含-extract后缀）导致根文件
        变为深度1被防御分支拒绝（真实bug，已修复：剥离增加结构判断，
        -extract段后仅剩单文件时保留不剥）。此形态下子目录license
        （docs/LICENSE）的包装段仍会剥离、深度为2按既有规则接受。
        """
        run_extract(sample_zip_flat, tmp_path)
        text = readme_of(tmp_path)
        assert "License: MIT\n" in text and MIT_MARK in text
        assert "LGPL-2.1" in text and LGPL_MARK in text
        assert "License: BSD-3-Clause" in text  # 子目录包装段剥离后深度2被接受

    def test_deep_nested_archive(self, sample_zip_deep, tmp_path):
        """双层顶层目录：递归检测到真正的项目根。"""
        run_extract(sample_zip_deep, tmp_path)
        text = readme_of(tmp_path)
        assert "License: MIT\n" in text and MIT_MARK in text

    def test_shadowing_resolves_root_license(self, shadow_zip, tmp_path):
        """遮蔽包端到端：无论扫描记录顺序，-p LICENSE选中的是根文件（MIT而非docs的BSD）。"""
        run_extract(shadow_zip, tmp_path, "-p", "LICENSE")
        text = readme_of(tmp_path)
        assert "License: MIT\n" in text and MIT_MARK in text
        assert "License: BSD-3-Clause" not in text

    def test_british_licence(self, british_zip, tmp_path):
        """英式拼写LICENCE包（tqdm场景）。"""
        run_extract(british_zip, tmp_path)
        text = readme_of(tmp_path)
        assert "License: Apache-2.0\n" in text and APACHE_MARK in text

    def test_spdx_suffix_filenames(self, spdx_zip, tmp_path):
        """文件名以SPDX版本后缀结尾的包（Apache-2.0/GPL-3.0-only）。"""
        run_extract(spdx_zip, tmp_path)
        text = readme_of(tmp_path)
        assert "License: Apache-2.0\n" in text
        assert "License: GPL-3.0-only" in text

    def test_package_without_license(self, bare_zip, tmp_path):
        """无license文件：输出占位文案而非报错。"""
        run_extract(bare_zip, tmp_path)
        assert "No license information found" in readme_of(tmp_path)

    def test_near_empty_package(self, near_empty_zip, tmp_path):
        """仅含占位文件的包：完整跑通不崩溃。"""
        run_extract(near_empty_zip, tmp_path)
        assert "No license information found" in readme_of(tmp_path)


@needs_scancode
class TestLicenseParams:
    """-l/-p参数组合的真实扫描行为。"""

    def test_name_and_path_recommended_combo(self, sample_zip, tmp_path):
        result = run_cli(tmp_path, "-t", str(sample_zip), "-n", "samplelib",
                         "-v", "1.2.3", "-l", "MIT", "-p", "LICENSE", "-o", str(tmp_path))
        assert result.returncode == 0, result.stdout[-2000:]
        text = readme_of(tmp_path)
        assert "License: MIT\n" in text and MIT_MARK in text
        assert "matches the license detected" in result.stdout

    def test_path_selects_licenses_dir(self, sample_zip, tmp_path):
        run_extract(sample_zip, tmp_path, "-p", "LICENSES/Apache-2.0.txt")
        text = readme_of(tmp_path)
        assert "License: Apache-2.0\n" in text and APACHE_MARK in text
        assert "License: MIT\n" not in text

    def test_explicit_nested_path(self, sample_zip, tmp_path):
        """显式指定嵌套文件同样可选。"""
        run_extract(sample_zip, tmp_path, "-p", "docs/LICENSE")
        assert "License: BSD-3-Clause\n" in readme_of(tmp_path)

    def test_path_outside_auto_detection_rules(self, sample_zip, tmp_path):
        """-p指向不符合自动识别规则的文件（NOTICE：文件名不在license
        模式内、位置为包根散文件）：按用户输入处理——记录无license检出
        时兜底Unknown，正文仍从用户指定的文件读出。"""
        run_extract(sample_zip, tmp_path, "-p", "NOTICE")
        text = readme_of(tmp_path)
        assert "License: Unknown" in text
        assert "This product includes software developed by the SampleLib Dev Team" in text


@needs_scancode
class TestInvalidInputs:
    """错误输入：退出码与提示信息。"""

    def test_missing_license_path(self, sample_zip, tmp_path):
        result = run_cli(tmp_path, "-t", str(sample_zip), "-n", "s", "-v", "1",
                         "-p", "NOT-EXIST", "-o", str(tmp_path))
        assert result.returncode == 1
        assert "License file not found" in result.stdout

    def test_license_path_is_directory(self, sample_zip, tmp_path):
        result = run_cli(tmp_path, "-t", str(sample_zip), "-n", "s", "-v", "1",
                         "-p", "LICENSES", "-o", str(tmp_path))
        assert result.returncode == 1
        assert "License file not found" in result.stdout

    def test_license_path_escape_rejected(self, sample_zip, tmp_path):
        result = run_cli(tmp_path, "-t", str(sample_zip), "-n", "s", "-v", "1",
                         "-p", "../escape.txt", "-o", str(tmp_path))
        assert result.returncode == 1
        assert "must be inside the target" in result.stdout

    def test_license_path_symlink_escape_rejected(self, sample_dir, tmp_path):
        """目录输入下，目标内symlink指向外部文件：拒绝而非跟随扫描。"""
        import os
        outside = tmp_path / "outside_secret.txt"
        outside.write_text("external\n", encoding="utf-8")
        link = sample_dir / "sneaky"
        try:
            os.symlink(outside, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlink creation not permitted on this platform/account")
        try:
            result = run_cli(tmp_path, "-t", str(sample_dir), "-n", "s", "-v", "1",
                             "-p", "sneaky", "-o", str(tmp_path))
        finally:
            link.unlink(missing_ok=True)
        assert result.returncode == 1
        assert "must be inside the target" in result.stdout

    def test_target_not_exists(self, tmp_path):
        result = run_cli(tmp_path, "-t", str(tmp_path / "ghost.zip"),
                         "-n", "s", "-v", "1", "-o", str(tmp_path))
        assert result.returncode == 1
        assert "does not exist" in result.stdout

    def test_target_plain_file_rejected(self, tmp_path):
        """target为非压缩包普通文件：流水线失败而非静默产出。"""
        plain = tmp_path / "plain.txt"
        plain.write_text("not an archive\n", encoding="utf-8")
        result = run_cli(tmp_path, "-t", str(plain), "-n", "s", "-v", "1",
                         "-o", str(tmp_path))
        assert result.returncode != 0
        assert "Pipeline failed" in result.stdout

    def test_output_dir_nested_auto_created(self, sample_zip, tmp_path):
        """-o指向多级不存在目录时自动创建并落入其中。"""
        out = tmp_path / "level1" / "level2"
        result = run_cli(tmp_path, "-t", str(sample_zip), "-n", "samplelib",
                         "-v", "1.2.3", "-o", str(out))
        assert result.returncode == 0, result.stdout[-2000:]
        assert (out / "Readme.opensource").exists()

    def test_jobs_passthrough(self, sample_zip, tmp_path):
        """-j/--max-in-memory透传给scancode且流水线正常完成。"""
        run_extract(sample_zip, tmp_path, "-j", "2", "--max-in-memory", "100")
        assert "License: MIT\n" in readme_of(tmp_path)

    def test_failure_cleans_previous_outputs(self, sample_zip, tmp_path):
        """失败路径的清理回调：删除输出目录中已存在的过程文件（含旧产物）。"""
        stale = tmp_path / "Readme.opensource"
        stale.write_text("stale content from previous run\n", encoding="utf-8")
        result = run_cli(tmp_path, "-t", str(sample_zip), "-n", "s", "-v", "1",
                         "-p", "NOT-EXIST", "-o", str(tmp_path))
        assert result.returncode == 1
        assert not stale.exists()  # 失败时清理回调删除旧产物（当前实现的契约）
        # 无解压目录残留
        assert not list(tmp_path.glob("*-extract"))


class TestCliBehavior:
    """CLI通用行为（无需扫描）。"""

    def test_guide(self, tmp_path):
        result = run_cli(tmp_path, "--guide")
        assert result.returncode == 0
        assert "OSS information Extraction Tool" in result.stdout

    def test_missing_required_args(self, tmp_path):
        import subprocess, sys
        from conftest import SRC
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC)
        result = subprocess.run([sys.executable, "-m", "ossinfo_extraction.main",
                                 "-t", "x"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", cwd=tmp_path, env=env)
        assert result.returncode == 2  # argparse缺参标准退出码

    def test_quiet_log_level(self, tmp_path):
        import subprocess, sys
        from conftest import SRC
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC)
        env["LOG_LEVEL"] = "QUIET"
        result = subprocess.run([sys.executable, "-m", "ossinfo_extraction.main",
                                 "--guide"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", cwd=tmp_path, env=env)
        assert result.returncode == 0
        assert "[INFO]" not in result.stdout
        assert "OSS information Extraction Tool" in result.stdout

    @needs_scancode
    def test_default_output_location(self, sample_zip, tmp_path):
        """不带-o时输出到目标文件同级目录。"""
        local_zip = tmp_path / "local-sample.zip"
        shutil.copy(sample_zip, local_zip)
        result = run_cli(tmp_path, "-t", str(local_zip), "-n", "samplelib", "-v", "1.2.3")
        assert result.returncode == 0, result.stdout[-2000:]
        assert (tmp_path / "Readme.opensource").exists()
        assert "License: MIT\n" in (tmp_path / "Readme.opensource").read_text(encoding="utf-8")
