"""Start/stop an isolated local PostgreSQL cluster using user-supplied binaries.

No service installation, admin rights, external listener, or system configuration changes.
"""

import argparse
import os
import secrets
import subprocess
from pathlib import Path


def run(command):
    return subprocess.run(
        command, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["start", "stop"])
    p.add_argument("--bin", type=Path, required=True)
    p.add_argument("--home", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--port", type=int, default=55432)
    args = p.parse_args()
    root = args.home.resolve()
    runtime = root / ".runtime"
    runtime.mkdir(exist_ok=True)
    data = runtime / "pgdata"
    suffix = ".exe" if os.name == "nt" else ""
    binary = args.bin.resolve()
    if args.action == "stop":
        run([str(binary / ("pg_ctl" + suffix)), "-D", str(data), "-m", "fast", "-w", "stop"])
        return
    env_file = root / ".env"
    if not data.exists():
        if env_file.exists():
            raise RuntimeError(
                "Existing .env: supply your database manually or choose an unused project copy"
            )
        password = secrets.token_urlsafe(32)
        password_file = runtime / "init.password"
        password_file.write_text(password, encoding="utf-8")
        try:
            run(
                [
                    str(binary / ("initdb" + suffix)),
                    "-D",
                    str(data),
                    "-U",
                    "faro",
                    "--auth=scram-sha-256",
                    "--pwfile=" + str(password_file),
                    "--encoding=UTF8",
                    "--locale=C",
                ]
            )
        finally:
            password_file.unlink(missing_ok=True)
        with (data / "postgresql.conf").open("a", encoding="utf-8") as out:
            out.write(
                "\nlisten_addresses='127.0.0.1'\nshared_buffers='128MB'\nwork_mem='16MB'\nmax_connections=40\n"
            )
        env_file.write_text(
            f"FARO_DB_PASSWORD={password}\nFARO_DB_PORT={args.port}\n"
            "FARO_DB_HOST=127.0.0.1\nFARO_DB_USER=faro\nFARO_DB_NAME=faro\n",
            encoding="utf-8",
        )
    run(
        [
            str(binary / ("pg_ctl" + suffix)),
            "-D",
            str(data),
            "-l",
            str(runtime / "postgres.log"),
            "-o",
            f"-p {args.port}",
            "-w",
            "start",
        ]
    )
    from faro_foundation.cli import load_env
    from faro_foundation.common import Settings
    from faro_foundation.store import connect

    os.environ["FARO_HOME"] = str(root)
    load_env(root)
    from dataclasses import replace

    settings = replace(Settings.from_env(), database="postgres")
    with connect(settings, autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname='faro'").fetchone():
            conn.execute("CREATE DATABASE faro OWNER faro")
    print("PostgreSQL ready on loopback; credentials stored in ignored .env")


if __name__ == "__main__":
    main()
