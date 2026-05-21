@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


rem Test case for CPU free-surface tracking output using the noslip XML.

set name=CaseGranularColumnCollapse2D_Feng2021_a05_dp002_noslip
set dirout=%name%_FSTrack_CPU_out
set diroutdata=%dirout%\data

rem "executables" are renamed and called from their directory

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set partvtkout="%dirbin%/PartVTKOut_win64.exe"

set fstrackvars=+FSType
set fluidvars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,%fstrackvars%
set boundvars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,%fstrackvars%

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
rem "dirout" to store results is removed if it already exists
if exist %dirout% rd /s /q %dirout%

rem CODES are executed according the selected parameters of execution in this testcase

%gencase% %name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc_noslip %dirout%/%name% %dirout% -dirdataout data -svres
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
rem Executes PartVTK to create VTK files with soil particles.
rem FSType: 0 internal, 2 free surface, 3 isolated/splash-like, 4 boundary.
set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartFluid -onlytype:-all,fluid -vars:%fluidvars%
if not "%ERRORLEVEL%" == "0" goto fail

%partvtk% -dirin %diroutdata% -files:100 -savecsv %dirout2%/PartFluidCsv_final -onlytype:-all,fluid -vars:%fluidvars%
if not "%ERRORLEVEL%" == "0" goto fail

rem Executes PartVTK to create VTK files with boundary particles.
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartBound -onlytype:-all,bound -vars:%boundvars%
if not "%ERRORLEVEL%" == "0" goto fail

rem Executes PartVTKOut to create VTK files with excluded particles, when present.
%partvtkout% -dirin %diroutdata% -savevtk %dirout2%/PartFluidOut -SaveResume %dirout2%/_ResumeFluidOut
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo All done
goto end

:fail
echo Execution aborted.

:end
if /i "%~1" == "-force" exit /b %ERRORLEVEL%
pause
