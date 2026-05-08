@echo off
setlocal
cd /d %~dp0
..\..\..\bin\windows\GenCase_win64.exe CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40_Def CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40_out\CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40 -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40_out\CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40 CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40_out -dirdataout data -partbegin:40:40 CaseStaticSoilColumn_cDBC_Dry_DDT0_RestartReady_out\data -sv:csv,binx
exit /b %errorlevel%
