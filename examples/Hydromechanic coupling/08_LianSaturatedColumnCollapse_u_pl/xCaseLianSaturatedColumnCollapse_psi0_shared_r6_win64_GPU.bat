@echo off
setlocal
rem r6 psi0-only CompletedOnly/n3 GPU diagnostic; retain the original certified GPU PRE.
set "C08_PRELOAD_SOURCE=CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out"
call "%~dp0support\run_lian_collapse_shared_r6_win64.bat" psi0 GPU %*
exit /b %ERRORLEVEL%
