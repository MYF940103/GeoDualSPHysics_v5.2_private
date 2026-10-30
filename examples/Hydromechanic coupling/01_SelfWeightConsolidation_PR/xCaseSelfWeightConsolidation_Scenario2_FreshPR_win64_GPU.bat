@echo off
setlocal
cd /d "%~dp0"

rem Fresh Windows x64/NVIDIA calculation; never delete outputs or use PART restart.
set name=CaseSelfWeightConsolidation_Scenario2_FreshPR
set dirout=%name%_out
set diroutdata=%dirout%\data
set dirbin=support/bin
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+Idp,+Mk,+Vel,+Rhop,+Press,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PorePress,+PorePress0,+ExcessPorePress,+HydroMechLoadAce
if not defined PYTHON set PYTHON=python
if /i "%~1"=="-postprocess" goto postprocess
if /i "%~1"=="-post" goto postprocess
if not "%~1"=="" if /i not "%~1"=="-solver-only" goto usage
if exist "%dirout%" goto exists
if not exist "%name%_Def.xml" goto fail
if not exist "%dirbin%/GenCase_win64.exe" goto fail
if not exist "%dirbin%/DualSPHysics5.2_GEO_win64.exe" goto fail
%gencase% "%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%"=="0" goto fail

rem Finite-Kw Tv=2 target; cap gives actual end 7.316858768463135 s.
%dualsphysicsgpu% -gpu -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:20459420
if not "%ERRORLEVEL%"=="0" goto fail
if /i "%~1"=="-solver-only" exit /b 0

:postprocess
rem This mode never invokes GenCase or the physical solver.
if not exist "%diroutdata%/Part_0402.bi4" goto fail
if not exist "%dirbin%/PartVTK_win64.exe" goto fail
if not exist "%dirbin%/ReadSelfWeightNative.exe" goto fail
if not exist "support/postprocess_selfweight_freshpr_r1.py" goto fail
if exist "%dirout%/particles" goto particles_exist
mkdir "%dirout%/particles"
%partvtk% -dirin "%diroutdata%" -savevtk "%dirout%/particles/PartFluid" -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%"=="0" goto fail
%partvtk% -dirin "%diroutdata%" -savevtk "%dirout%/particles/PartBound" -onlytype:-all,bound -vars:%vars%
if not "%ERRORLEVEL%"=="0" goto fail
set legacy=
if exist "tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/data/Part_0000.bi4" set legacy=--legacy-dir "tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out"
if not defined legacy echo Historical comparison pending: old raw data are not present in this package.
"%PYTHON%" "support/postprocess_selfweight_freshpr_r1.py" --config "%name%_Def.xml" --data-dir "%diroutdata%" --figures-dir figures --label "%name%" --reader "%dirbin%/ReadSelfWeightNative.exe" %legacy%
if not "%ERRORLEVEL%"=="0" goto fail
echo Completed calculation and derived particles/figures/CSV. Normal exit is not physical acceptance.
if "%~1"=="" pause
exit /b 0

:particles_exist
echo Existing particles preserved. Run the standalone postprocessor directly to repair only new analysis.
goto fail
:exists
echo Output already exists: %dirout%. Nothing was overwritten, restarted or deleted.
goto fail
:usage
echo Usage: double-click for full calculation and postprocessing; -solver-only; -postprocess.
goto fail
:fail
echo Aborted. Preserve complete and partial outputs; do not rerun the solver blindly.
if "%~1"=="" pause
exit /b 1
