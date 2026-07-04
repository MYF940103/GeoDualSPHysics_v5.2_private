@echo off
setlocal
pushd "%~dp0"

call xCaseSelfWeightConsolidation_Stage1_win64_GPU.bat -force
if not "%ERRORLEVEL%" == "0" goto fail

call xCaseSelfWeightConsolidation_Scenario2_win64_GPU.bat -force
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo All GPU stages done
popd
pause
exit /b 0

:fail
echo GPU execution aborted.
popd
pause
exit /b 1
