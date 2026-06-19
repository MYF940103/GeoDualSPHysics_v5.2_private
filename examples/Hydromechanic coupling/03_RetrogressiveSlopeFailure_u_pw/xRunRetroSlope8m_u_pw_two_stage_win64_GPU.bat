@echo off
setlocal
pushd "%~dp0"

call xCaseRetroSlope8m_u_pw_prestress_win64_GPU.bat -force
if not "%ERRORLEVEL%" == "0" goto fail

call xCaseRetroSlope8m_u_pw_failure_win64_GPU.bat -force 50
if not "%ERRORLEVEL%" == "0" goto fail

echo u-pw 8m two-stage retrogressive slope GPU workflow completed.
popd
pause
exit /b 0

:fail
echo u-pw 8m two-stage retrogressive slope GPU workflow aborted.
popd
pause
exit /b 1
