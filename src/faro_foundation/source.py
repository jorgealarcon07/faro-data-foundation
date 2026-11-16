"""Verified downloads, repeatable synthetic workbook, and a streaming XLSX adapter."""

import hashlib
import json
import random
import re
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

from .common import FaroError, digest, write_json

HEADERS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]
RAW_SCHEMA = pa.schema(
    [
        (k, pa.string())
        for k in [
            "source_row_id",
            "sheet",
            "row_number",
            "invoice",
            "stock_code",
            "description",
            "quantity_text",
            "event_text",
            "price_text",
            "customer_text",
            "country",
        ]
    ]
)


def download(home: Path) -> Path:
    config = json.loads((home / "config/source.json").read_text())
    directory = home / "data/downloads"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "online-retail-ii.zip"
    if target.exists() and digest(target) == config["sha256"]:
        return extract_verified(target, config)
    partial = target.with_suffix(".partial")
    for attempt in range(3):
        try:
            request = urllib.request.Request(config["url"], headers={"User-Agent": "Faro/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as out:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > 80 * 1024 * 1024:
                        raise FaroError("Source exceeds the approved 80 MB download limit")
                    out.write(chunk)
            if digest(partial) != config["sha256"]:
                raise FaroError("Source checksum changed: review and approve a new dataset version")
            partial.replace(target)
            return extract_verified(target, config)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise FaroError(
                    "Download unavailable; use a verified cached ZIP or synthetic demo"
                ) from None
            time.sleep(2**attempt)
    raise FaroError("Download did not finish")


def extract_verified(path: Path, config: dict) -> Path:
    if digest(path) != config["sha256"]:
        raise FaroError("ZIP checksum mismatch")
    target = path.parent / config["member"]
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo(config["member"])
        if info.file_size > 80 * 1024 * 1024 or Path(info.filename).name != info.filename:
            raise FaroError("Unsafe archive member")
        with archive.open(info) as source, target.open("wb") as out:
            while chunk := source.read(1024 * 1024):
                out.write(chunk)
    return target


def fixture(home: Path, rows: int = 10000, seed: int = 2026) -> Path:
    if rows < 20:
        raise FaroError("Fixture must contain at least 20 rows")
    directory = home / "data/fixtures"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "synthetic.xlsx"
    rng = random.Random(seed)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "synthetic"
    sheet.append(HEADERS)
    for i in range(rows):
        day = datetime(2011, 1, 1) + timedelta(days=i % 10, hours=i % 8)
        row = [
            str(100000 + i // 3),
            f"{10000 + i % 40}",
            f"Synthetic item {i % 40}",
            rng.randint(1, 8),
            day,
            rng.choice([1.25, 2.50, 9.99]),
            str(10000 + i % 200),
            "United Kingdom",
        ]
        if i % 37 == 0:
            row[0], row[3] = "C" + row[0], -row[3]
        elif i % 41 == 0:
            row[1] = "POST"
        elif i % 43 == 0:
            row[5] = 0
        elif i % 47 == 0:
            row[3] = "invalid"
        elif i % 53 == 0:
            row[4] = "not-a-date"
        if i % 17 == 0:
            row[6] = None
        sheet.append(row)
    workbook.save(path)
    # XLSX ZIP timestamps are normalized so regeneration has a stable source hash.
    with zipfile.ZipFile(path) as archive:
        members = [(x.filename, archive.read(x.filename)) for x in archive.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members:
            if name == "docProps/core.xml":
                content = re.sub(
                    rb"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", b"2026-01-01T00:00:00Z", content
                )
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    write_json(
        directory / "synthetic.source.json",
        {
            "seed": seed,
            "rows": rows,
            "data_kind": "synthetic",
            "license": "CC0-1.0",
            "sha256": digest(path),
        },
    )
    return path


def text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value).strip()


def workbook_rows(path: Path, source_sha: str):
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in book:
            rows = sheet.iter_rows(values_only=True)
            if list(next(rows, [])) != HEADERS:
                raise FaroError(f"Incompatible header in sheet {sheet.title!r}")
            for number, values in enumerate(rows, 2):
                if len(values) != 8:
                    raise FaroError("Expected exactly eight columns")
                row_id = hashlib.sha256(f"{source_sha}:{sheet.title}:{number}".encode()).hexdigest()
                yield dict(
                    zip(
                        RAW_SCHEMA.names,
                        [row_id, sheet.title, str(number), *[text(v) for v in values]],
                        strict=True,
                    )
                )
    finally:
        book.close()


def decimal_or_none(value: str | None) -> Decimal | None:
    try:
        number = Decimal(value) if value is not None else None
        if number is None or not number.is_finite() or abs(number) > Decimal("1e15"):
            return None
        if max(0, -number.as_tuple().exponent) > 12:
            return None
        return number
    except (InvalidOperation, ValueError):
        return None


def datetime_or_none(value: str | None) -> datetime | None:
    try:
        result = datetime.fromisoformat(value or "")
        if result.tzinfo is not None or result.year < 1900:
            return None
        return result
    except ValueError:
        return None


def prepare(home: Path, path: Path, kind: str, batch_size: int) -> dict:
    source_sha = digest(path)
    namespace = "retail_uk_reference" if kind == "public_real_historical" else "retail_synthetic"
    if kind == "public_real_historical":
        config = json.loads((home / "config/source.json").read_text())
        # The independently verified workbook hash is pinned, not caller-supplied.
        if source_sha != config.get("workbook_sha256"):
            raise FaroError(
                "Real workbook checksum is not approved; run download or review source.json"
            )
    else:
        attribution = path.with_suffix(".source.json")
        if not attribution.exists():
            raise FaroError("Synthetic input requires its .source.json provenance sidecar")
        provenance = json.loads(attribution.read_text())
        if provenance.get("sha256") != source_sha or provenance.get("data_kind") != "synthetic":
            raise FaroError("Synthetic provenance checksum mismatch")
    directory = home / "data/prepared" / source_sha
    directory.mkdir(parents=True, exist_ok=True)
    metadata_path = directory / "source.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        if digest(directory / "raw.parquet") == metadata["parquet_sha256"]:
            return metadata
    target = directory / "raw.parquet"
    count = 0
    batch = []
    with pq.ParquetWriter(target.with_suffix(".partial"), RAW_SCHEMA, compression="zstd") as writer:
        for row in workbook_rows(path, source_sha):
            batch.append(row)
            count += 1
            if len(batch) >= batch_size:
                writer.write_table(pa.Table.from_pylist(batch, schema=RAW_SCHEMA))
                batch.clear()
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=RAW_SCHEMA))
    target.with_suffix(".partial").replace(target)
    if kind == "public_real_historical" and count != config["expected_rows"]:
        raise FaroError("Real source row count differs from approved version")
    metadata = {
        "dataset_sha256": source_sha,
        "parquet_sha256": digest(target),
        "source_namespace": namespace,
        "data_kind": kind,
        "rows": count,
        "source_path": str(path.resolve()),
        "parquet_path": str(target.resolve()),
        "seed": provenance["seed"] if kind == "synthetic" else None,
    }
    write_json(metadata_path, metadata)
    return metadata


def in_interval(value: datetime | None, start: str | None, end: str | None) -> bool:
    if start is None:
        return True
    return value is not None and date.fromisoformat(start) <= value.date() < date.fromisoformat(end)
