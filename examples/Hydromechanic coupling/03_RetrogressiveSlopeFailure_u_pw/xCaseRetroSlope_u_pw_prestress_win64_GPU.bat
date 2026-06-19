@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set force=0
if /i "%~1" == "-force" (
  set force=1
  shift
)

set tmax=%~1
set tout=%~2

set name=CaseRetroSlope_u_pw_prestress
set dirout=%name%_out
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress
set runextra=
if not "%tmax%" == "" set runextra=%runextra% -tmax:%tmax%
if not "%tout%" == "" set runextra=%runextra% -tout:%tout%

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

%dualsphysicsgpu% -gpu -mdbc_noslip:nopen "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 %runextra%
if not "%ERRORLEVEL%" == "0" goto fail

:postprocessing
set dirout2=%dirout%\particles
%partvtk% -dirin "%diroutdata%" -savevtk "%dirout2%/PartFluid" -onlytype:-all,fluid -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin "%diroutdata%" -savevtk "%dirout2%/PartBound" -onlytype:-all,bound -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+porepress,+porepress0
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo u-pw coupled prestress GPU stage completed.
echo Default restart PART for failure stage: %diroutdata%\Part_0050.bi4
popd
if "%force%" == "1" exit /b 0
pause
exit /b 0

:fail
echo u-pw coupled prestress GPU stage aborted.
popd
if "%force%" == "1" exit /b 1
pause
exit /b 1
