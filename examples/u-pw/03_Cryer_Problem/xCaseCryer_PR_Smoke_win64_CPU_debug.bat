@echo off
setlocal
set name=CaseCryer_PR_Smoke
set dirout=%name%_out
set dirbin=..\..\..\bin\windows
set gencase="%dirbin%\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\DualSPHysics5.2CPU_win64_debug.exe"

if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysicscpu% -cpu -mdbc %dirout%\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail

echo All done
goto end
:fail
echo Execution aborted.
:end
pause
