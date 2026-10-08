@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=Case_r010_drain0_full
set xml=%case%

set dirout=out
set data=%dirout%\data
set particles=%dirout%\particles
set analysis=analysis

set tmax=0.1011
set tout=0.0025

set radius=0.05
set dp=0.003
set q0=10000
set khyd=1e-4
set ramp=0.01

set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%\DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%\PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace

if exist "%dirout%" rd /s /q "%dirout%"
if not "%ERRORLEVEL%" == "0" goto fail
if exist "%analysis%" rd /s /q "%analysis%"
if not "%ERRORLEVEL%" == "0" goto fail
mkdir "%dirout%"
mkdir "%analysis%"

%gencase% %xml%_Def "%dirout%\%case%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu "%dirout%\%case%" "%dirout%" -dirdataout data -svres -svextraparts:1 -tmax:%tmax% -tout:%tout%
if not "%ERRORLEVEL%" == "0" goto fail

mkdir "%particles%"
%partvtk% -dirin "%data%" -savevtk "%particles%\PartFluid" -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

set CRYER_PARTICLES=%particles%
set CRYER_RUNOUT=%dirout%\Run.out
set CRYER_FIGDIR=%analysis%
set CRYER_OUTTAG=r010_drain0_full
set CRYER_SUMMARY_JSON=%analysis%\r010_drain0_full_summary.json
set CRYER_RADIUS=%radius%
set CRYER_DP=%dp%
set CRYER_Q0=%q0%
set CRYER_RAMP=%ramp%
set CRYER_K_HYD=%khyd%
py -3 analyze_r010_drain0_full.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo r010 drain-from-start full-cycle validation done.
echo VTK: %particles%
echo Analysis: %analysis%
popd
exit /b 0

:fail
echo r010 drain-from-start full-cycle validation aborted.
popd
exit /b 1
