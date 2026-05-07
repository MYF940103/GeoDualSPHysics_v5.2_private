@echo off
setlocal
cd /d %~dp0
..\..\..\bin\windows\GenCase_win64.exe CaseStaticSoilColumn_Dry_DDT0_RestartReady_Def CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\CaseStaticSoilColumn_Dry_DDT0_RestartReady -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64.exe -cpu -mdbc CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\CaseStaticSoilColumn_Dry_DDT0_RestartReady CaseStaticSoilColumn_Dry_DDT0_RestartReady_out -dirdataout data -sv:csv,binx
exit /b %errorlevel%
