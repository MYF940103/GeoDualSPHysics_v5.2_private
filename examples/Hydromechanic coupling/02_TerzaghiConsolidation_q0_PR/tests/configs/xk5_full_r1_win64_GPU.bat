@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."
set case=k5_full_r1
set dirout=tests/outputs/%case%
set diroutdata=%dirout%/data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
if exist "%dirout%" goto fail
rem Fresh uniform-1D 2Tv diagnostic; original safety limits and accepted fixed step unchanged.
%gencase% tests/configs/%case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysics% -gpu:0 -ompthreads:1 -stable -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -nsteps:145750572
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
