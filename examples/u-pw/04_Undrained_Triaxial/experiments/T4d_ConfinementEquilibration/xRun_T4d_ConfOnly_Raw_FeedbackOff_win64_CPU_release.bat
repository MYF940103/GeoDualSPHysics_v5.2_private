@echo off
setlocal
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%\PartVTK_win64.exe"

set name=CaseT4d_ConfOnly_Raw_FeedbackOff
set dirout=%name%_out
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" exit /b 1
%dualsphysicscpu% -cpu %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx -svres
if not "%ERRORLEVEL%" == "0" exit /b 1
set diroutdata=%dirout%\data
set dirvtk=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirvtk%\PartFluid -onlytype:-all,+fluid
if not "%ERRORLEVEL%" == "0" exit /b 1
echo T4d CPU Release confinement-only raw feedback-off smoke completed.
exit /b 0
