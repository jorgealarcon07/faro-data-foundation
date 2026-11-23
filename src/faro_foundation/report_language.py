"""Localized labels for the offline report."""

import json
import re
from html import escape

COPY = {
    "text_title": ("Faro · Cierre verificable", "Faro · Verifiable sales close"),
    "text_heading": ("Cierre de datos verificable", "Verifiable sales close"),
    "text_tagline": (
        "Una cifra publicada. Un origen explicable.",
        "Trace every published figure to its source.",
    ),
    "text_activity": ("Actividad comercial", "Sales activity"),
    "text_quality": ("Calidad y publicación", "Data quality and publication"),
    "text_rows": ("Filas conservadas por clasificación", "Rows retained by classification"),
    "text_amount": (
        "El importe firmado conserva cancelaciones y ajustes. No representa caja, "
        "ingresos reconocidos ni cartera.",
        "Signed amounts include cancellations and adjustments. Cash, recognized revenue "
        "and receivables are outside this measure.",
    ),
    "text_release": ("Decisión de publicación", "Publication decision"),
    "text_checks": (
        "Controles: conteos, importes Decimal, unicidad y baseline independiente.",
        "Checks cover counts, exact decimal amounts, uniqueness and an independent baseline.",
    ),
    "text_manifest": ("Manifiesto y datos JSON", "Download manifest and data JSON"),
    "text_activity_csv": ("Descargar actividad CSV", "Download activity CSV"),
    "text_by_date": ("Actividad por fecha de negocio", "Activity by business date"),
    "text_class": ("Clasificación", "Classification"),
    "text_all": ("Todas", "All"),
    "text_reasons": ("Razones de clasificación", "Classification reasons"),
    "text_history": ("Historial y recuperación", "Run history and recovery"),
    "text_recovery": (
        "Un fallo del candidato conserva la publicación anterior.",
        "If a candidate fails, the previous publication stays available.",
    ),
    "text_quality_csv": ("Descargar calidad CSV", "Download quality CSV"),
    "text_examples": (
        "Trazabilidad de excepciones · muestra máxima de 50 filas",
        "Trace exceptions · sample of up to 50 rows",
    ),
    "text_source": (
        "Cada fila conserva hoja y número de origen. Consulta completa con",
        "Each row retains its source sheet and row number. Inspect the full record with",
    ),
    "text_footer": (
        "Proyecto de portafolio · __NAMESPACE__ · datos y permisos en DATA_SOURCES.md. "
        "Reporte autónomo: sin red, cookies ni telemetría.",
        "Portfolio project · __NAMESPACE__ · see DATA_SOURCES.md for data and "
        "permissions. The report works offline and uses no cookies or telemetry.",
    ),
    "js_locale": ("es-CO", "en-US"),
    "js_sale": ("Venta elegible", "Eligible sale"),
    "js_cancellation": ("Cancelación / corrección", "Cancellation / correction"),
    "js_adjustment": ("Ajuste / no comercial", "Adjustment / non-sales"),
    "js_quarantine": ("Cuarentena", "Quarantine"),
    "js_no_date": ("Sin fecha", "No date"),
    "js_unknown": ("No calculable", "Unavailable"),
    "js_synthetic": ("DEMOSTRACIÓN SINTÉTICA", "SYNTHETIC DEMO"),
    "js_historical": ("FUENTE PÚBLICA HISTÓRICA · UCI", "HISTORICAL PUBLIC DATA · UCI"),
    "js_synthetic_notice": (
        "Escenario sintético. Las incidencias de esta demo son inyectadas; no "
        "son resultados de una empresa real.",
        "Synthetic scenario. The demo uses deliberately introduced incidents.",
    ),
    "js_historical_notice": (
        "Referencia histórica británica 2009–2011, CC BY 4.0. No representa "
        "clientes actuales en Colombia. Los datos incompletos se conservan y "
        "señalan.",
        "Historical UK data from 2009–2011, CC BY 4.0. The pipeline retains "
        "and flags incomplete records.",
    ),
    "js_rows_kept": ("Filas conservadas", "Rows retained"),
    "js_no_dedup": ("Sin deduplicación por contenido", "Identical source rows retained"),
    "js_sales": ("Venta elegible · GBP", "Eligible sales · GBP"),
    "js_round": ("Redondeo solo en presentación", "Rounded for display"),
    "js_missing_customer": ("Filas sin cliente", "Rows without a customer ID"),
    "js_row_counts": ("Filas; no clientes únicos", "Count of rows"),
    "js_no_loss": ("No se descarta silenciosamente", "Rows retained for review"),
    "js_date": ("Fecha local", "Local date"),
    "js_class": ("Clase", "Class"),
    "js_rows": ("Filas", "Rows"),
    "js_signed": ("Importe firmado GBP", "Signed amount (GBP)"),
    "js_missing_amount": ("Importe no calculable", "Rows with unknown amounts"),
    "js_reason": ("Razón", "Reason"),
    "js_known": ("Importe conocido GBP", "Known amount (GBP)"),
    "js_run": ("Ejecución", "Run"),
    "js_status": ("Estado", "Status"),
    "js_cause": ("Motivo", "Reason"),
    "js_source_id": ("ID origen", "Source ID"),
    "js_sheet": ("Hoja", "Sheet"),
    "js_row": ("Fila", "Row"),
    "js_invoice": ("Factura", "Invoice"),
    "js_gbp": ("Importe GBP", "Amount (GBP)"),
    "js_publication": ("Publicación", "Publication"),
    "js_generated": ("generado", "generated"),
    "js_groups": ("grupos reconciliados", "reconciled groups"),
    "js_passed": ("tests dbt correctos.", "dbt tests passed."),
    "js_eligible_sale": ("Venta elegible", "Eligible sale"),
    "js_cancellation_or_correction": ("Cancelación o corrección", "Cancellation or correction"),
    "js_non_merchandise_code": ("Código ajeno a mercancía", "Non-merchandise code"),
    "js_non_positive_price": ("Precio no positivo", "Nonpositive price"),
    "js_invalid_field": ("Campo inválido", "Invalid field"),
    "js_missing_invoice": ("Factura ausente", "Missing invoice"),
    "js_missing_date": ("Fecha ausente", "Missing date"),
    "js_published": ("Publicado", "Published"),
    "js_failed": ("Fallido", "Failed"),
    "js_validated": ("Validado", "Validated"),
    "js_loading": ("Cargando", "Loading"),
    "js_loaded": ("Cargado", "Loaded"),
    "js_provisional": ("Provisional", "Provisional"),
}


REPORT_FILES = {"es": "index.html", "en": "index.en.html"}


def labels(language):
    if language not in REPORT_FILES:
        raise ValueError(f"Unsupported report language: {language}")
    column = 0 if language == "es" else 1
    return {key: pair[column] for key, pair in COPY.items()}


def localize(template, language):
    copy = labels(language)
    alternate = "en" if language == "es" else "es"
    html = {
        **{key: escape(value) for key, value in copy.items()},
        "lang": language,
        "other_lang": alternate,
        "other_file": REPORT_FILES[alternate],
        "other_label": "English" if alternate == "en" else "Español",
    }
    js_copy = {key: value for key, value in copy.items() if key.startswith("js_")}
    html["js_copy"] = json.dumps(js_copy, ensure_ascii=False).replace("<", r"\u003c")

    return re.sub(r"@@([a-z_]+)@@", lambda match: html[match[1]], template)
