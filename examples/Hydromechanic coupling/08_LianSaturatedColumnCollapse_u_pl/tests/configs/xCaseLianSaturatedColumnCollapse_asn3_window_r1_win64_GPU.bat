@echo off
setlocal
cd /d "%~dp0.."
rem TEST ONLY: complete body, epsilon0.2/exponent3 locality window, not a formal collapse or proven repair.
rem All5000 soil particles evolve; only the existing three native IDs are traced.
rem No added SPR, HG, pressure filter, FOS, half-step chain, PRE solve or automatic decoder.
set "c08python=D:\anaconda3\python.exe"
if not exist "%c08python%" set "c08python=python"
set "c08unattended=0"
set "c08notify="
for %%A in (%*) do (
    if /i not "%%~A" == "--notify" if /i not "%%~A" == "--unattended" if /i not "%%~A" == "-unattended" if /i not "%%~A" == "-batch" goto badargs
    if /i "%%~A" == "--notify" set "c08notify=--notify"
    if /i "%%~A" == "--unattended" set "c08unattended=1"
    if /i "%%~A" == "-unattended" set "c08unattended=1"
    if /i "%%~A" == "-batch" set "c08unattended=1"
)
if not exist "logs\upl_c08_asn3_window_GPU_r1.admission.json" goto unbound
"%c08python%" -X utf8 -B "support\upl_c08_asn3_window_r1.py" --execution-authorized %c08notify%
set "c08rc=%ERRORLEVEL%"
if not "%c08rc%" == "0" echo Preserve the first failure and partial output. Do not restart this job.
if "%c08rc%" == "0" echo Window ended normally; separate native and physical review remain pending.
goto done

:badargs
echo Supported flags: --notify --unattended -unattended -batch. No program was started.
set "c08rc=1"
goto done

:unbound
echo Root full-read and independent single-job admission are required. No program was started.
set "c08rc=1"

:done
if "%c08unattended%" == "0" pause
exit /b %c08rc%
