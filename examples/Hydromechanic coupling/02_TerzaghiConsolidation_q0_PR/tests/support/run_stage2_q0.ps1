param(
  [string[]]$Tags = @("s2p0138_k1em2"),
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

$caseByTag = @{
  "s2p0138_k1em2" = @{
    case = "CaseTzq0_s2p0138_k1em2"
    restartPart = 138
    restartDataRel = "tests\outputs\CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010_out\data"
    timeOut = "0.00182185714285714"
  }
}

py (Join-Path $PSScriptRoot "make_stage2_q0_tests.py")

foreach($tag in $Tags){
  if(-not $caseByTag.ContainsKey($tag)){
    throw "Unknown Stage2 tag: $tag"
  }
  $meta = $caseByTag[$tag]
  $case = $meta.case
  $restartPart = $meta.restartPart
  $restartDataRel = $meta.restartDataRel
  $restartFile = Join-Path $caseRoot "$restartDataRel\Part_$($restartPart.ToString('0000')).bi4"
  if(-not (Test-Path -LiteralPath $restartFile)){
    throw "Missing restart file: $restartFile"
  }

  $defRelNoExt = "tests\configs\$($case)_Def"
  $outdir = Join-Path $tests "outputs\$($case)_out"
  $outdirRel = "tests\outputs\$($case)_out"
  $caseRelPrefix = Join-Path $outdirRel $case
  $figdir = Join-Path $tests "figures\$case"
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
    $solverArgs = @("-cpu", "-mdbc", "$caseRelPrefix", "$outdirRel", "-dirdataout", "data", "-svres", "-svextraparts:1", "-partbegin:$($restartPart):0", "$restartDataRel")
    & $solver @solverArgs >> $log 2>> $errlog
    if($LASTEXITCODE -ne 0){ throw "DualSPHysics failed for $case with code $LASTEXITCODE" }
    $vtkdirRel = Join-Path $outdirRel "particles"
    & $partvtk -dirin "$outdirRel\data" -savevtk "$vtkdirRel\PartFluid" -onlytype:-bound -vars:$vars >> $log 2>> $errlog
    if($LASTEXITCODE -ne 0){ throw "PartVTK failed for $case with code $LASTEXITCODE" }
  }
  finally{
    Pop-Location
  }

  py (Join-Path $PSScriptRoot "postprocess_stage2_q0.py") --case $case --particles (Join-Path $outdir "particles") --figdir $figdir --time-out $meta.timeOut
}
