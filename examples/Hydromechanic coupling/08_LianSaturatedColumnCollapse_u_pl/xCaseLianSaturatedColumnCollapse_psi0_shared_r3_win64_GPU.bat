@echo off
rem r3 server candidate: first finish this backend source, then run its receivers in order.
call "%~dp0support\run_lian_collapse_shared_r3_win64.bat" psi0 GPU %*
exit /b %ERRORLEVEL%
