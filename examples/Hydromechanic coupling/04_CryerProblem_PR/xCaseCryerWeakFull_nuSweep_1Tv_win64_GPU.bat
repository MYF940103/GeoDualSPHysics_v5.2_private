@echo off
setlocal
pushd "%~dp0" || exit /b 1
if defined CRYER_PYTHON goto configured_python
where py.exe >nul 2>nul
if not errorlevel 1 (
  py.exe -3.11 -B -X utf8 "%~dp0support\run_cryer_weak_nu_sweep.py" %*
  goto finish
)
where python.exe >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 with NumPy, SciPy, Pandas and Matplotlib is required. Set CRYER_PYTHON.
  popd
  exit /b 1
)
python.exe -B -X utf8 "%~dp0support\run_cryer_weak_nu_sweep.py" %*
goto finish
:configured_python
"%CRYER_PYTHON%" -B -X utf8 "%~dp0support\run_cryer_weak_nu_sweep.py" %*
:finish
set "runrc=%errorlevel%"
popd
exit /b %runrc%
