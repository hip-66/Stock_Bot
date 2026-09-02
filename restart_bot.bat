@echo off
chcp 65001 >nul
title Stock Bot - Control Center

:: 1. בדיקה והרמת הרשאות מנהל אוטומטית למניעת שגיאות גישה
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit
)

:menu
cls
echo ========================================================
echo               STOCK BOT CONTROL CENTER
echo ========================================================
echo.
echo  [R] Restart / Start the Bot
echo  [X] Exit this control window
echo.
echo --------------------------------------------------------

:: 2. בדיקה האם הבוט כבר רץ ברקע כרגע
powershell -Command "$p = Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*bot.py*'}; if ($p) { exit 0 } else { exit 1 }"
if %errorlevel% equ 0 (
    echo  Status: Bot is currently RUNNING in the background.
) else (
    echo  Status: Bot is currently STOPPED.
)
echo.

set /p choice="Press 'R' to restart/start the bot, or 'X' to exit: "

if /i "%choice%"=="r" goto do_restart
if /i "%choice%"=="x" exit
goto menu

:do_restart
echo.
echo [1/3] Stopping any existing bot instances...
taskkill /f /im python.exe >nul 2>&1

echo [2/3] Waiting 2 seconds to release resources...
timeout /t 2 /nobreak >nul

echo [3/3] Starting the bot in the background...
cd /d "C:\Users\Uriya.DESKTOP-AEQOV71\Desktop\Projects\Stock Bot"
start /min "" run_bot.bat

echo.
echo Bot is now running in the background!
timeout /t 2 >nul
goto menu