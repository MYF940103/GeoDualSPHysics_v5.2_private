@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\..\.."

rem Real GPU program with ordinary save events.
rem Native BI4 only. Offline comparisons are separate; retained outputs are never deleted.
set name=spr_yao_release_smoke_r1_faces_on
set dirout=tests\outputs\%name%
set diroutdata=%dirout%\data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set stepcheck="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set dirinput=tests\outputs\%name%_input
if exist %dirout% goto fail
if exist %dirinput% goto fail
%gencase% tests/configs/%name%_Def %dirinput%/%name% -save:all
if not "%ERRORLEVEL%"=="0" goto fail
%stepcheck% -gpu -stable %dirinput%/%name% %dirout% -dirdataout data -svres -svextraparts:1
if not "%ERRORLEVEL%"=="0" goto fail
popd
exit /b 0
:fail
echo Diagnostic refused or failed. Retained outputs were not deleted.
popd
exit /b 1
