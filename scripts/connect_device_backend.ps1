# Restore the USB port forwarding the dev App needs to reach the PC backend.
# HBuilderX clears custom `adb reverse` rules whenever it re-runs the project,
# so run this script after every "运行到手机" (the backend must already be on 18000).
param(
    [string]$Adb,
    [int[]]$Ports = @(18000, 5173),
    [switch]$Watch
)
$ErrorActionPreference = 'Stop'

if (-not $Adb) {
    $candidates = @(
        'adb',
        'D:\bcsoft\HBuilderX\HBuilderX\plugins\launcher-tools\tools\adbs\adb.exe',
        'D:\bcsoft\微信web开发者工具\resources\app.asar.unpacked\bin\adb-win\adb.exe',
        'D:\HBuilderX\HBuilderX\plugins\launcher-tools\tools\adbs\adb.exe'
    )
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) { $Adb = $command.Source; break }
    }
}
if (-not $Adb) { throw 'adb not found. Pass -Adb <path to adb.exe>.' }

$devices = & $Adb devices
if (-not ($devices -match "\sdevice\s*$")) { throw 'No Android device in "device" state. Reconnect USB debugging first.' }

foreach ($port in $Ports) {
    & $Adb reverse "tcp:$port" "tcp:$port" | Out-Null
    Write-Output ("forwarded phone 127.0.0.1:{0} -> PC {0}" -f $port)
}

Write-Output '--- current reverse rules ---'
& $Adb reverse --list

$status = (& $Adb shell "curl -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:18000/api/v1/tour-session/spots") -join ''
Write-Output ("backend from the phone: HTTP {0}" -f $status)
if ($status -ne '200') {
    Write-Output 'Backend did not answer 200. Start it with start_backend.ps1 and try again.'
    exit 1
}


if ($Watch) {
    # HBuilder reruns clear the reverse rules. Restore only missing rules.
    while ($true) {
        Start-Sleep -Seconds 1
        $connected = & $Adb devices 2>$null
        if (-not ($connected -match "\sdevice\s*$")) { continue }
        $rules = (& $Adb reverse --list 2>$null) -join ' '
        foreach ($port in $Ports) {
            if ($rules -notmatch ("tcp:{0} tcp:{0}(\s|$)" -f $port)) {
                & $Adb reverse "tcp:$port" "tcp:$port" 2>$null | Out-Null
            }
        }
    }
}
