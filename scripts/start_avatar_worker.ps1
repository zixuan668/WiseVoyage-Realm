param([string]$SourceVideo)
$ErrorActionPreference = 'Stop'
$project = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$python = Join-Path $project '.venv-musetalk/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'MuseTalk environment not installed' }
if ($SourceVideo) { $env:DIGITAL_HUMAN_SOURCE = (Resolve-Path -LiteralPath $SourceVideo).Path }
$env:PYTHONIOENCODING = 'utf-8'
Push-Location $project
try { & $python -m uvicorn server.digital_human.digital_human_server:app --host 127.0.0.1 --port 8002 }
finally { Pop-Location }
