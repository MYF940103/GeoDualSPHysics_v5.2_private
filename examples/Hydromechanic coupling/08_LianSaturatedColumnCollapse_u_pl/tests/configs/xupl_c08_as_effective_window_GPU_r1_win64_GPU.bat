@echo off
cd /d "%~dp0..\.."
"D:\anaconda3\python.exe" -X utf8 -B "tests\support\upl_c08_as_effective_window_r1.py" run --execution-authorized --notify
if errorlevel 1 pause
