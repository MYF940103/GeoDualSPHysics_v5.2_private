@echo off
setlocal
set "CASE=upl_c08_rvisc_window_GPU_r1"
set "PYTHON=D:\anaconda3\python.exe"
if not exist "%PYTHON%" exit /b 2
if not exist "%~dp0%CASE%_Def.xml" exit /b 2
"%PYTHON%" -X utf8 -B "%~dp0..\support\upl_c08_rvisc_jobs_r1.py" run --profile window --execution-authorized --notify
set "EC=%ERRORLEVEL%"
if not "%~1"=="--unattended" pause
exit /b %EC%
