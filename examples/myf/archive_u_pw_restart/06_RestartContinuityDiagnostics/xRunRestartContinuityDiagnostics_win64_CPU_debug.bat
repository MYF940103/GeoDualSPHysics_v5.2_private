@echo off
setlocal
cd /d %~dp0
echo ==== CaseRestartContinuity_A_DryRestart ====
..\..\..\bin\windows\GenCase_win64.exe CaseRestartContinuity_A_DryRestart_Def CaseRestartContinuity_A_DryRestart_out\CaseRestartContinuity_A_DryRestart -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu -mdbc ^
  CaseRestartContinuity_A_DryRestart_out\CaseRestartContinuity_A_DryRestart ^
  CaseRestartContinuity_A_DryRestart_out ^
  -dirdataout data ^
  -partbegin:40:0 ..\04_StaticSoilColumn_DryRelaxation_RestartReady\CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\data ^
  -sv:csv,binx
if errorlevel 1 exit /b %errorlevel%
echo ==== CaseRestartContinuity_B_HydroDiagOnly ====
..\..\..\bin\windows\GenCase_win64.exe CaseRestartContinuity_B_HydroDiagOnly_Def CaseRestartContinuity_B_HydroDiagOnly_out\CaseRestartContinuity_B_HydroDiagOnly -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu -mdbc ^
  CaseRestartContinuity_B_HydroDiagOnly_out\CaseRestartContinuity_B_HydroDiagOnly ^
  CaseRestartContinuity_B_HydroDiagOnly_out ^
  -dirdataout data ^
  -partbegin:40:0 ..\04_StaticSoilColumn_DryRelaxation_RestartReady\CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\data ^
  -sv:csv,binx
if errorlevel 1 exit /b %errorlevel%
echo ==== CaseRestartContinuity_C_HydrostaticPR ====
..\..\..\bin\windows\GenCase_win64.exe CaseRestartContinuity_C_HydrostaticPR_Def CaseRestartContinuity_C_HydrostaticPR_out\CaseRestartContinuity_C_HydrostaticPR -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu -mdbc ^
  CaseRestartContinuity_C_HydrostaticPR_out\CaseRestartContinuity_C_HydrostaticPR ^
  CaseRestartContinuity_C_HydrostaticPR_out ^
  -dirdataout data ^
  -partbegin:40:0 ..\04_StaticSoilColumn_DryRelaxation_RestartReady\CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\data ^
  -sv:csv,binx
if errorlevel 1 exit /b %errorlevel%
echo ==== CaseRestartContinuity_D_AnalyticalTopDrained ====
..\..\..\bin\windows\GenCase_win64.exe CaseRestartContinuity_D_AnalyticalTopDrained_Def CaseRestartContinuity_D_AnalyticalTopDrained_out\CaseRestartContinuity_D_AnalyticalTopDrained -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe -cpu -mdbc ^
  CaseRestartContinuity_D_AnalyticalTopDrained_out\CaseRestartContinuity_D_AnalyticalTopDrained ^
  CaseRestartContinuity_D_AnalyticalTopDrained_out ^
  -dirdataout data ^
  -partbegin:40:0 ..\04_StaticSoilColumn_DryRelaxation_RestartReady\CaseStaticSoilColumn_Dry_DDT0_RestartReady_out\data ^
  -sv:csv,binx
if errorlevel 1 exit /b %errorlevel%
exit /b 0
