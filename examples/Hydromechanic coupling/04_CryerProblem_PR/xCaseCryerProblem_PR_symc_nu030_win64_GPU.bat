@echo off
setlocal
cd /d "%~dp0"

rem Portable Windows x64 / RTX A6000 fresh calculation. Never delete retained data.
set name=CaseCryerProblem_PR_symc_nu030
set dirout=%name%_out
set dirbin=support/bin
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set runopts=
set unattended=0

:arguments
if "%~1" == "" goto run
if "%~1" == "--unattended" (
    set unattended=1
    shift
    goto arguments
)
if "%~1" == "--smoke" (
    set dirout=%name%_smoke_out
    set runopts=-tmax:0.0001220703125
    shift
    goto arguments
)
echo Unknown argument: %~1
goto fail

:run
if exist "%dirout%" goto exists
if not exist "%dirbin%/GenCase_win64.exe" goto fail
if not exist "%dirbin%/DualSPHysics5.2_GEO_win64.exe" goto fail
%gencase% "%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

rem Default:1926740 steps through drainage-relative legacy Tv=1. Smoke:256 steps only.
%dualsphysicsgpu% -gpu -stable %runopts% "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

echo Calculation finished. Preserve and copy the ENTIRE %dirout% folder for analysis.
echo A normal exit or smoke completion is not full-cycle theory acceptance.
if "%unattended%" == "0" pause
exit /b 0

:exists
echo Output already exists: %dirout%. Nothing was overwritten or restarted.
if "%unattended%" == "0" pause
exit /b 1

:fail
echo Execution aborted. Existing and partial outputs are preserved.
if "%unattended%" == "0" pause
exit /b 1
