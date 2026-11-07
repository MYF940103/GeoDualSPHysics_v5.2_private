@echo off
rem UNEXECUTED candidate; common launcher stays locked pending scope/runtime verification.
call "%~dp0upl_collapse_candidate_r1_win64.bat" psi2p5 CPU "%~1"
exit /b %ERRORLEVEL%
