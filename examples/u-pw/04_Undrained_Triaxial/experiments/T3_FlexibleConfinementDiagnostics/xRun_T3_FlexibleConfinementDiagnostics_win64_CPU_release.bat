@echo off
setlocal
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%\PartVTK_win64.exe"

call :run CaseT3_ConfinementOnly_Legacy
if not "%ERRORLEVEL%" == "0" goto fail
call :run CaseT3_ConfinementOnly_Selected
if not "%ERRORLEVEL%" == "0" goto fail
call :run CaseT3_AxialConfinement_Selected
if not "%ERRORLEVEL%" == "0" goto fail

echo All T3 CPU Release diagnostics completed.
goto end

:run
set name=%1
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
exit /b 0

:fail
echo T3 execution aborted.
exit /b 1
:end
exit /b 0
