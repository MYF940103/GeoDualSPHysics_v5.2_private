@echo off
setlocal
set "support=%~dp0"
set "dest=%~dp0..\outputs\c08_m0_pressure_cuda_r1"
set "public=%~dp0..\..\..\..\..\src\source"
if exist "%dest%\row.dll" exit /b 1
if not exist "%dest%" mkdir "%dest%" || exit /b 1
for /f "usebackq tokens=*" %%v in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "vsdir=%%v"
call "%vsdir%\VC\Auxiliary\Build\vcvars64.bat" || exit /b 1
pushd "%dest%" || exit /b 1
nvcc -shared -O2 -lineinfo --fmad=false -gencode arch=compute_86,code=sm_86 -gencode arch=compute_86,code=compute_86 -I"%public%" -o row.dll "%support%c08_m0_pressure_row.cu"
set "rc=%errorlevel%"
popd
exit /b %rc%
