@echo off
rem Tests-only source. Root admission is required; no receiver is started.
setlocal
cd /d "%~dp0.."
set "PYTHON=D:\anaconda3\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" -X utf8 -B "%~dp0..\support\upl_c08_hdp15_preload_r1.py" --execution-authorized --notify
set "EC=%ERRORLEVEL%"
if /i not "%~1"=="--unattended" pause
exit /b %EC%
