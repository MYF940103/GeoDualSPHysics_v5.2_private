@echo off
setlocal EnableDelayedExpansion
rem Don't remove the two jump line after than the next line [set NL=^]
set NL=^


pushd "%~dp0"

set partbegin=40
set force=0
if /i "%~1" == "-force" (
  set force=1
) else (
  if not "%~1" == "" set partbegin=%~1
)
if /i "%~2" == "-force" (
  set force=1
)

set partbegin4=0000%partbegin%
set partbegin4=%partbegin4:~-4%

set case2=CaseSWSc2_MLSDirect_Tv2
set xml2=configs\%case2%_Def
set dirout2=outputs\%case2%_from_p%partbegin4%_GPU_out
set diroutdata2=%dirout2%\data
set particles2=%dirout2%\particles
set figures2=figures\%case2%_from_p%partbegin4%

set initcase=CaseSWSt1_MLSDirect
set initdir=outputs\%initcase%_GPU_out\data

set dirbin=../../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+Idp,+Mk,+Vel,+Rhop,+Press,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PorePress,+PorePress0,+ExcessPorePress,+HydroMechLoadAce

if not exist "%initdir%\Part_%partbegin4%.bi4" (
  echo Required restart file "%initdir%\Part_%partbegin4%.bi4" was not found.
  echo Run xCaseSWSt1_MLSDirect_win64_GPU.bat first, then choose an available Part.
  goto fail
)
if not exist "%initdir%\PartExtra_%partbegin4%.bi4" (
  echo Required mDBC restart file "%initdir%\PartExtra_%partbegin4%.bi4" was not found.
  echo Stage 1 must be run with -svextraparts:1.
  goto fail
)

:menu
if exist "%dirout2%" (
  if "%force%" == "1" goto run
  set /p option="The folder "%dirout2%" already exists. Choose an option.!NL!  [1]-Delete and continue.!NL!  [2]-Post-process.!NL!  [3]-Abort: "
  if "!option!" == "1" goto run
  if "!option!" == "2" goto postprocessing
  goto fail
)

:run
if exist "%dirout2%" rd /s /q "%dirout2%"
if not "%ERRORLEVEL%" == "0" goto fail
if exist "%figures2%" rd /s /q "%figures2%"
if not "%ERRORLEVEL%" == "0" goto fail

%gencase% %xml2% %dirout2%/%case2% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu %dirout2%/%case2% %dirout2% -dirdataout data -svres -svextraparts:1 -partbegin:%partbegin%:0 "%initdir%"
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
if not exist "%particles2%" mkdir "%particles2%"
%partvtk% -dirin %diroutdata2% -savevtk %particles2%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata2% -savevtk %particles2%/PartBound -onlytype:-all,bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py -3 support\postprocess_scenario2_restart.py --particles "%particles2%" --xml "configs\%case2%_Def.xml" --figdir "%figures2%" --case "%case2%" --restart-label "restart from %initcase% Part_%partbegin4%"
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo %case2% GPU done.
echo Restart: %initcase% Part_%partbegin4%
echo Output: %dirout2%
echo Figures: %figures2%
popd
if "%force%" == "1" exit /b 0
pause
exit /b 0

:fail
echo %case2% GPU aborted.
popd
if "%force%" == "1" exit /b 1
pause
exit /b 1
