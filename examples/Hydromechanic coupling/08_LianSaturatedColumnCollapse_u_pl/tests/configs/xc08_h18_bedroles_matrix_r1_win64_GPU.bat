@echo off
setlocal
cd /d "%~dp0..\.."
set "c08python=D:\anaconda3\python.exe"
if not exist "%c08python%" set "c08python=python"
"%c08python%" -X utf8 -B "tests\support\c08_h18_bedroles_matrix_r1.py" run --execution-authorized --notify
set "EC=%ERRORLEVEL%"
if not "%~1"=="--unattended" pause
exit /b %EC%
