# Continuous SatDump product watch for SkyCache (Windows).
# Legal: FTA open weather product ingest only.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\Start-RxWatch.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Start-RxWatch.ps1 -Once
#   powershell -ExecutionPolicy Bypass -File scripts\Start-RxWatch.ps1 -Interval 15 -Satellite "NOAA 18"

param(
    [string]$DataDir = "",
    [string]$ProductsDir = "",
    [string]$Satellite = "",
    [double]$Interval = 30,
    [switch]$Once
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $DataDir) { $DataDir = Join-Path $Root "data" }
if (-not $ProductsDir) { $ProductsDir = Join-Path $DataDir "satdump-products" }

if (-not (Test-Path $ProductsDir)) {
    New-Item -ItemType Directory -Force -Path $ProductsDir | Out-Null
}

$args = @(
    "-m", "skycache", "rx", "watch",
    "--dir", $ProductsDir,
    "--data-dir", $DataDir,
    "--interval", "$Interval",
    "--recipe", "product_import"
)
if ($Satellite) { $args += @("--satellite", $Satellite) }
if ($Once) { $args += "--once" } else { $args += @("--iterations", "0") }

Write-Host "Watching: $ProductsDir"
Write-Host "Data:     $DataDir"
Write-Host "Ctrl+C to stop (continuous mode)."
& py -3 @args
