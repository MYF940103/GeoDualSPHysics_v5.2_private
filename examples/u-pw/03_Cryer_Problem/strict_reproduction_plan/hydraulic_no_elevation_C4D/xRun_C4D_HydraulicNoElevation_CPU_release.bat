@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%\PartVTK_win64.exe"

call :run_case CaseC4D_SourceOn_Regression
if not "%ERRORLEVEL%" == "0" goto fail
call :run_case CaseC4D_NoElevation_Diffusion
if not "%ERRORLEVEL%" == "0" goto fail
call :run_case CaseC4D_NoElevation_Compression
if not "%ERRORLEVEL%" == "0" goto fail

py scripts\analyze_c4d_hydraulic_no_elevation.py
if not "%ERRORLEVEL%" == "0" goto fail
py scripts\plot_c4d_hydraulic_no_elevation.py
if not "%ERRORLEVEL%" == "0" goto fail

echo C4-D hydraulic no-elevation CPU smokes completed.
goto end

:run_case
set name=%1
set dirout=%name%_cpu_out
set diroutdata=%dirout%\data
set dirvtk=%name%_cpu_vtk_particles
if exist %dirout% rd /s /q %dirout%
if exist %dirvtk% rd /s /q %dirvtk%
%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" exit /b 1
%dualsphysicscpu% -cpu %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" exit /b 1
if not exist %dirvtk% mkdir %dirvtk%
%partvtk% -dirin %diroutdata% -filexml %dirout%\%name%.xml -savevtk %dirvtk%\PartFluid -onlytype:-all,+fluid -vars:+idp,+vel,+rhop,+type,+mk,+PorePress,+ExcessPorePress,+PorePressRate,+DivVel,+LapPorePress,+LapZ,+PorePressureAccelDiff,+Kplastic
if not "%ERRORLEVEL%" == "0" exit /b 1
exit /b 0

:fail
echo C4-D hydraulic no-elevation run failed.

:end
pause
