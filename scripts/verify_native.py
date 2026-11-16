"""Bounded Windows validation: real PostgreSQL and clients share one network sandbox.

Requires a previously initialized project cluster (native_postgres.py) and PG binaries.
Stops only that cluster on completion. Does not delete data or install a service.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from faro_foundation.cli import demo, load_env
from faro_foundation.common import Settings, write_json
from faro_foundation.store import connect


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bin", type=Path, required=True)
    p.add_argument(
        "--full", action="store_true", help="Also run the complete real source, replay and backfill"
    )
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ["FARO_HOME"] = str(root)
    load_env(root)
    settings = Settings.from_env()
    binary = args.bin.resolve()
    data = root / ".runtime/pgdata"
    if not (data / "PG_VERSION").exists():
        raise SystemExit("Initialize the project cluster with native_postgres.py first")
    runtime = root / ".runtime"
    (runtime / "tmp").mkdir(exist_ok=True)
    os.environ["TEMP"] = str(runtime / "tmp")
    os.environ["TMP"] = str(runtime / "tmp")
    suffix = ".exe" if os.name == "nt" else ""
    ctl = str(binary / ("pg_ctl" + suffix))
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    # pg_ctl only targets the explicit project data directory; no unrelated server is stopped.
    subprocess.run(
        [ctl, "-D", str(data), "-m", "fast", "-w", "stop"],
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=40,
        check=False,
    )
    with (runtime / "verification-postgres.log").open("a") as log:
        server = subprocess.Popen(
            [str(binary / ("postgres" + suffix)), "-D", str(data), "-p", str(settings.port)],
            stdout=log,
            stderr=log,
            creationflags=flags,
        )
        try:
            for _ in range(10):
                time.sleep(1)
                try:
                    with connect(settings) as conn:
                        version = conn.execute("select version()").fetchone()
                    break
                except Exception:
                    if server.poll() is not None:
                        raise RuntimeError(
                            "PostgreSQL stopped; inspect verification-postgres.log"
                        ) from None
            else:
                raise RuntimeError("PostgreSQL did not become available")
            (root / "reports").mkdir(exist_ok=True)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-m",
                    "not airflow",
                    "--tb=short",
                    "--junitxml=reports/tests.xml",
                ],
                check=True,
            )
            details = demo(settings)
            result = {"postgres": version, "demo": details}
            if args.full:
                from faro_foundation import pipeline, source, store
                from faro_foundation.report import export_report

                beginning = time.perf_counter()
                path = source.download(root)
                metadata = source.prepare(root, path, "public_real_historical", settings.batch_size)
                result["preparation_seconds"] = time.perf_counter() - beginning
                runs = []
                for label, kwargs in [
                    ("full", {}),
                    ("replay", {}),
                    ("backfill", {"start": "2010-12-01", "end": "2010-12-08"}),
                ]:
                    started = time.perf_counter()
                    manifest = pipeline.execute(settings, metadata, **kwargs)
                    runs.append(
                        {
                            **manifest,
                            "benchmark_label": label,
                            "measured_wall_seconds": time.perf_counter() - started,
                        }
                    )
                    print(
                        json.dumps(
                            {
                                "stage": label,
                                "run_id": manifest["run_id"],
                                "rows": manifest["rows"],
                                "seconds": runs[-1]["measured_wall_seconds"],
                            }
                        ),
                        flush=True,
                    )
                assert len({r["data_sha256"] for r in runs}) == 1
                result["real_runs"] = runs
                result["report"] = str(export_report(settings, "retail_uk_reference"))
                with store.connect(settings) as conn:
                    result["query_plan"] = conn.execute(
                        "EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) "
                        "SELECT record_class,count(*),sum(signed_amount) FROM faro.current_fact_invoice_line "
                        "WHERE source_namespace=%s GROUP BY record_class",
                        ("retail_uk_reference",),
                    ).fetchone()
            write_json(root / "reports/acceptance.json", result)
            print("Acceptance completed; evidence in reports/acceptance.json")
        finally:
            subprocess.run(
                [ctl, "-D", str(data), "-m", "fast", "-w", "stop"],
                creationflags=flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=40,
                check=False,
            )
            server.wait(timeout=20)


if __name__ == "__main__":
    main()
