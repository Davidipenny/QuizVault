$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$runtime = Join-Path $root 'installer\vendor\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
$runtimeChecksum = "$runtime.sha256"
$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $candidate = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
    if (Test-Path -LiteralPath $candidate) { $iscc = $candidate }
}
if (-not (Test-Path -LiteralPath $python)) { throw 'Python environment is missing; run scripts/setup.ps1 first.' }
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Verified WebView2 offline installer is missing; run scripts/fetch-webview2.ps1 with the pinned SHA256.' }
if (-not (Test-Path -LiteralPath $runtimeChecksum)) { throw 'WebView2 checksum record is missing; fetch the installer again.' }
$expectedHash = (Get-Content -Raw -LiteralPath $runtimeChecksum).Trim().ToUpperInvariant()
$actualHash = (Get-FileHash -LiteralPath $runtime -Algorithm SHA256).Hash
if ($actualHash -ne $expectedHash) { throw "WebView2 checksum mismatch. Expected $expectedHash, got $actualHash" }
Push-Location $root
try {
    & $python -m PyInstaller --noconfirm desktop.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    if (-not $iscc) { throw 'Inno Setup 6 compiler was not found.' }
    & $iscc (Join-Path $root 'installer\QuizVault.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
} finally {
    Pop-Location
}
