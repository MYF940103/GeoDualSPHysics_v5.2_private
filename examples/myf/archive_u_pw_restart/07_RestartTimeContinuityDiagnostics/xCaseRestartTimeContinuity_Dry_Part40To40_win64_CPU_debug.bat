@echo off
set CASE=CaseRestartTimeContinuity_Dry_Part40To40
set OUT=%CASE%_out
..\..\..\bin\windows\GenCase_win64.exe %CASE%_Def %OUT%\%CASE% -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu -mdbc %OUT%\%CASE% %OUT% -dirdataout data -partbegin:40:40 ..\04_StaticSoilColumn_DryRelaxation_RestartReady\CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\data -sv:csv,binx
exit /b %errorlevel%
