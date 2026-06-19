@echo off
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\run_stage1_dp001_gpu.ps1"
set err=%ERRORLEVEL%
popd
exit /b %err%
