@echo off
setlocal
cd /d "%~dp0..\.."
set name=lian_mirror_short_r1_cpu_debug
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\bin\windows\DualSPHysics5.2CPU_win64_debug.exe"
if exist "%dirout%" goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysics% -cpu -ompthreads:8 -stable -mdbc_freeslip %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0
:fail
echo Execution aborted; retained outputs are never deleted.
exit /b 1
