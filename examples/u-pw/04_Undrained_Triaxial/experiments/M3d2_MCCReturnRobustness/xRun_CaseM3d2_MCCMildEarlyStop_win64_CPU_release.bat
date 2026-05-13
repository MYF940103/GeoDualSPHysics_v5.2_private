@echo off
setlocal
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
set name=CaseM3d2_MCCMildEarlyStop
set dirout=%name%_out
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" exit /b 1
%dualsphysicscpu% -cpu %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx -svres
if not "%ERRORLEVEL%" == "0" exit /b 1
echo M3d2 CPU Release completed for CaseM3d2_MCCMildEarlyStop.
exit /b 0
