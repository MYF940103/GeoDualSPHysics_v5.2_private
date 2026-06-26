@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set basecase=CaseLianFlexibleStrip2D_PR
set suffix=gpu3s
set tmax=3
set tout=0.05
set dtfixed=0.000005
set poresafety=0.1
if not "%~1" == "" set tmax=%~1
if not "%~2" == "" set tout=%~2
if not "%~3" == "" set suffix=%~3
set case=%basecase%_%suffix%
set dirout=%case%_out
set diroutdata=%dirout%\data

set caseroot=..
set dirbin=../../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
if not exist %dualsphysicsgpu% set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_win64_debug.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace

if exist %dirout% rd /s /q %dirout%
if not "%ERRORLEVEL%" == "0" goto fail

rem Build a temporary 3s definition from the base Lian case.
py support\make_lian_gpu3s_def.py --base "%caseroot%/%basecase%_Def.xml" --out %case%_Def.xml --tmax %tmax% --tout %tout% --dtfixed %dtfixed% --poresafety %poresafety%
if not "%ERRORLEVEL%" == "0" goto fail

rem Lian 2023 flexible strip loading: q0=10 kPa, tL=1 s, open top drainage outside strip after tL.
%gencase% %case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysicsgpu% -gpu -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -tmax:%tmax% -tout:%tout%
if not "%ERRORLEVEL%" == "0" goto fail

set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartAll -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

py support\postprocess_lian_flexible_strip.py --run-dir %dirout% --out-dir figures
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo Lian 2D flexible strip loading GPU validation done.
popd
exit /b 0

:fail
echo Lian 2D flexible strip loading GPU validation aborted.
popd
exit /b 1
