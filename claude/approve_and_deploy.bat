@echo off
setlocal
set GITEXE=C:\Program Files\Git\cmd\git.exe
title Stock Bot - Approve and deploy to production
cd /d "%~dp0.."

echo ============================================================
echo   Approve the pipeline's changes and deploy to production (main)
echo ============================================================
echo.
echo Tip: run review_changes.bat first to read the diff on GitHub.
echo.

"%GITEXE%" fetch origin
if errorlevel 1 (
    echo Failed to fetch from GitHub. Check your internet/auth and try again.
    goto :end
)

echo Commits that would be merged into main:
echo.
"%GITEXE%" log --oneline main..origin/pipeline-dev
echo.

set /p CONFIRM="Merge these changes into main now? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Cancelled - nothing changed.
    goto :end
)

"%GITEXE%" checkout main
"%GITEXE%" merge origin/pipeline-dev -m "Approved and merged pipeline-dev into main"
if errorlevel 1 (
    echo Merge failed or had conflicts - resolve manually in this folder, nothing was pushed.
    goto :end
)

"%GITEXE%" push origin main
if errorlevel 1 (
    echo Merge succeeded locally but push to GitHub failed.
    echo Check your internet/auth and run: git push origin main
    goto :end
)

echo.
echo Code updated in the live folder and pushed to GitHub main.
echo.

set /p RESTART="Restart the live bot now so this code goes live on Telegram? (y/n): "
if /i not "%RESTART%"=="y" (
    echo Code updated but the bot was NOT restarted - it'll pick this up next restart.
    goto :end
)

echo Stopping the running bot instance (only the bot.py process, nothing else)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bot.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
timeout /t 2 /nobreak >nul
echo Starting the bot with the approved code...
start /min "" run_bot.bat
echo Done - the live bot is running the approved code.

:end
echo.
pause
endlocal
