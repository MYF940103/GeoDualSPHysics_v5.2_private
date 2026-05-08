@echo off
setlocal
cd /d %~dp0
..\..\..\bin\windows\DualSPHysics5.2CPU_win64.exe -cpu CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40_out\CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40 CaseStaticSoilColumn_cDBC_Dry_Restart_Part40To40_out -dirdataout data_release_restart -partbegin:40:40 CaseStaticSoilColumn_cDBC_Dry_DDT0_RestartReady_out\data -sv:csv,binx
exit /b %errorlevel%
