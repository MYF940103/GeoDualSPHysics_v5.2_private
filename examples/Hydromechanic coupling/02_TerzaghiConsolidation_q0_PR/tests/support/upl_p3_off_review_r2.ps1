param(
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='p3_r2',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Report='upl_p3_off_review_r2'
)
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$logs=Join-Path $tests 'logs'
$output=Join-Path $logs ($Report+'.check.json')
if(Test-Path -LiteralPath $output){throw 'Retained review protected'}
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()}}
$groups=@();$frames=0
foreach($configuration in @('DebugCPU','ReleaseCPU')){
  $buildPath=Join-Path $logs "upl_p2_${configuration}_${Label}.build.json"
  $build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
  if($build.status -ne 'built_not_run'){throw 'Fixture build was not successful'}
  foreach($item in $build.inputs){$now=Entry $item.path;if($now.bytes -ne $item.bytes -or $now.sha256 -ne $item.sha256){throw "Frozen build input changed: $($item.path)"}}
  foreach($suffix in @('default_OFF','open_default_OFF','s8_observer','s128_observer','open_s128_observer')){
    $path=Join-Path $logs "upl_p2_${configuration}_${Label}_${suffix}.check.json"
    $check=Get-Content -Raw -LiteralPath $path|ConvertFrom-Json
    if(!$check.passed -or !$check.all15_original_arrays_ID_aligned_0ULP -or !$check.saved_clock_step_dterror_exact){throw "Comparison failed: $path"}
    $expected=if($suffix -eq 's8_observer'){2}else{17}
    if($check.actual_native_samples -ne $expected -or $check.receipts.Count -ne $expected){throw 'Sample coverage mismatch'}
    foreach($receipt in $check.receipts){
      $now=Entry $receipt.path;if($now.bytes -ne $receipt.bytes -or $now.sha256 -ne $receipt.sha256){throw 'Comparison receipt changed'}
      $sample=Get-Content -Raw -LiteralPath $receipt.path|ConvertFrom-Json
      if(!$sample.passed -or $sample.native_count -ne 1040 -or $sample.arrays -ne 15 -or !$sample.native_ID_aligned -or !$sample.all_original_physical_array_bits_identical -or !$sample.saved_time_step_dterror_exact -or !$sample.no_exclusions){throw 'Native sample failed'}
    }
    $frames+=$expected
    $groups+=@{configuration=$configuration;comparison=$suffix;frames=$expected;check=(Entry $path)}
  }
  $calls=Get-ChildItem -LiteralPath $logs -Filter "upl_p2_${configuration}_${Label}*.run.json"
  foreach($path in $calls){$call=Get-Content -Raw -LiteralPath $path.FullName|ConvertFrom-Json;if($call.exit_code -ne 0 -or !$call.owned_call_exited){throw 'A bounded owned call did not exit successfully'}}
}
if($frames -ne 140){throw 'Total frame-pair coverage mismatch'}
$result=[ordered]@{passed=$true;label=$Label;scope='DynamicPorePressure default-OFF regression and observer equivalence after wrapper repair';groups=$groups;actual_native_frame_pairs=$frames;native_ids_per_pair=1040;existing_arrays_per_pair=15;all_bits_0ULP=$true;clock_step_dterror_exact=$true;exclusions=0;physical_acceptance=$false;raw_BI4_cloud_backup_claimed=$false}
[IO.File]::WriteAllText($output,($result|ConvertTo-Json -Depth 8)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "PASS: $frames native frame pairs; 1040 IDs; 15 arrays; clocks/steps/dterror exact. $output"
