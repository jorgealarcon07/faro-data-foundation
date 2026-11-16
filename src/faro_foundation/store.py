"""PostgreSQL operations; all values parameterized and identifiers quoted."""

import hashlib
import json
import re
from pathlib import Path

import psycopg
import pyarrow.parquet as pq
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .common import FaroError, Settings
from .source import datetime_or_none, decimal_or_none


def connect(settings: Settings, *, autocommit=False):
    return psycopg.connect(**settings.connect_kwargs(), row_factory=dict_row, autocommit=autocommit)


def schema_name(run_id: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise FaroError("Invalid run ID")
    return "r_" + run_id


def initialize(settings: Settings):
    with connect(settings) as conn:
        conn.execute((settings.home / "sql/001_control.sql").read_text())


def load(settings: Settings, metadata: dict) -> bool:
    with connect(settings) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (metadata["dataset_sha256"],))
        existing = conn.execute(
            "SELECT * FROM faro.sources WHERE dataset_sha256=%s", (metadata["dataset_sha256"],)
        ).fetchone()
        if existing:
            count = conn.execute(
                "SELECT count(*) AS n FROM faro.source_rows WHERE dataset_sha256=%s",
                (metadata["dataset_sha256"],),
            ).fetchone()["n"]
            if (
                count != metadata["rows"]
                or existing["parquet_sha256"] != metadata["parquet_sha256"]
            ):
                raise FaroError("Immutable source cache failed integrity check")
            return False
        conn.execute(
            "INSERT INTO faro.sources VALUES (%s,%s,%s,%s,%s,%s,now())",
            (
                metadata["dataset_sha256"],
                metadata["parquet_sha256"],
                metadata["source_namespace"],
                metadata["data_kind"],
                metadata["rows"],
                Jsonb(metadata),
            ),
        )
        with conn.cursor().copy("COPY faro.source_rows FROM STDIN") as copy:
            for batch in pq.ParquetFile(metadata["parquet_path"]).iter_batches(settings.batch_size):
                for row in batch.to_pylist():
                    copy.write_row(
                        (
                            metadata["dataset_sha256"],
                            *row.values(),
                            decimal_or_none(row["quantity_text"]),
                            decimal_or_none(row["price_text"]),
                            datetime_or_none(row["event_text"]),
                        )
                    )
        count = conn.execute(
            "SELECT count(*) AS n FROM faro.source_rows WHERE dataset_sha256=%s",
            (metadata["dataset_sha256"],),
        ).fetchone()["n"]
        if count != metadata["rows"]:
            raise FaroError("Staging row count mismatch")
        conn.execute("ANALYZE faro.source_rows")
    return True


def event(settings: Settings, run_id: str, stage: str, payload: dict):
    with connect(settings) as conn:
        conn.execute(
            "INSERT INTO faro.events(run_id,stage,payload) VALUES(%s,%s,%s)",
            (run_id, stage, Jsonb(payload)),
        )


def clone_for_backfill(settings: Settings, run: dict):
    candidate = schema_name(run["run_id"])
    with connect(settings) as conn:
        active = conn.execute(
            "SELECT 1 FROM faro.runs WHERE candidate_schema=%s AND state='published'", (candidate,)
        ).fetchone()
        if active:
            raise FaroError("A published snapshot cannot be rebuilt in place")
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(candidate)))
        if run["start_date"]:
            prior = conn.execute(
                "SELECT candidate_schema FROM faro.runs WHERE run_id=%s", (run["previous_run"],)
            ).fetchone()
            # Only drop the isolated, never-published candidate table, not source or active data.
            conn.execute(
                sql.SQL("DROP TABLE IF EXISTS {}.fact_invoice_line CASCADE").format(
                    sql.Identifier(candidate)
                )
            )
            conn.execute(
                sql.SQL("CREATE TABLE {}.fact_invoice_line AS TABLE {}.fact_invoice_line").format(
                    sql.Identifier(candidate), sql.Identifier(prior["candidate_schema"])
                )
            )
            conn.execute(
                sql.SQL(
                    "DELETE FROM {}.fact_invoice_line WHERE business_date >= %s "
                    "AND business_date < %s"
                ).format(sql.Identifier(candidate)),
                (run["start_date"], run["end_date"]),
            )


def data_hash(settings: Settings, candidate: str) -> str:
    h = hashlib.sha256()
    with connect(settings) as conn:
        query = sql.SQL(
            "COPY (SELECT * FROM {}.fact_invoice_line ORDER BY source_row_id) "
            "TO STDOUT WITH (FORMAT CSV, NULL '\\N')"
        ).format(sql.Identifier(candidate))
        with conn.cursor().copy(query) as copy:
            for block in copy:
                h.update(block)
    return h.hexdigest()


PUBLIC_MODELS = [
    "fact_invoice_line",
    "dim_customer",
    "dim_product",
    "dim_date",
    "mart_activity",
    "mart_quality",
]


def publish(settings: Settings, run: dict):
    """One transaction switches the namespace pointer and all stable consumer views."""
    with connect(settings) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('faro-publication'))")
        current = conn.execute(
            "SELECT run_id FROM faro.publications WHERE namespace=%s", (run["namespace"],)
        ).fetchone()
        if (current["run_id"] if current else None) != run["previous_run"]:
            raise FaroError("Concurrent publication changed the head; create a new run")
        validated = conn.execute(
            "SELECT state,manifest FROM faro.runs WHERE run_id=%s", (run["run_id"],)
        ).fetchone()
        if not validated or validated["state"] != "validated" or not validated["manifest"]:
            raise FaroError("Only independently validated candidates may be published")
        conn.execute(
            "INSERT INTO faro.publications(namespace,run_id,candidate_schema) VALUES(%s,%s,%s) "
            "ON CONFLICT(namespace) DO UPDATE SET run_id=excluded.run_id, "
            "candidate_schema=excluded.candidate_schema, published_at=now()",
            (run["namespace"], run["run_id"], run["candidate_schema"]),
        )
        snapshots = conn.execute("SELECT * FROM faro.publications ORDER BY namespace").fetchall()
        for model in PUBLIC_MODELS:
            selects = [
                sql.SQL("SELECT *, {}::text AS publication_run_id FROM {}.{}").format(
                    sql.Literal(p["run_id"]),
                    sql.Identifier(p["candidate_schema"]),
                    sql.Identifier(model),
                )
                for p in snapshots
            ]
            conn.execute(
                sql.SQL("CREATE OR REPLACE VIEW faro.{} AS {}").format(
                    sql.Identifier("current_" + model), sql.SQL(" UNION ALL ").join(selects)
                )
            )
        conn.execute(
            "UPDATE faro.runs SET state='published',finished_at=now() WHERE run_id=%s",
            (run["run_id"],),
        )


def fetch_run(settings: Settings, run_id: str) -> dict:
    schema_name(run_id)
    with connect(settings) as conn:
        run = conn.execute("SELECT * FROM faro.runs WHERE run_id=%s", (run_id,)).fetchone()
    if not run:
        raise FaroError("Run does not exist")
    return run


def read_metadata(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
