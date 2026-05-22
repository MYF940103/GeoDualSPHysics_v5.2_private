@echo off
setlocal

call xCaseRetroSlope_Bui2021_init_win64_CPU.bat -force
if not "%ERRORLEVEL%" == "0" goto fail

call xCaseRetroSlope_Bui2021_failure_win64_CPU.bat -force
if not "%ERRORLEVEL%" == "0" goto fail

echo Two-stage retrogressive slope workflow completed.
goto end

:fail
echo Two-stage workflow aborted.

:end
pause
