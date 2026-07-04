@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


pushd "%~dp0"

set force=0
if /i "%~1" == "-force" (
  set force=1
)

set case1=CaseSelfWeightConsolidation_Stage1
set dirout1=%case1%_out
set diroutdata1=%dirout1%\data

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+Idp,+Mk,+Vel,+Rhop,+Press,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PorePress,+PorePress0,+ExcessPorePress,+HydroMechLoadAce

:menu
if exist "%dirout1%" (
  if "%force%" == "1" goto run
  set /p option="The folder "%dirout1%" already exists. Choose an option.!NL!  [1]-Delete and continue.!NL!  [2]-Post-process.!NL!  [3]-Abort: "
  if "!option!" == "1" goto run
  if "!option!" == "2" goto postprocessing
  goto fail
)

:run
if exist "%dirout1%" rd /s /q "%dirout1%"
if not "%ERRORLEVEL%" == "0" goto fail

rem Stage 1 baseline: FreeSurface init, drainage on, Shepard interval 40, SoilDampingCoef=0.02. Time settings are read from XML.
%gencase% %case1%_Def %dirout1%/%case1% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu -mdbc %dirout1%/%case1% %dirout1% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
set vtkdir=%dirout1%\particles
%partvtk% -dirin %diroutdata1% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata1% -savevtk %vtkdir%/PartBound -onlytype:-all,bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py support\postprocess_stage1_history.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Stage 1 GPU done
popd
if "%force%" == "1" exit /b 0
pause
exit /b 0

:fail
echo Stage 1 GPU aborted.
popd
if "%force%" == "1" exit /b 1
pause
exit /b 1
