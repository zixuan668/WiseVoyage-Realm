@echo off
rem Re-apply the USB port forwarding the dev App needs after every HBuilderX re-run.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0connect_device_backend.ps1" %*
pause
