@echo off
setlocal
cd /d %~dp0
..\..\..\bin\windows\GenCase_win64.exe CaseRestartPrecision_SavePosDouble_Dry_Part40To40_Def CaseRestartPrecision_SavePosDouble_Dry_Part40To40_out\CaseRestartPrecision_SavePosDouble_Dry_Part40To40 -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu -mdbc CaseRestartPrecision_SavePosDouble_Dry_Part40To40_out\CaseRestartPrecision_SavePosDouble_Dry_Part40To40 CaseRestartPrecision_SavePosDouble_Dry_Part40To40_out -dirdataout data -partbegin:40:40 ..\08_StaticSoilColumn_DryRelaxation_RestartReady_SavePosDouble\CaseStaticSoilColumn_Dry_DDT0_RestartReady_SavePosDouble_out\data -sv:csv,binx
exit /b %errorlevel%
