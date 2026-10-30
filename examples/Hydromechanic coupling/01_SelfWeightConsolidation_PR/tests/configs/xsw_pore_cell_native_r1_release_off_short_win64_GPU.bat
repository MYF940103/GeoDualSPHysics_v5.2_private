@echo off
setlocal
cd /d "%~dp0\..\.."

set name=sw_pore_cell_native_r1_release_off_short
set dirout=tests/outputs/%name%
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="tests/outputs/sw_pore_cell_build_r1/Release/out/DualSPHysics5.2_GEO_win64.exe"

if exist "%dirout%" goto fail
%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysics% -gpu -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:2000
set solvercode=%ERRORLEVEL%
if not "%solvercode%" == "0" exit /b %solvercode%
exit /b 0

:fail
echo Existing/partial data preserved.
exit /b 1
