import json
import subprocess
import sys


def collect(path: str) -> dict:
    """Run radon cyclomatic complexity analysis on a Python project.

    Args:
        path: Root directory or file path to analyze.

    Returns:
        Parsed JSON output from radon as a dict.

    Raises:
        RuntimeError: If radon exits with a non-zero return code.
    """
    cmd = [sys.executable, "-m", "radon", "cc", "-j", path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)
