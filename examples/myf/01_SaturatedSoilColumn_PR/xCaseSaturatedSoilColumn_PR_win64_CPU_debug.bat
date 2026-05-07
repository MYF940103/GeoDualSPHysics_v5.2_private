@echo off
setlocal EnableDelayedExpansion

set name=CaseSaturatedSoilColumn_PR
set dirout=%name%_out
set diroutdata=%dirout%\data
set dirbin=..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64_debug.exe"

if exist %dirout% (
  echo The folder %dirout% already exists. Delete it or rename it before rerunning this script.
  exit /b 1
)

%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail

echo All done
exit /b 0

:fail
echo Execution aborted.
exit /b 1
