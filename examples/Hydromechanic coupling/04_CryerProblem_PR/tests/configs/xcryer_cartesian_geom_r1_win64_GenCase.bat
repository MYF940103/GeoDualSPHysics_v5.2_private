@echo off
setlocal
cd /d "%~dp0..\.."
set name=cryer_cartesian_geom_r1
set dirout=tests\outputs\%name%
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
if exist "%dirout%" goto fail
%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
exit /b 0
:fail
echo Geometry generation aborted; retained outputs are never deleted.
exit /b 1
