@echo off
setlocal
cd /d "%~dp0..\.."
set name=cryer_symc_gpu_short_r1_h
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="tests/outputs/cryer_symc_gpu_build_r3/Release/cryer_symc_gpu_r3_Release.exe"
if exist "%dirout%" goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysicsgpu% -gpu -stable %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0
:fail
echo Execution aborted; retained outputs are never deleted.
exit /b 1
