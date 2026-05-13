@echo off
setlocal

set BASEDIR=%~dp0
set BIN=%BASEDIR%..\..\..\..\..\bin\windows

set CASES=CaseCryer_PR_StrictSphere_C5j_FinerDiffusionMLS CaseCryer_PR_StrictSphere_C5j_CoarseDiffusionMLS

for %%C in (%CASES%) do (
  if exist "%BASEDIR%%%C_cpu_out" rd /s /q "%BASEDIR%%%C_cpu_out"
  if exist "%BASEDIR%%%C_cpu_vtk_particles" rd /s /q "%BASEDIR%%%C_cpu_vtk_particles"

  echo.
  echo === GenCase %%C ===
  "%BIN%\GenCase_win64.exe" "%BASEDIR%%%C_Def" "%BASEDIR%%%C_cpu_out\%%C" -save:all
  if errorlevel 1 exit /b 1

  echo.
  echo === DualSPHysics CPU Release %%C ===
  "%BIN%\DualSPHysics5.2CPU_win64.exe" -cpu "%BASEDIR%%%C_cpu_out\%%C" "%BASEDIR%%%C_cpu_out" -dirdataout data -sv:csv,binx
  if errorlevel 1 exit /b 1

  echo.
  echo === PartVTK %%C ===
  if not exist "%BASEDIR%%%C_cpu_vtk_particles" mkdir "%BASEDIR%%%C_cpu_vtk_particles"
  "%BIN%\PartVTK_win64.exe" -dirin "%BASEDIR%%%C_cpu_out\data" -filexml "%BASEDIR%%%C_cpu_out\%%C.xml" -savevtk "%BASEDIR%%%C_cpu_vtk_particles\PartFluid" -onlytype:-all,+fluid -vars:+idp,+vel,+rhop,+type,+mk,+PorePress,+ExcessPorePress,+PorePressRate,+DivVel,+LapPorePress,+LapZ,+PorePressureAccelDiff,+Kplastic
  if errorlevel 1 exit /b 1
)

echo.
echo === C5j analysis ===
py -3 "%BASEDIR%scripts\analyze_c5j_mls_boundary_flux.py"
if errorlevel 1 exit /b 1

echo.
echo C5j pressure-only gate complete.
endlocal
