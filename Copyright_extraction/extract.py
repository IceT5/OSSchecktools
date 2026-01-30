import os
import tempfile
import sys
import subprocess
from pathlib import Path

def run_extractcode(target: str) -> Path:
    """
    When target is an archive, execute this function.
    Run extractcode --shallow.
    extractcode will create <archive_name>-extract directory automatically.
    """
    archive = Path(target).resolve()

    custom_tmp = Path(tempfile.mkdtemp(prefix="scancode_tmp_", dir=str(archive.parent)))
    env = os.environ.copy()
    env['TMP'] = str(custom_tmp)
    env['TEMP'] = str(custom_tmp)

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
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"extractcode failed with exit code {result.returncode}")

    extract_dir = archive.parent / f"{archive.name}-extract"

    if not extract_dir.exists():
        raise RuntimeError(
            f"Expected extract directory not found: {extract_dir}"
        )

    return extract_dir
