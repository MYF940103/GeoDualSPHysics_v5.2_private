@echo off
setlocal
rem r5 GPU receiver; only psi0 admitted, others locked; keep the original certified GPU PRE.
set "C08_PRELOAD_SOURCE=CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out"
call "%~dp0support\run_lian_collapse_shared_r5_win64.bat" psi0 GPU %*
exit /b %ERRORLEVEL%
