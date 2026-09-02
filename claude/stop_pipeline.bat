@echo off
setlocal
set PIDFILE=%~dp0state\pipeline.pid
if not exist "%PIDFILE%" (
    echo No pipeline.pid found - pipeline does not appear to be running.
    goto :end
)
for /f "usebackq delims=" %%p in ("%PIDFILE%") do set PID=%%p
echo Stopping pipeline process %PID%...
taskkill /PID %PID% /T /F
del "%PIDFILE%"
:end
endlocal
