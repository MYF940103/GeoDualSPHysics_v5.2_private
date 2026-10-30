@echo off
setlocal
cd /d "%~dp0\..\.."

set name=symc_1d_short_r1_gpu_old
set dirout=tests/outputs/%name%
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="../04_CryerProblem_PR/tests/outputs/cryer_darcy_switch_base_r1/DualSPHysics5.2_GEO_win64.exe"

if exist "%dirout%" goto fail
%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysics% -gpu -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:15000
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0

:fail
echo Fresh test failed; existing/partial data preserved.
exit /b 1
