@echo off
setlocal
set solverrc=
pushd "%~dp0\..\.."
set tag=upl_prestress_extended_CPU_r1
set name=CaseLianSaturatedColumnCollapse_prestress_gravity_r1
set seed=tests\outputs\upl_prestress_gravity_r1_seed\%name%
set dirout=tests\outputs\%tag%
set dirrun=tests\outputs\%tag%_runtime
set solver=tests\outputs\upl_prestress_ReleaseCPU_r1\DualSPHysics5.2CPU_win64.exe
set runtime=tests\outputs\upl_prestress_check_release_CPU_r1_runtime
set exe=DualSPHysics5.2CPU_win64.exe
rem Fresh actual gravity prestress; no GenCase, direct sigma assignment, restart or postprocessing.
if exist "%dirout%" goto fail
if exist "%dirrun%" goto fail
for %%F in (.start.json .call.json .run.json .status.json .status.tmp .log .queue_attempt.json .queue_result.json) do if exist "tests\logs\%tag%%%F" goto fail
if not exist "%solver%" goto fail
if not exist "tests\logs\upl_prestress_extended_r1.admission.json" goto fail
powershell -NoProfile -Command "$a=Get-Content -Raw -LiteralPath 'tests\logs\upl_prestress_extended_r1.admission.json'|ConvertFrom-Json;if(-not $a.passed -or $a.allowed_job -ne '%tag%'){exit 1}"
if errorlevel 1 goto fail
if not exist "%seed%.xml" goto fail
if not exist "%seed%.bi4" goto fail
if not exist "%seed%_Normals.nbi4" goto fail
for %%F in (DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll) do if not exist "%runtime%\%%F" goto fail
mkdir "%dirrun%"
if errorlevel 1 goto fail
mkdir "%dirout%"
if errorlevel 1 goto fail
copy /b "%solver%" "%dirrun%\%exe%" >nul
if errorlevel 1 goto fail
for %%F in (DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll) do (
    copy /b "%runtime%\%%F" "%dirrun%\%%F" >nul
    if errorlevel 1 goto fail
)
>"%dirout%\run_command.txt" echo "%dirrun%\%exe%" -cpu -ompthreads:8 -stable -mdbc_freeslip "%seed%" "%dirout%" -dirdataout data -svres -nsteps:2000000
"%dirrun%\%exe%" -cpu -ompthreads:8 -stable -mdbc_freeslip "%seed%" "%dirout%" -dirdataout data -svres -nsteps:2000000
set solverrc=%ERRORLEVEL%
>"%dirout%\solver_exit_code.txt" echo %solverrc%
if not "%solverrc%"=="0" goto fail
echo Solver exited0. Native clocks, safety and physical convergence remain pending review.
popd
if /i "%~1" == "-batch" exit /b 0
pause
exit /b 0
:fail
if not defined solverrc set solverrc=1
echo Preload stopped. Existing and partial outputs are retained; no retry or restart.
popd
if /i "%~1" == "-batch" exit /b %solverrc%
pause
exit /b %solverrc%
