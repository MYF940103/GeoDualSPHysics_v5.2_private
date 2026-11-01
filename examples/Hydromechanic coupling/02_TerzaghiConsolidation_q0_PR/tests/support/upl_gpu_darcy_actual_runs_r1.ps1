param([Parameter(Mandatory=$true)][ValidateSet('Prepare','RunJob','ReviewJob','ReviewRetained')][string]$Mode,[ValidateSet('Smoke','GPU_k0_c','GPU_k0_h','GPU_constant_c','GPU_constant_h','CPU_constant_c','CPU_constant_h','CPU_k0_c','CPU_k0_h','GPU_legacy_k0_c','GPU_legacy_k0_h')][string]$Job='Smoke',[switch]$ExecutionAuthorized)
# Explicit one-action driver. No production build/edit, CPU rerun, worker, notifier or Git.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$figures=Join-Path $t 'figures';$manifest=Join-Path $logs 'upl_gpu_darcy_actual_r1.inputs.json';$note=Join-Path $t 'notes\upl_gpu_darcy_actual_runs_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 22)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function NeedCheck([string]$p){$r=J $p;if(!$r.passed -or $r.physical_acceptance){throw "Prior bounded gate rejected: $p"};if($r.files){V $r.files};if($r.inputs -is [array]){V $r.inputs};if($r.bindings -is [array]){V $r.bindings};foreach($key in @('completion','call','source_run','source_build','helper')){if($r.$key){V @($r.$key)}};E $p}
function CurrentHelper([string]$cfg){
  $p=Join-Path $logs ('upl_gpu_darcy_actual_'+$cfg+'_r1.helper.json');$h=J $p
  if($h.fixture -ne 'DarcyActual' -or $h.configuration -ne $cfg -or $h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or !$h.exact_link_closure_verified -or $h.link_object_count -ne 111){throw 'Frozen exact-closure actual helper required'}
  V $h.inputs;V $h.author_files;V $h.transitive_project_include_files;V $h.tools;V $h.libraries;V $h.objects;V @($h.program,$h.source_build,$h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}
  $g=J $h.source_build.path;V $g.inputs;V $g.objects;V @($g.source_freeze,$g.project_call,$g.isolated_GPU_program,$g.baseline);$s=J $g.source_freeze.path;V $s.source;V $s.five_targets
  if($g.configuration -ne $cfg -or $g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or @($g.objects).Count -ne 110 -or @($s.source).Count -ne 265 -or @($s.five_targets).Count -ne 5){throw 'Wrong current Darcy r2 build closure'}
  [pscustomobject]@{record=(E $p);value=$h}
}
function RuntimeGates(){
  $d=NeedCheck (Join-Path $logs 'upl_gpu_darcy_component_Debug_review_r4.check.json');$r=NeedCheck (Join-Path $logs 'upl_gpu_darcy_component_Release_run_r4.check.json')
  $dc=J $d.path;$rc=J $r.path;if(!$dc.memcheck_zero_errors_and_leaks -or $dc.completed_physical_steps -ne 0 -or $rc.completed_physical_steps -ne 0 -or $dc.source_build.sha256 -ine $helpers.Debug.value.source_build.sha256 -or $rc.source_build.sha256 -ine $helpers.Release.value.source_build.sha256){throw 'Component tests must bind current production builds and zero-step scope'}
  $legacyPath=Join-Path $logs 'upl_gpu_darcy_legacy_r1.check.json';$legacy=J $legacyPath
  if(!$legacy.passed -or !$legacy.all_native_typed15_clock_step_dterror_exact -or !$legacy.all_observer_J_n_theta_exact -or !$legacy.all_feedback_immutable_33_export_exact -or $legacy.DynamicPorePressure_enabled -or @($legacy.job_checks).Count -ne 7){throw 'Passed unchanged Dynamic=false/OFF legacy regressions required'}
  V $legacy.inputs;V $legacy.job_checks;@($d,$r,(E $legacyPath))
}
function OutputFiles([string]$dir){if(Test-Path -LiteralPath $dir){@(Get-ChildItem -LiteralPath $dir -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})}else{@()}}
function Call($target,[string[]]$argv,[string]$label,[bool]$mem,[bool]$solver){
  $call=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($p in @($call,$log)){if(Test-Path -LiteralPath $p){throw 'Owned invocation retained'}}
  $tool=$target;$arguments=$argv;$toolRecord=$null
  if($mem){$toolRecord=E (Join-Path $logs 'upl_gpu_darcy_component_Debug_run_r3.call.json');$old=J $toolRecord.path;if(!$old.owned_call_exited -or $old.exit_code -ne 0 -or !$old.memcheck_zero_errors_and_leaks){throw 'Successful exact memcheck tool receipt required'};$tool=$old.program;V @($tool);$arguments=@('--tool','memcheck','--leak-check','full','--error-exitcode','97',$target.path)+$argv}
  V @($target);[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$exitCode=$null;$exited=$false;$launchFailure=$null;$oldPreference=$ErrorActionPreference;$ErrorActionPreference='Continue'
  try{Push-Location (Join-Path $repo 'src');try{& $tool.path @arguments 2>&1|Tee-Object -FilePath $log|Out-Host;$exitCode=$LASTEXITCODE;$exited=$true}finally{Pop-Location}}catch{$launchFailure=$_.Exception.Message}finally{$ErrorActionPreference=$oldPreference}
  $text=[IO.File]::ReadAllText($log);$zero=($mem -and $text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations')
  Save $call ([ordered]@{owned_call_exited=$exited;exit_code=$exitCode;launch_error=$launchFailure;program=$tool;target_program=$target;arguments=$arguments;target_arguments=$argv;log=(E $log);started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');working_directory=(Join-Path $repo 'src');memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;memcheck_tool_source_call=$toolRecord;recipe=@(E $PSCommandPath;E $note;E $manifest);actual_GPU_Run_invoked=$solver;physical_acceptance=$false})
  E $call
}
function RequireOwned($entry,[bool]$mem){$r=J $entry.path;V @($r.log,$r.program);if($r.target_program){V @($r.target_program)};if(!$r.owned_call_exited -or $r.exit_code -ne 0 -or ($mem -and !$r.memcheck_zero_errors_and_leaks)){throw 'Owned invocation rejected; keep all partial evidence'};$r}
if(!$ExecutionAuthorized){throw 'Root complete fixture/driver review and explicit single-action authorization required'}
$helpers=@{};foreach($cfg in @('Debug','Release')){$helpers[$cfg]=CurrentHelper $cfg}
if($Mode -eq 'Prepare'){
  if(Test-Path -LiteralPath $manifest){throw 'Prepared manifest retained'};$oldPath=Join-Path $logs 'upl_gpu_k0_actual_r2.inputs.json';$old=J $oldPath
  $folder=Join-Path $outputs 'upl_gpu_darcy_actual_seed_r1';if(Test-Path -LiteralPath $folder){throw 'Prepared seed folder retained'};[void](New-Item -ItemType Directory -Path $folder)
  $jobs=@();foreach($label in @('Smoke','GPU_k0_c','GPU_k0_h','GPU_constant_c','GPU_constant_h')){
    $smoke=$label -eq 'Smoke';$half=$label.EndsWith('_h');$model=if($label.StartsWith('GPU_k0')){'k0'}else{'constant'};$originalLabel=if($smoke){'Smoke'}elseif($half){'GPU_h'}else{'GPU_c'}
    $original=@($old.jobs|Where-Object {$_.job -eq $originalLabel});if($original.Count -ne 1){throw 'One retained matching runtime seed required'};$o=$original[0];V @($o.xml,$o.bi4)
    $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($o.xml.path);$nodes=$doc.SelectNodes('/case/execution/special/hydromechanics/HydraulicConductivity');if($nodes.Count -ne 1 -or $nodes[0].GetAttribute('value') -ne '0'){throw 'Expected unchanged private k0 runtime seed'};$nodes[0].SetAttribute('value',$(if($model -eq 'k0'){'0'}else{'0.0001'}))
    $prefix=Join-Path $folder ('CaseDarcy_'+$label);[IO.File]::WriteAllText($prefix+'.xml',$doc.OuterXml,(New-Object Text.UTF8Encoding($false)));Copy-Item -LiteralPath $o.bi4.path -Destination ($prefix+'.bi4');$bi=E ($prefix+'.bi4');if($bi.sha256 -ine $o.bi4.sha256){throw 'Original particle bytes changed'}
    $jobs+=@{job=$label;backend='GPU';model=$model;configuration=$(if($smoke){'Debug'}else{'Release'});smoke=$smoke;dt=[double]$o.dt;end=[double]$o.end;cadence=[double]$o.cadence;samples=[int]$o.samples;steps=[int]$o.steps;prefix=$prefix;xml=(E ($prefix+'.xml'));bi4=$bi;source_xml=$o.xml;source_bi4=$o.bi4}
  }
  # Record old raw ownership and clocks, not old26-column exports or a fabricated new CPU run.
  $pubPath=Join-Path $logs 'upl_cpu_public_r1.inputs.json';$pub=J $pubPath;$retained=@()
  foreach($label in @('CPU_constant_c','CPU_constant_h','CPU_k0_c','CPU_k0_h','GPU_legacy_k0_c','GPU_legacy_k0_h')){
    $tag=if($label.EndsWith('_h')){'h'}else{'c'};$cpu=$label.StartsWith('CPU');$constant=$label.StartsWith('CPU_constant');$backend=if($cpu){'CPU'}else{'GPU'}
    if($constant){$oldRunPath=Join-Path $logs ('upl_cpu_public_periodic_constant_'+$tag+'_r1.solver.check.json');$r=J $oldRunPath;$sel=@($pub.jobs|Where-Object {$_.label -eq ('periodic_constant_'+$tag)});if($sel.Count -ne 1 -or !$r.passed -or $r.native_frames -ne 257){throw 'Retained CPU positive native solve not sealed'};$o=$sel[0];$xml=$o.runtime;$bi=$o.copied_geometry;$out=$o.planned_output;$dt=[double]$o.dt;$end=[double]$o.end;$cadence=[double]$o.cadence;$steps=[int]$o.steps;$call=$r.call}
    else{$oldJob=if($cpu){'CPU_'+$tag}else{'GPU_'+$tag};$oldRunPath=Join-Path $logs ('upl_gpu_k0_actual_'+$oldJob+'_r3.run.json');$r=J $oldRunPath;if(!$r.owned_solver_exit0 -or $r.native_frames -ne 257){throw 'Retained old k0 native solve not sealed'};$o=$r.selected_input;$xml=$o.xml;$bi=$o.bi4;$out=Join-Path $outputs ('upl_gpu_k0_actual_'+$oldJob+'_r3');$dt=[double]$o.dt;$end=[double]$o.end;$cadence=[double]$o.cadence;$steps=[int]$o.steps;$call=$r.call}
    V $r.files;V @($xml,$bi,$call);$owned=J $call.path;if(!$owned.owned_call_exited -or $owned.exit_code -ne 0){throw 'Retained original solver must have exact owned exit0'};V @($owned.log,$owned.program);if($owned.target_program){V @($owned.target_program)}
    $retained+=@{job=$label;backend=$backend;model=$(if($constant){'constant'}else{'k0'});configuration='Release';smoke=$false;dt=$dt;end=$end;cadence=$cadence;samples=257;steps=$steps;xml=$xml;bi4=$bi;source_out=$out;data=(Join-Path $out 'data');source_run=(E $oldRunPath);source_call=$call;source_files=$r.files;new_solver_run=$false}
  }
  Save $manifest ([ordered]@{prepared_only=$true;inputs=@(E $PSCommandPath;E $note;E $oldPath;E $pubPath);GPU_helpers=@($helpers.Debug.record,$helpers.Release.record);jobs=$jobs;retained=$retained;all_initial_BI4_byte_identical=$true;new_CPU_runs=0;physical_fields_rewritten=$false;public_GPU_dynamic_accepted=$false;physical_acceptance=$false});exit 0
}
$prerequisites=RuntimeGates;$prepared=J $manifest;V $prepared.inputs;V $prepared.GPU_helpers
$retainedMode=$Mode -eq 'ReviewRetained';$selected=@($(if($retainedMode){$prepared.retained}else{$prepared.jobs})|Where-Object {$_.job -eq $Job});if($selected.Count -ne 1){throw 'Selected action/job is not a declared fresh or retained job'};$jobInfo=$selected[0];V @($jobInfo.xml,$jobInfo.bi4)
$retainedPrefix=if($retainedMode){'retained_'}else{''};$name='upl_gpu_darcy_actual_'+$retainedPrefix+$Job+'_r1';$out=if($retainedMode){$jobInfo.source_out}else{Join-Path $outputs $name};$run=Join-Path $logs ($name+'.run.json');$check=Join-Path $logs ($name+'.check.json');$review=Join-Path $outputs ($name+'_review');$helper=$helpers[$jobInfo.configuration]
if($Mode -eq 'RunJob'){
  if($Job -ne 'Smoke'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_darcy_actual_Smoke_r1.check.json')}
  if($Job -eq 'GPU_k0_h'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_darcy_actual_GPU_k0_c_r1.check.json');$prerequisites+=NeedCheck (Join-Path $figures 'upl_gpu_darcy_actual_k0_bridge_c_r1.json')}
  if($Job -eq 'GPU_constant_c'){foreach($kind in @('k0_half','k0_bridge_c','k0_bridge_h')){$prerequisites+=NeedCheck (Join-Path $figures ('upl_gpu_darcy_actual_'+$kind+'_r1.json'))}}
  if($Job -eq 'GPU_constant_h'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_darcy_actual_GPU_constant_c_r1.check.json');$prerequisites+=NeedCheck (Join-Path $figures 'upl_gpu_darcy_actual_cross_c_r1.json')}
  foreach($p in @($out,$run)){if(Test-Path -LiteralPath $p){throw 'Retained solver protected; analysis repair must not rerun it'}}
  $argv=@('--solver-'+$jobInfo.model);if($jobInfo.smoke){$argv+='--smoke'};$argv+=@('-gpu:0','-stable',$jobInfo.prefix,$out,'-dirdataout','data','-svres')
  $call=Call $helper.value.program $argv $name ([bool]$jobInfo.smoke) $true
  try{
    [void](RequireOwned $call ([bool]$jobInfo.smoke));$actualPath=Join-Path $out 'actual_complete.json';$actual=J $actualPath
    if(!$actual.passed -or !$actual.actual_production_Run -or !$actual.private_feedback -or !$actual.private_complete_dynamic_rate -or $actual.public_GPU_dynamic_mode -or $actual.physical_fields_rewritten_by_fixture -or [int]$actual.completed_steps -ne [int]$jobInfo.steps -or [double]$actual.actual_end_s -ne [double]$jobInfo.end -or [double]$actual.dt_s -ne [double]$jobInfo.dt -or $actual.model -ne $jobInfo.model -or !$actual.predictor_histories_released){throw 'Actual Run finish rejected'}
    $parts=@(Get-ChildItem -LiteralPath (Join-Path $out 'data') -Filter 'Part_????.bi4' -File);if($parts.Count -ne $jobInfo.samples){throw 'Declared native output count missing'}
    V $prepared.inputs;V @($jobInfo.xml,$jobInfo.bi4,$helper.record,$helper.value.program);V $helper.value.transitive_project_include_files
    Save $run ([ordered]@{owned_solver_exit0=$true;job=$Job;backend='GPU';model=$jobInfo.model;call=$call;input=(E $manifest);selected_input=$jobInfo;helper=$helper.record;actual_completion=(E $actualPath);files=@(OutputFiles $out);native_frames=$parts.Count;prerequisites=$prerequisites;solver_completed_before_analysis=$true;retained_run_reused=$false;physical_acceptance=$false})
  }catch{if(!(Test-Path -LiteralPath $run)){$ownedFailure=J $call.path;Save $run ([ordered]@{owned_solver_exit0=($ownedFailure.owned_call_exited -and $ownedFailure.exit_code -eq 0);native_output_sealed=$false;job=$Job;model=$jobInfo.model;call=$call;input=(E $manifest);failure=$_.Exception.Message;files=@(OutputFiles $out);solver_must_not_be_restarted_for_analysis=$true;physical_acceptance=$false})};throw};exit 0
}
if($retainedMode){
  foreach($p in @($run,$review,$check)){if(Test-Path -LiteralPath $p){throw 'Retained offline adoption protected'}};V @($jobInfo.source_run,$jobInfo.source_call);V $jobInfo.source_files;$original=J $jobInfo.source_call.path;if(!$original.owned_call_exited -or $original.exit_code -ne 0){throw 'Old owned solver exit0 required'}
  Save $run ([ordered]@{owned_solver_exit0=$true;job=$Job;backend=$jobInfo.backend;model=$jobInfo.model;retained_run_reused=$true;new_solver_run=$false;old_source_run=$jobInfo.source_run;call=$jobInfo.source_call;input=(E $manifest);selected_input=$jobInfo;files=$jobInfo.source_files;native_frames=257;solver_completed_before_analysis=$true;old_program_source_not_revalidated_as_current=$true;physical_acceptance=$false})
}
$sealed=J $run;if(!$sealed.owned_solver_exit0 -or $sealed.native_frames -ne $jobInfo.samples){throw 'A sealed completed solve is required; raw files alone do not establish exit'};V @($sealed.call,$sealed.input);V $sealed.files;[void](RequireOwned $sealed.call ([bool]$jobInfo.smoke))
foreach($p in @($review,$check)){if(Test-Path -LiteralPath $p){throw 'Offline review protected; use a new analysis label, never rerun the completed solve'}}
$argv=@('--read',$jobInfo.model,$jobInfo.backend,(Join-Path $out 'data'),([double]$jobInfo.dt).ToString('R',[Globalization.CultureInfo]::InvariantCulture),$jobInfo.xml.path,$review);if($jobInfo.smoke){$argv+='--smoke'}
$readerCall=Call $helper.value.program $argv ($name+'_review') $false $false
try{
  [void](RequireOwned $readerCall $false);$completion=Join-Path $review 'completion.json';$d=J $completion
  if(!$d.passed -or $d.model -ne $jobInfo.model -or $d.backend -ne $jobInfo.backend -or $d.samples -ne $jobInfo.samples -or $d.native_count -ne 512 -or $d.fixed_count -ne 0 -or $d.common_columns -ne 33 -or [double]$d.actual_end_s -ne [double]$jobInfo.end -or [double]$d.dt_s -ne [double]$jobInfo.dt -or [double]$d.cadence_s -ne [double]$jobInfo.cadence -or $d.native_ledger_checks -ne (512*[int]$jobInfo.samples) -or !$d.saved_clock_step_exact -or !$d.native_ID_aligned -or !$d.no_exclusions -or !$d.runtime_XML_exact_model_material_and_clock_checked -or $d.physical_acceptance){throw 'Native typed single-run gate rejected'}
  if([double]$d.max_energy_ratio -gt 1.1 -or [double]$d.max_saved_coupled_CFL -gt .01 -or [double]$d.max_saved_Ddt_h2 -gt .01 -or [double]$d.max_ledger_relative_error -gt 5e-13 -or [double]$d.max_signed_dterror_s -gt 1e-14 -or [double]$d.max_abs_J_minus_1 -le $(if($jobInfo.smoke){0.}else{1e-8})){throw 'Original saved safety/ledger/nonempty gates rejected'}
  $cpu=$jobInfo.backend -eq 'CPU';if($d.native_J_arrays -ne $(if($cpu){6}else{3}) -or [bool]$d.native_PosDiv_observed -ne $cpu -or [bool]$d.public_dynamic_metadata -ne $cpu -or [bool]$d.GPU_V_rho_k_derived_not_native_arrays -eq $cpu){throw 'Backend native schema or explicit derivation differs'}
  $liveExact=$false;if(!$retainedMode -and !$cpu){$live=E (Join-Path $out 'live_final.csv');$last=E (Join-Path $review 'last_poro.csv');if($live.bytes -ne $last.bytes -or $live.sha256 -ine $last.sha256){throw 'Actual live final and saved final J/n/theta CSV differ'};$liveExact=$true}
  V $sealed.files;V @($jobInfo.xml,$jobInfo.bi4,$helper.record,$helper.value.program);V $helper.value.transitive_project_include_files
  Save $check ([ordered]@{passed=$true;job=$Job;backend=$jobInfo.backend;model=$jobInfo.model;source_run=(E $run);call=$readerCall;completion=(E $completion);files=@(OutputFiles $review);input=(E $manifest);helper=$helper.record;prerequisites=$prerequisites;retained_native_re_read=$retainedMode;new_CPU_solver_run=$false;common_columns=33;native_frames=[int]$jobInfo.samples;actual_saved_final_matches_live_J_n_theta=$liveExact;actual_solver_exit_verified_by_wrapper=$true;full_force_stage_scales_independently_observed=$false;physical_acceptance=$false;full_cycle_accepted=$false;public_GPU_accepted=$false})
}catch{if(!(Test-Path -LiteralPath $check)){Save $check ([ordered]@{passed=$false;job=$Job;model=$jobInfo.model;source_run=(E $run);call=$readerCall;failure=$_.Exception.Message;files=@(OutputFiles $review);solver_must_not_be_restarted_for_analysis=$true;physical_acceptance=$false})};throw}
