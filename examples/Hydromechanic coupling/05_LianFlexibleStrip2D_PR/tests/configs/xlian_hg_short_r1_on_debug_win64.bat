@echo off
setlocal
cd /d "%~dp0..\.."
set name=lian_hg_short_r1_on_debug
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=tests/outputs/lian_hg_np_build_r1
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="%dirbin%/DualSPHysics5.2_win64_debug.exe"
if exist "%dirout%" goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe" --tool memcheck --error-exitcode 99 --leak-check full %dualsphysics% -gpu -stable -mdbc_freeslip %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0
:fail
echo Execution aborted; retained outputs are never deleted.
exit /b 1
