param(
  [double]$TargetTv = 1.0,
  [double]$Xi = 0.02,
  [double]$PoreDtSafety = 1.0
)

$ErrorActionPreference = "Stop"

$driver = Join-Path $PSScriptRoot "run_full_validation_q0.ps1"
$work = Join-Path $PSScriptRoot "full_validation"
$status = Join-Path $work "low_k_fixeddt_status.csv"

New-Item -ItemType Directory -Force -Path $work | Out-Null
"case,k,dtfixed,poredtsafety,targettv,status,start,end" | Set-Content -Path $status -Encoding ASCII

function Run-LowKCase([string]$kText, [double]$dtFixed) {
  $case = "CaseTerzaghiConsolidation_q0_PR_full_k$($kText.Replace('e-', 'em'))"
  $start = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$case,$kText,$dtFixed,$PoreDtSafety,$TargetTv,started,$start," | Add-Content -Path $status -Encoding ASCII
  Write-Host "[$start] Starting low-k validation: k=$kText, DtFixed=$dtFixed, TargetTv=$TargetTv"
  & $driver -KCases $kText -TargetTv $TargetTv -Xi $Xi -DtFixed $dtFixed -PoreDtSafety $PoreDtSafety
  $end = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$case,$kText,$dtFixed,$PoreDtSafety,$TargetTv,done,$start,$end" | Add-Content -Path $status -Encoding ASCII
  Write-Host "[$end] Finished low-k validation: k=$kText"
}

Run-LowKCase "1e-3" 1e-6
Run-LowKCase "1e-4" 1e-5
