@echo off
setlocal
cd /d "%~dp0\..\.."

set name=sw_pore_cell_1d_r1_gpu_on
set dirout=tests/outputs/%name%
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="../01_SelfWeightConsolidation_PR/tests/outputs/sw_pore_cell_build_r1/Release/out/DualSPHysics5.2_GEO_win64.exe"

if exist "%dirout%" goto fail
%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysics% -gpu -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:15000
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0

:fail
echo Fresh test failed; existing/partial data preserved.
exit /b 1
