@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


set name=CaseSelfWeightConsolidation_PR_Scenario1_StageA
set rundir=Scenario1_StageA_PR_run
set dirout=%rundir%\%name%_out
set diroutdata=%dirout%\data

set dirbin=..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%\PartVTK_win64.exe"

:menu
if exist %dirout% (
    set /p option="The folder "%dirout%" already exists. Choose an option.!NL!  [1]- Delete it and run again.!NL!  [2]- Execute particle post-processing only.!NL!  [3]- Abort and exit.!NL!"
    if "!option!" == "1" goto run else (
        if "!option!" == "2" goto postprocessing else (
            if "!option!" == "3" goto fail else (
                goto menu
            )
        )
    )
)

:run
if exist %dirout% rd /s /q %dirout%
if not exist %rundir% mkdir %rundir%

%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
set dirout2=%rundir%\vtk_particles
if not exist %dirout2% mkdir %dirout2%
%partvtk% -dirin %diroutdata% -filexml %dirout%\%name%.xml -savevtk %dirout2%\PartFluid -onlytype:-all,+fluid -vars:+idp,+vel,+rhop,+type,+mk,+PorePress,+ExcessPorePress,+PorePressRate,+DivVel,+LapPorePress,+LapZ,+PorePressureAccelDiff
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo All done
goto end

:fail
echo Execution aborted.

:end
pause
