param([string]$Python = "python", [switch]$Integration)
$ErrorActionPreference = "Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    & $Python -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "Lint failed" }
    & $Python scripts/check_contracts.py
    if ($LASTEXITCODE -ne 0) { throw "Contracts failed" }
    if ($Integration) { & $Python -m pytest -m "not airflow" --junitxml=reports/tests.xml }
    else { & $Python -m pytest -m "not integration and not airflow" }
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
} finally { Pop-Location }
