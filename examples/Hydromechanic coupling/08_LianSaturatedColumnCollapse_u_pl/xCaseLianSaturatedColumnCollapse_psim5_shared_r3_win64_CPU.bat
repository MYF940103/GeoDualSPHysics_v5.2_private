@echo off
rem r3 server candidate: first finish this backend source, then run its receivers in order.
call "%~dp0support\run_lian_collapse_shared_r3_win64.bat" psim5 CPU %*
exit /b %ERRORLEVEL%
