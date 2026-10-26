@echo off
setlocal
cd /d "%~dp0"

rem Independent formal release; never delete retained outputs.
set name=CaseLianFlexibleStrip2D_PR_release
set dirout=%name%_out
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set python="D:\Anaconda3\python.exe"
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace

if exist "%dirout%" goto fail
%gencase% %name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

rem Actual 100 s run: mode4 mirrored contact, original mixed mDBC, no SPR/HG/TPI.
%dualsphysicsgpu% -gpu -stable -mdbc_freeslip %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

rem Native data are retained; convert fluid/boundary fields for visualization.
set dirout2=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartFluid -onlytype:-all,fluid -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata% -savevtk %dirout2%/PartBound -onlytype:-all,bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

rem Native figures and matching CSVs; reference/visual acceptance remains separate.
%python% -B support/postprocess_lian_release.py --folder "%dirout%" --tag lian_release100_r1
if not "%ERRORLEVEL%" == "0" goto fail
echo All done. Review formal figures and SPH/FEM comparisons before acceptance.
if not "%~1" == "--unattended" pause
exit /b 0

:fail
echo Execution aborted. Existing and partial outputs are preserved; never rerun blindly.
if not "%~1" == "--unattended" pause
exit /b 1
