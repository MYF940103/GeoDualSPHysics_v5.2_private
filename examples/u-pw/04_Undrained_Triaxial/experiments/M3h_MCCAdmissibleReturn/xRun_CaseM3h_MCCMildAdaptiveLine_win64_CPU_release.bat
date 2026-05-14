@echo off
setlocal
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
set name=CaseM3h_MCCMildAdaptiveLine
set dirout=%name%_out
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" exit /b 1
%dualsphysicscpu% -cpu %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx -svres
if not "%ERRORLEVEL%" == "0" exit /b 1
echo M3h CPU Release completed for CaseM3h_MCCMildAdaptiveLine.
exit /b 0
