@echo off
setlocal
cd /d "%~dp0.."
set dirbin=support\runtime_r3
set backend=%~2
set name=
set solver=
set runmode=
if /i "%~1" == "PRELOAD" set name=CaseLianSaturatedColumnCollapse_shared_preload_r3
if /i "%~1" == "psi0" set name=CaseLianSaturatedColumnCollapse_psi0_shared_r3
if /i "%~1" == "psi2p5" set name=CaseLianSaturatedColumnCollapse_psi2p5_shared_r3
if /i "%~1" == "psim5" set name=CaseLianSaturatedColumnCollapse_psim5_shared_r3
if /i "%backend%" == "CPU" (
    set backend=CPU
    set solver=DualSPHysics5.2CPU_win64.exe
    set runmode=-cpu -ompthreads:8
)
if /i "%backend%" == "GPU" (
    set backend=GPU
    set solver=DualSPHysics5.2_GEO_win64.exe
    set runmode=-gpu:0
)
if not defined name goto fail
if not defined solver goto fail
set dirout=%name%_%backend%_out
set sourceout=CaseLianSaturatedColumnCollapse_shared_preload_r3_%backend%_out
set prepart=Part_1000.bi4
if exist "%dirout%" goto exists
if not exist "%name%_Def.xml" goto fail
for %%F in (GenCase_win64.exe %solver% DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll msvcp140.dll vcruntime140.dll vcruntime140_1.dll) do if not exist "%dirbin%\%%F" goto fail
if /i "%~1" == "PRELOAD" goto preload

rem Run.csv/filename checks establish scheduling only. Native loader certifies PRE.
call :checksource
if not "%ERRORLEVEL%" == "0" goto fail
mkdir "%dirout%"
if not "%ERRORLEVEL%" == "0" goto fail
set prestate=%CD%\%sourceout%\data\%prepart%
set template=%CD%\%name%_Def.xml
set prepared=%CD%\%dirout%\%name%_Def.xml
powershell -NoProfile -Command "try { $t=[IO.File]::ReadAllText($env:template); if(([regex]::Matches($t,'__GRAVITY_PRELOAD_STATE__')).Count -ne 1){throw 'Statefile marker differs'}; $t=$t.Replace('__GRAVITY_PRELOAD_STATE__',[Security.SecurityElement]::Escape($env:prestate)); [IO.File]::WriteAllText($env:prepared,$t,(New-Object Text.UTF8Encoding($false))) } catch { Write-Error $_; exit 1 }"
if not "%ERRORLEVEL%" == "0" goto fail
"%dirbin%\GenCase_win64.exe" "%dirout%\%name%_Def" "%dirout%\%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail
rem Exactly one receiver process, actual source clock through TimeMax13; no PART restart.
"%dirbin%\%solver%" %runmode% -stable -mdbc_freeslip "%dirout%\%name%" "%dirout%" -dirdataout data -svres
if not "%ERRORLEVEL%" == "0" goto fail
echo Receiver exited normally. Full collapse and paper comparison still require review.
goto done

:preload
"%dirbin%\GenCase_win64.exe" "%name%_Def" "%dirout%\%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail
rem TimeMax13 keeps the event valid; stop at completed4000000 PRE before release.
"%dirbin%\%solver%" %runmode% -stable -mdbc_freeslip "%dirout%\%name%" "%dirout%" -dirdataout data -svres -nsteps:4000000
if not "%ERRORLEVEL%" == "0" goto fail
call :checksource
if not "%ERRORLEVEL%" == "0" goto fail
echo Source exited at scheduled PRE. The receiving loader must certify the actual file.
echo Run the three material BAT files with the SAME backend. Preserve this source output.
goto done

:checksource
powershell -NoProfile -ExecutionPolicy Bypass -File "support\check_lian_preload_schedule_r1.ps1" -SourceOut "%sourceout%"
exit /b %ERRORLEVEL%

:exists
echo Output already exists: %dirout%. Nothing was overwritten or restarted.
goto failed
:fail
echo Execution aborted. Preserve partial outputs; do not bypass source certification.
:failed
if not "%~3" == "--unattended" pause
exit /b 1
:done
echo Copy COMPLETE source and material output folders back for offline native analysis.
echo This launcher has no Python, plotting, VTK conversion or automatic fallback.
if not "%~3" == "--unattended" pause
exit /b 0
