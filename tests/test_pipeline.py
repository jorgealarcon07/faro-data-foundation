import json
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

from faro_foundation import pipeline, source, store
from faro_foundation.common import FaroError
from faro_foundation.report import export_report

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def metadata(settings):
    path = source.fixture(settings.home, rows=120)
    return source.prepare(settings.home, path, "synthetic", settings.batch_size)


def head(settings):
    with store.connect(settings) as conn:
        return conn.execute(
            "SELECT run_id FROM faro.publications WHERE namespace='retail_synthetic'"
        ).fetchone()["run_id"]


def test_real_postgres_dbt_replay_backfill(settings, metadata):
    first = pipeline.execute(settings, metadata)
    second = pipeline.execute(settings, metadata)
    partial = pipeline.execute(settings, metadata, start="2011-01-03", end="2011-01-05")
    assert first["rows"] == 120
    assert first["dbt"]["tests_passed"] >= 10
    assert first["data_sha256"] == second["data_sha256"] == partial["data_sha256"]
    assert first["checks"]["unknown_customer_rows"] > 0
    assert pipeline.execute(settings, resume=partial["run_id"])["run_id"] == partial["run_id"]


@pytest.mark.parametrize("point", ["after-load", "before-publish"])
def test_crash_preserves_head_and_resume(settings, metadata, point):
    previous = head(settings)
    with pytest.raises(FaroError, match="Injected crash"):
        pipeline.execute(settings, metadata, failpoint=point)
    assert head(settings) == previous
    with store.connect(settings) as conn:
        run = conn.execute(
            "SELECT run_id FROM faro.runs WHERE state='failed' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()["run_id"]
    result = pipeline.execute(settings, resume=run)
    assert result["rows"] == 120
    assert head(settings) == run


@pytest.mark.parametrize("fault", ["drop-row", "amount"])
def test_independent_gate_detects_corruption(settings, metadata, fault):
    previous = head(settings)
    with pytest.raises(FaroError, match="baseline reconciliation failed"):
        pipeline.execute(settings, metadata, fault=fault)
    assert head(settings) == previous


def test_primary_key_rejects_duplicate_source_key(settings, metadata):
    with pytest.raises(psycopg.errors.UniqueViolation), store.connect(settings) as conn:
        conn.execute(
            "INSERT INTO faro.source_rows SELECT * FROM faro.source_rows "
            "WHERE dataset_sha256=%s LIMIT 1",
            (metadata["dataset_sha256"],),
        )


def test_concurrent_head_cannot_overwrite_new_publication(settings, metadata):
    stale = pipeline.new_run(settings, metadata)
    pipeline.execute(settings, metadata)
    with pytest.raises(FaroError, match="Concurrent publication"):
        store.publish(settings, stale)


def test_consumer_exports_and_cli(settings, metadata, tmp_path):
    target = export_report(settings, "retail_synthetic", tmp_path)
    payload = json.loads((tmp_path / "report.json").read_text())
    assert payload["manifest"]["rows"] == 120
    assert target.exists() and (tmp_path / "activity.csv").exists()
    assert "DEMOSTRACIÓN SINTÉTICA" in target.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "faro_foundation.cli", "validate"],
        cwd=settings.home,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_backfill_requires_same_version(settings, metadata):
    altered = {**metadata, "dataset_sha256": "a" * 64}
    with pytest.raises(FaroError, match="SAME approved source"):
        pipeline.new_run(settings, altered, "2011-01-01", "2011-01-02")


def test_explain_sql_parameterization(settings):
    with store.connect(settings) as conn:
        result = conn.execute(
            "SELECT source_row_id FROM faro.source_rows WHERE source_row_id=%s", ("' OR TRUE --",)
        ).fetchall()
    assert result == []


def test_five_workflow_phases(settings, metadata):
    import uuid

    from faro_foundation.workflow import phase

    key = "pytest-" + uuid.uuid4().hex
    for stage in ["prepare", "load", "build", "validate", "publish"]:
        result = phase(settings, stage, key, Path(metadata["source_path"]), kind="synthetic")
    assert result["run_id"] == head(settings)
    assert phase(settings, "publish", key)["run_id"] == result["run_id"]


def test_cannot_publish_unvalidated_candidate(settings, metadata):
    run = pipeline.new_run(settings, metadata)
    with pytest.raises(FaroError, match="Only independently validated"):
        store.publish(settings, run)
