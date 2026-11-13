@echo off
setlocal
set "PYTHON=D:\anaconda3\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" -X utf8 -B "%~dp0..\support\c08_h18_plastic_pre_r1.py" run --group psi0 --execution-authorized --notify
set "EC=%ERRORLEVEL%"
if not "%~1"=="--unattended" pause
exit /b %EC%
