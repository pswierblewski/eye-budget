#!/usr/bin/env python3
"""Load backend/.env, build a PostgreSQL URL, then run `yoyo apply` (same as manual CLI)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv


def _connection_url() -> str:
    user = quote(os.environ["POSTGRESQL_USER"], safe="")
    password = quote(os.environ["POSTGRESQL_PASSWORD"], safe="")
    host = os.environ["POSTGRESQL_HOST"]
    port = os.environ["POSTGRESQL_PORT"]
    db = os.environ["POSTGRESQL_DB"]
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def main() -> int:
    backend_dir = Path(__file__).resolve().parent.parent
    load_dotenv(backend_dir / ".env")
    for key in (
        "POSTGRESQL_HOST",
        "POSTGRESQL_PORT",
        "POSTGRESQL_USER",
        "POSTGRESQL_PASSWORD",
        "POSTGRESQL_DB",
    ):
        if key not in os.environ or not os.environ[key]:
            print(f"Missing or empty {key} after loading backend/.env", file=sys.stderr)
            return 1

    url = _connection_url()
    cmd = [
        sys.executable,
        "-m",
        "yoyo",
        "apply",
        "--batch",
        "--no-config-file",
        "-d",
        url,
        "migrations",
    ]
    return subprocess.run(cmd, check=False, cwd=str(backend_dir)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
