@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case1=CaseSelfWeightConsolidation_Stage1
set dirout1=%case1%_out
set diroutdata1=%dirout1%\data
set tmax1=0.20
set tout1=0.005

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+porepress,+porepress0,+excessporepress

if exist %dirout1% rd /s /q %dirout1%
if not "%ERRORLEVEL%" == "0" goto fail

rem Stage 1: k=0 undrained self-weight response. Edit Stage1 XML and tmax1/tout1 here for prestress studies.
%gencase% %case1%_Def %dirout1%/%case1% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc %dirout1%/%case1% %dirout1% -dirdataout data -svres -svextraparts:1 -tmax:%tmax1% -tout:%tout1%
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout1%\particles
%partvtk% -dirin %diroutdata1% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata1% -savevtk %vtkdir%/PartBound -onlytype:+bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py support\postprocess_stage1_history.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Stage 1 done
popd
exit /b 0

:fail
echo Stage 1 aborted.
popd
exit /b 1
