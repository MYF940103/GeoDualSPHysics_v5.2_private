@echo off
setlocal
cd /d "%~dp0"

rem Portable Windows x64 / RTX A6000 calculation; never delete retained outputs.
set name=CaseLianFlexibleStrip2D_PR_release
set dirout=%name%_HGSPR_out
set diroutdata=%dirout%\data
set dirbin=support/bin
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"

if exist "%dirout%" goto exists
if not exist "%dirbin%/GenCase_win64.exe" goto fail
if not exist "%dirbin%/DualSPHysics5.2_GEO_win64.exe" goto fail
%gencase% "%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

rem 100 s fresh start: HG=.1, SPR=1, gradient correction=1; mixed mDBC, no TPI.
%dualsphysicsgpu% -gpu -stable -mdbc_freeslip "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

rem Preserve the COMPLETE output folder. Plotting is deferred until copy-back.
echo Calculation finished. Copy the complete %dirout% folder back for analysis.
echo Normal exit is not paper-reference or full-cycle accuracy acceptance.
if not "%~1" == "--unattended" pause
exit /b 0

:exists
echo Output already exists: %dirout%. Nothing was overwritten or restarted.
if not "%~1" == "--unattended" pause
exit /b 1

:fail
echo Execution aborted. Existing and partial outputs are preserved; never rerun blindly.
if not "%~1" == "--unattended" pause
exit /b 1
