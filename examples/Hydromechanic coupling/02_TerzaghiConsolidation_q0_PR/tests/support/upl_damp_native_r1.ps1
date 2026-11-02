param([Parameter(Mandatory=$true)][ValidateSet('CPU','GPU')][string]$Backend,[Parameter(Mandatory=$true)][ValidateSet('smoke','eta0','coarse','half')][string]$Window)
# Reuse the sealed typed native reader; no new decoder, solver or build.
$ErrorActionPreference='Stop';$Backend=$Backend.ToUpperInvariant();$Window=$Window.ToLowerInvariant();$tests=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $tests 'logs';$tag='upl_damp_'+$Backend+'_'+$Window+'_r1'
$review=Join-Path $tests ('outputs\'+$tag+'_native');$record=Join-Path $logs ($tag+'.native.json');$callPath=Join-Path $logs ($tag+'_reader.call.json');$log=Join-Path $logs ($tag+'_reader.log')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Need([bool]$ok,[string]$why){if(!$ok){throw $why}}
function V($rows){foreach($e in $rows){Need ($e.path -and $e.sha256) 'Missing Entry';$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed artifact: '+$e.path)}}
function Fresh($paths){foreach($p in $paths){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
Fresh @($review,$record,$callPath,$log)
$runPath=Join-Path $logs ($tag+'.run.json');$r=J $runPath;$c=J $r.call.path
Need ($r.passed -and $r.stage -ceq 'upl_damp_run_r1' -and $r.backend -ceq $Backend -and $r.window -ceq $Window -and $r.public_project_main -and !$r.fixture_or_Run_override -and $r.source_inputs_objects_runtime_canonical_unchanged) 'Own actual Run required'
Need ($c.owned_call_exited -and $c.typed_LASTEXITCODE_captured_immediately -and $c.exit_code -is [int] -and $c.exit_code -eq 0 -and !$c.invocation_failure -and $c.target_program.sha256 -ceq $r.program.sha256) 'Original actual tool exit0 required'
if($Backend -ceq 'GPU' -and $Window -ceq 'smoke'){Need $r.memcheck_zero_errors_and_leaks 'Own GPU smoke memory check required'}
$eta0=$Window -ceq 'eta0';$helper=Join-Path $logs $(if($eta0){'upl_column_public_reader_ReleaseCPU_r1.helper.json'}else{'upl_column_ringdown_reader_ReleaseCPU_r1.helper.json'});$h=J $helper
Need ($h.passed -and $h.exact_link_closure_verified -and $h.kind -ceq 'reader' -and $h.configuration -ceq 'ReleaseCPU' -and @($h.objects).Count -eq 85 -and $h.link_object_count -eq 86 -and @($h.runtime).Count -eq 4 -and !$h.solver_started) 'Sealed CPU85 plus reader authority required'
$bindings=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_damp_plan_r1.json')),(E $runPath),$r.call,(E $helper),$h.program,$h.helper_object,$h.compile_call,$h.link_call,$h.source_build,$h.source_freeze)+@($r.inputs)+@($r.files)+@($h.tools)+@($h.libraries)+@($h.objects)
# The old reader's archived build is provenance, not a claim that its old source originals equal today's solver.
foreach($p in $h.runtime){$bindings+=@($p.original,$p.copy)}
$data=Join-Path (Split-Path -Parent $r.run_out.path) 'data';$argv=@('--read',$Backend,$data)
if($eta0){$argv+=@('769','0.0000025',$review)}else{$argv+=@($Window,$review)}
V $bindings;$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$saved=$ErrorActionPreference
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $h.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{$ErrorActionPreference=$saved}
Save $callPath ([ordered]@{program=$h.program;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;log=(E $log);pure_native_reader=$true;solver_or_build_invoked=$false})
$done=$null;$completion=$null;$files=@();$unchanged=$false;$historyRows=0
try{
  Need ($code -is [int] -and $code -eq 0 -and !$failure) 'Reader failed; repair offline, never rerun completed solver'
  $completion=E (Join-Path $review 'completion.json');$done=J $completion.path;$samples=[int]$r.job.expected_samples;$smoke=$Window -ceq 'smoke'
  Need ($done.passed -and $done.backend -ceq ($Backend+'_public') -and $done.samples -eq $samples -and $done.native_count -eq 1000 -and $done.fixed_count -eq 40 -and $done.physical_columns -eq 26 -and $done.native_total_arrays -eq 22 -and $done.PART_typed_public_metadata_verified -and $done.public_master_on -and $done.no_exclusions -and $done.all_exported_physical_fields_finite -and !$done.physical_acceptance) 'Typed public22/native1040/finite/schema check rejected'
  Need ($done.max_ledger_relative_error -le 5e-13 -and $done.dt_s -eq $r.job.dt_s -and [Math]::Abs([double]$done.actual_end_s-[double]$r.job.end_s) -le 1e-14 -and $done.max_noninitial_signed_dterror_s -le 1e-14 -and $done.noninitial_signed_dterror_intervals -eq ($samples-1)) 'Original ledger/actual-time/necessary-step checks rejected'
  if(!$eta0){Need ($done.stage -ceq 'upl_column_ringdown_native_r1' -and $done.preset -ceq $Window -and $done.actual_time_step_locked_dt_exact -and $done.planned_completed_steps -eq $r.job.steps) 'Exact dyadic preset differs'}
  $history=@(Import-Csv -LiteralPath (Join-Path $review 'history.csv'));$historyRows=$history.Count;Need ($historyRows -eq $samples) 'Native history row count differs'
  $opened=0;for($i=0;$i -lt $samples;$i++){
    $row=$history[$i];$step=[long]$row.completed_step;$post=if($eta0){$step -gt 4000}else{$step -gt $(if($Window -ceq 'half'){10486}else{5243})}
    Need ([int]$row.part -eq $i -and [int]$row.activeDrainCount -eq $(if($post){10}else{0})) 'Nonempty actual drainage mask differs';$opened+=[int]$post
    if(!$eta0){$expected=$r.job.saved_clock_table[$i];Need ($step -eq $expected.completed_steps -and [double]$row.time_s -eq [double]$expected.time_s) 'Actual dyadic history schedule differs'}
  }
  Need ($opened -eq $(if($smoke){0}elseif($eta0){359}else{1073}) -and $done.post_open_drained_particle_checks -eq 10*$opened) 'Post-opening coverage differs'
  $expected=@('original15.bin','physical.bin','clock.bin','common_j_theta.bin','soil_n.bin','native_ids.csv','fixed_ids.csv','history.csv','ledger.csv','fixed_samples.csv','last_poro.csv','columns.csv','completion.json');$leaves=@(Get-ChildItem -LiteralPath $review -File);Need ($leaves.Count -eq 13 -and !(Compare-Object ($leaves.Name|Sort-Object) ($expected|Sort-Object))) 'Native leaf set differs'
}catch{$failure=$_.Exception.Message}
try{V $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}};if(Test-Path -LiteralPath $review){$files=@(Get-ChildItem -LiteralPath $review -File|Sort-Object Name|ForEach-Object {E $_.FullName})}
$passed=(!$failure -and $unchanged -and $null -ne $done)
Save $record ([ordered]@{stage='upl_damp_native_r1';passed=[bool]$passed;backend=$Backend;window=$Window;source_run=(E $runPath);reader_helper=(E $helper);reader_call=(E $callPath);completion=$completion;inputs=$bindings;files=$files;paths=@{native_dir=$review;solver_dir=(Split-Path -Parent $r.run_out.path)};history_rows=$historyRows;original_native_guards_passed=[bool]$passed;drainage_nonempty_per_frame_verified=([bool]$passed -and !$smoke);bindings_unchanged=$unchanged;reader_rebuilt=$false;old_reader_source_not_asserted_current=$true;solver_or_build_invoked=$false;physical_acceptance=$false;failure=$failure})
if(!$passed){throw "Native review rejected; preserve $record and raw outputs"};Write-Output "One damping native review sealed: $record"
