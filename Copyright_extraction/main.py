import json
import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(cmd, check=False):
    """
    统一的命令执行封装
    """
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def ensure_scancode_installed():
    """
    确保 scancode-toolkit 已安装并可用
    """
    #  先检查 scancode 是否可用
    code, out, err = run_command(["scancode", "--version"])

    if code == 0:
        print(f"[OK] ScanCode detected: {out}")
        return

    print("[INFO] ScanCode not found, installing scancode-toolkit via pip...")

    #  安装 scancode-toolkit
    code, out, err = run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", "scancode-toolkit"],
        check=False
    )

    if code != 0:
        print("[ERROR] Failed to install scancode-toolkit")
        print(err or out)
        sys.exit(1)

    #  再次验证
    code, out, err = run_command(["scancode", "--version"])

    if code != 0:
        print("[ERROR] scancode-toolkit installed but scancode command is still unavailable.")
        print("Possible reasons:")
        print("  - pip install path not in PATH")
        print("  - virtual environment not activated")
        print("  - permission issues")
        sys.exit(1)

    print(f"[OK] ScanCode installed successfully: {out}")


def run_extractcode(archive_path: str) -> Path:
    """
    Run extractcode --shallow.
    extractcode will create <archive_name>-extract directory automatically.
    """
    archive = Path(archive_path).resolve()

    if not archive.exists():
        raise FileNotFoundError(f"Archive not found: {archive}")

    cmd = [
        "extractcode",
        "--shallow",
        str(archive),
    ]

    print("Running extractcode:")
    print(" ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if result.returncode != 0:
        raise RuntimeError(f"extractcode failed with exit code {result.returncode}")

    extract_dir = archive.parent / f"{archive.name}-extract"

    if not extract_dir.exists():
        raise RuntimeError(
            f"Expected extract directory not found: {extract_dir}"
        )

    return extract_dir


def run_scancode(scan_target: Path, result_json: Path, jobs: int = 8):
    """
    Run ScanCode Toolkit.
    """
    cmd = [
        "scancode",
        "-c",
        "--filter-clues",
        "--only-findings",
        "--json-pp",
        str(result_json),
        str(scan_target),
        "-n",
        str(jobs),
    ]

    print("Running scancode:")
    print(" ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ScanCode failed with exit code {result.returncode}")


def extract_and_deduplicate_copyright(
    result_json: Path,
    output_txt: Path,
):
    ignored_suffixes = {
        ".md",
        ".rst",
        ".txt",
        ".adoc",
        ".markdown",
    }
    with result_json.open("r", encoding="utf-8") as f:
        data = json.load(f)

    unique_records = set()
    deduplicated_results = []

    for file_info in data.get("files", []):
        file_path = file_info.get("path", "")
        suffix = Path(file_path).suffix.lower()

        if suffix in ignored_suffixes:
            continue

        for copyright_info in file_info.get("copyrights", []):
            value = (
                copyright_info.get("copyright")
                or copyright_info.get("statement")
            )
            if not value:
                continue
            
            value_stripped = value.strip()

            if "copyright" not in value_stripped.lower():
                continue

            if value_stripped not in unique_records:
                unique_records.add(value_stripped)
                deduplicated_results.append(value_stripped)

    with output_txt.open("w", encoding="utf-8") as f:
        for item in deduplicated_results:
            f.write(item.strip() + "\n")

    print(f"Extracted {len(deduplicated_results)} unique records")
    print(f"Output written to {output_txt}")


def cleanup_extract_dir(extracted_dir: Path):
    """
    安全删除 extractcode 生成的目录
    """
    if not extract_dir.exists():
        print(f"[INFO] Extracted directory not found, skip cleanup: {extract_dir}")
        return

    if not extract_dir.is_dir():
        print(f"[WARN] Path is not a directory, skip cleanup: {extract_dir}")
        return

    # 额外安全校验：目录名必须以 _extract 结尾
    if not extract_dir.name.endswith("-extract"):
        print(f"[WARN] Directory name does not end with '-extract', skip cleanup: {extract_dir}")
        return

    try:
        shutil.rmtree(extracted_dir)
        # os.remove(RESULT_JSON)
        print(f"[OK] Cleaned up extracted directory: {extract_dir}")
    except Exception as e:
        print(f"[WARN] Failed to cleanup extracted directory: {extract_dir}")
        print(f"       Reason: {e}")



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scan_archive.py <archive_file>")
        sys.exit(1)

    archive_file = Path(sys.argv[1]).resolve()

    RESULT_JSON = archive_file.parent / "result.json"
    OUTPUT_TXT = archive_file.parent / f"{archive_file.name}_copyright"
    
    try:
        # 1. install scancode
        ensure_scancode_installed()

        # 2. extract archive
        extract_dir = run_extractcode(archive_file)

        # 3. scan extracted directory
        run_scancode(extract_dir, RESULT_JSON)

        # 4. parse and deduplicate
        extract_and_deduplicate_copyright(RESULT_JSON, OUTPUT_TXT)

    except Exception as e:
        print("[ERROR] Pipeline failed, extracted directory will be kept for debugging.")
        print(e)
        raise

    else:
        #  只有全部成功，才清理
        cleanup_extract_dir(extract_dir)
