# Backend launcher compatible with Windows PowerShell 5 and PowerShell 7.
# Usage: powershell -ExecutionPolicy Bypass -File .\start_backend.ps1

param([int]$Port = 18000)
$ErrorActionPreference = "Stop"

$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing .env. Copy .env.example to .env and fill in the required settings."
}

Get-Content -LiteralPath $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2 -and $parts[0]) {
            $name = $parts[0].Trim()
            $value = $parts[1].Trim().Trim('"').Trim("'")
            Set-Item -Path ("Env:" + $name) -Value $value
        }
    }
}

foreach ($requiredName in @("POSTGRES_PASSWORD", "LLM_API_KEY", "TOKEN_JWT_SECURITY_KEY", "ADMIN_PASSWORD")) {
    $requiredValue = Get-Item -Path ("Env:" + $requiredName) -ErrorAction SilentlyContinue
    if (-not $requiredValue -or -not $requiredValue.Value) {
        throw ("Missing required .env setting: " + $requiredName)
    }
}

$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:FILES_URL_BASE = "http://localhost:$Port/api/v1"
if (-not $env:POSTGRES_SERVER) { $env:POSTGRES_SERVER = "127.0.0.1" }
if (-not $env:POSTGRES_PORT) { $env:POSTGRES_PORT = "25432" }
if (-not $env:POSTGRES_DB) { $env:POSTGRES_DB = "streamer_sales_db" }

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Scenic AI Guide - Backend" -ForegroundColor Cyan
Write-Host "  http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan

uvicorn server.base.base_server:app --host 0.0.0.0 --port $Port
