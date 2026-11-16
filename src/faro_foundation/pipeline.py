"""Batch orchestration with isolated candidates, independently checked gates, and atomic publication."""

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import date
from pathlib import Path

import jsonschema
import psutil
from psycopg import sql
from psycopg.types.json import Jsonb

from . import baseline, store
from .common import (
    FaroError,
    Settings,
    code_fingerprint,
    digest,
    environment,
    git_sha,
    utc_now,
    write_json,
)

logger = logging.getLogger("faro")


def _log(settings: Settings, run_id: str, stage: str, **payload):
    record = {"time": utc_now(), "run_id": run_id, "stage": stage, **payload}
    directory = settings.home / "reports/runs" / run_id
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "events.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps(record, default=str) + "\n")
    logger.info(json.dumps(record, default=str))
    store.event(settings, run_id, stage, payload)


class MemorySampler:
    """Sample Python+child RSS, not the separately running database server."""

    def __init__(self):
        self.peak = 0
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self):
        while not self.stop.wait(0.1):
            try:
                process = psutil.Process()
                self.peak = max(
                    self.peak,
                    sum(
                        p.memory_info().rss
                        for p in [process, *process.children(recursive=True)]
                        if p.is_running()
                    ),
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=2)


def new_run(settings: Settings, metadata: dict, start=None, end=None) -> dict:
    if bool(start) != bool(end):
        raise FaroError("Backfill requires both start and end, interval [start,end)")
    if start and date.fromisoformat(start) >= date.fromisoformat(end):
        raise FaroError("Backfill end must follow start")
    with store.connect(settings) as conn:
        previous = conn.execute(
            "SELECT p.*, r.dataset_sha256 FROM faro.publications p "
            "JOIN faro.runs r USING(run_id) WHERE p.namespace=%s",
            (metadata["source_namespace"],),
        ).fetchone()
        if start and (not previous or previous["dataset_sha256"] != metadata["dataset_sha256"]):
            raise FaroError(
                "Backfill needs a published snapshot of the SAME approved source version"
            )
        run_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO faro.runs(run_id,namespace,dataset_sha256,candidate_schema,state,"
            "start_date,end_date,previous_run,source_metadata) VALUES(%s,%s,%s,%s,'created',%s,%s,%s,%s)",
            (
                run_id,
                metadata["source_namespace"],
                metadata["dataset_sha256"],
                store.schema_name(run_id),
                start,
                end,
                previous["run_id"] if previous else None,
                Jsonb(metadata),
            ),
        )
    return store.fetch_run(settings, run_id)


def dbt_build(settings: Settings, run: dict, directory: Path, *, test_only=False):
    env = os.environ.copy()
    env.update(
        {
            "FARO_CANDIDATE_SCHEMA": run["candidate_schema"],
            "FARO_DB_PASSWORD": settings.password,
            "FARO_DB_HOST": settings.host,
            "FARO_DB_PORT": str(settings.port),
            "FARO_DB_NAME": settings.database,
            "FARO_DB_USER": settings.user,
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            "DBT_LOG_FORMAT": "json",
            "DBT_LOG_PATH": str(directory / "dbt_logs"),
            "DBT_TARGET_PATH": str(directory / "dbt_target"),
        }
    )
    variables = {
        "namespace": run["namespace"],
        "dataset_sha256": run["dataset_sha256"],
        "data_kind": run["source_metadata"]["data_kind"],
        "start_date": str(run["start_date"]) if run["start_date"] else "",
        "end_date": str(run["end_date"]) if run["end_date"] else "",
    }
    executable = shutil.which("dbt") or str(
        Path(sys.executable).parent / ("dbt.exe" if os.name == "nt" else "dbt")
    )
    command = [
        executable,
        "test" if test_only else "build",
        "--project-dir",
        str(settings.home / "dbt"),
        "--profiles-dir",
        str(settings.home / "dbt"),
        "--vars",
        json.dumps(variables),
        "--no-use-colors",
        "--no-partial-parse",
    ]
    with (directory / ("dbt-test.log" if test_only else "dbt-build.log")).open(
        "w", encoding="utf-8"
    ) as log:
        result = subprocess.run(
            command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=900, check=False
        )
    if result.returncode:
        raise FaroError(
            "dbt failed; inspect the run's dbt-build.log / dbt-test.log (no publication)"
        )
    results = json.loads((directory / "dbt_target/run_results.json").read_text())
    return {
        "nodes": len(results["results"]),
        "tests_passed": sum(r["status"] == "pass" for r in results["results"]),
    }


