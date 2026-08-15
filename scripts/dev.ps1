$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw '请先运行 scripts/setup.ps1' }
Start-Process -FilePath $python -ArgumentList '-m','uvicorn','app.main:app','--reload','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $root 'server') -WindowStyle Hidden
Set-Location (Join-Path $root 'web')
pnpm dev

