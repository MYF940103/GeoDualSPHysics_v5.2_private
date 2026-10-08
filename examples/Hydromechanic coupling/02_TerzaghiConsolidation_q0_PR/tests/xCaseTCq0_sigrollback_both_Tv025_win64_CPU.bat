@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseTCq0_sigrollback_both_Tv025
set dirout=outputs\gpu_validation\%case%_cpu_out
set diroutdata=%dirout%\data

set dirbin=../../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress

if exist "%dirout%" (
  if /i "%~1"=="-force" (
    rd /s /q "%dirout%"
  ) else (
    echo Output directory "%dirout%" already exists.
    choice /c YN /m "Delete it and rerun CPU boundary sigma rollback Tv0.25 validation"
    if errorlevel 2 goto abort
    rd /s /q "%dirout%"
  )
)
if exist "%dirout%" goto fail

rem q0 Terzaghi consolidation CPU validation, k=1e-4 m/s, Tv=0.25, matched boundary sigma rollback diagnostic.
%gencase% configs/gpu_validation/%case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo q0 Terzaghi consolidation k=1e-4 CPU boundary sigma rollback Tv0.25 validation done.
popd
exit /b 0

:abort
echo q0 Terzaghi consolidation k=1e-4 CPU boundary sigma rollback Tv0.25 validation aborted by user.
popd
exit /b 0

:fail
echo q0 Terzaghi consolidation k=1e-4 CPU boundary sigma rollback Tv0.25 validation failed.
popd
exit /b 1
