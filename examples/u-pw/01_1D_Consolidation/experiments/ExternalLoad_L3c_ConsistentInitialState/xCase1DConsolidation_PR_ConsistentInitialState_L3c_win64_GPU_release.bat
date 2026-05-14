@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem Don't remove the two jump lines after the next line [set NL=^]
set NL=^


set name=Case1DConsolidation_PR_ConsistentInitialState_L3c
set dirout=%name%_gpu_out
set diroutdata=%dirout%\data
set dirvtk=%name%_gpu_vtk_particles
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%\DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%\PartVTK_win64.exe"

:menu
if exist %dirout% (
    set /p option="The folder "%dirout%" already exists. Choose an option.!NL!  [1]- Delete it and run again.!NL!  [2]- Execute particle VTK post-processing only.!NL!  [3]- Abort and exit.!NL!"
    if "!option!" == "1" goto run
    if "!option!" == "2" goto postprocessing
    if "!option!" == "3" goto fail
    goto menu
)

:run
if exist %dirout% rd /s /q %dirout%
if exist %dirvtk% rd /s /q %dirvtk%

%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
if not exist %dirvtk% mkdir %dirvtk%

%partvtk% -dirin %diroutdata% -filexml %dirout%\%name%.xml -savevtk %dirvtk%\PartFluid -onlytype:-all,+fluid -vars:+idp,+vel,+rhop,+type,+mk,+PorePress,+ExcessPorePress,+PorePressRate,+DivVel,+LapPorePress,+LapZ,+PorePressureAccelDiff
if not "%ERRORLEVEL%" == "0" goto fail

echo All done
goto end

:fail
echo Execution aborted.

:end
pause
