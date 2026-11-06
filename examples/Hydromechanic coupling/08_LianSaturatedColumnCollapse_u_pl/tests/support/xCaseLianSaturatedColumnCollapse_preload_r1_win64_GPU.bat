@echo off
setlocal
set solverrc=
pushd "%~dp0\..\.."
set name=CaseLianSaturatedColumnCollapse_preload_r1
set dirseed=tests\outputs\upl_material_preload_r1_seed
set dirout=tests\outputs\upl_material_preload_GPU_r1
set dirrun=tests\outputs\upl_material_preload_GPU_r1_runtime
set dirbin=..\..\..\bin\windows
set exe=DualSPHysics5.2_win64_debug.exe
set solver=tests\outputs\upl_material_gravity_Debug_r1\%exe%
rem One fresh GPU8192 preload observation, using the retained geometry and verified gravity program.
rem No GenCase, restart, postprocessing, repeated short control or automatic follow-up in this BAT.
if exist "%dirout%" goto fail
if exist "%dirrun%" goto fail
if not exist "%solver%" goto fail
if not exist "%dirseed%\%name%.xml" goto fail
if not exist "%dirseed%\%name%.bi4" goto fail
if not exist "%dirseed%\%name%_Normals.nbi4" goto fail
for %%F in (DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll) do if not exist "%dirbin%\%%F" goto fail
mkdir "%dirrun%"
if errorlevel 1 goto fail
mkdir "%dirout%"
if errorlevel 1 goto fail
copy /b "%solver%" "%dirrun%\%exe%" >nul
if errorlevel 1 goto fail
for %%F in (DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll) do (
    copy /b "%dirbin%\%%F" "%dirrun%\%%F" >nul
    if errorlevel 1 goto fail
)
>"%dirout%\run_command.txt" echo "%dirrun%\%exe%" -gpu:0 -stable -mdbc_freeslip "%dirseed%\%name%" "%dirout%" -dirdataout data -svres -nsteps:8192
"%dirrun%\%exe%" -gpu:0 -stable -mdbc_freeslip "%dirseed%\%name%" "%dirout%" -dirdataout data -svres -nsteps:8192
set solverrc=%ERRORLEVEL%
>"%dirout%\solver_exit_code.txt" echo %solverrc%
if not "%solverrc%"=="0" goto fail
echo Preload process exited0. Native safety and physical review remain separate.
popd
if /i "%~1" == "-batch" exit /b 0
pause
exit /b 0
:fail
if not defined solverrc set solverrc=1
echo Preload stopped or an output already exists. Existing evidence is retained.
popd
if /i "%~1" == "-batch" exit /b %solverrc%
pause
exit /b %solverrc%
