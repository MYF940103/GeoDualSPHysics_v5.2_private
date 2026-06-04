@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case2=CaseSelfWeightConsolidation_Scenario1
set dirout1=CaseSelfWeightConsolidation_Stage1_out
set dirout2=%case2%_out
set diroutdata1=%dirout1%\data
set diroutdata2=%dirout2%\data
set partbegin=40
set partbeginfile=0040
set tmax2=0.60
set tout2=0.02

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+porepress,+porepress0,+excessporepress

if not exist "%diroutdata1%\Part_%partbeginfile%.bi4" goto fail
if not exist "%diroutdata1%\PartExtra_%partbeginfile%.bi4" goto fail

if exist %dirout2% rd /s /q %dirout2%
if not "%ERRORLEVEL%" == "0" goto fail

rem Scenario 1: restart from selected Stage 1 output, switch gravity off, and dissipate pore pressure.
%gencase% %case2%_Def %dirout2%/%case2% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc %dirout2%/%case2% %dirout2% -dirdataout data -svres -svextraparts:1 -partbegin:%partbegin%:%partbegin% %diroutdata1% -tmax:%tmax2% -tout:%tout2%
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout2%\particles
%partvtk% -dirin %diroutdata2% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py support\postprocess_self_weight_scenario1.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Scenario 1 done
popd
exit /b 0

:fail
echo Scenario 1 aborted.
popd
exit /b 1
