@echo off
setlocal
cd /d "%~dp0.."

rem Windows x64 CPU8 / NVIDIA GPU0; preserve retained outputs and run one backend per group.
set dirbin=support\runtime
set name=
set solver=
set runmode=
if /i "%~1" == "psi0" set name=CaseLianSaturatedColumnCollapse_psi0_r1
if /i "%~1" == "psi2p5" set name=CaseLianSaturatedColumnCollapse_psi2p5_r1
if /i "%~1" == "psim5" set name=CaseLianSaturatedColumnCollapse_psim5_r1
if /i "%~2" == "CPU" (
    set solver=DualSPHysics5.2CPU_win64.exe
    set runmode=-cpu -ompthreads:8
)
if /i "%~2" == "GPU" (
    set solver=DualSPHysics5.2_GEO_win64.exe
    set runmode=-gpu:0
)
if not defined name goto fail
if not defined solver goto fail
set dirdef=.
set dirout=%name%_out
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysics="%dirbin%\%solver%"
if exist "%dirout%" goto exists
if not exist "%dirdef%\%name%_Def.xml" goto fail
if not exist "%dirbin%\GenCase_win64.exe" goto fail
if not exist "%dirbin%\%solver%" goto fail
for %%F in (DsphConfig.xml ChronoEngine.dll dsphchrono.dll vcomp140.dll) do if not exist "%dirbin%\%%F" goto fail

%gencase% "%dirdef%\%name%_Def" "%dirout%\%name%" -save:all
if not "%ERRORLEVEL%" == "0" goto fail

rem One fresh process: initial sigma0, hydrostatic p0, actual preload, continuous release/collapse.
rem XML sets dt=2.5us, release10s and TimeMax13s; evolving necessary limits stay active.
%dualsphysics% %runmode% -stable -mdbc_freeslip "%dirout%\%name%" "%dirout%" -dirdataout data -svres
if not "%ERRORLEVEL%" == "0" goto fail

echo Calculation exited normally. Copy the COMPLETE %dirout% folder back for analysis.
echo Native safety, pre-release state and paper-reference comparison remain separate reviews.
echo This launcher performs GenCase and the solver only; no plotting or restart.
if not "%~3" == "--unattended" pause
exit /b 0

:exists
echo Output already exists: %dirout%. Nothing was overwritten or restarted.
if not "%~3" == "--unattended" pause
exit /b 1

:fail
echo Execution aborted. Existing and partial outputs are preserved; diagnose before a new attempt.
if not "%~3" == "--unattended" pause
exit /b 1
