@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


pushd "%~dp0"

set force=0
if /i "%~1" == "-force" (
  set force=1
)

set case1=CaseSWSt1_HeadN
set xml1=configs\%case1%_Def
set dirout1=outputs\%case1%_PairwiseOpt_GPU_out
set diroutdata1=%dirout1%\data
set particles1=%dirout1%\particles
set figures1=figures\%case1%_PairwiseOpt

set dirbin=../../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+Idp,+Mk,+Vel,+Rhop,+Press,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PorePress,+PorePress0,+ExcessPorePress,+HydroMechLoadAce

:menu
if exist "%dirout1%" (
  if "%force%" == "1" goto run
  set /p option="The folder "%dirout1%" already exists. Choose an option.!NL!  [1]-Delete and continue.!NL!  [2]-Post-process.!NL!  [3]-Abort: "
  if "!option!" == "1" goto run
  if "!option!" == "2" goto postprocessing
  goto fail
)

:run
if exist "%dirout1%" rd /s /q "%dirout1%"
if not "%ERRORLEVEL%" == "0" goto fail
if exist "%figures1%" rd /s /q "%figures1%"
if not "%ERRORLEVEL%" == "0" goto fail

%gencase% %xml1% %dirout1%/%case1% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu %dirout1%/%case1% %dirout1% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
if not exist "%particles1%" mkdir "%particles1%"
%partvtk% -dirin %diroutdata1% -savevtk %particles1%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata1% -savevtk %particles1%/PartBound -onlytype:-all,bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py -3 support\postprocess_stage1_test.py --particles "%particles1%" --xml "configs\%case1%_Def.xml" --figdir "%figures1%" --case "%case1%"
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo %case1% PairwiseOpt GPU done.
echo Output: %dirout1%
echo Figures: %figures1%
popd
if "%force%" == "1" exit /b 0
pause
exit /b 0

:fail
echo %case1% PairwiseOpt GPU aborted.
popd
if "%force%" == "1" exit /b 1
pause
exit /b 1
