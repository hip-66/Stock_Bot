@echo off
REM Signals a paused pipeline (see PIPELINE_GUIDE.md - "scheduled review pause") to
REM resume. Does nothing if the pipeline isn't currently paused and waiting.
setlocal
set STATEDIR=%~dp0state
if not exist "%STATEDIR%" mkdir "%STATEDIR%"
type nul > "%STATEDIR%\continue_signal"
echo Signal sent - the pipeline will resume within about 30 seconds.
endlocal
pause
