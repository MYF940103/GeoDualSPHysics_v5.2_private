@echo off
setlocal
pushd "%~dp0\..\.."

set name=CaseLianSaturatedColumnCollapse_geometry_r1
set dirsource=tests\outputs\lian_collapse_geometry_r1
set dirout=tests\outputs\upl_c08_observer_r1_seed
set companion=tests\configs\CaseLianSaturatedColumnCollapse_observer_r1.xml

rem Copy-only seed preparation. No GenCase, component, solver or integration is launched.
if exist "%dirout%" (
    echo Observer seed "%dirout%" already exists. Retain it for review.
    goto fail
)
if not exist "%dirsource%\%name%.bi4" goto fail
if not exist "%dirsource%\%name%_Normals.nbi4" goto fail
if not exist "%companion%" goto fail
if not exist "tests\outputs" mkdir "tests\outputs"
mkdir "%dirout%"
if errorlevel 1 goto fail

copy /b "%dirsource%\%name%.bi4" "%dirout%\%name%.bi4" >nul
if errorlevel 1 goto fail
copy /b "%dirsource%\%name%_Normals.nbi4" "%dirout%\%name%_Normals.nbi4" >nul
if errorlevel 1 goto fail
copy /b "%companion%" "%dirout%\%name%.xml" >nul
if errorlevel 1 goto fail
fc /b "%dirsource%\%name%.bi4" "%dirout%\%name%.bi4" >nul
if errorlevel 1 goto fail
fc /b "%dirsource%\%name%_Normals.nbi4" "%dirout%\%name%_Normals.nbi4" >nul
if errorlevel 1 goto fail

echo Retained 7060-ID observer seed copied. No component or physical calculation was run.
popd
if /i "%~1" == "-batch" exit /b 0
pause
exit /b 0

:fail
echo Observer seed preparation aborted. Existing and partial outputs were preserved.
popd
if /i "%~1" == "-batch" exit /b 1
pause
exit /b 1
