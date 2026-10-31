@echo off
setlocal
cd /d "%~dp0"

rem Independent Poisson-ratio candidate. Never delete, overwrite or restart data.
set smoke=
set unattended=0
:arguments
if "%~1" == "" goto run
if "%~1" == "--smoke" (
    set smoke=-Smoke
    shift
    goto arguments
)
if "%~1" == "--unattended" (
    set unattended=1
    shift
    goto arguments
)
echo Unknown argument: %~1
set result=1
goto end

:run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "support\run_cryer_nu_release_r1.ps1" -Nu 010 %smoke%
set result=%ERRORLEVEL%
:end
if "%unattended%" == "0" pause
exit /b %result%
