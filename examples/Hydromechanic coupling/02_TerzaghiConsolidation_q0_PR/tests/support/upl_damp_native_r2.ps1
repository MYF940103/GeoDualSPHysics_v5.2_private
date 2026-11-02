param([Parameter(Mandatory=$true)][ValidateSet('CPU','GPU')][string]$Backend,[Parameter(Mandatory=$true)][ValidateSet('smoke','eta0','coarse','half')][string]$Window,[switch]$AdoptCompletedReader)
# r2 changes only wrapper schedule truth; the typed reader and all scientific guards are unchanged.
$ErrorActionPreference='Stop';$Backend=$Backend.ToUpperInvariant();$Window=$Window.ToLowerInvariant();$tests=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $tests 'logs';$runTag='upl_damp_'+$Backend+'_'+$Window+'_r1';$tag='upl_damp_'+$Backend+'_'+$Window+'_r2'
$review=Join-Path $tests ('outputs\'+$tag+'_native');$record=Join-Path $logs ($tag+'.native.json');$callPath=Join-Path $logs ($tag+'_reader.call.json');$log=Join-Path $logs ($tag+'_reader.log')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Need([bool]$ok,[string]$why){if(!$ok){throw $why}}
function V($rows){foreach($e in $rows){Need ($e.path -and $e.sha256) 'Missing Entry';$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed artifact: '+$e.path)}}
function Fresh($paths){foreach($p in $paths){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function N($v){if($v -is [ValueType]){$n=[double]$v}else{Need (![string]::IsNullOrWhiteSpace([string]$v)) 'Empty number';$n=[double]::Parse([string]$v,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture)};Need (![double]::IsNaN($n) -and ![double]::IsInfinity($n)) 'Nonfinite number';return $n}
Fresh @($record);$prior=$null;$priorEntry=$null;$readerCallEntry=$null;$readerExecuted=$false
if($AdoptCompletedReader){Need ($Backend -ceq 'CPU' -and $Window -ceq 'coarse') 'Adoption is restricted to completed CPU coarse r1'}else{Need (!($Backend -ceq 'CPU' -and $Window -ceq 'coarse')) 'Completed CPU coarse reader must be explicitly adopted, not rerun';Fresh @($review,$callPath,$log)}
$runPath=Join-Path $logs ($runTag+'.run.json');$r=J $runPath;$c=J $r.call.path
Need ($r.passed -and $r.stage -ceq 'upl_damp_run_r1' -and $r.backend -ceq $Backend -and $r.window -ceq $Window -and $r.public_project_main -and !$r.fixture_or_Run_override -and $r.source_inputs_objects_runtime_canonical_unchanged) 'Own actual Run required'
Need ($c.owned_call_exited -and $c.typed_LASTEXITCODE_captured_immediately -and $c.exit_code -is [int] -and $c.exit_code -eq 0 -and !$c.invocation_failure -and $c.target_program.sha256 -ceq $r.program.sha256) 'Original actual tool exit0 required'
if($Backend -ceq 'GPU' -and $Window -ceq 'smoke'){Need $r.memcheck_zero_errors_and_leaks 'Own GPU smoke memory check required'}
$eta0=$Window -ceq 'eta0';$helper=Join-Path $logs $(if($eta0){'upl_column_public_reader_ReleaseCPU_r1.helper.json'}else{'upl_column_ringdown_reader_ReleaseCPU_r1.helper.json'});$h=J $helper
Need ($h.passed -and $h.exact_link_closure_verified -and $h.kind -ceq 'reader' -and $h.configuration -ceq 'ReleaseCPU' -and @($h.objects).Count -eq 85 -and $h.link_object_count -eq 86 -and @($h.runtime).Count -eq 4 -and !$h.solver_started) 'Sealed CPU85 plus reader authority required'
$bindings=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_damp_native_r2.json')),(E (Join-Path $tests 'notes\upl_damp_plan_r1.json')),(E $runPath),$r.call,(E $helper),$h.program,$h.helper_object,$h.compile_call,$h.link_call,$h.source_build,$h.source_freeze)+@($r.inputs)+@($r.files)+@($h.tools)+@($h.libraries)+@($h.objects)
# Archived reader build is provenance; its historical source originals are not asserted current.
foreach($p in $h.runtime){$bindings+=@($p.original,$p.copy)}
if($AdoptCompletedReader){
  $priorEntry=E (Join-Path $logs ($runTag+'.native.json'));$prior=J $priorEntry.path
  Need ($prior.stage -ceq 'upl_damp_native_r1' -and $prior.passed -eq $false -and $prior.failure -ceq 'Actual dyadic history schedule differs' -and $prior.bindings_unchanged -and $prior.backend -ceq 'CPU' -and $prior.window -ceq 'coarse' -and $prior.history_rows -eq 1277 -and @($prior.files).Count -eq 13) 'Only the sealed r1 schedule postcheck failure may be adopted'
  Need ($prior.source_run.path -ceq (E $runPath).path -and $prior.source_run.sha256 -ceq (E $runPath).sha256 -and $prior.reader_helper.sha256 -ceq (E $helper).sha256 -and $prior.paths.native_dir -ceq (Join-Path $tests ('outputs\'+$runTag+'_native')) -and $prior.paths.solver_dir -ceq (Split-Path -Parent $r.run_out.path)) 'Prior reader/Run/directory attribution differs'
  V (@($prior.source_run,$prior.reader_helper,$prior.reader_call,$prior.completion)+@($prior.inputs)+@($prior.files));$oldCall=J $prior.reader_call.path;$oldDone=J $prior.completion.path
  Need ($oldCall.direct_native_call -and $oldCall.pure_native_reader -and !$oldCall.solver_or_build_invoked -and $oldCall.owned_call_exited -and $oldCall.typed_LASTEXITCODE_captured_immediately -and $oldCall.exit_code -is [int] -and $oldCall.exit_code -eq 0 -and !$oldCall.invocation_failure -and $oldCall.program.sha256 -ceq $h.program.sha256 -and $oldDone.passed) 'Completed prior reader typed exit0 and passed completion required'
  V @($oldCall.program,$oldCall.log);$review=$prior.paths.native_dir;$readerCallEntry=$prior.reader_call;$bindings+=@($priorEntry,$prior.reader_call,$prior.completion,$oldCall.program,$oldCall.log)
}
$data=Join-Path (Split-Path -Parent $r.run_out.path) 'data';$argv=@('--read',$Backend,$data)
if($eta0){$argv+=@('769','0.0000025',$review)}else{$argv+=@($Window,$review)}
V $bindings;$code=$null;$failure=$null
if($AdoptCompletedReader){Need (@($oldCall.arguments).Count -eq $argv.Count) 'Prior reader argv count differs';for($i=0;$i -lt $argv.Count;$i++){Need ($oldCall.arguments[$i] -ceq $argv[$i]) 'Prior reader argv differs'};$code=$oldCall.exit_code}else{
  $started=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$saved=$ErrorActionPreference
  try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $h.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE;$readerExecuted=$true}catch{$failure=$_.Exception.Message}finally{$ErrorActionPreference=$saved}
  Save $callPath ([ordered]@{program=$h.program;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;log=(E $log);pure_native_reader=$true;solver_or_build_invoked=$false});$readerCallEntry=E $callPath
}
$done=$null;$completion=$null;$files=@();$unchanged=$false;$historyRows=0;$jsonTimeMax=0.0;$jsonTimeDifferences=0;$smoke=$Window -ceq 'smoke'
try{
  Need ($code -is [int] -and $code -eq 0 -and !$failure) 'Reader failed; repair offline, never rerun completed solver'
  $completion=E (Join-Path $review 'completion.json');$done=J $completion.path;$samples=[int]$r.job.expected_samples
  Need ($done.passed -and $done.backend -ceq ($Backend+'_public') -and $done.samples -eq $samples -and $done.native_count -eq 1000 -and $done.fixed_count -eq 40 -and $done.physical_columns -eq 26 -and $done.native_total_arrays -eq 22 -and $done.PART_typed_public_metadata_verified -and $done.public_master_on -and $done.no_exclusions -and $done.all_exported_physical_fields_finite -and !$done.physical_acceptance) 'Typed public22/native1040/finite/schema check rejected'
  Need ($done.max_ledger_relative_error -le 5e-13 -and $done.dt_s -eq $r.job.dt_s -and [Math]::Abs([double]$done.actual_end_s-[double]$r.job.end_s) -le 1e-14 -and $done.max_noninitial_signed_dterror_s -le 1e-14 -and $done.noninitial_signed_dterror_intervals -eq ($samples-1)) 'Original ledger/actual-time/necessary-step checks rejected'
  if(!$eta0){$lockedDt=[Math]::Pow(2,$(if($Window -ceq 'half'){-20}else{-19}));Need ($done.stage -ceq 'upl_column_ringdown_native_r1' -and $done.preset -ceq $Window -and $done.actual_time_step_locked_dt_exact -and $done.planned_completed_steps -eq $r.job.steps -and $done.dt_s -eq $lockedDt -and @($r.job.saved_clock_table).Count -eq $samples) 'Exact dyadic preset differs'}
  $history=@(Import-Csv -LiteralPath (Join-Path $review 'history.csv'));$historyRows=$history.Count;Need ($historyRows -eq $samples) 'Native history row count differs'
  $opened=0;for($i=0;$i -lt $samples;$i++){
    $row=$history[$i];$step=[long]$row.completed_step;$post=if($eta0){$step -gt 4000}else{$step -gt $(if($Window -ceq 'half'){10486}else{5243})}
    Need ([int]$row.part -eq $i -and [int]$row.activeDrainCount -eq $(if($post){10}else{0})) 'Nonempty actual drainage mask differs';$opened+=[int]$post
    if(!$eta0){
      $expected=$r.job.saved_clock_table[$i];$savedStep=if($step -gt 0){$step-1}else{0};$wantedTime=[double]$step*$lockedDt
      Need ([int]$expected.part -eq $i -and $step -eq [long]$expected.completed_steps -and [long]$expected.saved_step -eq $savedStep -and [long]$row.saved_step -eq $savedStep -and [BitConverter]::DoubleToInt64Bits((N $row.time_s)) -eq [BitConverter]::DoubleToInt64Bits($wantedTime) -and [BitConverter]::DoubleToInt64Bits((N $row.dt_s)) -eq [BitConverter]::DoubleToInt64Bits($lockedDt)) 'Actual dyadic history schedule differs'
      $jsonDelta=[Math]::Abs((N $expected.time_s)-$wantedTime);$jsonTimeMax=[Math]::Max($jsonTimeMax,$jsonDelta);if($jsonDelta -ne 0){$jsonTimeDifferences++}
    }
  }
  Need ($opened -eq $(if($smoke){0}elseif($eta0){359}else{1073}) -and $done.post_open_drained_particle_checks -eq 10*$opened) 'Post-opening coverage differs'
  $expected=@('original15.bin','physical.bin','clock.bin','common_j_theta.bin','soil_n.bin','native_ids.csv','fixed_ids.csv','history.csv','ledger.csv','fixed_samples.csv','last_poro.csv','columns.csv','completion.json');$leaves=@(Get-ChildItem -LiteralPath $review -File);Need ($leaves.Count -eq 13 -and !(Compare-Object ($leaves.Name|Sort-Object) ($expected|Sort-Object))) 'Native leaf set differs'
}catch{$failure=$_.Exception.Message}
try{V $bindings;if($AdoptCompletedReader){V (@($prior.source_run,$prior.reader_helper,$prior.reader_call,$prior.completion)+@($prior.inputs)+@($prior.files))};$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}};if(Test-Path -LiteralPath $review){$files=@(Get-ChildItem -LiteralPath $review -File|Sort-Object Name|ForEach-Object {E $_.FullName})}
$passed=(!$failure -and $unchanged -and $null -ne $done)
Save $record ([ordered]@{stage='upl_damp_native_r2';passed=[bool]$passed;backend=$Backend;window=$Window;source_run=(E $runPath);reader_helper=(E $helper);reader_call=$readerCallEntry;completion=$completion;inputs=$bindings;files=$files;paths=@{native_dir=$review;solver_dir=(Split-Path -Parent $r.run_out.path)};history_rows=$historyRows;original_native_guards_passed=[bool]$passed;drainage_nonempty_per_frame_verified=([bool]$passed -and !$smoke);bindings_unchanged=$unchanged;adopted_completed_reader=[bool]$AdoptCompletedReader;adopted_prior_native=$priorEntry;reader_executed_by_this_action=$readerExecuted;prior_failed_record_preserved=[bool]$AdoptCompletedReader;dyadic_schedule_truth='integer completed_steps times locked binary dt; typed native reader exact clock guard retained';deserialized_JSON_time_differences_diagnostic=$jsonTimeDifferences;max_deserialized_JSON_time_difference_s_diagnostic=$jsonTimeMax;JSON_text_or_native_clock_modified=$false;reader_rebuilt=$false;old_reader_source_not_asserted_current=$true;solver_or_build_invoked=$false;physical_acceptance=$false;failure=$failure})
if(!$passed){throw "Native review rejected; preserve $record and raw outputs"};Write-Output "One damping native review sealed: $record"

