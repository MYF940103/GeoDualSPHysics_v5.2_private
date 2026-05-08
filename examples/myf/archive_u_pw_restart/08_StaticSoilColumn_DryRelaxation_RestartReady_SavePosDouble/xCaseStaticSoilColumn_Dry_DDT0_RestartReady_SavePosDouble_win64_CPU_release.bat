@echo off
setlocal
cd /d %~dp0
..\..\..\bin\windows\GenCase_win64.exe CaseStaticSoilColumn_Dry_DDT0_RestartReady_SavePosDouble_Def CaseStaticSoilColumn_Dry_DDT0_RestartReady_SavePosDouble_out\CaseStaticSoilColumn_Dry_DDT0_RestartReady_SavePosDouble -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64.exe -cpu -mdbc CaseStaticSoilColumn_Dry_DDT0_RestartReady_SavePosDouble_out\CaseStaticSoilColumn_Dry_DDT0_RestartReady_SavePosDouble CaseStaticSoilColumn_Dry_DDT0_RestartReady_SavePosDouble_out -dirdataout data -saveposdouble:1 -sv:csv,binx
exit /b %errorlevel%
