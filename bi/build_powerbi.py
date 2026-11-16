"""Generate editable PBIP/PBIR and a tabular import model. No Desktop automation or fabricated PBIX."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def field(table, name, measure=False):
    return {
        "field": {
            "Measure" if measure else "Column": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": name,
            }
        },
        "queryRef": table + "." + name,
        "nativeQueryRef": name,
    }


def visual(page, name, kind, x, y, w, h, roles):
    save(
        ROOT / "Faro.Report/definition/pages" / page / "visuals" / name / "visual.json",
        {
            "$schema": BASE + "visualContainer/2.0.0/schema.json",
            "name": name,
            "position": {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0},
            "visual": {
                "visualType": kind,
                "query": {
                    "queryState": {
                        role: {"projections": projections} for role, projections in roles.items()
                    }
                },
                "drillFilterOtherVisuals": True,
            },
        },
    )


def build(data_directory):
    save(
        ROOT / "Faro.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": "Faro.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    save(
        ROOT / "Faro.Report/definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": "../Faro.SemanticModel"}},
        },
    )
    save(ROOT / "Faro.SemanticModel/definition.pbism", {"version": "1.0", "settings": {}})
    definition = ROOT / "Faro.Report/definition"
    save(
        definition / "version.json",
        {"$schema": BASE + "versionMetadata/1.0.0/schema.json", "version": "4.0.0"},
    )
    save(
        definition / "report.json",
        {"$schema": BASE + "report/3.0.0/schema.json", "themeCollection": {}},
    )
    save(
        definition / "pages/pages.json",
        {
            "$schema": BASE + "pagesMetadata/1.0.0/schema.json",
            "pageOrder": ["Activity", "Quality"],
            "activePageName": "Activity",
        },
    )
    for name, title in [
        ("Activity", "Actividad comercial · GBP"),
        ("Quality", "Calidad y publicación"),
    ]:
        save(
            definition / "pages" / name / "page.json",
            {
                "$schema": BASE + "page/2.0.0/schema.json",
                "name": name,
                "displayName": title,
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
            },
        )
    visual(
        "Activity", "rows", "card", 30, 20, 350, 130, {"Values": [field("Activity", "Filas", True)]}
    )
    visual(
        "Activity",
        "sales",
        "card",
        420,
        20,
        350,
        130,
        {"Values": [field("Activity", "Ventas elegibles GBP", True)]},
    )
    visual(
        "Activity",
        "trend",
        "clusteredColumnChart",
        30,
        180,
        740,
        480,
        {
            "Category": [field("Activity", "business_date")],
            "Y": [field("Activity", "Ventas elegibles GBP", True)],
        },
    )
    visual(
        "Activity",
        "classes",
        "tableEx",
        800,
        180,
        440,
        480,
        {
            "Values": [
                field("Activity", "record_class"),
                field("Activity", "Filas", True),
                field("Activity", "Importe firmado GBP", True),
            ]
        },
    )
    visual(
        "Quality",
        "unknown",
        "card",
        30,
        20,
        350,
        130,
        {"Values": [field("Quality", "Filas sin cliente", True)]},
    )
    visual(
        "Quality",
        "quarantine",
        "card",
        420,
        20,
        350,
        130,
        {"Values": [field("Quality", "Filas en cuarentena", True)]},
    )
    visual(
        "Quality",
        "quality_dates",
        "tableEx",
        30,
        180,
        1210,
        480,
        {
            "Values": [
                field("Quality", "business_date"),
                field("Quality", "publication_status"),
                field("Quality", "Filas sin cliente", True),
                field("Quality", "Filas en cuarentena", True),
            ]
        },
    )
    tables = []
    specs = {
        "Activity": (
            "activity.csv",
            {
                "source_namespace": "string",
                "data_kind": "string",
                "currency": "string",
                "business_date": "dateTime",
                "record_class": "string",
                "row_count": "int64",
                "signed_amount": "double",
                "unknown_amount_rows": "int64",
                "publication_run_id": "string",
            },
            [
                ("Filas", "SUM(Activity[row_count])", "#,0"),
                ("Importe firmado GBP", "SUM(Activity[signed_amount])", "£#,0.00"),
                (
                    "Ventas elegibles GBP",
                    'CALCULATE(SUM(Activity[signed_amount]), Activity[record_class] = "sale")',
                    "£#,0.00",
                ),
            ],
        ),
        "Quality": (
            "quality.csv",
            {
                "source_namespace": "string",
                "data_kind": "string",
                "currency": "string",
                "business_date": "dateTime",
                "input_rows": "int64",
                "unknown_customer_rows": "int64",
                "quarantine_rows": "int64",
                "adjustment_rows": "int64",
                "unknown_amount_rows": "int64",
                "quarantined_known_amount": "double",
                "publication_status": "string",
                "publication_run_id": "string",
            },
            [
                ("Filas sin cliente", "SUM(Quality[unknown_customer_rows])", "#,0"),
                ("Filas en cuarentena", "SUM(Quality[quarantine_rows])", "#,0"),
                (
                    "Porcentaje sin cliente",
                    "DIVIDE([Filas sin cliente], SUM(Quality[input_rows]))",
                    "0.00%",
                ),
            ],
        ),
    }
    for name, (filename, columns, measures) in specs.items():
        types = {
            "string": "type text",
            "dateTime": "type date",
            "int64": "Int64.Type",
            "double": "type number",
        }
        conversions = ", ".join(
            '{"' + col + '", ' + types[typ] + "}" for col, typ in columns.items()
        )
        expression = [
            "let",
            f'  Raw = Csv.Document(File.Contents(DataDirectory & "/{filename}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
            "  Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),",
            '  Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),',
            f'  Typed = Table.TransformColumnTypes(Nulls, {{{conversions}}}, "en-US")',
            "in Typed",
        ]
        tables.append(
            {
                "name": name,
                "columns": [
                    {"name": c, "dataType": t, "sourceColumn": c, "summarizeBy": "none"}
                    for c, t in columns.items()
                ],
                "partitions": [
                    {
                        "name": name,
                        "mode": "import",
                        "source": {"type": "m", "expression": expression},
                    }
                ],
                "measures": [
                    {"name": n, "expression": e, "formatString": fmt} for n, e, fmt in measures
                ],
            }
        )
    save(
        ROOT / "Faro.SemanticModel/model.bim",
        {
            "name": "Faro",
            "compatibilityLevel": 1600,
            "model": {
                "culture": "en-US",
                "defaultPowerBIDataSourceVersion": "powerBI_V3",
                "expressions": [
                    {
                        "name": "DataDirectory",
                        "kind": "m",
                        "expression": json.dumps(str(data_directory).replace("\\", "/"))
                        + ' meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
                    }
                ],
                "tables": tables,
            },
        },
    )
    print(
        "Generated PBIP: 2 pages, 7 visuals, 6 DAX measures. Desktop runtime validation remains separate."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", type=Path, default=ROOT.parent / "reports/latest/retail_uk_reference"
    )
    build(parser.parse_args().data_dir.resolve())
