@echo off
setlocal EnableDelayedExpansion

set name=S1_BGStop_T005
set dirout=%name%_gpu_out
set dirbin=..\..\..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysics="%dirbin%\DualSPHysics5.2_GEO_win64.exe"

if exist %dirout% rd /s /q %dirout%
if not exist %dirout% mkdir %dirout%

%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysics% -gpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail

echo All done
goto end

:fail
echo Execution aborted.

:end
pause
