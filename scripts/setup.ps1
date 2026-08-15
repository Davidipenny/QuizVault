$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
python -m venv (Join-Path $root '.venv')
& (Join-Path $root '.venv\Scripts\python.exe') -m pip install -r (Join-Path $root 'server\requirements.txt')
Set-Location (Join-Path $root 'web')
pnpm install

