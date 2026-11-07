@echo off
rem r2: one backend source, then its three qualified material branches.
call "%~dp0support\run_lian_collapse_shared_r2_win64.bat" psi2p5 CPU %*
exit /b %ERRORLEVEL%
