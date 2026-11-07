@echo off
setlocal
cd /d "%~dp0"
set checked=0
set failed=0
rem Read existing source outputs only. No GenCase, solver, receiver or file writes.
for %%V in (r2 r3) do for %%B in (CPU GPU) do call :checkexisting "CaseLianSaturatedColumnCollapse_shared_preload_%%V_%%B_out"
if "%checked%" == "0" (
    echo No existing r2/r3 CPU/GPU shared-preload output folder was found.
    goto fail
)
if not "%failed%" == "0" goto fail
echo All %checked% existing source folders passed scheduling checks only.
echo Use the receiving native loader for actual PRE certification.
if not "%~1" == "--unattended" pause
exit /b 0

:checkexisting
if not exist "%~1\" exit /b 0
set /a checked+=1 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "support\check_lian_preload_schedule_r1.ps1" -SourceOut "%~1"
if errorlevel 1 (
    set /a failed+=1 >nul
    exit /b 1
)
exit /b 0

:fail
echo Scheduling check did not pass. Preserve the complete source output; nothing was restarted or overwritten.
if not "%~1" == "--unattended" pause
exit /b 1
