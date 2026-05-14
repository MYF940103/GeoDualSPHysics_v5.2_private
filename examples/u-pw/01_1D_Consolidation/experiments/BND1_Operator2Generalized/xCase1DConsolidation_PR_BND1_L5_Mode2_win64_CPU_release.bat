@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set name=Case1DConsolidation_PR_BND1_L5_Mode2
set dirout=%name%_cpu_out
set diroutdata=%dirout%\data
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysicscpu% -cpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail
echo All done
goto end
:fail
echo Execution aborted.
exit /b 1
:end
exit /b 0
