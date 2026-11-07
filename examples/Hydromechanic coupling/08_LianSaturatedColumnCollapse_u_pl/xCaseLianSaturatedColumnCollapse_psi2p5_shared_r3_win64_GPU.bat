@echo off
setlocal
rem Unified r3 material; reuse the original certified r2 GPU elastic PRE.
set "C08_PRELOAD_SOURCE=CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out"
call "%~dp0support\run_lian_collapse_shared_r3_win64.bat" psi2p5 GPU %*
exit /b %ERRORLEVEL%
