@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseLianFlexibleStrip2D_PR
set dirout=%case%_short_out
set diroutdata=%dirout%\data
set tmax=0.0002
set tout=0.0002

set caseroot=..
set dirbin=../../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if not exist %dualsphysicscpu% set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace

if exist %dirout% rd /s /q %dirout%
if not "%ERRORLEVEL%" == "0" goto fail

rem Lian 2023 flexible strip loading smoke test: local q0 strip x=[0,1.25] m, no TPI.
%gencase% "%caseroot%/%case%_Def" %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicscpu% -cpu -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -tmax:%tmax% -tout:%tout%
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartAll -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Lian 2D flexible strip loading short CPU smoke test done.
popd
exit /b 0

:fail
echo Lian 2D flexible strip loading short CPU smoke test aborted.
popd
exit /b 1
