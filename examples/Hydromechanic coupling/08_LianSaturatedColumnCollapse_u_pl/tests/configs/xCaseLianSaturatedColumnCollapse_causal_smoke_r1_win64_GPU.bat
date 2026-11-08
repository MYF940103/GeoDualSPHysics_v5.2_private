@echo off
setlocal
set "PYTHON=D:\anaconda3\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" -X utf8 -B "%~dp0..\support\upl_c08_causal_jobs_r1.py" smoke --execution-authorized
set "EC=%ERRORLEVEL%"
if not "%~1"=="--unattended" pause
exit /b %EC%
