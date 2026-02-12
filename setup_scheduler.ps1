$taskName = "DailyStockScreener"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$PSScriptRoot\run_screener.bat`""
$trigger = New-ScheduledTaskTrigger -Daily -At 8am
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Daily Stock Screener (Weinstein + SEPA)"

Write-Host "✅ 작업 스케줄러 등록 완료: $taskName (매일 오전 8시 실행)" -ForegroundColor Green
Write-Host "직접 테스트하려면 작업 스케줄러에서 '실행'을 누르세요."
Pause
