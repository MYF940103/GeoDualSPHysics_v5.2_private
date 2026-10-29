@echo off
setlocal
cd /d "%~dp0..\.."
set name=cryer_darcy_switch_native_r1_cpu_on
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="tests/outputs/cryer_darcy_switch_build_r1/ReleaseCPU/out/DualSPHysics5.2CPU_win64.exe"
if exist "%dirout%" goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysicscpu% -cpu -ompthreads:8 -stable %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0
:fail
echo Execution aborted; retained outputs are never deleted.
exit /b 1
