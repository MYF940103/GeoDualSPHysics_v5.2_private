@echo off
rem Fresh continuous preload/collapse; run only one backend for this group.
call "%~dp0support\run_lian_collapse_upl_r1_win64.bat" psi0 CPU "%~1"
exit /b %ERRORLEVEL%
