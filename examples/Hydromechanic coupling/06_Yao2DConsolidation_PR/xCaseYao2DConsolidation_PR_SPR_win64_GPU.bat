@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

rem Reviewed fixed-plane SPR entry. Original default case and retained data are not replaced.
rem This BAT runs GenCase, the real GPU Release program and PartVTK; it does not make theory plots.
set name=CaseYao2DConsolidation_PR_SPR
set dirout=%name%_out
set diroutdata=%dirout%\data

rem "executables" are renamed and called from their directory.
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace

if exist "%dirout%" (
    echo Output "%dirout%" already exists. Retained results were not deleted.
    goto fail
)
if not exist %gencase% goto fail
if not exist %dualsphysicsgpu% goto fail
if not exist %partvtk% goto fail

%gencase% %name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%"=="0" goto fail

%dualsphysicsgpu% -gpu -stable -mdbc_freeslip %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%"=="0" goto fail

:postprocessing
rem Native fields for fluid and boundary visualization; analytical comparisons are separate.
set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartFluid -onlytype:-all,fluid -vars:%vars%
if not "%ERRORLEVEL%"=="0" goto fail
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartBound -onlytype:-all,bound -vars:%vars%
if not "%ERRORLEVEL%"=="0" goto fail

:success
echo All done. Output: %dirout%
popd
pause
exit /b 0

:fail
echo Execution refused or aborted. Existing outputs were not deleted.
popd
pause
exit /b 1
