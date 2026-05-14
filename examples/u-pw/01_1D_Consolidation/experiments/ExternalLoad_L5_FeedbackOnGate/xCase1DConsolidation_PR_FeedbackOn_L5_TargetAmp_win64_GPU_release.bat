@echo off
cd /d "%~dp0"
set name=Case1DConsolidation_PR_FeedbackOn_L5_TargetAmp
set dirout=%name%_gpu_out
set dirbin=..\..\..\..\..\bin\windows
if exist %dirout% rd /s /q %dirout%
mkdir %dirout%
"%dirbin%\GenCase_win64.exe" %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
"%dirbin%\DualSPHysics5.2_GEO_win64.exe" -gpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail
echo All done
goto end
:fail
echo Execution aborted.
:end
pause
