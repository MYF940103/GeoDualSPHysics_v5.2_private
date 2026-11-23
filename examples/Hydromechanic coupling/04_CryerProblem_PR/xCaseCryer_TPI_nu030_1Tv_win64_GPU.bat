@echo off
setlocal
pushd "%~dp0" || exit /b 1
set "case=CaseCryer_TPI_nu030_1Tv"
set "bin=%~dp0bin"
if not exist "%bin%\GenCase_win64.exe" set "bin=%~dp0..\..\..\bin\windows"
set "out=%case%_GPU_out"
set "steps=481685"
if not "%~2"=="" goto usage
if /i "%~1"=="--smoke" (
  set "out=tests\outputs\cryer_tpi_1tv_smoke_gpu"
  set "steps=2"
) else if not "%~1"=="" goto usage
if exist "%out%" (
  echo Output already exists. Preserving "%out%".
  goto fail
)
for %%P in (GenCase_win64.exe DualSPHysics5.2_GEO_win64.exe PartVTK_win64.exe) do if not exist "%bin%\%%P" (
  echo Missing program "%bin%\%%P".
  goto fail
)
mkdir "%out%" || goto fail
"%bin%\GenCase_win64.exe" "%case%_Def" "%out%\%case%" -save:all || goto fail
"%bin%\DualSPHysics5.2_GEO_win64.exe" -gpu -stable "%out%\%case%" "%out%" -dirdataout data -svres -nsteps:%steps% || goto fail
findstr /L /C:"HydroMechModel=2" "%out%\Run.out" >nul || goto fail
mkdir "%out%\particles" || goto fail
"%bin%\PartVTK_win64.exe" -dirin "%out%\data" -savevtk "%out%\particles\PartFluid" -onlytype:-all,fluid -vars:+idp,+vel,+porepress || goto fail
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0support\check_public_cryer_tpi.ps1" "%out%" %steps% || goto fail
echo Completed %steps% steps. Native data and Fluid VTK are in "%out%".
popd
exit /b 0
:usage
echo Usage: %~nx0 [--smoke]
:fail
popd
exit /b 1
