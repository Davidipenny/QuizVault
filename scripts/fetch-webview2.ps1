param(
    [Parameter(Mandatory = $true)][string]$ExpectedSha256,
    [string]$Url = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vendor = Join-Path $root 'installer\vendor'
$destination = Join-Path $vendor 'MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
$checksum = "$destination.sha256"
$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ("QuizVault-WebView2-{0}.exe" -f [guid]::NewGuid())
New-Item -ItemType Directory -Path $vendor -Force | Out-Null
try {
    Invoke-WebRequest -Uri $Url -OutFile $temporary -UseBasicParsing
    $actual = (Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash
    if ($actual -ne $ExpectedSha256.ToUpperInvariant()) {
        throw "WebView2 SHA256 mismatch. Expected $ExpectedSha256, got $actual"
    }
    Move-Item -LiteralPath $temporary -Destination $destination -Force
    Set-Content -LiteralPath $checksum -Value $actual -Encoding ascii -NoNewline
    Write-Output "WebView2 offline installer verified: $actual"
} finally {
    Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
}
