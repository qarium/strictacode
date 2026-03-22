import json
import subprocess
import sys


def collect(path: str) -> dict:
    cmd = [sys.executable, "-m", "radon", "cc", "-j", path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)
