$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $root 'dist\QuizVault-Setup.exe'
$target = Join-Path ([System.IO.Path]::GetTempPath()) ("QuizVault-install-test-{0}" -f [guid]::NewGuid())
$dataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("QuizVault-install-data-{0}" -f [guid]::NewGuid())
$previousDataDir = $env:QUIZVAULT_DATA_DIR
$previousExpectation = $env:QUIZVAULT_SMOKE_EXPECT_EXISTING
if (-not (Test-Path -LiteralPath $installer)) { throw 'QuizVault-Setup.exe does not exist.' }
try {
    $install = Start-Process -FilePath $installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',("/DIR=$target") -Wait -PassThru -WindowStyle Hidden
    if ($install.ExitCode -ne 0) { throw "Installer failed with exit code $($install.ExitCode)." }
    $executable = Join-Path $target 'QuizVault.exe'
    $env:QUIZVAULT_DATA_DIR = $dataDir
    foreach ($run in 1..2) {
        if ($run -eq 2) { $env:QUIZVAULT_SMOKE_EXPECT_EXISTING = '1' }
        $smoke = Start-Process -FilePath $executable -ArgumentList '--smoke-test' -Wait -PassThru -WindowStyle Hidden
        if ($smoke.ExitCode -ne 0) { throw "Smoke run $run failed with exit code $($smoke.ExitCode)." }
    }
    $uninstaller = Join-Path $target 'unins000.exe'
    $uninstall = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait -PassThru -WindowStyle Hidden
    if ($uninstall.ExitCode -ne 0) { throw "Uninstall failed with exit code $($uninstall.ExitCode)." }
    Write-Output 'Install, two offline smoke starts, and uninstall passed.'
} finally {
    $env:QUIZVAULT_DATA_DIR = $previousDataDir
    $env:QUIZVAULT_SMOKE_EXPECT_EXISTING = $previousExpectation
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $dataDir) {
        Remove-Item -LiteralPath $dataDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
