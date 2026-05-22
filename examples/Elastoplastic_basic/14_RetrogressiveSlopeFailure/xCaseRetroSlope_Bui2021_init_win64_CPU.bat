@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


set name=CaseRetroSlope_Bui2021_init
set dirout=%name%_CPU_out
set diroutdata=%dirout%\data

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

:menu
if exist %dirout% (
    if /i "%~1" == "-force" goto run
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

%dualsphysicscpu% -cpu -mdbc_noslip %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartFluid -onlytype:-all,fluid -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic
if not "%ERRORLEVEL%" == "0" goto fail

%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartBound -onlytype:-all,bound -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Initial stress stage completed.
echo Restart PART for the failure stage: %diroutdata%\Part_0050.bi4
goto end

:fail
echo Execution aborted.

:end
if /i "%~1" == "-force" exit /b %ERRORLEVEL%
pause
