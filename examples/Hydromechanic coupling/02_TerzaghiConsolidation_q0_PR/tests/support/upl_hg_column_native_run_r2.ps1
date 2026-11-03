param(
  [Parameter(Mandatory=$true)][ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration,
  [Parameter(Mandatory=$true)][ValidateSet('smoke','short_c','short_h','coarse','half')][string]$Window,
  [switch]$AdoptCompletedReader,
  [switch]$ExecutionAuthorized
)
# One owned pure-reader call against one completed HG-column project-main Run.
# No solver, compilation, GenCase, Git, source edit, adoption or automatic retry.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Explicit -ExecutionAuthorized is required for this one native-reader action.'}
$tests=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $tests
$logs=Join-Path $tests 'logs'
$tag='upl_hg_column_'+$Configuration+'_'+$Window+'_r1'
$review=Join-Path $tests ('outputs\'+$tag+'_native')
$record=Join-Path $logs ($tag+'.native_r2.json')
$callPath=Join-Path $logs ($tag+'_reader.call.json')
$log=Join-Path $logs ($tag+'_reader.log')
$note=Join-Path $tests 'notes\upl_hg_column_native_run_r2.json'
$runPath=Join-Path $logs ($tag+'.run.json')
$manifestPath=Join-Path $logs 'upl_hg_column_r1.inputs.json'
$buildPath=Join-Path $logs ('upl_hg_column_'+$Configuration+'_r1.build.json')
$smoke=$Window -ceq 'smoke'
$short=$Window -in @('short_c','short_h')
$half=$Window -in @('short_h','half')
$factor=if($half){2}else{1}
$dt=[Math]::Pow(2,$(if($half){-20}else{-19}))
$steps=if($smoke){2}elseif($short){13120*$factor}else{262144*$factor}
$end=[double]$steps*$dt
$drainStep=5243*$factor
$samples=if($smoke){3}elseif($short){458}else{1469}
$postCount=if($smoke){0}elseif($short){254}else{1265}
$preset=if($smoke){'smoke'}elseif($half){'half'}else{'coarse'}
$helperPath=Join-Path $logs $(if($smoke){'upl_column_ringdown_reader_ReleaseCPU_r1.helper.json'}elseif($short){'upl_hg_column_short_native_ReleaseCPU_r1.helper.json'}else{'upl_damp_long_reader_ReleaseCPU_r1.helper.json'})
$helperStage=if($smoke){'upl_column_ringdown_reader_build_r1'}elseif($short){'upl_hg_column_short_native_build_r1'}else{'upl_damp_long_reader_build_r1'}
$completionStage=if($smoke){'upl_column_ringdown_native_r1'}elseif($short){'upl_hg_column_short_native_r1'}else{'upl_damp_long_native_r1'}
$completionWindow=if($smoke){'smoke'}elseif($short){'dyadic_short458'}else{'damped500'}
$bindings=New-Object 'Collections.Generic.List[object]'
$archiveRows=New-Object 'Collections.Generic.List[object]'
$archiveBuilds=New-Object 'Collections.Generic.List[object]'
$archiveByKey=@{}

function Need([bool]$ok,[string]$why){if(!$ok){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p -Force;Need (!$f.PSIsContainer) ('File expected: '+$p);[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function N($v){
  Need ($null -ne $v -and ![string]::IsNullOrWhiteSpace([string]$v)) 'Missing number'
  $value=if($v -is [ValueType]){[double]$v}else{[double]::Parse([string]$v,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture)}
  Need (![double]::IsNaN($value) -and ![double]::IsInfinity($value)) 'Nonfinite number'
  return $value
}
function PathKey([string]$p){return [IO.Path]::GetFullPath($p).ToUpperInvariant()}
function EntryKey($e){return (PathKey $e.path)+'|'+([string]$e.sha256).ToLowerInvariant()+'|'+[string]$e.bytes}
function SameEntry($a,$b){return ((PathKey $a.path) -ceq (PathKey $b.path) -and [long]$a.bytes -eq [long]$b.bytes -and $a.sha256 -ieq $b.sha256)}
function B($e){Need ($null -ne $e -and $e.path -and $null -ne $e.bytes -and $e.sha256) 'Missing bound file Entry';[void]$bindings.Add($e)}
function V($rows){foreach($e in $rows){Need ($null -ne $e -and $e.path -and $null -ne $e.bytes -and $e.sha256) 'Missing bound file Entry';$a=E $e.path;Need (SameEntry $a $e) ('Changed artifact: '+$e.path)}}
function Fresh($paths){foreach($p in $paths){Need (!(Test-Path -LiteralPath $p)) ('Retained artifact protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Owned($entry){
  V @($entry);B $entry;$c=J $entry.path
  Need ($c.direct_native_call -and $c.owned_call_exited -and $c.typed_LASTEXITCODE_captured_immediately -and $c.exit_code -is [int] -and $c.exit_code -eq 0 -and !$c.invocation_failure) 'Actual owned immediate typed tool exit0 required'
  B $c.program
  # Old project_call metadata has no embedded log; the build manifest binds it.
  if($c.log){B $c.log}
  return $c
}
function ArchivePair($pair){
  if($null -eq $pair -or !$pair.snapshot){return}
  Need ($pair.original.path -and $pair.snapshot.path -and $pair.original.bytes -eq $pair.snapshot.bytes -and $pair.original.sha256 -ieq $pair.snapshot.sha256) 'Historical reader source/snapshot metadata differs'
  $key=EntryKey $pair.original
  if(!$archiveByKey.ContainsKey($key)){$archiveByKey[$key]=$pair.snapshot;[void]$archiveRows.Add([ordered]@{historical_original=$pair.original;bound_archive=$pair.snapshot;original_asserted_current=$false})}
  B $pair.snapshot
}
function ArchiveBuild($entry){
  if(!$entry){return}
  V @($entry);B $entry;$a=J $entry.path
  Need ($a.passed -and $a.source_bindings_unchanged -and !$a.solver_started -and !$a.physical_acceptance) 'Sealed reader source-build authority required'
  foreach($pair in @($a.source_snapshot)+@($a.documentation_snapshot,$a.case_readme_snapshot)){ArchivePair $pair}
  [void]$archiveBuilds.Add($a)
}
function HistoricalB($entry){
  if(!$entry){return}
  $key=EntryKey $entry
  if($archiveByKey.ContainsKey($key)){B $archiveByKey[$key]}else{B $entry}
}
function CurrentPair($pair){
  if($null -eq $pair -or !$pair.snapshot){return}
  Need ($pair.original.bytes -eq $pair.snapshot.bytes -and $pair.original.sha256 -ieq $pair.snapshot.sha256) 'Actual solver source/snapshot metadata differs'
  B $pair.original;B $pair.snapshot
}
function Binary([string]$leaf,[uint32[]]$header,[long]$payload){
  $path=Join-Path $review $leaf;$e=E $path
  Need ($e.bytes -eq 4L*$header.Count+$payload) ('Binary length differs: '+$leaf)
  $reader=New-Object IO.BinaryReader([IO.File]::OpenRead($path))
  try{foreach($number in $header){Need ($reader.ReadUInt32() -eq $number) ('Binary header differs: '+$leaf)}}finally{$reader.Dispose()}
  return [ordered]@{file=$e;header=$header;payload_bytes=$payload;length_verified=$true}
}
function RawClosure{
  V $bindings.ToArray()
  $actual=@(Get-ChildItem -LiteralPath $r.job.output_directory -Recurse -File|ForEach-Object{PathKey $_.FullName}|Sort-Object)
  $declared=@($r.files|ForEach-Object{PathKey $_.path}|Sort-Object)
  Need ($actual.Count -eq $declared.Count -and !(Compare-Object $actual $declared)) 'Completed solver raw output membership changed'
}

if($AdoptCompletedReader){Fresh @($record)}else{Fresh @($review,$record,$callPath,$log)}
$manifest=J $manifestPath
Need ($manifest.passed -and $manifest.prepared -and $manifest.stage -ceq 'upl_hg_column_prepare_r1' -and @($manifest.variants).Count -eq 3 -and @($manifest.jobs).Count -eq 6 -and $manifest.integer_steps_times_locked_binary_dt_are_clock_truth -and !$manifest.physical_acceptance) 'Prepared three-seed/six-job HG manifest required'
$selected=@($manifest.jobs|Where-Object{$_.configuration -ceq $Configuration -and $_.window -ceq $Window})
Need ($selected.Count -eq 1) 'Only a declared configuration/window is admitted'
$job=$selected[0]
Need ($job.tag -ceq $tag -and $job.expected_samples -eq $samples -and $job.steps -eq $steps -and (N $job.dt_s) -eq $dt -and $job.event_completed_step -eq $drainStep -and $job.post_open_frames -eq $postCount -and $job.expected_native_total_arrays -eq 22 -and $job.expected_total_native_count -eq 1040 -and @($job.saved_clock_table).Count -eq $samples) 'Declared HG native window differs'
Need ((PathKey $job.output_directory) -ceq (PathKey (Join-Path $tests ('outputs\'+$tag)))) 'Only this job output directory is admitted'
$saveSteps=@(0,1,2)
if(!$smoke){
  $set=New-Object 'Collections.Generic.SortedSet[long]'
  for($n=0;$n -le 65536;$n+=64){[void]$set.Add([long]($factor*$n))}
  for($n=5120;$n -le 5376;$n++){[void]$set.Add([long]($factor*$n))}
  for($n=66560;$n -le 262144;$n+=1024){[void]$set.Add([long]($factor*$n))}
  $saveSteps=@($set|Where-Object{$_ -le $steps})
}
Need ($saveSteps.Count -eq $samples -and $saveSteps[-1] -eq $steps -and @($saveSteps|Where-Object{$_ -gt $drainStep}).Count -eq $postCount) 'Independent integer dyadic sample plan differs'

$r=J $runPath
Need ($r.passed -and $r.stage -in @('upl_hg_column_run_r1','upl_hg_column_run_r2') -and $r.backend -ceq 'CPU' -and $r.configuration -ceq $Configuration -and $r.window -ceq $Window -and $r.tag -ceq $tag -and $r.bindings_unchanged -and !$r.physical_acceptance) 'Own completed CPU project-main HG Run required'
Need ($r.job.tag -ceq $job.tag -and $r.job.steps -eq $steps -and $r.job.expected_samples -eq $samples -and (PathKey $r.job.output_directory) -ceq (PathKey $job.output_directory) -and (PathKey $r.job.input_prefix) -ceq (PathKey $job.input_prefix)) 'Completed Run job identity differs'
Need (SameEntry $r.input_manifest (E $manifestPath)) 'Completed Run does not bind the exact prepared input manifest'
Need ((PathKey $r.run_out.path) -ceq (PathKey (Join-Path $job.output_directory 'Run.out'))) 'Actual own Run.out required'
$b=J $buildPath
Need (SameEntry $r.source_build (E $buildPath)) 'Actual Run source-build hash/path differs'
Need ($b.passed -and $b.stage -ceq 'upl_hg_column_build_r1' -and $b.configuration -ceq $Configuration -and $b.backend -ceq 'CPU' -and $b.source_bindings_unchanged -and $b.canonical_programs_unchanged -and $b.runtime_unchanged -and $b.exact_object_basename_closure -and $b.objects_include_project_main -and @($b.objects).Count -eq 86 -and $b.non_main_object_count -eq 85 -and !$b.solver_started -and !$b.physical_acceptance) 'Actual authoritative CPU86 project-main build required'
Need (SameEntry $r.program $b.program) 'Actual Run target differs from its compiled project program'
$solver=Owned $r.call
Need ($solver.actual_solver_call -and $solver.public_project_main -and !$solver.fixture_or_Run_override -and (SameEntry $solver.program $b.program) -and (SameEntry $solver.target_program $b.program)) 'Own actual project-main target binding required'
Need (@($solver.arguments).Count -eq @($job.arguments).Count -and @($solver.target_arguments).Count -eq @($job.arguments).Count) 'Owned solver argument count differs'
for($i=0;$i -lt @($job.arguments).Count;$i++){Need ([string]$solver.arguments[$i] -ceq [string]$job.arguments[$i] -and [string]$solver.target_arguments[$i] -ceq [string]$job.arguments[$i]) 'Owned solver argument differs from prepared job'}
foreach($entry in @((E $PSCommandPath),(E $note),(E $manifestPath),(E $runPath),$r.source_build,$r.input_manifest,$r.program,$r.run_out,$b.program,$b.log,$b.binlog)+@($r.inputs)+@($r.files)+@($b.inputs)+@($b.tools)+@($b.libraries)+@($b.objects)+@($b.canonical_programs_before)+@($b.runtime_before)){B $entry}
if($b.project_call){$null=Owned $b.project_call}
foreach($pair in @($b.source_snapshot)+@($b.documentation_snapshot,$b.case_readme_snapshot)){CurrentPair $pair}
foreach($pair in $b.runtime){B $pair.original;B $pair.copy}

$h=J $helperPath
Need ($h.passed -and $h.stage -ceq $helperStage -and $h.configuration -ceq 'ReleaseCPU' -and @($h.runtime).Count -eq 4 -and !$h.physical_acceptance) 'Sealed actual native-reader helper required'
if($short){
  # The new helper uses the lean actual-project-class build receipt schema.
  Need ($h.frozen_inputs_unchanged -and $h.actual_project_classes_no_stubs -and $h.object_count -eq 85 -and @($h.project_objects).Count -eq 85 -and !$h.solver_run -and !$h.program_run -and !$h.canonical_program_installed) 'Actual current short-reader CPU85 authority required'
  $readerObjects=@($h.project_objects)
}else{
  Need ($h.kind -ceq 'reader' -and $h.build_and_source_bindings_unchanged -and $h.exact_link_closure_verified -and @($h.objects).Count -eq 85 -and $h.CPU_non_main_objects -eq 85 -and $h.link_object_count -eq 86 -and !$h.solver_started) 'Retained CPU85 plus reader86 link authority required'
  $readerObjects=@($h.objects)
}
B (E $helperPath)
ArchiveBuild $h.source_build
if($h.source_freeze -and !(SameEntry $h.source_build $h.source_freeze)){ArchiveBuild $h.source_freeze}else{if($h.source_freeze){B $h.source_freeze}}
foreach($pair in @($h.source_snapshot)+@($h.documentation_snapshot,$h.case_readme_snapshot)){ArchivePair $pair}
# Bind historical source copies, never assert old solver source/doc originals
# still match the newly compiled HG solver. All other reader artifacts stay exact.
foreach($a in $archiveBuilds){
  foreach($entry in @($a.inputs)+@($a.tools)+@($a.libraries)+@($a.objects)){HistoricalB $entry}
  foreach($name in @('program','log','binlog','adopted_Debug_source_build','owned_exit_record')){if($a.$name){HistoricalB $a.$name}}
  if($a.project_call){$null=Owned $a.project_call}
}
foreach($entry in @($h.inputs)+@($h.tools)+@($h.libraries)+$readerObjects+@($h.author_files)+@($h.retained_reader_authors)+@($h.actual_includes)){HistoricalB $entry}
foreach($name in @('program','helper_object','compiler_dependency_record','environment_source','retained_compiler_recipe','adopted_Debug_source_build','neutral_include')){if($h.$name){HistoricalB $h.$name}}
$compileMetadata=Owned $h.compile_call
$linkMetadata=Owned $h.link_call
# Independently inspect actual owned linker arguments for the same exact85+1
# object closure in both helper receipt schemas; project main is never linked.
$linkObjects=@($linkMetadata.arguments|Where-Object{[IO.Path]::GetExtension(([string]$_).Trim('"')) -ieq '.obj'}|ForEach-Object{PathKey ([string]$_).Trim('"')})
$wantedObjects=@($readerObjects+@($h.helper_object)|ForEach-Object{PathKey $_.path})
Need ($linkObjects.Count -eq 86 -and @($linkObjects|Select-Object -Unique).Count -eq 86 -and !(Compare-Object ($linkObjects|Sort-Object) ($wantedObjects|Sort-Object)) -and @($linkObjects|Where-Object{[IO.Path]::GetFileName($_) -ieq 'main.obj'}).Count -eq 0) 'Actual owned linker object closure is not CPU85 plus reader1 without main'
$readerCpp=if($smoke){'upl_column_ringdown_native_r1.cpp'}elseif($short){'upl_hg_column_short_native_r1.cpp'}else{'upl_damp_long_native_r1.cpp'}
$compiledCpp=@($compileMetadata.arguments|Where-Object{[IO.Path]::GetExtension(([string]$_).Trim('"')) -ieq '.cpp'})
Need ($compiledCpp.Count -eq 1 -and [IO.Path]::GetFileName(([string]$compiledCpp[0]).Trim('"')) -ceq $readerCpp) 'Actual owned compile did not select the declared native-reader source'
foreach($pair in $h.runtime){HistoricalB $pair.original;B $pair.copy}
if($short){Need (SameEntry $h.source_build (E (Join-Path $logs 'upl_hg_column_ReleaseCPU_r1.build.json'))) 'New short reader must use the actual current HG ReleaseCPU build'}
$data=Join-Path $job.output_directory 'data'
$raw=@(Get-ChildItem -LiteralPath $data -File|Where-Object{$_.Name -cmatch '^Part_.*\.bi4$'})
Need ($raw.Count -eq $samples) 'Raw native PART/piece count differs'
for($i=0;$i -lt $samples;$i++){
  $wanted=Join-Path $data ('Part_'+$i.ToString('D4')+'.bi4')
  Need (Test-Path -LiteralPath $wanted -PathType Leaf) 'Declared native PART missing'
  $bound=@($r.files|Where-Object{(PathKey $_.path) -ceq (PathKey $wanted)})
  Need ($bound.Count -eq 1) 'Every actual native PART must be hash-bound by its owned Run'
}
# Remove only duplicate identical Entries. Conflicting claims are a hard failure.
$unique=@{}
foreach($entry in $bindings){$key=PathKey $entry.path;if($unique.ContainsKey($key)){Need (SameEntry $unique[$key] $entry) ('Conflicting file binding: '+$entry.path)}else{$unique[$key]=$entry}}
$bindings.Clear();foreach($entry in $unique.Values){B $entry}
RawClosure

$argv=@('--read','CPU',$data,$preset,$review)
$priorAnalysis=$null;$readerExecuted=$false
if($AdoptCompletedReader){
  Need ($Configuration -ceq 'DebugCPU' -and $Window -ceq 'smoke') 'Only the recorded completed Debug smoke reader may be adopted'
  $priorAnalysis=E (Join-Path $logs ($tag+'.native.json'));$old=J $priorAnalysis.path
  Need (!$old.passed -and $old.failure -ceq 'Cannot overwrite variable Error because it is read-only or constant.' -and $old.bindings_unchanged -and $old.reader_executed_by_this_action -and !$old.adopted_completed_reader -and (SameEntry $old.source_run (E $runPath))) 'Exact completed-reader analysis-only failure required'
  B $priorAnalysis;V $old.files;Need (@($old.files).Count -eq 13) 'Completed reader must have all13 sealed exports'
  foreach($entry in $old.files){B $entry}
  foreach($leaf in @('upl_hg_column_native_run_r1.ps1','upl_hg_column_native_run_r1.json')){
    $proof=@($old.inputs|Where-Object{[IO.Path]::GetFileName($_.path) -ceq $leaf});Need ($proof.Count -eq 1) 'Prior failed-analysis author binding absent';V $proof;B $proof[0]
  }
  $priorCall=Owned $old.reader_call
  Need ((SameEntry $old.reader_call (E $callPath)) -and (SameEntry $priorCall.program $h.program) -and ($priorCall.arguments -join [char]0) -ceq ($argv -join [char]0)) 'Original owned decoder program/argv differs'
  Need (SameEntry $old.completion (E (Join-Path $review 'completion.json'))) 'Completed decoder completion changed'
  $code=$priorCall.exit_code;$launchFailure=$null
}else{
$code=$null;$launchFailure=$null;$started=[DateTime]::UtcNow.ToString('o')
[IO.File]::WriteAllBytes($log,[byte[]]@())
$savedPreference=$ErrorActionPreference
Push-Location $caseRoot
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $h.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$launchFailure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$savedPreference}
Save $callPath ([ordered]@{stage='upl_hg_column_native_run_r2.reader';program=$h.program;target_program=$h.program;arguments=$argv;working_directory=$caseRoot;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$launchFailure;log=(E $log);pure_native_reader=$true;solver_or_build_invoked=$false;physical_acceptance=$false})
# Seal the real typed reader exit before inspecting any completion/export data.
  $readerExecuted=$true
}
$failure=$launchFailure;$done=$null;$completion=$null;$files=@();$headers=@();$unchanged=$false
$historyRows=0;$nativeIds=0;$fixedIds=0;$finalIds=0;$opened=0;$jsonTimeDifferences=0;$jsonTimeMax=0.0
try{
  Need ($code -is [int] -and $code -eq 0 -and !$launchFailure) 'Owned native reader failed; preserve partials, never rerun the completed solver'
  $completion=E (Join-Path $review 'completion.json');$done=J $completion.path
  Need ($done.passed -and $done.stage -ceq $completionStage -and $done.backend -ceq 'CPU_public' -and $done.window -ceq $completionWindow -and $done.preset -ceq $preset -and $done.grid -ceq $(if($half){'h'}else{'c'}) -and $done.model -ceq 'constant' -and $done.conductivity_model -eq 0 -and (N $done.conductivity_Ck) -eq 0 -and $done.public_schema -and $done.public_master_on) 'Native reader stage/backend/constant-model metadata differs'
  Need ($done.native_count -eq 1000 -and $done.fixed_count -eq 40 -and $done.total_native_count -eq 1040 -and $done.samples -eq $samples -and $done.physical_columns -eq 26 -and $done.physical_schema -ceq 'case02_common26_col21_ExcessPorePress_NOT_wave26' -and $done.original_typed_arrays -eq 15 -and $done.native_dynamic_double_arrays -eq 6 -and $done.native_total_arrays -eq 22 -and $done.native_PosDiv_present -and $done.native_PosDiv_is_float -and $done.native_V_rho_k_present -and $done.PART_typed_public_metadata_verified) 'Original typed native22/all1040/schema guards rejected'
  Need ((N $done.dt_s) -eq $dt -and [Math]::Abs((N $done.actual_end_s)-$end) -le 1e-14 -and [Math]::Abs((N $done.planned_end_s)-$end) -le 1e-14 -and $done.planned_completed_steps -eq $steps -and $done.declared_saved_completed_steps_exact -and $done.actual_time_step_locked_dt_exact -and $done.noninitial_signed_dterror_intervals -eq ($samples-1) -and $done.initial_empty_dterror_intervals -in @(0,1) -and $done.initial_dterror_excluded_from_noninitial_summary -and (N $done.max_noninitial_signed_dterror_s) -le 1e-14) 'Original native-clock/Step/locked-dt/signed-dterror guards rejected'
  Need ($done.event_is_declared_preset_not_BI4_metadata -and [Math]::Abs((N $done.declared_ramp_and_drain_event_s)-5243*[Math]::Pow(2,-19)) -le 1e-14 -and $done.soil_ledger_checks -eq 1000*$samples -and $done.fixed_public_zero_marker_checks -eq 40*$samples -and $done.all_native_J_theta_rows -eq 1040*$samples -and $done.soil_native_n_rows -eq 1000*$samples -and (N $done.max_ledger_relative_error) -le 5e-13) 'Original full native ledger coverage/tolerance rejected'
  Need ($done.fixed_J_theta_original15_not_zeroed_or_masked -and !$done.GPU_private_fixed_n_mirror_to_public_zero_is_schema_change -and $done.no_exclusions -and $done.initial_rest_and_decimal_lattice_verified -and $done.double_stress_and_float_display_verified -and $done.all_exported_physical_fields_finite -and !$done.PosDiv_fabricated_or_derived -and $done.common26_column21_is_actual_ExcessPorePress -and $done.pre_open_event_pressure_not_forced_zero -and $done.density_and_J_not_frozen_on_drained_receivers) 'Original unmasked native fields/markers/finite/initial-state guards rejected'
  Need ($done.post_open_completed_step_threshold -eq $drainStep -and $done.post_open_frames -eq $postCount -and $done.post_open_drained_particle_checks -eq 10*$postCount -and $done.max_activeDrainCount -eq $(if($smoke){0}else{10})) 'Original actual drained-receiver coverage differs'
  Need ($done.descriptive_saved_field_summaries -and !$done.new_scientific_acceptance_gate -and !$done.same_force_stage_load_budget_verified -and !$done.force_stage_guard_independently_observed -and !$done.historical_private_comparison_performed_by_reader -and !$done.live_final_compared_by_reader -and !$done.independent_half_performed -and !$done.physical_acceptance) 'Reader descriptive/same-force-stage scope differs'
  if($short){Need ($done.declared_first458_full_schedule_only -and !$done.full_half_second_complete -and !$done.full_window_prefix_data_compared -and $done.post_open_native_receiver_coverage_verified) 'Stopped first458 native scope differs'}
  $history=@(Import-Csv -LiteralPath (Join-Path $review 'history.csv'));$historyRows=$history.Count
  Need ($historyRows -eq $samples -and @($r.job.saved_clock_table).Count -eq $samples) 'Native or owned Run history schedule count differs'
  for($i=0;$i -lt $samples;$i++){
    $row=$history[$i];$step=[long]$saveSteps[$i];$savedStep=if($step -gt 0){$step-1}else{0};$time=[double]$step*$dt;$post=$step -gt $drainStep
    foreach($expected in @($job.saved_clock_table[$i],$r.job.saved_clock_table[$i])){
      Need ($expected.part -eq $i -and [long]$expected.completed_steps -eq $step -and [long]$expected.saved_step -eq $savedStep) 'Prepared/owned integer clock schedule differs'
      # JSON time round-trip loss is diagnostic only. The native CSV and typed
      # C++ clock check use exact completed_steps*locked_binary_dt instead.
      $delta=[Math]::Abs((N $expected.time_s)-$time);$jsonTimeMax=[Math]::Max($jsonTimeMax,$delta);if($delta -ne 0){$jsonTimeDifferences++}
    }
    Need ((N $row.part) -eq $i -and (N $row.completed_step) -eq $step -and (N $row.saved_step) -eq $savedStep -and [BitConverter]::DoubleToInt64Bits((N $row.time_s)) -eq [BitConverter]::DoubleToInt64Bits($time) -and [BitConverter]::DoubleToInt64Bits((N $row.dt_s)) -eq [BitConverter]::DoubleToInt64Bits($dt)) 'Actual native dyadic history clock differs'
    Need ((N $row.post_open_by_completed_step) -eq [int]$post -and (N $row.activeDrainCount) -eq $(if($post){10}else{0}) -and (N $row.max_ledger_relative_error) -le 5e-13) 'Per-frame native drainage mask or ledger differs'
    $nativeStepError=N $row.signed_dterror_s
    if($i){Need ((N $row.dterror_interval_empty) -eq 0 -and (N $row.dterror_used_in_noninitial_summary) -eq 1 -and $nativeStepError -le 1e-14) 'Original noninitial signed necessary-step interval rejected'}
    else{Need ((N $row.dterror_used_in_noninitial_summary) -eq 0 -and ((N $row.dterror_interval_empty) -eq 1 -or $nativeStepError -le 1e-14)) 'Initial signed diagnostic scope differs'}
    $opened+=[int]$post
  }
  Need ($opened -eq $postCount) 'Independent per-frame drainage coverage differs'
  foreach($kind in @('native','fixed')){
    $rows=@(Import-Csv -LiteralPath (Join-Path $review ($kind+'_ids.csv')));$count=if($kind -ceq 'native'){1000}else{40};$first=if($kind -ceq 'native'){40}else{0}
    Need ($rows.Count -eq $count) 'Native/fixed ID export count differs'
    for($i=0;$i -lt $count;$i++){Need ((N $rows[$i].row) -eq $i -and (N $rows[$i].id) -eq ($first+$i)) 'All1040 original ID membership/order differs';$null=N $rows[$i].x0;$null=N $rows[$i].y0;$null=N $rows[$i].z0}
    if($kind -ceq 'native'){$nativeIds=$rows.Count}else{$fixedIds=$rows.Count}
  }
  $last=@(Import-Csv -LiteralPath (Join-Path $review 'last_poro.csv'));$finalIds=$last.Count;Need ($finalIds -eq 1000) 'Final soil1000 J/n/theta rows differ'
  for($i=0;$i -lt 1000;$i++){Need ((N $last[$i].id) -eq ($i+40)) 'Final soil native ID membership/order differs';$null=N $last[$i].J;$null=N $last[$i].n;$null=N $last[$i].theta}
  $names=@('x','y','z','vx','vy','vz','PorePress','PorePress0','J','theta','sigma_xx','sigma_xy','sigma_xz','sigma_yy','sigma_yz','sigma_zz','Kplastic','FSType','FSNormal_x','FSNormal_y','FSNormal_z','ExcessPorePress','LoadAce_x','LoadAce_y','LoadAce_z','legacy_Rhop')
  $columns=@(Import-Csv -LiteralPath (Join-Path $review 'columns.csv'));Need ($columns.Count -eq 26) 'Physical column count differs'
  for($i=0;$i -lt 26;$i++){Need ((N $columns[$i].column) -eq $i -and $columns[$i].name -ceq $names[$i]) 'Unmasked common26 column semantics differ'}
  $expectedLeaves=@('original15.bin','physical.bin','clock.bin','common_j_theta.bin','soil_n.bin','native_ids.csv','fixed_ids.csv','history.csv','ledger.csv','fixed_samples.csv','last_poro.csv','columns.csv','completion.json')
  $actualLeaves=@(Get-ChildItem -LiteralPath $review -File|ForEach-Object{$_.Name})
  Need ($actualLeaves.Count -eq 13 -and !(Compare-Object ($actualLeaves|Sort-Object) ($expectedLeaves|Sort-Object)) -and @(Get-ChildItem -LiteralPath $review -Directory).Count -eq 0) 'Exactly13 declared native output leaves required'
  $headers+=@(Binary 'original15.bin' @(1040,15,$samples) ([long]$samples*166408))
  $headers+=@(Binary 'physical.bin' @(1000,26,$samples) ([long]$samples*208008))
  $headers+=@(Binary 'clock.bin' @($samples,28) ([long]$samples*28))
  $headers+=@(Binary 'common_j_theta.bin' @(1040,2,$samples) ([long]$samples*16648))
  $headers+=@(Binary 'soil_n.bin' @(1000,1,$samples) ([long]$samples*8008))
}catch{$failure=$_.Exception.Message}
try{RawClosure;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
if(Test-Path -LiteralPath $review){$files=@(Get-ChildItem -LiteralPath $review -File|Sort-Object Name|ForEach-Object{E $_.FullName})}
$passed=(!$failure -and $unchanged -and $null -ne $done -and $headers.Count -eq 5 -and $code -is [int] -and $code -eq 0)
Save $record ([ordered]@{
  stage='upl_hg_column_native_run_r2';passed=[bool]$passed;tag=$tag;backend='CPU';configuration=$Configuration;window=$Window
  source_run=(E $runPath);source_build=$r.source_build;input_manifest=$r.input_manifest;reader_helper=(E $helperPath);reader_source_build=$h.source_build;reader_source_freeze=$h.source_freeze
  reader_call=(E $callPath);completion=$completion;inputs=$bindings.ToArray();files=$files;paths=@{native_dir=$review;solver_dir=$job.output_directory}
  binary_header_length_checks=$headers;native_samples=$samples;history_rows_reparsed=$historyRows;native_ID_rows_reparsed=$nativeIds;fixed_ID_rows_reparsed=$fixedIds;final_J_n_theta_rows_reparsed=$finalIds
  original_native_guards_passed=[bool]$passed;typed_native_total_arrays=22;typed_native_total_ID_count=1040;typed_soil_ledger_checks=$(if($done){$done.soil_ledger_checks}else{0});typed_fixed_zero_marker_checks=$(if($done){$done.fixed_public_zero_marker_checks}else{0});ledger_CSV_rows_reparsed=0
  drainage_nonempty_per_frame_verified=([bool]$passed -and !$smoke);post_open_frames_verified=$opened;saved_step_plan_verified=[bool]$passed
  dyadic_schedule_truth='integer completed_steps times locked binary dt; typed native C++ exact-clock and signed-dterror checks retained'
  deserialized_JSON_time_differences_diagnostic=$jsonTimeDifferences;max_deserialized_JSON_time_difference_s_diagnostic=$jsonTimeMax;JSON_time_used_as_equality_gate=$false
  historical_reader_original_to_archive_bindings=$archiveRows.ToArray();historical_reader_source_originals_asserted_current=$false;actual_solver_source_build_and_raw_output_hashes_verified=$unchanged;bindings_unchanged=$unchanged
  reader_executed_by_this_action=$readerExecuted;adopted_completed_reader=[bool]$AdoptCompletedReader;prior_failed_analysis=$priorAnalysis;reader_rebuilt=$false;native_fields_metadata_or_signed_dterror_masked=$false
  saved_final_J_weighted_load_is_descriptive_only=$true;same_force_stage_qA_guard_verified=$false;same_force_stage_load_budget_verified=$false;force_stage_guard_independently_observed=$false
  HG_ON_vs_OFF_bit_identity_claimed=$false;independent_half_or_physical_comparison_performed=$false;new_scientific_acceptance_gate=$false;solver_or_build_invoked=$false;GenCase_invoked=$false;Git_invoked=$false;physical_acceptance=$false;failure=$failure
})
if(!$passed){throw "HG-column native review rejected; preserve $record and partial outputs; do not rerun the completed solver"}
Write-Output "One CPU HG-column native review sealed: $record"
