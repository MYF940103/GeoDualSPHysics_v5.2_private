param(
  [string[]]$KCases = @("1e-2", "1e-3", "1e-4"),
  [double]$TargetTv = 1.0,
  [double]$Xi = 0.02,
  [double]$DtFixed = 1e-6,
  [double]$PoreDtSafety = 0.1
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$baseCase = "CaseTerzaghiConsolidation_q0_PR"
$baseDef = Join-Path $root "$($baseCase)_Def.xml"
$dirbin = Resolve-Path (Join-Path $root "..\..\..\bin\windows")
$gencase = Join-Path $dirbin "GenCase_win64.exe"
$solver = Join-Path $dirbin "DualSPHysics5.2CPU_win64.exe"
$partvtk = Join-Path $dirbin "PartVTK_win64.exe"
$vars = "+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+porepress,+porepress0,+excessporepress"
$work = Join-Path $PSScriptRoot "full_validation"
$summary = Join-Path $work "run_status.csv"

$E = 2.0e6
$nu = 0.3
$rhoW = 1000.0
$g = 9.81
$H = 1.0
$tL = 0.01
$M = $E * (1.0 - $nu) / ((1.0 + $nu) * (1.0 - 2.0 * $nu))

New-Item -ItemType Directory -Force -Path $work | Out-Null
"case,k,xi,dtfixed,poredtsafety,tmax,tout,status,start,end" | Set-Content -Path $summary -Encoding ASCII

function Get-Tag([string]$k) {
  return ($k.Replace("e-", "em").Replace("e+", "ep").Replace(".", "p"))
}

foreach($kText in $KCases){
  $k = [double]$kText
  if($k -le 0){ throw "Invalid hydraulic conductivity: $kText" }
  $cv = $k * $M / ($rhoW * $g)
  $tmax = $tL + $TargetTv * $H * $H / $cv
  $tout = [Math]::Max(0.0025, ($H * $H / $cv) / 250.0)
  $tag = "k$(Get-Tag $kText)"
  $case = "$($baseCase)_full_$tag"
  $def = Join-Path $root "$($case)_Def.xml"
  $dirout = Join-Path $root "$($case)_out"
  $log = Join-Path $work "$($case).log"
  $start = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$case,$kText,$Xi,$DtFixed,$PoreDtSafety,$tmax,$tout,started,$start," | Add-Content -Path $summary -Encoding ASCII
  Write-Host "[$start] Starting $case, k=$kText, xi=$Xi, poredtsafety=$PoreDtSafety, tmax=$tmax, tout=$tout"

  [xml]$doc = Get-Content -Path $baseDef
  $soils = $doc.case.execution.special.soils
  $khyd = $soils.HydraulicConductivity
  if(-not $khyd){ throw "HydraulicConductivity element not found in $baseDef" }
  $khyd.value = $kText
  $khyd.comment = "Full q0 validation hydraulic conductivity"
  $poredt = $soils.PoreDtSafety
  if(-not $poredt){ throw "PoreDtSafety element not found in $baseDef" }
  $poredt.value = ("{0:g}" -f $PoreDtSafety)
  $poredt.comment = "Full q0 validation pore-pressure time-step safety"

  $params = $doc.case.execution.parameters.parameter
  ($params | Where-Object { $_.key -eq "SoilDampingCoef" }).value = [string]$Xi
  ($params | Where-Object { $_.key -eq "DtFixed" }).value = ("{0:g}" -f $DtFixed)
  ($params | Where-Object { $_.key -eq "TimeMax" }).value = ("{0:g}" -f $tmax)
  ($params | Where-Object { $_.key -eq "TimeOut" }).value = ("{0:g}" -f $tout)
  $doc.Save($def)

  if(Test-Path $dirout){ Remove-Item -Recurse -Force -LiteralPath $dirout }

  Push-Location $root
  try{
    & $gencase "$($case)_Def" "$dirout\$case" -save:all *> $log
    if($LASTEXITCODE -ne 0){ throw "GenCase failed for $case with code $LASTEXITCODE" }
    & $solver -cpu -mdbc "$dirout\$case" $dirout -dirdataout data -svres -svextraparts:1 -tmax:$tmax -tout:$tout *>> $log
    if($LASTEXITCODE -ne 0){ throw "DualSPHysics failed for $case with code $LASTEXITCODE" }
    $vtkdir = Join-Path $dirout "particles"
    & $partvtk -dirin "$dirout\data" -savevtk "$vtkdir\PartFluid" -onlytype:-bound -vars:$vars *>> $log
    if($LASTEXITCODE -ne 0){ throw "PartVTK failed for $case with code $LASTEXITCODE" }
  }
  finally{
    Pop-Location
  }

  $end = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$case,$kText,$Xi,$DtFixed,$PoreDtSafety,$tmax,$tout,done,$start,$end" | Add-Content -Path $summary -Encoding ASCII
  Write-Host "[$end] Finished $case"
}

py (Join-Path $PSScriptRoot "summarize_full_validation_q0.py")
