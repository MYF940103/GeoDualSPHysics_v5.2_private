@echo off
setlocal EnableDelayedExpansion

set name=Case1DConsolidation_PR_GPU_G5_NonUniform
set dirout=%name%_out
set diroutdata=%dirout%\data
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%\DualSPHysics5.2_win64_debug.exe"

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
