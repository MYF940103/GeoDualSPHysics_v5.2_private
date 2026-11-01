# Read-only posthoc sealing of the failed first actual-helper component attempt.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $tests 'logs'
function Entry([string]$path){$a=Get-Item -LiteralPath $path;[ordered]@{path=$a.FullName;bytes=$a.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($entries){foreach($a in $entries){$b=Entry $a.path;if($a.sha256 -ne $b.sha256 -or $a.bytes -ne $b.bytes){throw "Evidence changed before sealing: $($a.path)"}}}
$out=Join-Path $logs 'upl_p3_actual_DebugCPU_r1.failure_seal.json'
if(Test-Path -LiteralPath $out){throw 'Retained failure seal protected'}
$buildPath=Join-Path $logs 'upl_p3_actual_DebugCPU_r1.build.json';$runPath=Join-Path $logs 'upl_p3_actual_DebugCPU_r1_run.run.json'
$build=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json;$run=Get-Content -LiteralPath $runPath -Raw|ConvertFrom-Json
if($build.compile_exit -ne 0 -or $build.link_exit -ne 0 -or $run.actual_exit -ne 1 -or $null -ne $run.control_exit){throw 'Unexpected attempt state'}
Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify $build.controls;Verify @($build.program,$build.log,$run.log,$run.build_receipt)
foreach($a in $build.runtime){Verify @($a.original,$a.copy)}
$authPath=Join-Path $logs 'upl_p3_actual_build_r1.json';$auth=Get-Content -LiteralPath $authPath -Raw|ConvertFrom-Json
foreach($a in $auth.source){Verify @($a.original,$a.snapshot)}
$raw=@(Get-ChildItem -LiteralPath (Join-Path $tests 'outputs\upl_p3_actual_DebugCPU_r1_run') -File -Recurse|Sort-Object FullName|ForEach-Object {Entry $_.FullName})
$record=[ordered]@{
  status='first_actual_ct_sentinel_failed_retained_no_later_stage_admitted'
  utc=[DateTime]::UtcNow.ToString('o')
  build_receipt=(Entry $buildPath);run_receipt=(Entry $runPath);authoritative_receipt=(Entry $authPath)
  frozen_fixture=$build.snapshots;production_snapshot=$auth.source
  original_input_bindings_verified=$build.inputs.Count;runtime_pairs_verified=$build.runtime.Count
  raw_outputs=$raw;output_manifest_posthoc=$true;pre_run_output_attestation=$false
  failed_case='2D regular nonperiodic, k=0, theta observed by actual ct; sentinel check failed before theta CSV/other fields were written'
  stopped_at='first CtSuppression call; no rate Check cases, no default-OFF control, no Release companion run'
  observed='Program exit1 with Old ct pressure source was not suppressed. Exact changed array value was not serialized, so no direct numeric value is asserted.'
  source_explanation='JSphCpu.cpp line2893 wrapper unconditionally memset(t.porepressrate,0,sizeof(float)*t.np) before new !DynamicPorePressure source suppression. It clears the 1234567f sentinel even when all old accumulations are disabled.'
  process='Synchronous owned program exited; no solver/monitor was launched or left running by this recipe.'
  unchanged_gates=$true;physical_acceptance=$false;seal_recipe=(Entry $PSCommandPath)
}
[IO.File]::WriteAllText($out,($record|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $out"
