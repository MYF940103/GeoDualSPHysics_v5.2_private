@echo off
setlocal
pushd "%~dp0"

set tmax=%~1
if "%tmax%" == "" set tmax=0.2
set tout=%~2
if "%tout%" == "" set tout=0.02

call xCaseRetroSlope_u_pw_init_win64_CPU.bat upward %tmax% %tout%
if not "%ERRORLEVEL%" == "0" goto fail

call xCaseRetroSlope_u_pw_init_win64_CPU.bat allfs %tmax% %tout%
if not "%ERRORLEVEL%" == "0" goto fail

py support\analyze_retro_slope_hydrostatic.py CaseRetroSlope_u_pw_init_upward_CPU_out CaseRetroSlope_u_pw_init_allfs_CPU_out
if not "%ERRORLEVEL%" == "0" goto fail

echo Retrogressive slope u-pw hydrostatic comparison completed.
popd
exit /b 0

:fail
echo Retrogressive slope u-pw hydrostatic comparison aborted.
popd
exit /b 1
