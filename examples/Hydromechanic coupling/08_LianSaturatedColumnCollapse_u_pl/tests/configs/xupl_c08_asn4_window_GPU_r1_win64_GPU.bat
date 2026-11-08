@echo off
setlocal
set "PYTHON=D:\anaconda3\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" -X utf8 -B "%~dp0..\support\upl_c08_asn4_window_r1.py" --execution-authorized --notify
set "EC=%ERRORLEVEL%"
if not "%~1"=="--unattended" pause
exit /b %EC%
