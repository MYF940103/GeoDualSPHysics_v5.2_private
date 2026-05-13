@echo off
setlocal
set SCRIPT_DIR=%~dp0
set BUILD_DIR=%SCRIPT_DIR%build
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
cl /nologo /EHsc /std:c++17 /O2 /Fo"%BUILD_DIR%\\" /Fe:"%BUILD_DIR%\mcc_single_point_driver.exe" "%SCRIPT_DIR%mcc_model.cpp" "%SCRIPT_DIR%mcc_single_point_driver.cpp"
exit /b %ERRORLEVEL%
