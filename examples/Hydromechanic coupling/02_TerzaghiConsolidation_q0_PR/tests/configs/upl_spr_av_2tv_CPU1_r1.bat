@echo off
setlocal EnableExtensions
pushd "%~dp0..\..\..\..\..\src"
if errorlevel 1 exit /b 1
set "program=..\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\tests\outputs\upl_spr_av_ReleaseCPU_r1\DualSPHysics5.2CPU_win64.exe"
set "case=..\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\tests\outputs\upl_spr_av_2tv_seed_r1\upl_spr_av_2tv_r1"
set "dirout=..\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\tests\outputs\upl_spr_av_2tv_CPU1_r1"
if exist "%dirout%" goto protected
if not exist "%program%" goto missing
if not exist "%case%.xml" goto missing
if not exist "%case%.bi4" goto missing
if not exist "%case%_Normals.nbi4" goto missing
"%program%" -cpu -ompthreads:1 -stable -mdbc_freeslip "%case%" "%dirout%" -dirdataout data -svres -nsteps:38212357
set "result=%ERRORLEVEL%"
popd
exit /b %result%
:protected
echo Existing output preserved; no solver was launched.
popd
exit /b 1
:missing
echo Frozen program or prepared input missing; no solver was launched.
popd
exit /b 1
