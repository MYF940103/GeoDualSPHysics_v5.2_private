@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


pushd "%~dp0"

set force=0
if /i "%~1" == "-force" (
  set force=1
)

set partbegin=60
set partbegin4=0000%partbegin%
set partbegin4=%partbegin4:~-4%

set case2=CaseSelfWeightConsolidation_Scenario2
set dirout2=%case2%_out
set diroutdata2=%dirout2%\data
set initcase=CaseSelfWeightConsolidation_Stage1
set initdir=%initcase%_out\data

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+Idp,+Mk,+Vel,+Rhop,+Press,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PorePress,+PorePress0,+ExcessPorePress,+HydroMechLoadAce

if not exist "%initdir%\Part_%partbegin4%.bi4" (
  echo Required restart file "%initdir%\Part_%partbegin4%.bi4" was not found.
  echo Run xCaseSelfWeightConsolidation_Stage1_win64_GPU.bat first.
  goto fail
)
if not exist "%initdir%\PartExtra_%partbegin4%.bi4" (
  echo Required mDBC restart file "%initdir%\PartExtra_%partbegin4%.bi4" was not found.
  echo Stage 1 must be run with -svextraparts:1.
  goto fail
)

:menu
if exist "%dirout2%" (
  if "%force%" == "1" goto run
  set /p option="The folder "%dirout2%" already exists. Choose an option.!NL!  [1]-Delete and continue.!NL!  [2]-Post-process.!NL!  [3]-Abort: "
  if "!option!" == "1" goto run
  if "!option!" == "2" goto postprocessing
  goto fail
)

:run
if exist "%dirout2%" rd /s /q "%dirout2%"
if not "%ERRORLEVEL%" == "0" goto fail

rem Scenario 2: inherit Stage 1 Part_%partbegin4% pore pressure and effective stress. Time settings are read from XML.
%gencase% %case2%_Def %dirout2%/%case2% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu -mdbc %dirout2%/%case2% %dirout2% -dirdataout data -svres -svextraparts:1 -partbegin:%partbegin%:0 "%initdir%"
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
set vtkdir=%dirout2%\particles
%partvtk% -dirin %diroutdata2% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata2% -savevtk %vtkdir%/PartBound -onlytype:-all,bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py support\postprocess_self_weight_consolidation.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Scenario 2 GPU done
popd
if "%force%" == "1" exit /b 0
pause
exit /b 0

:fail
echo Scenario 2 GPU aborted.
popd
if "%force%" == "1" exit /b 1
pause
exit /b 1
