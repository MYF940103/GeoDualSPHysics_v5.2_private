@echo off
setlocal
cd /d "%~dp0\..\.."

set name=sw_pore_cell_native_r1_debug_on_event
set dirout=tests/outputs/%name%
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="tests/outputs/sw_pore_cell_build_r1/Debug/out/DualSPHysics5.2_win64_debug.exe"

if exist "%dirout%" goto fail
%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail
"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe" --tool memcheck --error-exitcode 99 --log-file "tests/logs/sw_pore_cell_native_r1_debug_on_event.memcheck.log" %dualsphysics% -gpu -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:80
set solvercode=%ERRORLEVEL%
if not "%solvercode%" == "0" exit /b %solvercode%
exit /b 0

:fail
echo Existing/partial data preserved.
exit /b 1
