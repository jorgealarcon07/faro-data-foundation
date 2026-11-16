"""Portable, offline consumer: two report views, exports, and source-level explanations."""

import csv
import html
import json
from pathlib import Path

from . import store
from .common import FaroError, Settings, utc_now, write_json


def export_report(settings: Settings, namespace: str, directory: Path | None = None) -> Path:
    directory = directory or settings.home / "reports/latest" / namespace
    directory.mkdir(parents=True, exist_ok=True)
    with store.connect(settings) as conn:
        head = conn.execute(
            "SELECT p.*, r.manifest FROM faro.publications p JOIN faro.runs r USING(run_id) "
            "WHERE p.namespace=%s",
            (namespace,),
        ).fetchone()
        if not head:
            raise FaroError("No valid publication for this namespace")
        activity = conn.execute(
            "SELECT * FROM faro.current_mart_activity WHERE source_namespace=%s "
            "ORDER BY business_date NULLS LAST,record_class",
            (namespace,),
        ).fetchall()
        quality = conn.execute(
            "SELECT * FROM faro.current_mart_quality WHERE source_namespace=%s "
            "ORDER BY business_date NULLS LAST",
            (namespace,),
        ).fetchall()
        reasons = conn.execute(
            "SELECT classification_reason,count(*) AS rows,sum(signed_amount) AS signed_amount "
            "FROM faro.current_fact_invoice_line WHERE source_namespace=%s GROUP BY 1 "
            "ORDER BY rows DESC",
            (namespace,),
        ).fetchall()
        examples = conn.execute(
            "SELECT source_row_id,sheet,row_number,invoice_id,product_key,"
            "business_date,quantity,unit_price,signed_amount,record_class,classification_reason "
            "FROM faro.current_fact_invoice_line WHERE source_namespace=%s "
            "AND record_class<>'sale' ORDER BY source_row_id LIMIT 50",
            (namespace,),
        ).fetchall()
        history = conn.execute(
            "SELECT r.run_id,r.state,coalesce(r.error_code,(SELECT payload->>'error' FROM faro.events e "
            "WHERE e.run_id=r.run_id AND stage='failed' ORDER BY e.id DESC LIMIT 1)) AS error_code, "
            "r.created_at FROM faro.runs r WHERE namespace=%s "
            "ORDER BY created_at DESC LIMIT 20",
            (namespace,),
        ).fetchall()
    payload = {
        "generated_at": utc_now(),
        "namespace": namespace,
        "publication_run_id": head["run_id"],
        "manifest": head["manifest"],
        "activity": activity,
        "quality": quality,
        "reasons": reasons,
        "examples": examples,
        "history": history,
    }
    write_json(directory / "report.json", payload)
    for name in ["activity", "quality", "reasons", "examples", "history"]:
        rows = payload[name]
        with (directory / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            if rows:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    encoded = json.dumps(payload, default=str, ensure_ascii=False).replace("<", "\\u003c")
    template = (settings.home / "src/faro_foundation/templates/report.html").read_text(
        encoding="utf-8"
    )
    rendered = template.replace("__PAYLOAD__", encoded).replace(
        "__NAMESPACE__", html.escape(namespace)
    )
    target = directory / "index.html"
    target.write_text(rendered, encoding="utf-8")
    return target
