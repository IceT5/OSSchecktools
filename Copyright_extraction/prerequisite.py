import subprocess

def check_scancode_available():
    """
    Check whether scancode command is available.
    """
    try:
        result = subprocess.run(["scancode","--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        raise RuntimeError(
            "scancode command not found.\n"
            "Please install dependencies first:\n"
            " pip install -r requirements.txt\n"
            "or\n"
            " pip install ."
        )
    
    if result.returncode != 0:
        raise RuntimeError(
            "scancode command exists but is not working properly.\n"
            f"stderr: {result.stderr}"
        )

    print(f"[OK] Scancode available: {result.stdout.strip()}")