@echo off
setlocal
cd /d "%~dp0..\.."
set name=cryer_darcy_switch_native_r1_gpu_dbg
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="tests/outputs/cryer_darcy_switch_build_r2/Debug/out/DualSPHysics5.2_win64_debug.exe"
if exist "%dirout%" goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe" --tool memcheck --error-exitcode 86 --leak-check full --log-file "%dirout%\memcheck.log" %dualsphysicsgpu% -gpu -stable %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0
:fail
echo Execution aborted; retained outputs are never deleted.
exit /b 1
