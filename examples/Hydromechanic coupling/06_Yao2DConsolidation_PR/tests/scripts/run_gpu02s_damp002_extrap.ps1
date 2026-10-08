$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$testsDir = Split-Path -Parent $scriptDir
Set-Location $testsDir
New-Item -ItemType Directory -Force -Path 'outputs','logs' | Out-Null
$case = 'CaseYao2DConsolidation_PR'
$out = 'outputs\CaseYao2DConsolidation_PR_gpu02s_dp01_damp002_regencheck_slip1_out'
$logPrefix = 'logs\run_gpu02s_damp002_regencheck_slip1'
$bin = '..\..\..\..\bin\windows'
$vars = '+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace'
if(Test-Path $out){ Remove-Item -Recurse -Force $out }
& "$bin\GenCase_win64.exe" "..\CaseYao2DConsolidation_PR_Def" "$out\$case" -save:all *> "${logPrefix}_gencase.log"
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
& "$bin\DualSPHysics5.2_GEO_win64.exe" -gpu -mdbc "$out\$case" "$out" -dirdataout data -svres -svextraparts:1 -tmax:0.2 -tout:0.02 *> "${logPrefix}_solver.log"
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
$vtkdir = "$out\particles"
& "$bin\PartVTK_win64.exe" -dirin "$out\data" -savevtk "$vtkdir\PartBound" -onlytype:-all,bound -vars:$vars *> "${logPrefix}_partvtk_bound.log"
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
& "$bin\PartVTK_win64.exe" -dirin "$out\data" -savevtk "$vtkdir\PartFluid" -onlytype:-all,fluid -vars:$vars *> "${logPrefix}_partvtk.log"
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
exit 0
