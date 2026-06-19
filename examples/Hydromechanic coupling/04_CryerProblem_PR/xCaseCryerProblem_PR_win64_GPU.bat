@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseCryerProblem_PR
set stage1xml=%case%_Stage1
set stage2xml=%case%_Stage2

set dirout=%case%_out
set stage1out=%dirout%\stage1
set stage2out=%dirout%\stage2
set stage1data=%stage1out%\data
set stage2data=%stage2out%\data

rem dp=0.003, k=1e-4 full-cycle Cryer setting retained from refinement\ud2_k1e4_full.
set stage1_tmax=0.082
set stage1_tout=0.002
set stage2_tmax=0.173101
set stage2_tout=0.0025
set stage2_duration=0.0911
set partbegin=41

set radius=0.05
set dp=0.003
set q0=10000
set khyd=1e-4

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress

if exist "%dirout%" rd /s /q "%dirout%"
if not "%ERRORLEVEL%" == "0" goto fail
mkdir "%stage1out%"
mkdir "%stage2out%"
mkdir "%dirout%\figures"

rem Stage 1: undrained spherical normal loading.
%gencase% %stage1xml%_Def "%stage1out%/%case%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu "%stage1out%/%case%" "%stage1out%" -dirdataout data -svres -svextraparts:1 -tmax:%stage1_tmax% -tout:%stage1_tout%
if not "%ERRORLEVEL%" == "0" goto fail

set stage1vtk=%stage1out%\particles
%partvtk% -dirin "%stage1data%" -savevtk "%stage1vtk%/PartFluid" -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

rem Stage 2: restart from the settled undrained state and open FreeSurface drainage.
%gencase% %stage2xml%_Def "%stage2out%/%case%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu "%stage2out%/%case%" "%stage2out%" -dirdataout data -svres -svextraparts:1 -partbegin:%partbegin%:0 "%stage1data%" -tmax:%stage2_tmax% -tout:%stage2_tout%
if not "%ERRORLEVEL%" == "0" goto fail

set stage2vtk=%stage2out%\particles
%partvtk% -dirin "%stage2data%" -savevtk "%stage2vtk%/PartFluid" -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

set CRYER_PARTICLES=%stage2vtk%
set CRYER_FIGDIR=%dirout%\figures
set CRYER_OUTTAG=cryer_center_pressure
set CRYER_SUMMARY_JSON=%dirout%\figures\cryer_center_pressure_summary.json
set CRYER_RADIUS=%radius%
set CRYER_DP=%dp%
set CRYER_Q0=%q0%
set CRYER_TL=0
set CRYER_LOAD_RAMP=0
set CRYER_K_HYD=%khyd%
set CRYER_TOUT=%stage2_tout%
set CRYER_TIME_MAX=%stage2_duration%
py support\postprocess_cryer.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Cryer problem two-stage validation done.
echo Stage 1 VTK: %stage1vtk%
echo Stage 2 VTK: %stage2vtk%
echo Figures: %dirout%\figures
popd
exit /b 0

:fail
echo Cryer problem validation aborted.
popd
exit /b 1
