$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$logs=Join-Path $tests 'logs'
$target=Join-Path $logs 'upl_p3_time_stage_r2.check.json'
if(Test-Path -LiteralPath $target){throw 'Retained stage review protected'}
function Entry([string]$path){
  $f=Get-Item -LiteralPath $path
  [ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Verify($entries){
  foreach($item in $entries){
    $now=Entry $item.path
    if($now.bytes -ne $item.bytes -or $now.sha256 -ne $item.sha256){throw "Frozen binding changed: $($item.path)"}
  }
}
$freezePath=Join-Path $logs 'upl_p3_time_build_r1.json'
$freeze=Get-Content -LiteralPath $freezePath -Raw|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Authoritative build failed'}
foreach($s in $freeze.source){Verify @($s.original,$s.snapshot)}
Verify $freeze.programs;Verify $freeze.logs
$offPath=Join-Path $logs 'upl_p3_time_off_r1.check.json'
$off=Get-Content -LiteralPath $offPath -Raw|ConvertFrom-Json
if(!$off.passed -or !$off.all_bits_0ULP -or !$off.clock_step_dterror_exact -or $off.actual_native_frame_pairs -ne 140 -or $off.exclusions -ne 0){throw 'Default-OFF regression failed'}
$guardPath=Join-Path $logs 'upl_p3_timeguard_review_r1.check.json'
$guard=Get-Content -LiteralPath $guardPath -Raw|ConvertFrom-Json
if(!$guard.passed -or $guard.max_independent_scale_relative_error -ne 0 -or $guard.actual_first_step_rejections -ne 8 -or $guard.first_step_native_state_pairs -ne 144){throw 'Independent guard tests failed'}
Verify $guard.text_files
$groups=@();$jobs=0;$comparisons=0
foreach($configuration in @('DebugCPU','ReleaseCPU')){
  foreach($window in @('wave','m4')){
    $path=Join-Path $logs "upl_p3_time_${window}_${configuration}_r1.check.json"
    $check=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
    $n=if($window -eq 'wave'){257}else{65}
    $expectedJobs=if($window -eq 'wave'){10}else{4}
    if(!$check.passed -or $check.solver_jobs -ne $expectedJobs -or $check.actual_time_pairs -ne $n -or $check.native_ids -ne 128 -or $check.serialized_columns -ne 26){throw "Incomplete integration check: $path"}
    Verify $check.receipts;Verify $check.files
    foreach($receipt in $check.receipts){
      $call=Get-Content -LiteralPath $receipt.path -Raw|ConvertFrom-Json
      if($receipt.path.EndsWith('.run.json')){
        if($call.exit_code -ne 0 -or !$call.owned_call_exited){throw 'An owned integration/comparison call failed'}
      }elseif($receipt.path.EndsWith('.check.json')){
        if(!$call.passed){throw 'An integration comparison check failed'}
      }else{throw 'Unexpected receipt type'}
    }
    $jobs+=$check.solver_jobs;$comparisons+=$check.comparison_jobs
    $halfPath=Join-Path $logs "upl_p3_time_${window}_${configuration}_r1_k1_half_compare.check.json"
    $half=Get-Content -LiteralPath $halfPath -Raw|ConvertFrom-Json
    if(!$half.passed -or !$half.half_comparison -or $half.max_pressure_RMS_Pa -gt 5 -or $half.max_material_displacement_mm -gt .005){throw 'Original independent half bounds failed'}
    $groups+=@{configuration=$configuration;window=$window;check=(Entry $path);half=(Entry $halfPath);pressure_half_max_Pa=$half.max_pressure_RMS_Pa;displacement_half_max_mm=$half.max_material_displacement_mm}
  }
}
if($jobs -ne 28 -or $comparisons -ne 42){throw 'Unexpected admitted integration coverage'}
$result=[ordered]@{
  passed=$true;utc=[DateTime]::UtcNow.ToString('o')
  scope='Private CPU necessary-scale/domain/step rejection, old-OFF equivalence and bounded actual periodic integration'
  build=(Entry $freezePath);default_OFF=(Entry $offPath);guard=(Entry $guardPath);groups=$groups
  fresh_integration_jobs=$jobs;integration_comparison_calls=$comparisons
  default_OFF_native_pairs=140;actual_first_step_rejections=8
  source_review=(Entry (Join-Path $tests 'notes\upl_p3_time_source_review_r1.json'))
  half_ULP_placeholder_is_not_exact_agreement=$true
  offline_review_repair='Initial preflight confused comparison-check JSON with process receipts; no r1 report was emitted. This r2 review checks each type separately; no solver was rerun or threshold changed.'
  exact_HG_restart=$false;public_switch=$false;GPU=$false;physical_acceptance=$false
}
[IO.File]::WriteAllText($target,($result|ConvertTo-Json -Depth 10)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output 'PASS: 28 bounded integration jobs, 42 comparisons, independent guard tests and 140 default-OFF native pairs.'
