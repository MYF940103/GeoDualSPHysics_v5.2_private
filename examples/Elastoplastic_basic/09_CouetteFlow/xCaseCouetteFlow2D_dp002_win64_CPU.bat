@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


rem "name" and "dirout" are named according to the testcase

set name=CaseCouetteFlow2D_dp002
set dirout=%name%_CPU_out
set diroutdata=%dirout%\data

rem "executables" are renamed and called from their directory

set dirbin=../../../bin/windows
set dirbinref=D:\MYF\SPH\GeoDualSPHysics_v5.2\bin\windows
set PATH=%dirbinref%;%PATH%
set gencase="%dirbin%/GenCase_win64.exe"
if not exist %gencase% set gencase="%dirbinref%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbinref%/DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
if not exist %partvtk% set partvtk="%dirbinref%/PartVTK_win64.exe"
set measuretool="%dirbin%/MeasureTool_win64.exe"
if not exist %measuretool% set measuretool="%dirbinref%/MeasureTool_win64.exe"

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
rem "dirout" to store results is removed if it already exists
if exist %dirout% rd /s /q %dirout%

rem CODES are executed according the selected parameters of execution in this testcase

%gencase% %name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc_noslip %dirout%/%name% %dirout% -dirdataout data -svres
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
rem Executes PartVTK to create VTK files with particles.
set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartFluid -onlytype:-all,fluid -vars:+idp,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic
if not "%ERRORLEVEL%" == "0" goto fail

%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartBound -onlytype:-all,bound -vars:+idp,+vel,+rhop,+sigma_kk,+sigma_ij
if not "%ERRORLEVEL%" == "0" goto fail

rem Interpolates the velocity profile at x=0.5 m for analytical comparison.
set dirout2=%dirout%\measuretool
%measuretool% -dirin %diroutdata% -points PointsVelocity_dp002.txt -onlytype:-all,+fluid -distinter_2h:0.75 -vars:-all,+vel.x,+vel.m -savevtk %dirout2%/PointsVelocity -savecsv %dirout2%/_PointsVelocity
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo All done
goto end

:fail
echo Execution aborted.

:end
pause
