@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set force=0
if /i "%~1" == "-force" (
  set force=1
  shift
)

set partbegin=%~1
if "%partbegin%" == "" set partbegin=50
set partbegin4=0000%partbegin%
set partbegin4=%partbegin4:~-4%

set tmax=%~2
set tout=%~3

set name=CaseRetroSlope8m_u_pw_failure
set dirout=%name%_GPU_out
set diroutdata=%dirout%\data
set initname=CaseRetroSlope8m_u_pw_prestress
set initdir=%initname%_out\data

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set partvtkout="%dirbin%/PartVTKOut_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress
set runextra=
if not "%tmax%" == "" set runextra=%runextra% -tmax:%tmax%
if not "%tout%" == "" set runextra=%runextra% -tout:%tout%

if not exist "%initdir%\Part_%partbegin4%.bi4" (
  echo Required restart file "%initdir%\Part_%partbegin4%.bi4" was not found.
  echo Run the 8m coupled prestress stage first: xCaseRetroSlope8m_u_pw_prestress_win64_CPU.bat or xCaseRetroSlope8m_u_pw_prestress_win64_GPU.bat.
  goto fail
)
if not exist "%initdir%\PartExtra_%partbegin4%.bi4" (
  echo Required mDBC restart file "%initdir%\PartExtra_%partbegin4%.bi4" was not found.
  echo The prestress stage must be run with -svextraparts:1.
  goto fail
)

:menu
if exist "%dirout%" (
  if "%force%" == "1" goto run
  set /p option="The folder "%dirout%" already exists. Choose an option. [1]-Delete and continue [2]-Post-process [3]-Abort: "
  if "!option!" == "1" goto run
  if "!option!" == "2" goto postprocessing
  goto fail
)

:run
if exist "%dirout%" rd /s /q "%dirout%"
if not "%ERRORLEVEL%" == "0" goto fail

%gencase% %name%_Def "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu -mdbc_noslip:nopen "%dirout%/%name%" "%dirout%" -dirdataout data -svres -partbegin:%partbegin%:0 "%initdir%" %runextra%
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
set dirout2=%dirout%\particles
%partvtk% -dirin "%diroutdata%" -savevtk "%dirout2%/PartFluid" -onlytype:-all,fluid -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin "%diroutdata%" -savevtk "%dirout2%/PartBound" -onlytype:-all,bound -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+porepress,+porepress0
if not "%ERRORLEVEL%" == "0" goto fail
%partvtkout% -dirin "%diroutdata%" -savevtk "%dirout2%/PartFluidOut" -SaveResume "%dirout2%/_ResumeFluidOut"
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo u-pw 8m retrogressive failure GPU stage completed.
popd
if "%force%" == "1" exit /b 0
pause
exit /b 0

:fail
echo u-pw 8m retrogressive failure GPU stage aborted.
popd
if "%force%" == "1" exit /b 1
pause
exit /b 1
