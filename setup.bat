@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
set "setup_exit=%errorlevel%"
echo.
if not "%setup_exit%"=="0" echo Setup did not finish. Review the error above, then run setup.bat again.
pause
exit /b %setup_exit%
