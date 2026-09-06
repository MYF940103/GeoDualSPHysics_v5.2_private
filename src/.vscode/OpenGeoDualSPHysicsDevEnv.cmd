@echo off
setlocal

set "VSDEVCMD=D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat"
set "CODECMD=D:\Program Files\Microsoft VS Code\bin\code.cmd"
set "WORKDIR=D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\src"

if not exist "%VSDEVCMD%" (
    echo Cannot find VS Developer Command script:
    echo   %VSDEVCMD%
    pause
    exit /b 1
)

if not exist "%CODECMD%" (
    echo Cannot find VS Code command script:
    echo   %CODECMD%
    pause
    exit /b 1
)

call "%VSDEVCMD%" -arch=x64 -host_arch=x64
if errorlevel 1 (
    echo Failed to initialize the Visual Studio build environment.
    pause
    exit /b 1
)

cd /d "%WORKDIR%"
echo.
echo Visual Studio x64 build environment is ready.
echo Workspace: %WORKDIR%
echo.
where msbuild
where cl
echo.

call "%CODECMD%" --new-window "%WORKDIR%"

echo VS Code has been launched from this configured environment.
echo Keep this window open if you also want a ready Developer Command Prompt.
cmd /k
