"""Copy only reviewable, non-secret outputs; never package raw data, venv or PostgreSQL files."""

import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
acceptance = json.loads((root / "reports/acceptance.json").read_text())
for namespace in ["retail_uk_reference", "retail_synthetic"]:
    original = root / "reports/latest" / namespace
    target = root / "reports/published" / namespace
    target.mkdir(parents=True, exist_ok=True)
    for path in original.iterdir():
        if path.suffix in {".html", ".json", ".csv"}:
            shutil.copyfile(path, target / path.name)
run_ids = [r["run_id"] for r in acceptance.get("real_runs", [])] + [
    acceptance["demo"][k] for k in ["first_run", "resumed_run", "backfill_run"]
]
for run_id in dict.fromkeys(run_ids):
    source = root / "reports/runs" / run_id
    target = root / "reports/evidence" / run_id
    target.mkdir(parents=True, exist_ok=True)
    for name in ["manifest.json", "events.jsonl"]:
        shutil.copyfile(source / name, target / name)
    shutil.copyfile(source / "dbt_target/run_results.json", target / "dbt-run-results.json")
result = {
    "id": "faro-data-foundation",
    "title": "Cierre de datos verificable",
    "status": "implemented-core-verified",
    "business_context": "Faro is fictitious; historical reference and synthetic incidents.",
    "stack": [
        "Python",
        "SQL",
        "PostgreSQL",
        "dbt",
        "Airflow adapter",
        "Docker configuration",
        "Power BI editable project",
    ],
    "verified_rows": acceptance["real_runs"][0]["rows"],
    "data_sha256": acceptance["real_runs"][0]["data_sha256"],
    "source_license": "CC-BY-4.0 / Chen, UCI / DOI 10.24432/C5CG6D",
    "measurements": [
        {"label": r["benchmark_label"], "seconds": r["measured_wall_seconds"]}
        for r in acceptance["real_runs"]
    ],
    "business_impact_observed": None,
    "limits": [
        "historical UK data",
        "no observed business savings",
        "Docker/Airflow runtime not verified on this host",
        "Power BI Desktop refresh not verified",
        "AWS/Spark optional and not implemented",
    ],
}
(root / "assets/web/case-study.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("Published reports, six run evidences, and structured web case saved")
