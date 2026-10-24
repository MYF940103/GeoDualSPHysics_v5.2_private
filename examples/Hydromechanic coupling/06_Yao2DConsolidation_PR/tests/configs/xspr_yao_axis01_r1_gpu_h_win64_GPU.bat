@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."

rem Bounded .1-s axis-NoPen production-step companion, not formal 2D consolidation acceptance.
rem Native BI4; single-run and pair reviews are separate. Existing outputs are protected.
set name=spr_yao_axis01_r1_gpu_h
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set stepcheck="tests/outputs/spr_yao_axis_GPU_r1/axis_step.exe"
set dirinput=tests\outputs\%name%_input
if exist %dirout% goto fail
if exist %dirinput% goto fail
%gencase% tests/configs/%name%_Def %dirinput%/%name% -save:all
if not "%ERRORLEVEL%"=="0" goto fail
%stepcheck% 10000 100 -gpu -stable %dirinput%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%"=="0" goto fail
popd
exit /b 0
:fail
echo Diagnostic refused or failed. Retained outputs were not deleted.
popd
exit /b 1
