@echo off
setlocal
pushd "%~dp0"

call xCaseRetroSlope_u_pw_prestress_win64_CPU.bat -force
if not "%ERRORLEVEL%" == "0" goto fail

call xCaseRetroSlope_u_pw_failure_win64_CPU.bat -force 50
if not "%ERRORLEVEL%" == "0" goto fail

echo u-pw two-stage retrogressive slope CPU workflow completed.
popd
pause
exit /b 0

:fail
echo u-pw two-stage retrogressive slope CPU workflow aborted.
popd
pause
exit /b 1
