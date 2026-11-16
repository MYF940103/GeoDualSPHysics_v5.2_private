@echo off
call "D:\Program Files\VS2022\VC\Auxiliary\Build\vcvarsall.bat" x64 -vcvars_ver=14.36 >nul
if errorlevel 1 exit /b %errorlevel%
set
