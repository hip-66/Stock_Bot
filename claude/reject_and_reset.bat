@echo off
setlocal
set GITEXE=C:\Program Files\Git\cmd\git.exe
set WORKSPACE=C:\Users\Uriya.DESKTOP-AEQOV71\Desktop\Projects\Stock_Bot_pipeline_workspace
title Stock Bot - Reject changes and reset

echo ============================================================
echo   Reject the pipeline's changes and reset it back to production
echo ============================================================
echo.
echo Make sure the pipeline is stopped first (run stop_pipeline.bat) so it
echo isn't committing while this runs.
echo.

if not exist "%WORKSPACE%" (
    echo Workspace folder not found: %WORKSPACE%
    goto :end
)
cd /d "%WORKSPACE%"

"%GITEXE%" fetch origin
if errorlevel 1 (
    echo Failed to fetch from GitHub. Check your internet/auth and try again.
    goto :end
)

echo These commits will be PERMANENTLY discarded from pipeline-dev:
echo.
"%GITEXE%" log --oneline main..pipeline-dev
echo.

set /p CONFIRM="Discard all of the above and reset pipeline-dev back to main? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Cancelled - nothing changed.
    goto :end
)

"%GITEXE%" checkout pipeline-dev
"%GITEXE%" reset --hard main
"%GITEXE%" push origin pipeline-dev --force

echo.
echo Done. pipeline-dev now matches main again - nothing was kept.
echo The live bot in the "Stock Bot" folder was never touched by this.
echo Restart the pipeline (start_pipeline.bat) whenever you want it to try again.

:end
echo.
pause
endlocal
