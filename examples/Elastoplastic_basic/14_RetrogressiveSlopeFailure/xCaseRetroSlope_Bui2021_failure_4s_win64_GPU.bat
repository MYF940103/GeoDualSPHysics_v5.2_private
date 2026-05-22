@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


set name=CaseRetroSlope_Bui2021_failure_4s
set dirout=%name%_GPU_out
set diroutdata=%dirout%\data
set initname=CaseRetroSlope_Bui2021_init
set initdir=%initname%_CPU_out\data
set partbegin=50
set partbegin4=0050

set dirbin=../../../bin/windows
set dirbinref=D:\MYF\SPH\GeoDualSPHysics_v5.2\bin\windows
set PATH=%dirbinref%;%PATH%
set gencase="%dirbin%/GenCase_win64.exe"
if not exist %gencase% set gencase="%dirbinref%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbinref%/DualSPHysics5.2_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
if not exist %partvtk% set partvtk="%dirbinref%/PartVTK_win64.exe"
set partvtkout="%dirbin%/PartVTKOut_win64.exe"
if not exist %partvtkout% set partvtkout="%dirbinref%/PartVTKOut_win64.exe"

if not exist "%initdir%\Part_%partbegin4%.bi4" (
    echo Required restart file "%initdir%\Part_%partbegin4%.bi4" was not found.
    echo Run xCaseRetroSlope_Bui2021_init_win64_CPU.bat first, or edit partbegin in this file.
    goto fail
)
if not exist "%initdir%\PartExtra_%partbegin4%.bi4" (
    echo Required mDBC restart file "%initdir%\PartExtra_%partbegin4%.bi4" was not found.
    echo The initial stage must be run with -svextraparts:1.
    goto fail
)

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

%dualsphysicsgpu% -gpu -mdbc_noslip %dirout%/%name% %dirout% -dirdataout data -svres -partbegin:%partbegin%:0 %initdir%
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartFluid -onlytype:-all,fluid -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic
if not "%ERRORLEVEL%" == "0" goto fail

%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartBound -onlytype:-all,bound -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij
if not "%ERRORLEVEL%" == "0" goto fail

%partvtkout% -dirin %diroutdata% -savevtk %dirout2%/PartFluidOut -SaveResume %dirout2%/_ResumeFluidOut
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Retrogressive failure 4s GPU comparison completed.
goto end

:fail
echo Execution aborted.

:end
if /i "%~1" == "-force" exit /b %ERRORLEVEL%
pause
