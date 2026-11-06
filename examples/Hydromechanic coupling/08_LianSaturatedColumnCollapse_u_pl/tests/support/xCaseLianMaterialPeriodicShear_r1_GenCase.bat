@echo off
setlocal
pushd "%~dp0\..\.."
set name=CaseLianMaterialPeriodicShear_r1
set dirout=tests\outputs\upl_material_periodic_shear_r1_seed
set dirbin=..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
rem Preparation only. No solver, companion synthesis or postprocessing.
if exist "%dirout%" goto fail
if not exist %gencase% goto fail
if not exist "tests\configs\%name%_Def.xml" goto fail
if not exist "tests\outputs" mkdir "tests\outputs"
mkdir "%dirout%"
if errorlevel 1 goto fail
%gencase% "tests\configs\%name%_Def" "%dirout%\%name%" -save:all
set genrc=%ERRORLEVEL%
>"%dirout%\gencase_exit_code.txt" echo %genrc%
if not "%genrc%"=="0" goto fail
echo Fresh geometry generated. Review actual1024 fluid/zero bound and XML before any solver.
popd
if /i "%~1" == "-batch" exit /b 0
pause
exit /b 0
:fail
if not defined genrc set genrc=1
echo Preparation stopped. Existing and partial outputs are retained.
popd
if /i "%~1" == "-batch" exit /b %genrc%
pause
exit /b %genrc%
