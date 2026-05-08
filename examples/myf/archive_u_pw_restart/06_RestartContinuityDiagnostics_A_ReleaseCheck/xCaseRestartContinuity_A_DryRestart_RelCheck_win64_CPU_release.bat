@echo off
set CASE=CaseRestartContinuity_A_DryRestart_RelCheck
set OUT=%CASE%_out
..\..\..\bin\windows\GenCase_win64.exe %CASE%_Def %OUT%\%CASE% -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64.exe -cpu -mdbc %OUT%\%CASE% %OUT% -dirdataout data -partbegin:40:0 ..\04_StaticSoilColumn_DryRelaxation_RestartReady\CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\data -sv:csv,binx
exit /b %errorlevel%