def validate(settings: Settings, run: dict, expected: dict) -> dict:
    with store.connect(settings) as conn:
        rows = conn.execute(
            sql.SQL(
                "SELECT business_date, record_class, count(*) AS rows, "
                "coalesce(sum(signed_amount),0) AS amount, "
                "count(*) FILTER(WHERE signed_amount IS NULL) AS unknown_amount_rows "
                "FROM {}.fact_invoice_line GROUP BY 1,2"
            ).format(sql.Identifier(run["candidate_schema"]))
        ).fetchall()
        actual = {
            f"{r['business_date'] or 'invalid'}|{r['record_class']}": {
                k: str(r[k]) for k in ["rows", "amount", "unknown_amount_rows"]
            }
            for r in rows
        }
        from decimal import Decimal

        mismatches = []
        for key in sorted(set(actual) | set(expected["groups"])):
            a, e = actual.get(key), expected["groups"].get(key)
            if a is None or e is None or any(Decimal(a[k]) != Decimal(str(e[k])) for k in a):
                mismatches.append(key)
        if mismatches:
            raise FaroError(
                f"Independent baseline reconciliation failed in {len(mismatches)} groups"
            )
        count = sum(int(v["rows"]) for v in actual.values())
        if count != expected["rows"]:
            raise FaroError("Lost input rows")
        stats = conn.execute(
            sql.SQL(
                "SELECT count(*) AS rows, "
                "count(*) FILTER(WHERE customer_key='__UNKNOWN__') AS unknown_customer_rows, "
                "count(*) FILTER(WHERE record_class='quarantine') AS quarantine_rows, "
                "sum(signed_amount) AS known_signed_amount "
                "FROM {}.fact_invoice_line"
            ).format(sql.Identifier(run["candidate_schema"]))
        ).fetchone()
    return {
        "status": "provisional"
        if stats["quarantine_rows"] or stats["unknown_customer_rows"]
        else "ready",
        "reconciled_groups": len(actual),
        **stats,
    }


def make_manifest(settings, run, checks, fingerprint, dbt, timings, elapsed, peak):
    metadata = run["source_metadata"]
    return {
        "contract_version": "1.0.0",
        "contracts_sha256": digest(settings.home / "contracts.lock.json"),
        "run_id": run["run_id"],
        "git_sha": git_sha(settings.home),
        "code_sha256": code_fingerprint(settings.home),
        "dataset_sha256": metadata["dataset_sha256"],
        "source_namespace": run["namespace"],
        "data_kind": metadata["data_kind"],
        "seed": metadata["seed"],
        "as_of": utc_now(),
        "rows": checks["rows"],
        "data_sha256": fingerprint,
        "checks": checks,
        "dbt": dbt,
        "interval": {"start": str(run["start_date"] or ""), "end": str(run["end_date"] or "")},
        "timings": timings,
        "elapsed_seconds": elapsed,
        "peak_python_tree_rss_bytes": peak,
        "environment": environment(),
        "source_metadata": metadata,
    }


def save_validated(settings, run, manifest):
    contract = json.loads((settings.home / "contracts/v1/run_manifest.schema.json").read_text())
    payload = json.loads(json.dumps(manifest, default=str))
    jsonschema.validate(payload, contract)
    write_json(settings.home / "reports/runs" / run["run_id"] / "manifest.json", payload)
    with store.connect(settings) as conn:
        conn.execute(
            "UPDATE faro.runs SET state='validated',manifest=%s,error_code=NULL WHERE run_id=%s",
            (Jsonb(payload), run["run_id"]),
        )


