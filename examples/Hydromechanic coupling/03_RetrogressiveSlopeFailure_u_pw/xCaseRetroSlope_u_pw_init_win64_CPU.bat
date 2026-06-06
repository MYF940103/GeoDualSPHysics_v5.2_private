@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set mode=%~1
if "%mode%" == "" set mode=upward
if /i "%mode%" == "upward" (
  set case=CaseRetroSlope_u_pw_init_upward
) else if /i "%mode%" == "allfs" (
  set case=CaseRetroSlope_u_pw_init_allfs
) else if /i "%mode%" == "all" (
  set case=CaseRetroSlope_u_pw_init_allfs
) else (
  echo Usage: %~nx0 [upward^|allfs] [tmax] [tout]
  popd
  exit /b 1
)

set tmax=%~2
if "%tmax%" == "" set tmax=0.2
set tout=%~3
if "%tout%" == "" set tout=0.02

set dirout=%case%_CPU_out
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+porepress,+porepress0,+excessporepress

if exist %dirout% rd /s /q %dirout%
if not "%ERRORLEVEL%" == "0" goto fail

%gencase% %case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc_noslip %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -tmax:%tmax% -tout:%tout%
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-all,fluid -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py support\analyze_retro_slope_hydrostatic.py %dirout%
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Retrogressive slope u-pw hydrostatic test done: %case%
popd
exit /b 0

:fail
echo Retrogressive slope u-pw hydrostatic test aborted: %case%
popd
exit /b 1
