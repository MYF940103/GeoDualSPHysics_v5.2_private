@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseTCq0_res_k1em4_dp0025_fix_Tv01
set def=configs\resolution\%case%_Def
set dirout=outputs\resolution\%case%_out
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
    choice /c YN /m "Delete it and rerun corrected dp=0.025 Tv0.1 resolution test"
    if errorlevel 2 goto abort
    rd /s /q "%dirout%"
  )
)
if exist "%dirout%" goto fail

rem Corrected q0 Terzaghi resolution check, k=1e-4, dp=0.025, Tv=0.1.
%gencase% %def% %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -ompthreads:20 -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo corrected q0 Terzaghi dp=0.025 Tv0.1 resolution test done.
popd
exit /b 0

:abort
echo corrected q0 Terzaghi dp=0.025 Tv0.1 resolution test aborted by user.
popd
exit /b 0

:fail
echo corrected q0 Terzaghi dp=0.025 Tv0.1 resolution test failed.
popd
exit /b 1
