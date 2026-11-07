@echo off
setlocal
rem r4 NoPen receiver only; preserve and certify the original CPU elastic PRE.
set "C08_PRELOAD_SOURCE=CaseLianSaturatedColumnCollapse_shared_preload_r3_CPU_out"
call "%~dp0support\run_lian_collapse_shared_r4_win64.bat" psi2p5 CPU %*
exit /b %ERRORLEVEL%
