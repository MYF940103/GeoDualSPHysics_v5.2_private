@echo off
setlocal
cd /d "%~dp0"
set "result=1"
set "unattended=0"
set "name=CaseCryerProblem_u_pl_nu030_r1"
set "out=%name%_GPU_out"
set "seed=support\upl_seed_nu030_r1\%name%"
set "solver=support\bin_upl_r1\DualSPHysics5.2_GEO_win64.exe"

rem One fresh validation candidate. No GenCase, overwrite, restart or follow-up.
:arguments
if "%~1" == "" goto preflight
if /i "%~1" == "--unattended" (
    set "unattended=1"
    shift
    goto arguments
)
echo Unknown argument: %~1
goto end

:preflight
if exist "%out%" (
    echo Output "%out%" already exists. Retain it; no run was started.
    goto end
)
if not exist "%seed%.xml" goto missing
if not exist "%seed%.bi4" goto missing
if not exist "%solver%" goto missing
mkdir "%out%"
if errorlevel 1 goto fail
copy /b "%seed%.xml" "%out%\%name%.xml" >nul
if errorlevel 1 goto fail
copy /b "%seed%.bi4" "%out%\%name%.bi4" >nul
if errorlevel 1 goto fail

> "%out%\run_command.txt" echo "%solver%" -gpu -stable "%out%\%name%" "%out%" -dirdataout data -svres -nsteps:963370
"%solver%" -gpu -stable "%out%\%name%" "%out%" -dirdataout data -svres -nsteps:963370
set "result=%ERRORLEVEL%"
> "%out%\solver_exit_code.txt" echo %result%
if "%result%" == "0" echo Solver exited zero. Native and physical review remain pending.
if not "%result%" == "0" echo Solver failed or was interrupted. Keep the complete partial output.
goto end

:missing
echo Required seed XML, seed BI4 or packaged GPU program is missing. No run was started.
goto end

:fail
echo Input preparation failed. Existing and partial outputs were retained.

:end
if "%unattended%" == "0" pause
exit /b %result%
