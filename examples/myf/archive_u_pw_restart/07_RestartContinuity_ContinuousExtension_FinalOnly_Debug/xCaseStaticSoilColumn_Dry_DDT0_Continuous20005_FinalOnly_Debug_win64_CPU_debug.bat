@echo off
set CASE=CaseStaticSoilColumn_Dry_DDT0_Continuous20005_FinalOnly_Debug
set OUT=%CASE%_out
..\..\..\bin\windows\GenCase_win64.exe %CASE%_Def %OUT%\%CASE% -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu -mdbc %OUT%\%CASE% %OUT% -dirdataout data -sv:csv,binx
exit /b %errorlevel%
