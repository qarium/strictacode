"""stub"""

import json
import os
import subprocess
import tempfile


def collect(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        kts_file = os.path.join(tmpdir, "collector.kts")
        with open(kts_file, "w") as f:
            f.write(__doc__)

        cmd = ["kotlinc", "-script", kts_file, path]
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)
