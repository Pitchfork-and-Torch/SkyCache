# Setup permanent SkyCache live FTA RX station paths on Windows.
# Legal: receive-only open weather / open amateur - not commercial broadband.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\Setup-RxStation.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Setup-RxStation.ps1 -Lat 40.71 -Lon -74.01
#   powershell -ExecutionPolicy Bypass -File scripts\Setup-RxStation.ps1 -RefreshTle

param(
    [double]$Lat = 40.7128,
    [double]$Lon = -74.0060,
    [double]$AltM = 25,
    [string]$Name = "knock-station",
    [string]$Antenna = "V-dipole 137",
    [string]$DataDir = "",
    [switch]$RefreshTle
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $DataDir) { $DataDir = Join-Path $Root "data" }

$Products = Join-Path $DataDir "satdump-products"
$RxDir = Join-Path $DataDir "rx"
$TlePath = Join-Path $DataDir "tle-fta-priority.txt"
$Readme = Join-Path $Products "README.txt"

New-Item -ItemType Directory -Force -Path $Products, $RxDir | Out-Null

$readmeBody = @"
SkyCache SatDump product drop folder
====================================
Point SatDump (or any decoder) to write PNG/JPG products into this folder
(or a subfolder). Then either:

  py -3 -m skycache rx watch --dir `"$Products`" --data-dir `"$DataDir`" --once

or run scripts\Start-RxWatch.ps1 for continuous poll.

Legal: unencrypted free-to-air weather / open amateur only.
Not commercial satellite broadband.
"@
[System.IO.File]::WriteAllText($Readme, $readmeBody, [Text.UTF8Encoding]::new($false))

Write-Host "[1/5] pip install sgp4 (pass geometry)"
py -3 -m pip install "sgp4>=2.23" -q

if ($RefreshTle -or -not (Test-Path $TlePath)) {
    Write-Host "[2/5] Refresh FTA TLEs (Celestrak CATNR + weather Meteor)"
    py -3 (Join-Path $PSScriptRoot "refresh_fta_tles.py") --out $TlePath
} else {
    Write-Host "[2/5] TLEs present: $TlePath (pass -RefreshTle to update)"
}

Write-Host "[3/5] Station lat=$Lat lon=$Lon"
py -3 -m skycache rx station --data-dir $DataDir --lat $Lat --lon $Lon --alt-m $AltM --name $Name --antenna $Antenna

if (Test-Path $TlePath) {
    Write-Host "[4/5] Import TLE cache"
    py -3 -m skycache rx tle-import $TlePath --data-dir $DataDir
} else {
    Write-Host "[4/5] WARN: no TLE file; passes will use fixtures"
}

Write-Host "[5/5] Doctor + next passes"
py -3 -m skycache rx doctor --data-dir $DataDir
py -3 -m skycache rx passes --data-dir $DataDir --hours 24 --min-elev 15

Write-Host ""
Write-Host "DONE. Products folder: $Products"
Write-Host "Watch once:  py -3 -m skycache rx watch --dir `"$Products`" --data-dir `"$DataDir`" --once"
Write-Host "Watch loop:  powershell -ExecutionPolicy Bypass -File scripts\Start-RxWatch.ps1"
Write-Host "Portal:      py -3 -m skycache serve --data-dir `"$DataDir`" --host 127.0.0.1 --port 8080"
Write-Host "Edit lat/lon with -Lat -Lon if this is not your site."
