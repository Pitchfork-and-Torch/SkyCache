# Optional: register a Windows Scheduled Task that polls SatDump products every 5 minutes.
#
#   powershell -ExecutionPolicy Bypass -File scripts\Install-RxWatch-Task.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Install-RxWatch-Task.ps1 -Remove

param(
    [switch]$Remove,
    [string]$TaskName = "SkyCache-RxWatch"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$WatchScript = Join-Path $PSScriptRoot "Start-RxWatch.ps1"

if ($Remove) {
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed task $TaskName (if it existed)."
    exit 0
}

if (-not (Test-Path $WatchScript)) {
    throw "Missing $WatchScript"
}

# schtasks is more reliable across Windows SKUs than Register-ScheduledTask UserId forms
$tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$WatchScript`" -Once"
schtasks /Create /TN $TaskName /TR $tr /SC MINUTE /MO 5 /F /RL LIMITED | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks create failed with exit $LASTEXITCODE"
}

Write-Host "Registered task: $TaskName (every 5 minutes, one-shot watch)"
Write-Host "Products dir: $Root\data\satdump-products"
Write-Host "Working directory note: task runs with system default cwd; Start-RxWatch resolves paths from script location."
Write-Host "Remove with: -Remove"
schtasks /Query /TN $TaskName /FO LIST /V | Select-String -Pattern 'TaskName|Status|Task To Run|Next Run'
