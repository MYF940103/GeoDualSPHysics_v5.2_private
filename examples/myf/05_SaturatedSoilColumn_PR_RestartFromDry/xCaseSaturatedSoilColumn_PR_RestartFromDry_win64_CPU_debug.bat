@echo off
setlocal
cd /d %~dp0
..\..\..\bin\windows\GenCase_win64.exe CaseSaturatedSoilColumn_PR_RestartFromDry_Def CaseSaturatedSoilColumn_PR_RestartFromDry_out\CaseSaturatedSoilColumn_PR_RestartFromDry -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu -mdbc ^
  CaseSaturatedSoilColumn_PR_RestartFromDry_out\CaseSaturatedSoilColumn_PR_RestartFromDry ^
  CaseSaturatedSoilColumn_PR_RestartFromDry_out ^
  -dirdataout data ^
  -partbegin:40:40 ..\04_StaticSoilColumn_DryRelaxation_RestartReady\CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\data ^
  -sv:csv,binx
exit /b %errorlevel%
