@echo off
setlocal
set solverrc=
pushd "%~dp0\..\.."
set name=CaseLianSaturatedColumnCollapse_elastic_start_r1
set seedname=CaseLianSaturatedColumnCollapse_geometry_r1
set dirseed=tests\outputs\upl_c08_elastic_start_r1_seed
set oldseed=tests\outputs\upl_c08_observer_r1_seed
set dirout=tests\outputs\upl_c08_elastic_start_CPU_r1
set dirrun=tests\outputs\upl_c08_elastic_start_CPU_r1_runtime
set dirbin=..\..\..\bin\windows
set exe=DualSPHysics5.2CPU_win64_debug.exe
set solver=tests\outputs\upl_container_DebugCPU_r1\%exe%
rem Candidate preparation and one CPU128-update run only. No GenCase or postprocessing.
if exist "%dirout%" goto fail
if exist "%dirseed%" goto fail
if exist "%dirrun%" goto fail
if not exist "%solver%" goto fail
if not exist "tests\configs\%name%.xml" goto fail
if not exist "%oldseed%\%seedname%.bi4" goto fail
if not exist "%oldseed%\%seedname%_Normals.nbi4" goto fail
for %%F in (DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll) do if not exist "%dirbin%\%%F" goto fail
if not exist "tests\outputs" mkdir "tests\outputs"
mkdir "%dirseed%"
if errorlevel 1 goto fail
mkdir "%dirrun%"
if errorlevel 1 goto fail
mkdir "%dirout%"
if errorlevel 1 goto fail
copy /b "tests\configs\%name%.xml" "%dirseed%\%name%.xml" >nul
if errorlevel 1 goto fail
copy /b "%oldseed%\%seedname%.bi4" "%dirseed%\%name%.bi4" >nul
if errorlevel 1 goto fail
copy /b "%oldseed%\%seedname%_Normals.nbi4" "%dirseed%\%name%_Normals.nbi4" >nul
if errorlevel 1 goto fail
copy /b "%solver%" "%dirrun%\%exe%" >nul
if errorlevel 1 goto fail
for %%F in (DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll) do (
    copy /b "%dirbin%\%%F" "%dirrun%\%%F" >nul
    if errorlevel 1 goto fail
)
>"%dirout%\run_command.txt" echo "%dirrun%\%exe%" -cpu -ompthreads:1 -stable -mdbc_freeslip "%dirseed%\%name%" "%dirout%" -dirdataout data -svres -nsteps:128
"%dirrun%\%exe%" -cpu -ompthreads:1 -stable -mdbc_freeslip "%dirseed%\%name%" "%dirout%" -dirdataout data -svres -nsteps:128
set solverrc=%ERRORLEVEL%
>"%dirout%\solver_exit_code.txt" echo %solverrc%
if not "%solverrc%"=="0" goto fail
echo Candidate process exited0. Native and physical review are separate pending steps.
popd
if /i "%~1" == "-batch" exit /b 0
pause
exit /b 0
:fail
if not defined solverrc set solverrc=1
echo Startup candidate stopped. Existing and partial outputs are retained.
popd
if /i "%~1" == "-batch" exit /b %solverrc%
pause
exit /b %solverrc%
