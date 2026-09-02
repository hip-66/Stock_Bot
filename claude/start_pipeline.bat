@echo off
REM Starts the continuous 4-agent pipeline in its own window, detached from this one.
REM Close that window (or run stop_pipeline.bat) to stop it. It keeps running and
REM retrying through rate limits until you do.
cd /d "%~dp0"
start "Stock Bot Pipeline" cmd /k python "%~dp0run_pipeline.py"
