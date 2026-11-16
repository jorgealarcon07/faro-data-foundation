"""Five real pipeline phases usable by Airflow or a native batch invocation.

The task key becomes a SHA-256 directory name, never a shell command or SQL identifier.
"""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from . import baseline, pipeline, source, store
from .cli import load_env
from .common import Settings, write_json
from .report import export_report


def phase(
    settings: Settings,
    stage: str,
    key: str,
    input_file: Path | None = None,
    kind="public_real_historical",
    start=None,
    end=None,
):
    directory = settings.home / "reports/workflows" / hashlib.sha256(key.encode()).hexdigest()[:24]
    directory.mkdir(parents=True, exist_ok=True)
    state_path = directory / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    begin = time.perf_counter()
    if stage == "prepare":
        path = input_file or source.download(settings.home)
        state["source"] = source.prepare(settings.home, path, kind, settings.batch_size)
        state["start"], state["end"] = start, end
        baseline.reference(state["source"], Path(state["source"]["parquet_path"]).parent)
    elif stage == "load":
        store.initialize(settings)
        store.load(settings, state["source"])
        run = (
            store.fetch_run(settings, state["run_id"])
            if state.get("run_id")
            else pipeline.new_run(settings, state["source"], state.get("start"), state.get("end"))
        )
        state["run_id"] = run["run_id"]
        # Save the run key before building, so task retries resume the same candidate.
        write_json(state_path, state)
        if run["state"] != "published":
            store.clone_for_backfill(settings, run)
    else:
        run = store.fetch_run(settings, state["run_id"])
        if run["state"] == "published":
            return state
        run_dir = settings.home / "reports/runs" / run["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        if stage == "build":
            state["dbt"] = pipeline.dbt_build(settings, run, run_dir)
        elif stage == "validate":
            expected = baseline.reference(
                state["source"], Path(state["source"]["parquet_path"]).parent
            )
            checks = pipeline.validate(settings, run, expected)
            manifest = pipeline.make_manifest(
                settings,
                run,
                checks,
                store.data_hash(settings, run["candidate_schema"]),
                state["dbt"],
                state.get("timings", {}),
                sum(state.get("timings", {}).values()),
                None,
            )
            pipeline.save_validated(settings, run, manifest)
        elif stage == "publish":
            store.publish(settings, run)
            state["report"] = str(export_report(settings, run["namespace"]))
        else:
            raise ValueError("Unknown phase")
    state.setdefault("timings", {})[stage] = time.perf_counter() - begin
    write_json(state_path, state)
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "load", "build", "validate", "publish"])
    args = parser.parse_args()
    home = Path(os.environ.get("FARO_HOME", ".")).resolve()
    load_env(home)
    settings = Settings.from_env()
    result = phase(
        settings,
        args.phase,
        os.environ["FARO_WORKFLOW_KEY"],
        Path(os.environ["FARO_INPUT_FILE"]) if os.environ.get("FARO_INPUT_FILE") else None,
        os.environ.get("FARO_DATA_KIND", "public_real_historical"),
        os.environ.get("FARO_INTERVAL_START") or None,
        os.environ.get("FARO_INTERVAL_END") or None,
    )
    print(json.dumps({"phase": args.phase, "run_id": result.get("run_id")}))


if __name__ == "__main__":
    main()
