@echo off
setlocal
cd /d "%~dp0..\.."
set "c08python=D:\anaconda3\python.exe"
if not exist "%c08python%" set "c08python=python"
"%c08python%" -X utf8 -B "tests\support\c08_h18_pre_r1.py" --execution-authorized --notify
if errorlevel 1 goto fail
echo Fresh PRE finished. Native and equilibrium review still required.
pause
exit /b 0
:fail
echo Preserve outputs. Do not overwrite or restart this run.
pause
exit /b 1
