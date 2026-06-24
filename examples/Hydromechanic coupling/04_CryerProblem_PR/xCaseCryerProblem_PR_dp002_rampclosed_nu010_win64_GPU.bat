@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseCryerProblem_PR_dp002_rampclosed_nu010
set xml=%case%
set dirout=%case%_out
set data=%dirout%\data
set particles=%dirout%\particles
set figures=%dirout%\figures

rem High-resolution Cryer release candidate with closed load ramp.
rem dp=0.002, k=1e-5, nu010; Tv=1 after ramp corresponds to 1.199 s.
rem Load is ramped for 0.0025 s with drainage closed, then drainage opens and Tv is measured from ramp end.
set radius=0.05
set dp=0.002
set q0=10000
set khyd=1e-5
set nu=0.1
set loadramp=0.0025
set tvperiod=1.199
set tmax=1.2015
set tout=0.001199

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
set CRYER_OUTTAG=cryer_center_pressure_dp002_k1e5_rampclosed_nu010
set CRYER_SUMMARY_JSON=%figures%\cryer_center_pressure_dp002_k1e5_rampclosed_nu010_summary.json
set CRYER_RADIUS=%radius%
set CRYER_DP=%dp%
set CRYER_Q0=%q0%
set CRYER_TL=%loadramp%
set CRYER_LOAD_RAMP=%loadramp%
set CRYER_K_HYD=%khyd%
set CRYER_NU=%nu%
set CRYER_CENTER_SAMPLE_RADIUS=%dp%
set CRYER_TOUT=%tout%
set CRYER_TIME_MAX=%tmax%
set CRYER_TV_MIN=0.001
py support\postprocess_cryer.py
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Cryer problem high-resolution closed-ramp GPU validation done.
echo Data: %data%
echo VTK: %particles%
echo Figures: %figures%
popd
exit /b 0

:fail
echo Cryer problem high-resolution closed-ramp GPU validation aborted.
popd
exit /b 1
