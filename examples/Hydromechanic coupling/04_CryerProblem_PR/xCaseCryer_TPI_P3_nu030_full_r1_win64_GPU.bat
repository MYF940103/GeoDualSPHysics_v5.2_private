@echo off
setlocal
set "mode="
set "pause_at_end=1"
if /i "%~1"=="--check-only" set "mode=-CheckOnly"
if /i "%~1"=="--check-only" set "pause_at_end=0"
if /i "%~1"=="--unattended" set "pause_at_end=0"
if not "%~2"=="" exit /b 2
if not "%~1"=="" if "%pause_at_end%"=="1" exit /b 2
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0support\run_cryer_tpi_p3_r1.ps1" -Stage full %mode%
set "rc=%ERRORLEVEL%"
if "%pause_at_end%"=="1" pause
exit /b %rc%
