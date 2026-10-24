@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."

rem Integer-save diagnostic: the companion calls the production Symplectic step.
rem Native BI4 only. Offline comparisons are separate; retained outputs are never deleted.
set name=spr_yao_grid10_r1_faces_off
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set stepcheck="tests/outputs/spr_yao_step_r2rel/spr_yao_step.exe"
set dirinput=tests\outputs\%name%_input
if exist %dirout% goto fail
if exist %dirinput% goto fail
%gencase% tests/configs/%name%_Def %dirinput%/%name% -save:all
if not "%ERRORLEVEL%"=="0" goto fail
%stepcheck% 5000 50 -cpu -ompthreads:8 %dirinput%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%"=="0" goto fail
popd
exit /b 0
:fail
echo Diagnostic refused or failed. Retained outputs were not deleted.
popd
exit /b 1
