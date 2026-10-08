param(
  [string[]]$Tags = @("dt1em6"),
  [switch]$Clean
)

$ErrorActionPreference = "Stop"

$tests = Resolve-Path (Join-Path $PSScriptRoot "..")
$caseRoot = Resolve-Path (Join-Path $tests "..")
$repoRoot = Resolve-Path (Join-Path $caseRoot "..\..\..")
$bin = Join-Path $repoRoot "bin\windows"
$gencase = Join-Path $bin "GenCase_win64.exe"
$solver = Join-Path $bin "DualSPHysics5.2CPU_win64.exe"
$partvtk = Join-Path $bin "PartVTK_win64.exe"
$vars = "+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress"

py (Join-Path $PSScriptRoot "make_stage1_q0_tests.py")

foreach($tag in $Tags){
  $case = "CaseTerzaghiConsolidation_q0_PR_stage1_$tag"
  $def = Join-Path $tests "configs\$($case)_Def.xml"
  $outdir = Join-Path $tests "outputs\$($case)_out"
  $figdir = Join-Path $tests "figures\$case"
  $defRelNoExt = "tests\configs\$($case)_Def"
  $outdirRel = "tests\outputs\$($case)_out"
  $caseRelPrefix = Join-Path $outdirRel $case
  $restartPart = $null
  $restartDataRel = $null
  if($tag -eq "dt1em7_t015"){
    $restartPart = 200
    $restartDataRel = "tests\outputs\CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010_out\data"
  }
  $timeOffset = if($restartPart -ne $null){ $restartPart * 0.0005 } else { 0.0 }
  $log = Join-Path $tests "run_$case.log"
  $errlog = Join-Path $tests "run_$case.err.log"

  if($Clean -and (Test-Path -LiteralPath $outdir)){
    Remove-Item -LiteralPath $outdir -Recurse -Force
  }
  if($Clean -and (Test-Path -LiteralPath $figdir)){
    Remove-Item -LiteralPath $figdir -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path $outdir | Out-Null
  New-Item -ItemType Directory -Force -Path $figdir | Out-Null

  Push-Location $caseRoot
  try{
    & $gencase "$defRelNoExt" "$caseRelPrefix" -save:all > $log 2> $errlog
    if($LASTEXITCODE -ne 0){ throw "GenCase failed for $case with code $LASTEXITCODE" }
    $solverArgs = @("-cpu", "-mdbc", "$caseRelPrefix", "$outdirRel", "-dirdataout", "data", "-svres", "-svextraparts:1")
    if($restartPart -ne $null){
      $solverArgs += "-partbegin:$($restartPart):0"
      $solverArgs += "$restartDataRel"
    }
    & $solver @solverArgs >> $log 2>> $errlog
    if($LASTEXITCODE -ne 0){ throw "DualSPHysics failed for $case with code $LASTEXITCODE" }
    $vtkdirRel = Join-Path $outdirRel "particles"
    & $partvtk -dirin "$outdirRel\data" -savevtk "$vtkdirRel\PartFluid" -onlytype:-bound -vars:$vars >> $log 2>> $errlog
    if($LASTEXITCODE -ne 0){ throw "PartVTK failed for $case with code $LASTEXITCODE" }
  }
  finally{
    Pop-Location
  }

  py (Join-Path $PSScriptRoot "postprocess_stage1_q0.py") --case $case --particles (Join-Path $outdir "particles") --figdir $figdir --time-out 0.0005 --time-offset $timeOffset
}
