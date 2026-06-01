@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


set name=CaseStaticSoilColumn_PorePressure
set dirout=%name%_gpu_out
set diroutdata=%dirout%\data

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set boundaryvtk="%dirbin%/BoundaryVTK_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"

:menu
if exist %dirout% (
    set /p option="The folder "%dirout%" already exists. Choose an option.!NL!  [1]- Delete it and continue.!NL!  [2]- Execute post-processing.!NL!  [3]- Abort and exit.!NL!"
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

%gencase% %name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu -mdbc %dirout%/%name% %dirout% -dirdataout data -svres
if not exist "%diroutdata%\Part_0000.bi4" goto fail

:postprocessing
set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartFluid -onlytype:-all,fluid -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+porepress,+porepress0,+excessporepress
if not "%ERRORLEVEL%" == "0" goto fail

set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartBound -onlytype:-all,bound -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+fstype,+porepress,+porepress0,+excessporepress
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo All done
goto end

:fail
echo Execution aborted.

:end
pause
