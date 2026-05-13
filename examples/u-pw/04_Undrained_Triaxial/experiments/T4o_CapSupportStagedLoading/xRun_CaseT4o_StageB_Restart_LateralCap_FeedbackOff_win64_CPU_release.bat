@echo off
setlocal
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
set name=CaseT4o_StageB_Restart_LateralCap_FeedbackOff
set dirout=%name%_out
set olddiroutdata=CaseT4o_StageA_AllSurface_FeedbackOff_out\data
if not exist %olddiroutdata%\Part_0023.bi4 exit /b 1
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" exit /b 1
%dualsphysicscpu% -cpu %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx -svres -partbegin:23 %olddiroutdata%
if not "%ERRORLEVEL%" == "0" exit /b 1
echo T4o Stage B restart CPU Release completed for %name%.
exit /b 0
