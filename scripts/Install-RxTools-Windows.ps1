# Install SatDump (+ optional rtl-sdr CLI tools) for SkyCache live FTA RX on Windows.
# Legal: receive-only open weather / open amateur. Not commercial broadband.
#
#   powershell -ExecutionPolicy Bypass -File scripts\Install-RxTools-Windows.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Install-RxTools-Windows.ps1 -SkipRtlSdr

param(
    [switch]$SkipRtlSdr,
    [switch]$SkipSatDump
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root "tools\rx-windows"
New-Item -ItemType Directory -Force -Path $Tools | Out-Null

function Add-UserPathOnce([string]$Dir) {
    if (-not (Test-Path $Dir)) { return }
    $cur = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $cur) { $cur = "" }
    $parts = @($cur -split ";" | Where-Object { $_ -and $_.Trim() })
    if ($parts -contains $Dir) {
        Write-Host "PATH already has $Dir"
        return
    }
    $new = ($parts + $Dir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $new, "User")
    $env:Path = "$Dir;" + $env:Path
    Write-Host "Added to User PATH: $Dir"
}

if (-not $SkipSatDump) {
    Write-Host "[1/3] winget install SatDump.SatDump"
    winget install --id SatDump.SatDump -e --accept-package-agreements --accept-source-agreements
    # Common install locations (SatDump 1.2.x uses Program Files\SatDump\bin)
    $candidates = @(
        (Join-Path ${env:ProgramFiles} "SatDump\bin"),
        (Join-Path ${env:ProgramFiles} "SatDump"),
        (Join-Path ${env:ProgramFiles(x86)} "SatDump\bin"),
        (Join-Path ${env:ProgramFiles(x86)} "SatDump"),
        (Join-Path $env:LOCALAPPDATA "Programs\SatDump\bin"),
        (Join-Path $env:LOCALAPPDATA "Programs\SatDump"),
        "C:\SatDump\bin",
        "C:\SatDump"
    )
    $found = $null
    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c "satdump.exe")) { $found = $c; break }
    }
    if (-not $found) {
        $hit = Get-ChildItem -Path ${env:ProgramFiles},${env:ProgramFiles(x86)},${env:LOCALAPPDATA} -Filter "satdump.exe" -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) { $found = $hit.DirectoryName }
    }
    if ($found) {
        Add-UserPathOnce $found
        Write-Host "SatDump dir: $found"
    } else {
        Write-Host "WARN: satdump.exe not found yet - open a new shell after installer finishes."
    }
}

if (-not $SkipRtlSdr) {
    Write-Host "[2/3] Fetch librtlsdr Windows x64 tools (rtl_test / rtl_sdr)"
    $zip = Join-Path $Tools "rtlsdr.zip"
    $dest = Join-Path $Tools "rtlsdr"
    # Verified working as of 2026-07 (librtlsdr v0.9.0 + rtlsdrblog v1.3.6 tag)
    $urls = @(
        "https://github.com/librtlsdr/librtlsdr/releases/download/v0.9.0/rtlsdr-bin-w64_static.zip",
        "https://github.com/librtlsdr/librtlsdr/releases/download/v0.9.0/rtlsdr-bin-w64_dlldep.zip",
        "https://github.com/rtlsdrblog/rtl-sdr-blog/releases/download/v1.3.6/Release.zip"
    )
    $ok = $false
    foreach ($u in $urls) {
        try {
            Write-Host "  try $u"
            Invoke-WebRequest -Uri $u -OutFile $zip -UseBasicParsing -TimeoutSec 90 -UserAgent "SkyCache-RX-setup/1.1"
            if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
            Expand-Archive -Path $zip -DestinationPath $dest -Force
            $exe = Get-ChildItem $dest -Filter "rtl_test.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($exe) {
                Add-UserPathOnce $exe.DirectoryName
                Write-Host "rtl_test: $($exe.FullName)"
                $ok = $true
                break
            }
            Write-Host "  no rtl_test.exe in archive"
        } catch {
            Write-Host "  fail: $($_.Exception.Message)"
        }
    }
    if (-not $ok) {
        Write-Host "WARN: Could not auto-install rtl_test. Fallback options:"
        Write-Host "  winget install ryanvolz.radioconda"
        Write-Host "  https://www.rtl-sdr.com/rtl-sdr-quick-start-guide/  (Zadig + drivers)"
        Write-Host "  https://github.com/librtlsdr/librtlsdr/releases"
    }
}

Write-Host "[3/3] SkyCache rx doctor"
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
Push-Location $Root
try {
    py -3 -m skycache rx doctor --data-dir (Join-Path $Root "data")
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Next: plug in RTL-SDR (Zadig WinUSB if needed), then:"
Write-Host "  rtl_test -t"
Write-Host "  satdump  (or open SatDump GUI from Start menu)"
Write-Host "  Point SatDump products to: $Root\data\satdump-products"
Write-Host "  powershell -File scripts\Start-RxWatch.ps1 -Once"
Write-Host ""
Write-Host "Legal: receive-only open weather / open amateur. No commercial constellation clients."
