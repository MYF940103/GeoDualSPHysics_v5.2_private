@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

rem Fresh production-step diagnostic; existing output is protected.
"D:\Anaconda3\python.exe" -B "..\support\gpu_coupled_run.py" --name gpu_full_2tv_gpu_r1 --duration 72.88429 --dt 0.00001 --interval 0.01 --build "D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\tests\logs\gpu_coupled_Release_r2.build.json" --backend gpu --save --run
if not "%ERRORLEVEL%" == "0" goto fail
popd
exit /b 0

:fail
popd
exit /b 1
