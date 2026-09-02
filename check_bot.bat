@echo off

powershell -Command ^
"$p = Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*bot.py*'}; ^
if (!$p) { Start-Process 'C:\Users\Uriya.DESKTOP-AEQOV71\Desktop\Projects\Stock Bot\run_bot.bat' }"