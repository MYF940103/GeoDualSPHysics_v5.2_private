@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseLianFlexibleStrip2D_PR
set dirout=%case%_out
set diroutdata=%dirout%\data
set tmax=3
set tout=0.05

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace

if exist %dirout% rd /s /q %dirout%
if not "%ERRORLEVEL%" == "0" goto fail

rem Official Lian 2023 flexible strip loading case: base XML settings, no TPI.
%gencase% %case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -tmax:%tmax% -tout:%tout%
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartAll -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Lian 2D flexible strip loading GPU run done.
popd
exit /b 0

:fail
echo Lian 2D flexible strip loading GPU run aborted.
popd
exit /b 1
