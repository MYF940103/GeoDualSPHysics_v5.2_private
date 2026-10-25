@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."

rem Bounded 3-D production-step companion, not a formal consolidation run.
rem Runs coarse then half with native gates; preserves all retained results.
set python="D:\Anaconda3\python.exe"
%python% -B -u tests/support/spr_3d_run.py --backend cpu --geometry corner3 --slip 2 --tag spr_3d_manual_r1
if not "%ERRORLEVEL%"=="0" goto fail
popd
exit /b 0
:fail
echo Diagnostic refused or failed. Existing results were not removed.
popd
exit /b 1
