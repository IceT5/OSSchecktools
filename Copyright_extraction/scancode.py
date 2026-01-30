import sys
import subprocess
from pathlib import Path

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

    print("[INFO] Running scancode:")
    print(" ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ScanCode failed with exit code {result.returncode}")
