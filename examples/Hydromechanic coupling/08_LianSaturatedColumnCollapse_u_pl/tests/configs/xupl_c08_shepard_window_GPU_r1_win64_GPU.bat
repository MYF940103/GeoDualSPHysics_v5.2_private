@echo off
cd /d "%~dp0..\.."
"D:\anaconda3\python.exe" -X utf8 -B "tests\support\upl_c08_shepard_jobs_r1.py" run window --execution-authorized
if errorlevel 1 pause
