param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    & $Python -m faro_foundation.cli demo
    if ($LASTEXITCODE -ne 0) { throw "Demo failed; inspect reports/runs" }
} finally { Pop-Location }