def execute(
    settings: Settings,
    metadata: dict | None = None,
    *,
    start=None,
    end=None,
    resume=None,
    failpoint=None,
    fault=None,
) -> dict:
    store.initialize(settings)
    run = store.fetch_run(settings, resume) if resume else new_run(settings, metadata, start, end)
    if run["state"] == "published":
        return run["manifest"]
    metadata = run["source_metadata"]
    directory = settings.home / "reports/runs" / run["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    timings = {}
    # Session lock serializes retries of the same run. Namespace publication uses an optimistic head check.
    with store.connect(settings, autocommit=True) as lock, MemorySampler() as memory:
        lock.execute("SELECT pg_advisory_lock(hashtext(%s))", (run["run_id"],))
        try:
            current = store.fetch_run(settings, run["run_id"])
            if current["state"] == "published":
                return current["manifest"]
            stage = time.perf_counter()
            expected = baseline.reference(metadata, Path(metadata["parquet_path"]).parent)
            timings["baseline_seconds"] = time.perf_counter() - stage
            stage = time.perf_counter()
            loaded = store.load(settings, metadata)
            timings["load_seconds"] = time.perf_counter() - stage
            _log(settings, run["run_id"], "loaded", rows=metadata["rows"], cache_hit=not loaded)
            if failpoint == "after-load":
                raise FaroError("Injected crash after staging (SIMULATED)")
            store.clone_for_backfill(settings, run)
            stage = time.perf_counter()
            dbt = dbt_build(settings, run, directory)
            timings["dbt_seconds"] = time.perf_counter() - stage
            if fault:
                with store.connect(settings) as conn:
                    table = sql.SQL("{}.fact_invoice_line").format(
                        sql.Identifier(run["candidate_schema"])
                    )
                    if fault == "drop-row":
                        conn.execute(
                            sql.SQL(
                                "DELETE FROM {} WHERE source_row_id=(SELECT min(source_row_id) FROM {})"
                            ).format(table, table)
                        )
                    elif fault == "amount":
                        conn.execute(
                            sql.SQL(
                                "UPDATE {} SET signed_amount=signed_amount+1 WHERE source_row_id="
                                "(SELECT min(source_row_id) FROM {} WHERE signed_amount IS NOT NULL)"
                            ).format(table, table)
                        )
                    else:
                        raise FaroError("Unknown test fault")
            stage = time.perf_counter()
            checks = validate(settings, run, expected)
            fingerprint = store.data_hash(settings, run["candidate_schema"])
            timings["validation_seconds"] = time.perf_counter() - stage
            manifest = make_manifest(
                settings,
                run,
                checks,
                fingerprint,
                dbt,
                timings,
                time.perf_counter() - started,
                memory.peak,
            )
            save_validated(settings, run, manifest)
            _log(
                settings,
                run["run_id"],
                "validated",
                data_sha256=fingerprint,
                status=checks["status"],
            )
            if failpoint == "before-publish":
                raise FaroError("Injected crash before publication (SIMULATED)")
            store.publish(settings, run)
            _log(settings, run["run_id"], "published", rows=checks["rows"])
            return json.loads(json.dumps(manifest, default=str))
        except Exception as exc:
            # Do not put arbitrary driver/subprocess text (potentially containing DSN) in logs.
            safe = str(exc) if isinstance(exc, FaroError) else type(exc).__name__
            with store.connect(settings) as conn:
                conn.execute(
                    "UPDATE faro.runs SET state='failed',error_code=%s,finished_at=now() "
                    "WHERE run_id=%s AND state<>'published'",
                    (safe, run["run_id"]),
                )
            _log(settings, run["run_id"], "failed", error=safe)
            raise
