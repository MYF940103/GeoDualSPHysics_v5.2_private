pushd "D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\01_SelfWeightConsolidation_PR"
..\..\..\bin\windows\GenCase_win64.exe CaseSelfWeightConsolidation_Scenario2_Def support\diagnostics\diag1_scenario2_analytic_fixeddt_t04\CaseSelfWeightConsolidation_Scenario2 -save:all
if errorlevel 1 exit /b 1
..\..\..\bin\windows\DualSPHysics5.2CPU_win64.exe -cpu -mdbc support\diagnostics\diag1_scenario2_analytic_fixeddt_t04\CaseSelfWeightConsolidation_Scenario2 support\diagnostics\diag1_scenario2_analytic_fixeddt_t04 -dirdataout data -svres -svextraparts:1 -tmax:0.4 -tout:0.02
if errorlevel 1 exit /b 1
mkdir support\diagnostics\diag1_scenario2_analytic_fixeddt_t04\particles
..\..\..\bin\windows\PartVTK_win64.exe -dirin support\diagnostics\diag1_scenario2_analytic_fixeddt_t04\data -savevtk support\diagnostics\diag1_scenario2_analytic_fixeddt_t04\particles\PartFluid -onlytype:-bound -vars:+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+porepress,+porepress0,+excessporepress
popd
