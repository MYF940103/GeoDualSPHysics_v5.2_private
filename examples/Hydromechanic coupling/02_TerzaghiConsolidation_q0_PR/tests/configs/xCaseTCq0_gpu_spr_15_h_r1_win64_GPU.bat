@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

rem Fresh GPU diagnostic; existing output is protected.
"D:\Anaconda3\python.exe" -B "..\support\gpu_coupled_run.py" --name gpu_spr_15_h_r1 --duration 15 --dt 0.000005 --interval 0.001 --build "D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\tests\logs\gpu_coupled_Release_r2.build.json" --run
if not "%ERRORLEVEL%" == "0" goto fail
popd
exit /b 0

:fail
popd
exit /b 1
