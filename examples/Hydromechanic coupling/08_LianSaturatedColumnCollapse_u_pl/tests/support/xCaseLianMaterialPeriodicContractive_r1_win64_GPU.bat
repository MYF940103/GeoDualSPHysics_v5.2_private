@echo off
setlocal
set solverrc=
pushd "%~dp0\..\.."
set name=CaseLianMaterialPeriodicContractive_r1
set dirseed=tests\outputs\upl_plastic_contractive_r1_seed
set dirout=tests\outputs\upl_plastic_contractive_GPU_r1
set dirrun=tests\outputs\upl_plastic_contractive_GPU_r1_runtime
set dirbin=..\..\..\bin\windows
set exe=DualSPHysics5.2_win64_debug.exe
set solver=tests\outputs\upl_plastic_dilation_Debug_r1\%exe%
rem Prepared constant-friction cohesion-softening contractive periodic shear candidate. No GenCase or postprocessing in this BAT.
rem Root must review copied seed, explicitly derived companion, new build and native plan before this one fresh128 run.
if exist "%dirout%" goto fail
if exist "%dirrun%" goto fail
if not exist "%solver%" goto fail
if not exist "%dirseed%\%name%.xml" goto fail
if not exist "%dirseed%\%name%.bi4" goto fail
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
>"%dirout%\run_command.txt" echo "%dirrun%\%exe%" -gpu:0 -stable "%dirseed%\%name%" "%dirout%" -dirdataout data -svres -nsteps:128
"%dirrun%\%exe%" -gpu:0 -stable "%dirseed%\%name%" "%dirout%" -dirdataout data -svres -nsteps:128
set solverrc=%ERRORLEVEL%
>"%dirout%\solver_exit_code.txt" echo %solverrc%
if not "%solverrc%"=="0" goto fail
echo Candidate process exited0. All22 native fields, actual clocks and plastic response still require separate review.
popd
if /i "%~1" == "-batch" exit /b 0
pause
exit /b 0
:fail
if not defined solverrc set solverrc=1
echo Candidate stopped. Existing and partial outputs are retained; no automatic retry or next stage.
popd
if /i "%~1" == "-batch" exit /b %solverrc%
pause
exit /b %solverrc%
