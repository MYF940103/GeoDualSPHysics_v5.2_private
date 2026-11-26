@echo off
setlocal
pushd "%~dp0" || exit /b 1
if not defined C08_PYTHON (
    if exist "D:\anaconda3\python.exe" (
        set "C08_PYTHON=D:\anaconda3\python.exe"
    ) else (
        set "C08_PYTHON=python"
    )
)
"%C08_PYTHON%" -B -X utf8 "support\run_lian_tpi.py" --group all %*
set "rc=%ERRORLEVEL%"
popd
if not "%rc%"=="0" echo C08 TPI stopped with exit code %rc%. Existing results are preserved.
if not defined C08_BATCH_MODE pause
exit /b %rc%
