"""Run the project-local dbt CLI with dotenv credentials kept out of arguments."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def run_dbt(arguments, *, extra_env=None):
    env = {**os.environ}
    for key, value in dotenv_values(ROOT / ".env").items():
        if value is not None:
            env.setdefault(key, value)
    env.update(extra_env or {})
    env["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    return subprocess.run(
        [
            str(Path(sys.executable).parent / "dbt"),
            *arguments,
            "--project-dir",
            str(ROOT / "dbt"),
            "--profiles-dir",
            str(ROOT / "dbt"),
        ],
        cwd=ROOT,
        env=env,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(run_dbt(sys.argv[1:] or ["--help"]))
