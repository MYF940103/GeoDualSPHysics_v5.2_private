@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseCryerProblem_PR_nu020
set xml=%case%
set dirout=%case%_out
set data=%dirout%\data
set particles=%dirout%\particles
set figures=%dirout%\figures

rem Formal one-stage Cryer release configuration.
rem k=1e-5 with nu020 gives Tv=1 at 1.103625 s.
rem TimeOut is Delta Tv=0.001, so the full run writes 1000 nonzero-time intervals.
set radius=0.05
set dp=0.0025
set q0=10000
set khyd=1e-5
set nu=0.2
set tmax=1.103625
set tout=0.001103625

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace

if exist "%dirout%" rd /s /q "%dirout%"
if not "%ERRORLEVEL%" == "0" goto fail
mkdir "%dirout%"
mkdir "%particles%"
mkdir "%figures%"

%gencase% %xml%_Def "%dirout%/%case%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu "%dirout%/%case%" "%dirout%" -dirdataout data -svres -svextraparts:1 -tmax:%tmax% -tout:%tout%
if not "%ERRORLEVEL%" == "0" goto fail

%partvtk% -dirin "%data%" -savevtk "%particles%/PartFluid" -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

set CRYER_PARTICLES=%particles%
set CRYER_FIGDIR=%figures%
set CRYER_OUTTAG=cryer_center_pressure_dp0025_k1e5_nu020
set CRYER_SUMMARY_JSON=%figures%\cryer_center_pressure_dp0025_k1e5_nu020_summary.json
set CRYER_RADIUS=%radius%
set CRYER_DP=%dp%
set CRYER_Q0=%q0%
set CRYER_TL=0
set CRYER_LOAD_RAMP=0
set CRYER_K_HYD=%khyd%
set CRYER_NU=%nu%
set CRYER_CENTER_SAMPLE_RADIUS=%dp%
set CRYER_TOUT=%tout%
set CRYER_TIME_MAX=%tmax%
set CRYER_TV_MIN=0.001
py support\postprocess_cryer.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Cryer problem one-stage GPU validation done.
echo Data: %data%
echo VTK: %particles%
echo Figures: %figures%
popd
exit /b 0

:fail
echo Cryer problem one-stage GPU validation aborted.
popd
exit /b 1
