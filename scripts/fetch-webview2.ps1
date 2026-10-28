param(
    [Parameter(Mandatory = $true)][string]$ExpectedSha256,
    # 离线安装包来源：http(s)/file:// URL 或本地文件路径。
    # 微软没有常青（evergreen）的离线包直链——2124703 只是约 2MB 的联网 bootstrapper，
    # 且直链哈希随版本变化。先获取固定版本的离线安装包再固定其哈希，例如：
    #   winget download --id Microsoft.EdgeWebView2Runtime -e --architecture x64
    [Parameter(Mandatory = $true)][string]$Source
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vendor = Join-Path $root 'installer\vendor'
$destination = Join-Path $vendor 'MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
$checksum = "$destination.sha256"
$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ("QuizVault-WebView2-{0}.exe" -f [guid]::NewGuid())
New-Item -ItemType Directory -Path $vendor -Force | Out-Null
try {
    if (Test-Path -LiteralPath $Source) {
        Copy-Item -LiteralPath $Source -Destination $temporary -Force
    } else {
        Invoke-WebRequest -Uri $Source -OutFile $temporary -UseBasicParsing
    }
    $actual = (Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash
    if ($actual -ne $ExpectedSha256.ToUpperInvariant()) {
        throw "WebView2 SHA256 mismatch. Expected $ExpectedSha256, got $actual"
    }
    if ((Get-Item -LiteralPath $temporary).Length -lt 100MB) {
        throw 'Downloaded file is too small to be the offline installer (likely the ~2MB online bootstrapper).'
    }
    Move-Item -LiteralPath $temporary -Destination $destination -Force
    Set-Content -LiteralPath $checksum -Value $actual -Encoding ascii -NoNewline
    Write-Output "WebView2 offline installer verified: $actual"
} finally {
    Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
}
