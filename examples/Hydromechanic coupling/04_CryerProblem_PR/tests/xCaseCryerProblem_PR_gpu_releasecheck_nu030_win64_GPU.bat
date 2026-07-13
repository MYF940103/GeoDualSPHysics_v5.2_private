@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseCryerProblem_PR_gpu_releasecheck_nu030
set dirout=outputs\gpu_releasecheck\%case%_out
set diroutdata=%dirout%\data

set dirbin=../../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress

if exist "%dirout%" (
  if /i "%~1"=="-force" (
    rd /s /q "%dirout%"
  ) else (
    echo Output directory "%dirout%" already exists.
    choice /c YN /m "Delete it and rerun Cryer GPU release check nu030"
    if errorlevel 2 goto abort
    rd /s /q "%dirout%"
  )
)
if exist "%dirout%" goto fail

rem Cryer nu=0.3, dp=0.0025, k=1e-5 GPU release check.
%gencase% configs/gpu_releasecheck/%case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-all,fluid -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Cryer GPU release check nu030 done.
popd
exit /b 0

:abort
echo Cryer GPU release check nu030 aborted by user.
popd
exit /b 0

:fail
echo Cryer GPU release check nu030 failed.
popd
exit /b 1
