@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."

rem Independent short CPU test: preserve formal files and retained outputs.
rem Native BI4 output only; four-way comparison is performed by tests/scripts/spr_yao_review.py.
set name=spr_yao_short_r1_faces_on
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"
if exist %dirout% goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%"=="0" goto fail
%dualsphysicscpu% -cpu -ompthreads:8 %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%"=="0" goto fail
popd
exit /b 0
:fail
echo Test refused or failed. Retained outputs were not deleted.
popd
exit /b 1
