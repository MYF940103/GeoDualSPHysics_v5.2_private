@echo off
setlocal
set solverrc=
pushd "%~dp0\..\.."
set name=CaseLianSaturatedColumnCollapse_free_seepage_start_r1
set dirseed=tests\outputs\upl_c08_free_seepage_start_r1_seed
set cpuout=tests\outputs\upl_c08_free_seepage_start_CPU_r1
set dirout=tests\outputs\upl_c08_free_seepage_start_GPU_r1
set dirrun=tests\outputs\upl_c08_free_seepage_start_GPU_r1_runtime
set dirbin=..\..\..\bin\windows
set exe=DualSPHysics5.2_win64_debug.exe
set solver=tests\outputs\upl_free_seepage_Debug_r1\%exe%
rem Same CPU-prepared free-seepage seed with DtMin=1e-8; one ordinary Debug GPU128 run, no GenCase or postprocessing.
rem Root must review the CPU native/safety checks before GPU admission. Exit0 alone is not acceptance.
if exist "%dirout%" goto fail
if exist "%dirrun%" goto fail
if not exist "%solver%" goto fail
if not exist "%dirseed%\%name%.xml" goto missingseed
if not exist "%dirseed%\%name%.bi4" goto missingseed
if not exist "%dirseed%\%name%_Normals.nbi4" goto missingseed
if not exist "%cpuout%\solver_exit_code.txt" goto cpufail
set cpurc=
set /p cpurc=<"%cpuout%\solver_exit_code.txt"
if not "%cpurc%"=="0" goto cpufail
for %%F in (DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll) do if not exist "%dirbin%\%%F" goto fail
if not exist "tests\outputs" mkdir "tests\outputs"
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
:missingseed
echo CPU-prepared seed is missing. Prepare and review the CPU128 free-seepage r1 stage first.
echo This GPU BAT never regenerates geometry or copies input BI4/normals.
goto fail
:cpufail
echo CPU128 free-seepage r1 startup has no retained exit0 record. GPU startup remains held.
goto fail
:fail
if not defined solverrc set solverrc=1
echo Startup candidate stopped. Existing and partial outputs are retained.
popd
if /i "%~1" == "-batch" exit /b %solverrc%
pause
exit /b %solverrc%
