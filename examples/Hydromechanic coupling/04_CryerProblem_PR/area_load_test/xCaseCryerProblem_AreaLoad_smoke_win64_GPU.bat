@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseCryerProblem_AreaLoad
set stage1xml=%case%_Stage1
set stage2xml=%case%Smoke_Stage2

set dirout=out_smoke
set figdir=analysis_smoke
set stage1out=%dirout%\stage1
set stage2out=%dirout%\stage2
set stage1data=%stage1out%\data
set stage2data=%stage2out%\data

rem Short smoke test for the area-normalized SphereNormal load.
set stage1_tmax=0.006
set stage1_tout=0.002
set stage2_tmax=0.006
set stage2_tout=0.001
set stage2_duration=%stage2_tmax%
set partbegin=3

set radius=0.05
set dp=0.003
set q0=10000
set khyd=1e-4

set dirbin=../../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+hydromechloadace,+porepress,+porepress0,+excessporepress

if exist "%dirout%" rd /s /q "%dirout%"
if not "%ERRORLEVEL%" == "0" goto fail
mkdir "%stage1out%"
mkdir "%stage2out%"
if not exist "%figdir%" mkdir "%figdir%"
del /q "%figdir%\area_load_smoke_center_pressure.*" 2>nul

%gencase% %stage1xml%_Def "%stage1out%/%case%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu "%stage1out%/%case%" "%stage1out%" -dirdataout data -svres -svextraparts:1 -tmax:%stage1_tmax% -tout:%stage1_tout%
if not "%ERRORLEVEL%" == "0" goto fail

set stage1vtk=%stage1out%\particles
%partvtk% -dirin "%stage1data%" -savevtk "%stage1vtk%/PartFluid" -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

%gencase% %stage2xml%_Def "%stage2out%/%case%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu "%stage2out%/%case%" "%stage2out%" -dirdataout data -svres -svextraparts:1 -partbegin:%partbegin%:0 "%stage1data%" -tmax:%stage2_tmax% -tout:%stage2_tout%
if not "%ERRORLEVEL%" == "0" goto fail

set stage2vtk=%stage2out%\particles
%partvtk% -dirin "%stage2data%" -savevtk "%stage2vtk%/PartFluid" -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

set CRYER_PARTICLES=%stage2vtk%
set CRYER_FIGDIR=%figdir%
set CRYER_OUTTAG=area_load_smoke_center_pressure
set CRYER_SUMMARY_JSON=%figdir%\area_load_smoke_center_pressure_summary.json
set CRYER_RADIUS=%radius%
set CRYER_DP=%dp%
set CRYER_Q0=%q0%
set CRYER_TL=0
set CRYER_LOAD_RAMP=0
set CRYER_K_HYD=%khyd%
set CRYER_TOUT=%stage2_tout%
set CRYER_TIME_MAX=%stage2_duration%
py ..\support\postprocess_cryer.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Cryer area-load smoke test done.
echo Stage 1 VTK: %stage1vtk%
echo Stage 2 VTK: %stage2vtk%
echo Analysis: %figdir%
popd
exit /b 0

:fail
echo Cryer area-load smoke test aborted.
popd
exit /b 1
