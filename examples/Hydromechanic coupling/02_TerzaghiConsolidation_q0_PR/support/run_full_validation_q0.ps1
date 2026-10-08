param(
  [string[]]$Tags = @("k1em3", "k5em4", "k1em4"),
  [switch]$Clean
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$statusDir = Join-Path $PSScriptRoot "full_validation"
$status = Join-Path $statusDir "run_status.csv"

$caseByTag = @{
  "k1em3" = @{
    case = "CaseTerzaghiConsolidation_q0_PR_full_k1em3"
    bat = "xCaseTerzaghiConsolidation_q0_PR_full_k1em3_win64_CPU.bat"
    k = "1e-3"
    targetTv = "2"
  }
  "k5em4" = @{
    case = "CaseTerzaghiConsolidation_q0_PR_full_k5em4"
    bat = "xCaseTerzaghiConsolidation_q0_PR_full_k5em4_win64_CPU.bat"
    k = "5e-4"
    targetTv = "1"
  }
  "k1em4" = @{
    case = "CaseTerzaghiConsolidation_q0_PR_full_k1em4"
    bat = "xCaseTerzaghiConsolidation_q0_PR_full_k1em4_win64_CPU.bat"
    k = "1e-4"
    targetTv = "1"
  }
}

New-Item -ItemType Directory -Force -Path $statusDir | Out-Null
"case,k,target_tv,status,start,end,exit_code,stdout,stderr" | Set-Content -Path $status -Encoding ASCII

$jobs = @()
foreach($tag in $Tags){
  if(-not $caseByTag.ContainsKey($tag)){
    throw "Unknown formal q0 tag: $tag"
  }
  $meta = $caseByTag[$tag]
  $bat = Join-Path $root $meta.bat
  if(-not (Test-Path -LiteralPath $bat)){
    throw "Missing BAT file: $bat"
  }

  $start = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $stdout = Join-Path $statusDir "$($meta.case).out.log"
  $stderr = Join-Path $statusDir "$($meta.case).err.log"
  "$($meta.case),$($meta.k),$($meta.targetTv),started,$start,,,${stdout},${stderr}" | Add-Content -Path $status -Encoding ASCII
  Write-Host "[$start] Starting $($meta.case), k=$($meta.k), target Tv=$($meta.targetTv)"

  $batArgs = if($Clean){ "/d /c `"`"$bat`" -force`"" } else { "/d /c `"`"$bat`"`"" }
  $process = Start-Process -FilePath "cmd.exe" -ArgumentList $batArgs -WorkingDirectory $root -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
  $jobs += [pscustomobject]@{
    tag = $tag
    meta = $meta
    start = $start
    stdout = $stdout
    stderr = $stderr
    process = $process
  }
}

$failed = @()
foreach($job in $jobs){
  Wait-Process -Id $job.process.Id
  $job.process.Refresh()
  $end = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $exitCode = $job.process.ExitCode
  $state = if($exitCode -eq 0){ "done" } else { "failed" }
  "$($job.meta.case),$($job.meta.k),$($job.meta.targetTv),$state,$($job.start),$end,$exitCode,$($job.stdout),$($job.stderr)" | Add-Content -Path $status -Encoding ASCII
  Write-Host "[$end] Finished $($job.meta.case) with exit code $exitCode"
  if($exitCode -ne 0){
    $failed += $job.meta.case
  }
}

if($failed.Count -gt 0){
  throw "Formal q0 validation failed for: $($failed -join ', ')"
}

py (Join-Path $PSScriptRoot "summarize_full_validation_q0.py")
