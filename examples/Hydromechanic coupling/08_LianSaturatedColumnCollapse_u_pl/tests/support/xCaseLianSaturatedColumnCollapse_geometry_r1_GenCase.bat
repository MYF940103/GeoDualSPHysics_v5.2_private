@echo off
setlocal
pushd "%~dp0\..\.."

set name=CaseLianSaturatedColumnCollapse_geometry_r1
set dirout=tests\outputs\lian_collapse_geometry_r1
set dirbin=..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"

rem Geometry only. No solver or postprocessing is launched by this entry.
if exist "%dirout%" (
    echo Geometry output "%dirout%" already exists. Retain it for review.
    goto fail
)
if not exist %gencase% goto fail
if not exist "tests\outputs" mkdir "tests\outputs"
mkdir "%dirout%"
if errorlevel 1 goto fail

%gencase% "tests\configs\%name%_Def" "%dirout%\%name%" -save:all
if errorlevel 1 goto fail

echo Geometry generation completed. No u-pl physical acceptance is implied.
popd
if /i "%~1" == "-batch" exit /b 0
pause
exit /b 0

:fail
echo Geometry generation aborted. Existing outputs were preserved.
popd
if /i "%~1" == "-batch" exit /b 1
pause
exit /b 1
