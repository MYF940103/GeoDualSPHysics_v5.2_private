@echo off
setlocal
pushd "%~dp0" || exit /b 1
set "case=CaseCryerProblem_u_pl_nu030"
set "out=%case%_GPU_out"
set "bin=..\..\..\bin\windows"
set "steps=963370"
if /i "%~1"=="--smoke" (
  set "out=tests\outputs\cryer_upl_public_six_gpu"
  set "steps=6"
) else if not "%~1"=="" (
  echo Usage: %~nx0 [--smoke]
  goto fail
)
if exist "%out%" (
  echo Output directory already exists: "%out%"
  goto fail
)
mkdir "%out%" || goto fail
"%bin%\GenCase_win64.exe" "%case%_Def" "%out%\%case%" -save:all || goto fail
"%bin%\DualSPHysics5.2_GEO_win64.exe" -gpu -stable "%out%\%case%" "%out%" -dirdataout data -svres -nsteps:%steps% || goto fail
if /i "%~1"=="--smoke" goto done
"%bin%\PartVTK_win64.exe" -dirin "%out%\data" -savevtk "%out%\particles\PartFluid" -onlytype:-all,fluid -vars:+idp,+vel,+porepress || goto fail
:done
popd
exit /b 0
:fail
popd
exit /b 1
