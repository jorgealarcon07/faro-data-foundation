from datetime import datetime
from decimal import Decimal

import openpyxl
import pytest

from faro_foundation.baseline import classify
from faro_foundation.common import FaroError, digest
from faro_foundation.source import (
    HEADERS,
    datetime_or_none,
    decimal_or_none,
    fixture,
    workbook_rows,
)


def row(**updates):
    data = {
        "invoice": "123456",
        "stock_code": "12345A",
        "quantity_text": "2",
        "price_text": "2.95",
        "event_text": "2011-01-01T10:00:00",
    }
    return {**data, **updates}


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, "sale"),
        ({"invoice": "C123456"}, "cancellation"),
        ({"quantity_text": "-2"}, "cancellation"),
        ({"stock_code": "POST"}, "adjustment"),
        ({"price_text": "0"}, "adjustment"),
        ({"price_text": "-4"}, "adjustment"),
        ({"quantity_text": "0"}, "adjustment"),
        ({"quantity_text": "1.5"}, "quarantine"),
        ({"quantity_text": "bad"}, "quarantine"),
        ({"event_text": "wrong"}, "quarantine"),
        ({"price_text": None}, "quarantine"),
        ({"invoice": None}, "quarantine"),
    ],
)
def test_domain_edge_cases(changes, expected):
    assert classify(row(**changes))[0] == expected


def test_decimal_and_timezone():
    assert decimal_or_none("2.95") * 3 == Decimal("8.85")
    assert decimal_or_none("NaN") is None
    assert decimal_or_none("Infinity") is None
    assert datetime_or_none("2011-01-01T10:00:00+00:00") is None
    assert datetime_or_none("2011-01-01T10:00:00") == datetime(2011, 1, 1, 10)


def test_content_duplicates_preserve_identity(tmp_path):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(HEADERS)
    values = ["123", "12345", "same", 1, datetime(2011, 1, 1), 2.5, None, "UK"]
    sheet.append(values)
    sheet.append(values)
    path = tmp_path / "same.xlsx"
    book.save(path)
    records = list(workbook_rows(path, digest(path)))
    assert len(records) == 2
    assert records[0]["source_row_id"] != records[1]["source_row_id"]
    assert records[0]["invoice"] == records[1]["invoice"]


def test_incompatible_header_is_blocked(tmp_path):
    book = openpyxl.Workbook()
    book.active.append(["unexpected"])
    path = tmp_path / "wrong.xlsx"
    book.save(path)
    with pytest.raises(FaroError, match="Incompatible header"):
        list(workbook_rows(path, digest(path)))


def test_fixture_has_repeatable_row_ids(tmp_path):
    a = fixture(tmp_path, rows=120)
    first_hash = digest(a)
    first = [(r["invoice"], r["quantity_text"]) for r in workbook_rows(a, digest(a))]
    b = fixture(tmp_path, rows=120)
    second = [(r["invoice"], r["quantity_text"]) for r in workbook_rows(b, digest(b))]
    assert first == second
    assert first_hash == digest(b)


def test_oracle_preserves_admitted_high_precision(tmp_path):
    from decimal import Context

    from faro_foundation.baseline import reference

    book = openpyxl.Workbook()
    book.active.append(HEADERS)
    quantity = "999999999999999"
    price = "123456789012.123456789012"
    book.active.append(
        ["123", "12345", "High precision", quantity, datetime(2011, 1, 1), price, "1", "UK"]
    )
    path = tmp_path / "precision.xlsx"
    book.save(path)
    result = reference({"source_path": str(path), "dataset_sha256": digest(path)}, tmp_path)
    expected = Context(prec=80).multiply(Decimal(quantity), Decimal(price))
    assert Decimal(result["known_signed_amount"]) == expected
