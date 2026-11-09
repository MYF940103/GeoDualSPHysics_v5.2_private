@echo off
setlocal
cd /d "%~dp0..\.."
rem One admitted H1.8 fresh source; existing outputs are preserved.
set "c08python=D:\anaconda3\python.exe"
if not exist "%c08python%" set "c08python=python"
"%c08python%" -X utf8 -B "tests\support\c08_h18_bedroles_pre_r1.py" --execution-authorized --notify
set "EC=%ERRORLEVEL%"
if not "%~1"=="--unattended" pause
exit /b %EC%
