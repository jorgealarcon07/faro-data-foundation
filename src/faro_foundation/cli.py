"""Explicit batch commands; no work is performed during module import."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from . import pipeline, source, store
from .common import FaroError, Settings, write_json
from .report import export_report


def load_env(home: Path):
    path = home / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if key.startswith(("FARO_", "DBT_")):
                    os.environ.setdefault(key, value)


def parser():
    root = argparse.ArgumentParser(description="Faro: verified data close")
    root.add_argument("--home", type=Path, default=Path(os.getenv("FARO_HOME", ".")))
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("download")
    sub.add_parser("init-db")
    sub.add_parser("fixture")
    run = sub.add_parser("run")
    run.add_argument("--input", type=Path)
    run.add_argument("--kind", choices=["synthetic", "public_real_historical"], default="synthetic")
    run.add_argument("--start")
    run.add_argument("--end")
    run.add_argument("--resume")
    run.add_argument("--failpoint", choices=["after-load", "before-publish"])
    for name in ["validate", "report"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--namespace", default="retail_synthetic")
    explain = sub.add_parser("explain")
    explain.add_argument("--row-id", required=True)
    explain.add_argument("--namespace", default="retail_synthetic")
    sub.add_parser("demo")
    sub.add_parser("clean")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    home = args.home.resolve()
    os.environ["FARO_HOME"] = str(home)
    load_env(home)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        if args.command == "download":
            print(source.download(home))
            return 0
        if args.command == "fixture":
            print(source.fixture(home))
            return 0
        if args.command == "clean":
            # Deliberately non-destructive: stopping services is delegated to Compose/pg_ctl.
            print(
                "No source/snapshot removed. Use docker compose stop; see docs/RUNBOOK.md for retention."
            )
            return 0
        settings = Settings.from_env()
        if args.command == "init-db":
            store.initialize(settings)
            print("Control schema ready")
        elif args.command == "run":
            if not args.resume and not args.input:
                raise FaroError("run requires --input or --resume")
            metadata = (
                None
                if args.resume
                else source.prepare(home, args.input, args.kind, settings.batch_size)
            )
            result = pipeline.execute(
                settings,
                metadata,
                start=args.start,
                end=args.end,
                resume=args.resume,
                failpoint=args.failpoint,
            )
            report = export_report(settings, result["source_namespace"])
            print(
                json.dumps(
                    {
                        "run_id": result["run_id"],
                        "rows": result["rows"],
                        "data_sha256": result["data_sha256"],
                        "report": str(report),
                    }
                )
            )
        elif args.command in ["report", "validate"]:
            if args.command == "report":
                print(export_report(settings, args.namespace))
            else:
                with store.connect(settings) as conn:
                    row = conn.execute(
                        "SELECT r.* FROM faro.publications p JOIN faro.runs r USING(run_id) "
                        "WHERE p.namespace=%s",
                        (args.namespace,),
                    ).fetchone()
                if not row:
                    raise FaroError("No publication to validate")
                from .baseline import reference

                expected = reference(
                    row["source_metadata"], Path(row["source_metadata"]["parquet_path"]).parent
                )
                checks = pipeline.validate(settings, row, expected)
                fingerprint = store.data_hash(settings, row["candidate_schema"])
                if fingerprint != row["manifest"]["data_sha256"]:
                    raise FaroError("Published snapshot fingerprint changed")
                print(json.dumps(checks, default=str))
        elif args.command == "explain":
            with store.connect(settings) as conn:
                rows = conn.execute(
                    "SELECT f.*,r.quantity_text,r.price_text,r.event_text FROM "
                    "faro.current_fact_invoice_line f JOIN faro.source_rows r USING(dataset_sha256,source_row_id) "
                    "WHERE f.source_row_id=%s AND f.source_namespace=%s",
                    (args.row_id, args.namespace),
                ).fetchall()
            print(json.dumps(rows, default=str))
        elif args.command == "demo":
            result = demo(settings)
            print(json.dumps(result, default=str))
        return 0
    except Exception as exc:
        safe = str(exc) if isinstance(exc, FaroError) else type(exc).__name__
        print(json.dumps({"status": "failed", "error": safe}), file=sys.stderr)
        return 1


def demo(settings: Settings) -> dict:
    path = source.fixture(settings.home)
    metadata = source.prepare(settings.home, path, "synthetic", settings.batch_size)
    first = pipeline.execute(settings, metadata)
    failed_run = None
    try:
        pipeline.execute(settings, metadata, failpoint="before-publish")
    except FaroError:
        with store.connect(settings) as conn:
            failed_run = conn.execute(
                "SELECT run_id FROM faro.runs WHERE namespace=%s "
                "AND state='failed' ORDER BY created_at DESC LIMIT 1",
                (metadata["source_namespace"],),
            ).fetchone()["run_id"]
            active = conn.execute(
                "SELECT run_id FROM faro.publications WHERE namespace=%s",
                (metadata["source_namespace"],),
            ).fetchone()["run_id"]
            if active != first["run_id"]:
                raise FaroError("Demo failed: publication was not preserved") from None
    resumed = pipeline.execute(settings, resume=failed_run)
    backfill = pipeline.execute(settings, metadata, start="2011-01-03", end="2011-01-05")
    if len({first["data_sha256"], resumed["data_sha256"], backfill["data_sha256"]}) != 1:
        raise FaroError("Demo failed: rebuild/replay/backfill fingerprints differ")
    report = export_report(settings, metadata["source_namespace"])
    result = {
        "data_kind": "synthetic",
        "rows": first["rows"],
        "first_run": first["run_id"],
        "crash_run": failed_run,
        "resumed_run": resumed["run_id"],
        "backfill_run": backfill["run_id"],
        "data_sha256": backfill["data_sha256"],
        "publication_preserved": True,
        "rebuild_equals_backfill": True,
        "report": str(report),
    }
    write_json(settings.home / "reports/demo.json", result)
    return result


if __name__ == "__main__":
    sys.exit(main())
