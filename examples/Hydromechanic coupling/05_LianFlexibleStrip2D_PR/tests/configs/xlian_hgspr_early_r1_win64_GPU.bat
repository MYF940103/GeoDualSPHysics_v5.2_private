@echo off
setlocal
cd /d "%~dp0\..\.."

rem Fresh early native-save supplement; never delete or restart retained outputs.
set name=lian_hgspr_early_r1
set dirout=tests/outputs/%name%
set diroutdata=%dirout%\data
set dirbin=support/bin
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicsgpu="%dirbin%/DualSPHysics5.2_GEO_win64.exe"

if exist "%dirout%" goto exists
if not exist "%dirbin%/GenCase_win64.exe" goto fail
if not exist "%dirbin%/DualSPHysics5.2_GEO_win64.exe" goto fail
%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

rem Only TimeMax=1 and TimeOut=.01 differ; dt=10us and all physics are unchanged.
%dualsphysicsgpu% -gpu -stable -mdbc_freeslip "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%" == "0" goto fail

echo Early calculation finished. Preserve the complete %dirout% folder.
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

