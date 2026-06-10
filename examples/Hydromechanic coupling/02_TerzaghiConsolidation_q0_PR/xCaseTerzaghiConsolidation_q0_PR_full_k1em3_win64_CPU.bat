@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseTerzaghiConsolidation_q0_PR_full_k1em3
set dirout=%case%_out
set diroutdata=%dirout%\data
set tmax=3.66193285714285
set tout=0.0182185714285714

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+porepress,+porepress0,+excessporepress

if exist "%dirout%" (
  if /i "%~1"=="-force" (
    rd /s /q "%dirout%"
  ) else (
    echo Output directory "%dirout%" already exists.
    choice /c YN /m "Delete it and rerun k=1e-3 full validation"
    if errorlevel 2 goto abort
    rd /s /q "%dirout%"
  )
  if exist "%dirout%" goto fail
)

rem q0 Terzaghi consolidation full validation, k=1e-3 m/s.
%gencase% %case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -ompthreads:4 -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -tmax:%tmax% -tout:%tout%
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo q0 Terzaghi consolidation k=1e-3 full validation done.
popd
exit /b 0

:abort
echo q0 Terzaghi consolidation k=1e-3 full validation aborted by user.
popd
exit /b 0

:fail
echo q0 Terzaghi consolidation k=1e-3 full validation aborted.
popd
exit /b 1
