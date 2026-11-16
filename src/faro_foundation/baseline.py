"""Independent Python/Decimal oracle, rereading the workbook rather than dbt outputs."""

import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from .common import FaroError, digest, write_json
from .source import datetime_or_none, decimal_or_none, workbook_rows


def classify(row: dict) -> tuple[str, str]:
    quantity = decimal_or_none(row["quantity_text"])
    price = decimal_or_none(row["price_text"])
    moment = datetime_or_none(row["event_text"])
    if (
        not row["invoice"]
        or not row["stock_code"]
        or moment is None
        or quantity is None
        or quantity != quantity.to_integral_value()
        or price is None
    ):
        return "quarantine", "invalid_field"
    if row["invoice"].upper().startswith("C") or quantity < 0:
        return "cancellation", "cancellation_or_correction"
    if re.fullmatch(r"[0-9]{5}[A-Za-z]?", row["stock_code"]) is None:
        return "adjustment", "non_merchandise_code"
    if quantity == 0:
        return "adjustment", "zero_quantity"
    if price <= 0:
        return "adjustment", "non_positive_price"
    return "sale", "eligible_sale"


def reference(metadata: dict, directory: Path) -> dict:
    target = directory / "baseline.json"
    oracle_sha = digest(Path(__file__)) + digest(Path(__file__).with_name("source.py"))
    if target.exists():
        saved = json.loads(target.read_text())
        if (
            saved["dataset_sha256"] == metadata["dataset_sha256"]
            and saved.get("oracle_sha") == oracle_sha
        ):
            return saved
    path = Path(metadata["source_path"])
    if digest(path) != metadata["dataset_sha256"]:
        raise FaroError("Source changed before baseline scan")
    groups = defaultdict(lambda: {"rows": 0, "amount": Decimal(0), "unknown_amount_rows": 0})
    reasons = defaultdict(int)
    count = unknown_customers = 0
    total = Decimal(0)
    for row in workbook_rows(path, metadata["dataset_sha256"]):
        kind, reason = classify(row)
        moment = datetime_or_none(row["event_text"])
        key = f"{moment.date() if moment else 'invalid'}|{kind}"
        group = groups[key]
        group["rows"] += 1
        reasons[reason] += 1
        quantity, price = decimal_or_none(row["quantity_text"]), decimal_or_none(row["price_text"])
        if quantity is None or price is None:
            group["unknown_amount_rows"] += 1
        else:
            group["amount"] += quantity * price
            total += quantity * price
        unknown_customers += int(not row["customer_text"])
        count += 1
    result = {
        "dataset_sha256": metadata["dataset_sha256"],
        "oracle_sha": oracle_sha,
        "rows": count,
        "known_signed_amount": str(total),
        "unknown_customer_rows": unknown_customers,
        "reasons": dict(reasons),
        "groups": dict(groups),
    }
    write_json(target, result)
    return json.loads(target.read_text())
