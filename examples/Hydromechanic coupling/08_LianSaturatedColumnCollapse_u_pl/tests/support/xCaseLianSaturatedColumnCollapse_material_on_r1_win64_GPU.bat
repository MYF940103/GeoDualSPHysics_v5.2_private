@echo off
setlocal
set solverrc=
pushd "%~dp0\..\.."
set name=CaseLianSaturatedColumnCollapse_material_on_r1
set seedname=CaseLianSaturatedColumnCollapse_geometry_r1
set dirseed=tests\outputs\upl_material_on_r1_seed
set oldseed=tests\outputs\upl_c08_observer_r1_seed
set oldout=tests\outputs\upl_material_default_GPU_r1
set dirout=tests\outputs\upl_material_on_GPU_r1
set dirrun=tests\outputs\upl_material_on_GPU_r1_runtime
set dirbin=..\..\..\bin\windows
set exe=DualSPHysics5.2_win64_debug.exe
set solver=tests\outputs\upl_material_Debug_r1\%exe%
rem Explicit material selector1/decay0 only; one same-input GPU128 startup. No GenCase or postprocessing.
rem Root must first review completed default GPU native checks and separately admit this stage.
if exist "%dirout%" goto fail
if exist "%dirseed%" goto fail
if exist "%dirrun%" goto fail
if not exist "%solver%" goto fail
if not exist "tests\configs\%name%.xml" goto fail
if not exist "%oldseed%\%seedname%.bi4" goto fail
if not exist "%oldseed%\%seedname%_Normals.nbi4" goto fail
if not exist "%oldout%\solver_exit_code.txt" goto oldfail
set oldrc=
set /p oldrc=<"%oldout%\solver_exit_code.txt"
if not "%oldrc%"=="0" goto oldfail
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
>"%dirout%\run_command.txt" echo "%dirrun%\%exe%" -gpu:0 -stable -mdbc_freeslip "%dirseed%\%name%" "%dirout%" -dirdataout data -svres -nsteps:128
"%dirrun%\%exe%" -gpu:0 -stable -mdbc_freeslip "%dirseed%\%name%" "%dirout%" -dirdataout data -svres -nsteps:128
set solverrc=%ERRORLEVEL%
>"%dirout%\solver_exit_code.txt" echo %solverrc%
if not "%solverrc%"=="0" goto fail
echo Candidate process exited0. Native and physical review are separate pending steps.
popd
if /i "%~1" == "-batch" exit /b 0
pause
exit /b 0
:oldfail
echo Retained default-material GPU128 stage has no exit0 record. SelectorON startup remains held.
goto fail
:fail
if not defined solverrc set solverrc=1
echo Startup candidate stopped. Existing and partial outputs are retained.
popd
if /i "%~1" == "-batch" exit /b %solverrc%
pause
exit /b %solverrc%
