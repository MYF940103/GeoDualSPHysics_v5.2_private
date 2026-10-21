@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."
set case=k5_cpu_timing_r1_t1
set dirout=tests/outputs/%case%
set diroutdata=%dirout%/data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="%dirbin%/DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
if exist "%dirout%" goto fail
rem Short diagnostic only: original 100-Pa acceptance limits are unchanged.
%gencase% tests/configs/%case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysics% -cpu -ompthreads:1 -stable -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -nsteps:30000
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -first:150 -last:150 -dirin %diroutdata% -savevtk %dirout%/particles/PartFluid -onlytype:-bound -vars:+idp,+mk,+vel,+rhop,+sigma_kk,+sigma_ij,+kplastic,+porepress,+fstype
if not "%ERRORLEVEL%" == "0" goto fail
popd
exit /b 0
:fail
echo Diagnostic failed or output already exists; retained files were not deleted.
popd
exit /b 1
