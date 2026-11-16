"""Shared configuration and safe, deterministic serialization."""

import hashlib
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class FaroError(Exception):
    """An expected, actionable pipeline failure."""


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temp.replace(path)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Settings:
    home: Path
    host: str
    port: int
    database: str
    user: str
    password: str
    batch_size: int = 20000

    @classmethod
    def from_env(cls) -> "Settings":
        home = Path(os.getenv("FARO_HOME", ".")).resolve()
        password = os.getenv("FARO_DB_PASSWORD", "")
        batch = int(os.getenv("FARO_BATCH_SIZE", "20000"))
        port = int(os.getenv("FARO_DB_PORT", "55432"))
        if not password or not 1 <= port <= 65535 or not 100 <= batch <= 100000:
            raise FaroError("Set FARO_DB_PASSWORD; port must be 1..65535 and batch 100..100000")
        if not (home / "dbt" / "dbt_project.yml").exists():
            raise FaroError("FARO_HOME must point to the project repository")
        return cls(
            home,
            os.getenv("FARO_DB_HOST", "127.0.0.1"),
            port,
            os.getenv("FARO_DB_NAME", "faro"),
            os.getenv("FARO_DB_USER", "faro"),
            password,
            batch,
        )

    def connect_kwargs(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password,
            "connect_timeout": 10,
            "application_name": "faro-foundation",
        }


def git_sha(home: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=home, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unversioned"


def code_fingerprint(home: Path) -> str:
    files = []
    for folder in ["src", "dbt/models", "dbt/tests", "sql", "contracts", "config"]:
        files.extend(
            p for p in (home / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )
    files.extend(home / n for n in ["pyproject.toml", "requirements.lock", "contracts.lock.json"])
    h = hashlib.sha256()
    for path in sorted(files):
        h.update(path.relative_to(home).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()


def environment() -> dict:
    from importlib.metadata import version

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            n: version(n) for n in ["pyarrow", "openpyxl", "dbt-core", "dbt-postgres", "psycopg"]
        },
    }
