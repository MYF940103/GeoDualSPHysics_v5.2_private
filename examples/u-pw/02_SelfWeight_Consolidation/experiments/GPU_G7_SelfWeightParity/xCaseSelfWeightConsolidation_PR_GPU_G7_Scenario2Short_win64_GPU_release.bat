@echo off
setlocal EnableDelayedExpansion

set name=CaseSelfWeightConsolidation_PR_GPU_G7_Scenario2Short
set dirout=%name%_gpu_out
set diroutdata=%dirout%\data
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%\DualSPHysics5.2_GEO_win64.exe"

if exist %dirout% rd /s /q %dirout%

%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail

echo All done
goto end

:fail
echo Execution aborted.

:end
pause
