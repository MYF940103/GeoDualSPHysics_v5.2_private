@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."

rem Bounded GPU companion reproduction, not formal consolidation or theory acceptance.
rem Uses the retained verified companion; CSV/JSON only, combined plots are an offline step.
set name=spr_gpu_pulse_r1_std_wedge2_s1_h_gpu_manual_r1
set dirout=tests\outputs\%name%
set dirinput=tests\outputs\%name%_input
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set diagnostic="tests/outputs/spr_gpu_pulse_Release_op1/spr_gpu_pulse.exe"
if exist %dirout% goto fail
if exist %dirinput% goto fail
%gencase% tests/configs/spr_gpu_pulse_r1_std_wedge2_s1_h_Def %dirinput%/%name% -save:all
if not "%ERRORLEVEL%"=="0" goto fail
%diagnostic% 4000 20 -gpu -stable %dirinput%/%name% %dirout% -dirdataout data -sv:none
if not "%ERRORLEVEL%"=="0" goto fail
popd
exit /b 0
:fail
echo Diagnostic refused or failed. Existing results were not removed.
popd
exit /b 1
