@echo off
setlocal
cd /d "%~dp0\..\.."

set name=sw_shepard_event_r1_gpu_off
set dirout=tests/outputs/%name%
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="../04_CryerProblem_PR/tests/outputs/cryer_darcy_switch_build_r2/Release/out/DualSPHysics5.2_GEO_win64.exe"

if exist "%dirout%" goto fail
%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysics% -gpu -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:80
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0

:fail
echo Existing/partial data preserved.
exit /b 1
