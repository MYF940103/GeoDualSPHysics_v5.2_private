@echo off
setlocal
cd /d "%~dp0.."
set dirbin=support\runtime_r6
set backend=%~2
set name=
set solver=
set runmode=
set "c08postgroup=%~1"
set "c08postonly=0"
set "c08unattended=0"
for %%A in ("%~3" "%~4") do (
    if /i "%%~A" == "--postprocess" set "c08postonly=1"
    if /i "%%~A" == "--unattended" set "c08unattended=1"
    if /i "%%~A" == "-unattended" set "c08unattended=1"
)
if /i "%~1" == "psi0" set name=CaseLianSaturatedColumnCollapse_psi0_shared_r6
if /i "%~1" == "psi2p5" set name=CaseLianSaturatedColumnCollapse_psi2p5_shared_r6
if /i "%~1" == "psim5" set name=CaseLianSaturatedColumnCollapse_psim5_shared_r6
rem Only the reviewed psi0 GPU diagnostic is admitted; other groups remain locked and have no r6 inputs.
if /i not "%~1" == "psi0" goto locked
if /i not "%backend%" == "GPU" goto fail
if /i "%backend%" == "GPU" (
    set backend=GPU
    set solver=DualSPHysics5.2_GEO_win64.exe
    set runmode=-gpu:0
    set sourceout=CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out
)
if not defined name goto fail
if not defined solver goto fail
set dirout=%name%_%backend%_out
rem Root wrappers bind the original same-backend PRE; no new PRELOAD is provided.
if defined C08_PRELOAD_SOURCE set "sourceout=%C08_PRELOAD_SOURCE%"
set "prestate=%CD%\%sourceout%\data\Part_1000.bi4"
set "c08python=D:\anaconda3\python.exe"
if not exist "%c08python%" set "c08python=python"
call :checkposttools
if errorlevel 1 goto fail
if "%c08postonly%" == "1" goto postprocessonly
if exist "%dirout%" goto exists
if not exist "%name%_Def.xml" goto fail
for %%F in (GenCase_win64.exe %solver% DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll msvcp140.dll vcruntime140.dll vcruntime140_1.dll) do if not exist "%dirbin%\%%F" goto fail
rem Scheduling checks do not replace the receiving loader's full native PRE certification.
call :checksource
if errorlevel 1 goto fail
mkdir "%dirout%"
if not "%ERRORLEVEL%" == "0" goto fail
set template=%CD%\%name%_Def.xml
set prepared=%CD%\%dirout%\%name%_Def.xml
powershell -NoProfile -Command "try { $t=[IO.File]::ReadAllText($env:template); if(([regex]::Matches($t,'__GRAVITY_PRELOAD_STATE__')).Count -ne 1){throw 'Statefile marker differs'}; $t=$t.Replace('__GRAVITY_PRELOAD_STATE__',[Security.SecurityElement]::Escape($env:prestate)); [IO.File]::WriteAllText($env:prepared,$t,(New-Object Text.UTF8Encoding($false))) } catch { Write-Error $_; exit 1 }"
if not "%ERRORLEVEL%" == "0" goto fail
"%dirbin%\GenCase_win64.exe" "%dirout%\%name%_Def" "%dirout%\%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail
rem One receiver through TimeMax13, retaining actual source time and all material state.
"%dirbin%\%solver%" %runmode% -stable -mdbc_freeslip:1 "%dirout%\%name%" "%dirout%" -dirdataout data -svres
if not "%ERRORLEVEL%" == "0" goto fail
echo Receiver exited normally. Full collapse and paper comparison still require review.
call :postprocess
if errorlevel 1 goto fail
goto done

:postprocessonly
rem Existing-output mode never falls through to GenCase or a physical solver.
if not exist "%dirout%\Run.csv" goto fail
if not exist "%dirout%\Run.out" goto fail
call :checksource
if errorlevel 1 goto fail
call :postprocess
if errorlevel 1 goto fail
goto done

:checkposttools
if not exist "support\postprocess_lian_collapse_r6.py" exit /b 1
for %%F in (C08Native_win64.exe PartVTK_win64.exe) do if not exist "%dirbin%\%%F" exit /b 1
"%c08python%" -X utf8 -B "support\postprocess_lian_collapse_r6.py" --check-tools
if errorlevel 1 (
    echo Python with numpy and matplotlib plus runtime_r6 C08Native/PartVTK is required.
    echo Dependencies are not installed automatically. No GenCase or solver was started.
    exit /b 1
)
exit /b 0

:postprocess
"%c08python%" -X utf8 -B "support\postprocess_lian_collapse_r6.py" --group "%c08postgroup%" --outdir "%CD%\%dirout%" --source-pre "%prestate%"
exit /b %ERRORLEVEL%

:checksource
powershell -NoProfile -ExecutionPolicy Bypass -File "support\check_lian_preload_schedule_r1.ps1" -SourceOut "%sourceout%"
exit /b %ERRORLEVEL%

:locked
echo This group is prepared but NOT admitted. No GenCase, solver or postprocessing was started.
goto failed

:exists
echo Output already exists: %dirout%. Nothing was overwritten or restarted.
goto failed
:fail
echo Execution aborted. Preserve partial outputs; do not bypass source certification.
:failed
if not "%c08unattended%" == "1" pause
exit /b 1
:done
echo Native, separate PartFluid/PartBound, PNG and CSV postprocessing finished.
echo Preserve COMPLETE source and receiver folders. Normal exit is not physical acceptance.
echo No automatic next solver, retry, or fallback is performed.
if not "%c08unattended%" == "1" pause
exit /b 0
