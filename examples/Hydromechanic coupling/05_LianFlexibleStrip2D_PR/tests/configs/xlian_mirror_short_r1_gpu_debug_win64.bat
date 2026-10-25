@echo off
setlocal
cd /d "%~dp0..\.."
set name=lian_mirror_short_r1_gpu_debug
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\05_LianFlexibleStrip2D_PR\tests\outputs\lian_mirror_build_r1\DualSPHysics5.2_win64_debug.exe"
if exist "%dirout%" goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3\compute-sanitizer\compute-sanitizer.exe" --tool memcheck --error-exitcode 99 %dualsphysics% -gpu -stable -mdbc_freeslip %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0
:fail
echo Execution aborted; retained outputs are never deleted.
exit /b 1
