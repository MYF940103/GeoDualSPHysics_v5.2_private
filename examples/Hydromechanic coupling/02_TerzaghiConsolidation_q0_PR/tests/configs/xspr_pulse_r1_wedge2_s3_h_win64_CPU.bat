@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."

rem Bounded companion reproduction, not a formal consolidation run.
rem Writes native diagnostic CSV/JSON; combined comparison plots remain a separate offline step.
set name=spr_pulse_r1_wedge2_s3_h_manual_r1
set dirout=tests\outputs\%name%
set dirinput=tests\outputs\%name%_input
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set diagnostic="tests/outputs/spr_pulse_r1rel/spr_pulse.exe"
if exist %dirout% goto fail
if exist %dirinput% goto fail
%gencase% tests/configs/spr_pulse_r1_wedge2_s3_h_Def %dirinput%/%name% -save:all
if not "%ERRORLEVEL%"=="0" goto fail
%diagnostic% 4000 20 -cpu -ompthreads:1 %dirinput%/%name% %dirout% -dirdataout data -sv:none
if not "%ERRORLEVEL%"=="0" goto fail
popd
exit /b 0
:fail
echo Diagnostic refused or failed. Existing results were not removed.
popd
exit /b 1
