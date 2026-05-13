@echo off
setlocal
set name=CaseUndrainedTriaxial_PR_T1_Baseline
set dirout=%name%_out
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%\PartVTK_win64.exe"

if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx -svres
if not "%ERRORLEVEL%" == "0" goto fail

set diroutdata=%dirout%\data
set dirvtk=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirvtk%\PartFluid -onlytype:-all,+fluid
if not "%ERRORLEVEL%" == "0" goto fail

echo All done
goto end
:fail
echo Execution aborted.
exit /b 1
:end
exit /b 0
