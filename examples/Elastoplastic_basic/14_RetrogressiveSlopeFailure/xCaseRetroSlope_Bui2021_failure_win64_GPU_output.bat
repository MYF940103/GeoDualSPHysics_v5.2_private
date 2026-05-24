@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


set name=CaseRetroSlope_Bui2021_failure
set dirout=%name%_GPU_out
set diroutdata=%dirout%\data
set initname=CaseRetroSlope_Bui2021_init
set initdir=%initname%_GPU_out\data
set partbegin=50
set partbegin4=0050

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set partvtkout="%dirbin%/PartVTKOut_win64.exe"

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



:postprocessing
set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartFluid -onlytype:-all,fluid -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+soili1,+soilj2,+soilsigmamax,+soilyieldf,+soilcoh
if not "%ERRORLEVEL%" == "0" goto fail

%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartBound -onlytype:-all,bound -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij
if not "%ERRORLEVEL%" == "0" goto fail

%partvtkout% -dirin %diroutdata% -savevtk %dirout2%/PartFluidOut -SaveResume %dirout2%/_ResumeFluidOut
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Retrogressive failure GPU stage completed.
goto end

:fail
echo Execution aborted.

:end
if /i "%~1" == "-force" exit /b %ERRORLEVEL%
pause
