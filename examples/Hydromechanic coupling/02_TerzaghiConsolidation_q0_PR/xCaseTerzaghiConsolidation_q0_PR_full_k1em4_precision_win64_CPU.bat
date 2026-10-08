@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision
set dirout=%case%_out
set diroutdata=%dirout%\data
set baseline=CaseTerzaghiConsolidation_q0_PR_full_k1em4_out
set nopause=0
set postonly=0
for %%A in (%*) do (
  if /i "%%~A"=="-nopause" set nopause=1
  if /i "%%~A"=="-postprocess" set postonly=1
)

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress
set postprocess=support\compare_precision_q0.py

if not exist %gencase% goto missing
if not exist %dualsphysicscpu% goto missing
if not exist %partvtk% goto missing
if not exist "%postprocess%" goto missing
if not exist "%baseline%\Run.out" goto missing
py -3 -c "import numpy, matplotlib" >nul 2>&1
if not "%ERRORLEVEL%" == "0" (
  echo Python 3 with numpy and matplotlib is required. Check: py -3 -m pip show numpy matplotlib
  goto fail
)

if "%postonly%"=="1" goto postprocessing
if exist "%dirout%" (
  echo Output directory "%dirout%" already exists. All existing results are kept.
  echo Use this BAT with -postprocess to regenerate the precision comparison figures.
  goto fail
)

rem q0 Terzaghi consolidation, k=1e-4 m/s, compensated pore pressure, full Tv=2.
rem Uses the CPU Release with the retained precision patch; no new XML model switch.
%gencase% %case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -ompthreads:4 -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
if not exist "%diroutdata%\Part_Head.ibi4" goto missing
findstr /c:"Finished execution (code=0)." "%dirout%\Run.out" >nul
if not "%ERRORLEVEL%" == "0" (
  echo A successfully completed full run is required for final postprocessing.
  goto fail
)

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py -3 "%postprocess%" --baseline "%baseline%" --current "%dirout%" --output-prefix precision_q0_k1em4
if not "%ERRORLEVEL%" == "0" goto fail
goto success

:missing
echo A required executable, Python script, or case data file is missing.
goto fail

:success
echo q0 Terzaghi consolidation precision validation completed. See figures\precision_q0_k1em4*.
set result=0
goto end

:fail
echo q0 Terzaghi consolidation precision validation stopped. Existing results are preserved.
set result=1

:end
if "%nopause%"=="0" pause
popd
exit /b %result%
