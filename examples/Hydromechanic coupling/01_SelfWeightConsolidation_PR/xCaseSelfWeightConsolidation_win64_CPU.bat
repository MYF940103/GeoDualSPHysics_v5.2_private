@echo off
setlocal
pushd "%~dp0"

call xCaseSelfWeightConsolidation_Stage1_win64_CPU.bat
if not "%ERRORLEVEL%" == "0" goto fail

call xCaseSelfWeightConsolidation_Scenario2_win64_CPU.bat -force
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo All done
popd
exit /b 0

:fail
echo Execution aborted.
popd
exit /b 1
