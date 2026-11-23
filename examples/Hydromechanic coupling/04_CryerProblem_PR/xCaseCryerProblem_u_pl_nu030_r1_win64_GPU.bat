@echo off
setlocal
cd /d "%~dp0"
if not "%~3"=="" exit /b 2
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "support\hydro_frozen_runtime_r2.ps1" -Definition "CaseCryerProblem_u_pl_nu030_r1_Def.xml" -Portable -Option1 "opt=%~1" -Option2 "opt=%~2"
set "rc=%ERRORLEVEL%"
if not "%rc%"=="0" if "%~1"=="" pause
exit /b %rc%
