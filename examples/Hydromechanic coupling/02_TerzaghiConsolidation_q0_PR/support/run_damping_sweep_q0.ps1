param(
  [double]$TMax = 0.11,
  [double]$TOut = 0.0025
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
$work = Join-Path $PSScriptRoot "damping_sweep"
$summary = Join-Path $work "run_status.csv"

New-Item -ItemType Directory -Force -Path $work | Out-Null
"case,xi,status,start,end" | Set-Content -Path $summary -Encoding ASCII

$cases = @(
  @{ xi = "4e-5"; tag = "xi4e5" },
  @{ xi = "0.01"; tag = "xi0p01" },
  @{ xi = "0.02"; tag = "xi0p02" },
  @{ xi = "0.04"; tag = "xi0p04" },
  @{ xi = "0.05"; tag = "xi0p05" }
)

foreach($cfg in $cases){
  $xi = $cfg.xi
  $case = "$($baseCase)_$($cfg.tag)"
  $def = Join-Path $root "$($case)_Def.xml"
  $dirout = Join-Path $root "$($case)_out"
  $log = Join-Path $work "$($case).log"
  $start = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$case,$xi,started,$start," | Add-Content -Path $summary -Encoding ASCII
  Write-Host "[$start] Starting $case, SoilDampingCoef=$xi"

  [xml]$doc = Get-Content -Path $baseDef
  $param = $doc.case.execution.parameters.parameter | Where-Object { $_.key -eq "SoilDampingCoef" }
  if(-not $param){ throw "SoilDampingCoef parameter not found in $baseDef" }
  $param.value = $xi
  $param.comment = "Damping sweep coefficient xi"
  $doc.Save($def)

  if(Test-Path $dirout){ Remove-Item -Recurse -Force -LiteralPath $dirout }

  Push-Location $root
  try{
    & $gencase "$($case)_Def" "$dirout\$case" -save:all *> $log
    if($LASTEXITCODE -ne 0){ throw "GenCase failed for $case with code $LASTEXITCODE" }
    & $solver -cpu -mdbc "$dirout\$case" $dirout -dirdataout data -svres -svextraparts:1 -tmax:$TMax -tout:$TOut *>> $log
    if($LASTEXITCODE -ne 0){ throw "DualSPHysics failed for $case with code $LASTEXITCODE" }
    $vtkdir = Join-Path $dirout "particles"
    & $partvtk -dirin "$dirout\data" -savevtk "$vtkdir\PartFluid" -onlytype:-bound -vars:$vars *>> $log
    if($LASTEXITCODE -ne 0){ throw "PartVTK failed for $case with code $LASTEXITCODE" }
  }
  finally{
    Pop-Location
  }

  $end = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$case,$xi,done,$start,$end" | Add-Content -Path $summary -Encoding ASCII
  Write-Host "[$end] Finished $case"
}

py (Join-Path $PSScriptRoot "summarize_damping_sweep_q0.py")
