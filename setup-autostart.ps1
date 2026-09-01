# Setup Miso Bot to auto-start on Windows boot
# Run this script as Administrator on the old PC

$botPath = $PSScriptRoot
$taskName = "MisoBot-AutoStart"
$batchFile = Join-Path $botPath "start-persistent.bat"

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create trigger (at system startup)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create action (run batch file)
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batchFile`"" -WorkingDirectory $botPath

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Create principal (run with highest privileges)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Register the task
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Principal $principal -Description "Auto-start and update Miso Bot on system boot"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Miso Bot Auto-Start Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "The bot will now:" -ForegroundColor Cyan
Write-Host "  - Start automatically when Windows boots" -ForegroundColor White
Write-Host "  - Check for updates every 5 minutes" -ForegroundColor White
Write-Host "  - Auto-restart if it crashes" -ForegroundColor White
Write-Host "  - Pull code changes without conflicts" -ForegroundColor White
Write-Host ""
Write-Host "To test now, run: start-persistent.bat" -ForegroundColor Yellow
Write-Host ""
Write-Host "To remove auto-start:" -ForegroundColor Gray
Write-Host "  Run: schtasks /delete /tn `"$taskName`" /f" -ForegroundColor Gray
Write-Host ""

Pause
