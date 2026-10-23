@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."
set case=k5em5_hg05_15s_cpu_r1_c
set dirout=tests/outputs/%case%
set diroutdata=%dirout%/data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="%dirbin%/DualSPHysics5.2CPU_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
if exist "%dirout%" goto fail
rem Gated bounded uniform-grid diagnostic; no full-cycle admission.
%gencase% tests/configs/%case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysics% -cpu -ompthreads:8 -stable -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -nsteps:1500000
if not "%ERRORLEVEL%" == "0" goto fail
set /a lastpart=0 >nul
for %%F in ("%diroutdata%/Part_*.bi4") do set /a lastpart+=1 >nul
set /a lastpart-=1 >nul
%partvtk% -first:!lastpart! -last:!lastpart! -dirin %diroutdata% -savevtk %dirout%/particles/PartFluid -onlytype:-bound -vars:+idp,+mk,+vel,+rhop,+sigma_kk,+sigma_ij,+kplastic,+porepress,+fstype
if not "%ERRORLEVEL%" == "0" goto fail
popd
exit /b 0
:fail
echo Diagnostic failed or output already exists; retained files were not deleted.
popd
exit /b 1
