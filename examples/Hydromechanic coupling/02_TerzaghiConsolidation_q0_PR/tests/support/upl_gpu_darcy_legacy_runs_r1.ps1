param([Parameter(Mandatory=$true)][ValidateSet('Run','Review','Aggregate')][string]$Mode,[ValidateSet('OFF_smoke','Observer_smoke','Feedback_smoke','OFF_extended','Observer_extended','Feedback_c','Feedback_h')][string]$Job='OFF_smoke',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Exactly one selected solve or offline review; old data are adopted, never old solvers. No new Dynamic flag.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$note=Join-Path $t 'notes\upl_gpu_darcy_legacy_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function P([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){if(!$r -or !$r.path){throw 'Missing binding'};$a=E (P $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((P $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function CheckPath([string]$name){Join-Path $logs ('upl_gpu_darcy_legacy_'+$name+'_r1.check.json')}
function NeedCheck([string]$name){$p=CheckPath $name;$r=J $p;if(!$r.passed -or !$r.all_original15_exact -or !$r.all_actual_clock_step_signed_dterror_exact -or $r.DynamicPorePressure_enabled -or $r.physical_acceptance){throw "Exact prior gate required: $name"};V $r.files;V $r.calls;V @($r.source_run,$r.completion);$run=J $r.source_run.path;V $run.files;V @($run.call,$run.source_build,$run.helper);$call=J $run.call.path;if(!$call.owned_call_exited -or $call.exit_code -ne 0 -or ($name.EndsWith('_smoke') -and !$call.memcheck_zero_errors_and_leaks)){throw 'Prior owned exit or memcheck invalid'};E $p}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root full source/recipe review and explicit one-action authorization required'}
$names=@('OFF_smoke','Observer_smoke','Feedback_smoke','OFF_extended','Observer_extended','Feedback_c','Feedback_h')
if($Mode -eq 'Aggregate'){
  $checks=@();$inputs=@(E $PSCommandPath;E $note);foreach($n in $names){$checks+=NeedCheck $n;$q=J (CheckPath $n);$inputs+=@($q.inputs);if($n.StartsWith('Observer') -and !$q.all_observer_J_n_theta_exact){throw 'Observer double-state exact gate incomplete'};if($n.StartsWith('Feedback') -and (!$q.all_observer_J_n_theta_exact -or !$q.all_feedback_immutable_33_export_exact)){throw 'Feedback native33 gate incomplete'}}
  V $inputs;$gpaths=@($checks|ForEach-Object {(J $_.path).source_build.path}|Sort-Object -Unique);foreach($p in $gpaths){$g=J $p;V $g.inputs;V $g.objects;$s=J $g.source_freeze.path;V $s.source;$b=J $g.baseline.path;V $b.canonical_GPU;V @($g.source_freeze,$g.project_call);$inputs+=E $p}
  Save (Join-Path $logs 'upl_gpu_darcy_legacy_r1.check.json') ([ordered]@{passed=$true;all_native_typed15_clock_step_dterror_exact=$true;all_observer_J_n_theta_exact=$true;all_feedback_immutable_33_export_exact=$true;DynamicPorePressure_enabled=$false;job_checks=$checks;inputs=@($inputs|Sort-Object path -Unique);jobs=7;solver_frame_instances=557;typed_original15_frame_comparisons=557;physical_acceptance=$false;public_GPU_dynamic_accepted=$false;new_complete_Darcy_branch_tested=$false;canonical_GPU_unchanged=$true});exit 0
}
$feedback=$Job.StartsWith('Feedback');$observer=$Job.StartsWith('Observer') -or $feedback;$smoke=$Job.EndsWith('_smoke');$cfg=if($smoke){'Debug'}else{'Release'};$window=if($smoke){'Smoke'}else{'Extended'}
$manifest=Join-Path $logs $(if($feedback){'upl_gpu_k0_actual_r2.inputs.json'}else{'upl_gpu_observer_native_r1.inputs.json'});$prepared=J $manifest;V $prepared.inputs
if($feedback){$selectedName=if($smoke){'Smoke'}elseif($Job -eq 'Feedback_c'){'GPU_c'}else{'GPU_h'};$selected=@($prepared.jobs|Where-Object {$_.job -ceq $selectedName -and $_.backend -eq 'GPU'})}
else{$selected=@($prepared.jobs|Where-Object {$_.window -ceq $window})}
if($selected.Count -ne 1){throw 'One exact retained input required'};$j=$selected[0];V @($j.xml,$j.bi4)
$steps=if($smoke){2}elseif($feedback){if($Job -eq 'Feedback_c'){512}else{1024}}else{16};$samples=if($feedback -and !$smoke){257}else{$steps+1}
$dt=if($Job -eq 'Feedback_h'){[Math]::Pow(2,-25)}else{[Math]::Pow(2,-24)};$cadence=if($feedback -and !$smoke){[Math]::Pow(2,-23)}else{$dt}
if($j.configuration -ne $cfg -or $j.steps -ne $steps -or $j.samples -ne $samples -or [double]$j.dt -ne $dt -or [double]$j.end -ne $steps*$dt -or ($j.prefix+'.xml') -cne $j.xml.path){throw 'Declared clock/input differs'}
$dependencies=@();if(!$smoke){foreach($n in 'OFF_smoke','Observer_smoke','Feedback_smoke'){$dependencies+=NeedCheck $n}}
if($Job.StartsWith('Observer')){$dependencies+=NeedCheck $(if($smoke){'OFF_smoke'}else{'OFF_extended'})};if($Job -eq 'Feedback_h'){$dependencies+=NeedCheck 'Feedback_c'}
$gpuPath=Join-Path $logs ('upl_gpu_darcy_'+$cfg+'_r2.build.json');$g=J $gpuPath;$fixture=if($feedback){'Feedback'}else{'Native'}
$helperPath=Join-Path $logs ('upl_gpu_darcy_legacy_'+$fixture+'_'+$cfg+'_r1.helper.json');$h=J $helperPath
if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $cfg -or $h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne $fixture -or $h.configuration -ne $cfg -or $h.source_build.sha256 -ine (E $gpuPath).sha256 -or !$h.retained_native_functions_unchanged -or ($feedback -and !$h.unchanged_fixture_source) -or $h.DynamicPorePressure_enabled){throw 'New same-functions helper/current objects required'}
$nativePath=Join-Path $logs ('upl_gpu_darcy_legacy_Native_'+$cfg+'_r1.helper.json');$native=J $nativePath
if($native.fixture -ne 'Native' -or !$native.Native_batch_entry -or !$native.retained_native_functions_unchanged -or $native.source_build.sha256 -ine (E $gpuPath).sha256){throw 'Current retained typed-functions/batch link required'}
if($feedback){$oldLabel=if($smoke){'Smoke_r2'}elseif($Job -eq 'Feedback_c'){'GPU_c_r3'}else{'GPU_h_r3'};$oldCheckPath=Join-Path $logs ('upl_gpu_k0_actual_'+$oldLabel+'.check.json');$oldCheck=J $oldCheckPath;$oldRunPath=$oldCheck.source_run.path;$oldRun=J $oldRunPath;$oldFolder=Join-Path $outputs ('upl_gpu_k0_actual_'+$oldLabel)}
else{$kind=if($observer){'observer'}else{'newoff'};$oldCheckPath=Join-Path $logs ('upl_gpu_k0_time_'+$window+'_r1.review.check.json');$oldCheck=J $oldCheckPath;$oldRunPath=Join-Path $logs ('upl_gpu_k0_time_'+$window+'_r1_'+$kind+'.solver.check.json');$oldRun=J $oldRunPath;$oldFolder=Join-Path $outputs ('upl_gpu_k0_time_'+$window+'_r1_'+$kind)}
if(!$oldCheck.passed -or $oldRun.native_frames -ne $samples -or ($feedback -and !$oldRun.owned_solver_exit0) -or (!$feedback -and !$oldRun.passed)){throw 'Retained accepted owned control required'}
$oldCall=J $oldRun.call.path;if(!$oldCall.owned_call_exited -or $oldCall.exit_code -ne 0 -or ($smoke -and !$oldCall.memcheck_zero_errors_and_leaks)){throw 'Retained owned exit/memcheck invalid'}
$source=J $g.source_freeze.path;$baseline=J $g.baseline.path;$recipe=@(E $PSCommandPath;E $note;E $manifest;E $gpuPath;E $helperPath;E $nativePath;E $oldCheckPath;E $oldRunPath)
function VerifyAll {
  V $recipe;V $dependencies;V @($j.xml,$j.bi4);V $prepared.inputs;V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program);V $source.source;V $source.five_targets;V $baseline.canonical_GPU;V $baseline.other_source
  foreach($helper in @($h,$native)){V $helper.inputs;V $helper.author_files;V $helper.tools;V $helper.libraries;V @($helper.program,$helper.source_build,$helper.compile_call,$helper.link_call);foreach($r in $helper.runtime){V @($r.original,$r.copy)}}
  foreach($r in $g.runtime){V @($r.original,$r.copy)};V $oldCheck.files;V $oldRun.files;V @($oldRun.call);V @($oldCall.program,$oldCall.log)
}
$name='upl_gpu_darcy_legacy_'+$Job+'_r1';$folder=Join-Path $outputs $name;$runPath=Join-Path $logs ($name+'.run.json');$checkPath=CheckPath $Job;$review=Join-Path $outputs ($name+'_review')
$tools=@{} # Cache receipt identities within this one action; full hashes verified before and after all offline reads.
function InvokeOwned($target,[string[]]$argv,[string]$label,[bool]$mem=$false){
  $call=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($p in @($call,$log)){if(Test-Path -LiteralPath $p){throw 'Retained owned invocation protected'}}
  $program=$target;$arguments=$argv;if($mem){$prior=J (Join-Path $logs 'upl_gpu_k0_time_Debug_Scale_r1.call.json');$program=$prior.program;$arguments=@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$target.path)+$argv}
  if(!$tools.ContainsKey($program.path)){V @($program);$tools[$program.path]=$program};if(!$tools.ContainsKey($target.path)){V @($target);$tools[$target.path]=$target}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $program.path @arguments 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old;$zero=$false
  if($mem){$text=[IO.File]::ReadAllText($log);$zero=$text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'}
  Save $call ([ordered]@{owned_call_exited=$true;exit_code=$code;program=$program;target_program=$target;arguments=$arguments;target_arguments=$argv;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;source_build=(E $gpuPath);helper=(E $helperPath);recipe=$recipe;physical_acceptance=$false});if($code -ne 0 -or ($mem -and !$zero)){throw 'Owned call/memcheck rejected; retain evidence'};E $call
}
VerifyAll
if($Mode -eq 'Run'){
  foreach($p in @($folder,$runPath)){if(Test-Path -LiteralPath $p){throw 'Retained solver protected; use offline Review after completed solve'}}
  $target=$h.program;$argv=@('-gpu:0','-stable',$j.prefix,$folder,'-dirdataout','data','-svres')
  if($feedback){$argv=@($(if($smoke){'--solver-smoke'}else{'--solver'}))+$argv}elseif($observer){$argv=@('--solver','1')+$argv}else{$target=$g.isolated_GPU_program}
  $call=InvokeOwned $target $argv $name $smoke;$parts=@(Get-ChildItem -LiteralPath (Join-Path $folder 'data') -Filter 'Part_????.bi4' -File);if($parts.Count -ne $samples){throw 'Normal exit but missing native save; preserve data'}
  VerifyAll;V @($tools.Values);$files=@(Get-ChildItem -LiteralPath $folder -Recurse -File|ForEach-Object {E $_.FullName})
  Save $runPath ([ordered]@{owned_solver_exit0=$true;job=$Job;configuration=$cfg;steps=$steps;native_frames=$parts.Count;call=$call;source_build=(E $gpuPath);helper=(E $helperPath);input=(E $manifest);selected_input=$j;inputs=$recipe;dependencies=$dependencies;files=$files;DynamicPorePressure_enabled=$false;solver_completed_before_analysis=$true;physical_acceptance=$false});exit 0
}
$run=J $runPath;if(!$run.owned_solver_exit0 -or $run.job -cne $Job -or $run.native_frames -ne $samples -or $run.DynamicPorePressure_enabled -or $run.source_build.sha256 -ine (E $gpuPath).sha256){throw 'Completed sealed new solve required'};V $run.files;V @($run.call,$run.source_build,$run.helper,$run.input)
$owned=J $run.call.path;if(!$owned.owned_call_exited -or $owned.exit_code -ne 0 -or ($smoke -and !$owned.memcheck_zero_errors_and_leaks)){throw 'Owned exit/memcheck invalid'}
foreach($p in @($review,$checkPath)){if(Test-Path -LiteralPath $p){throw 'Retained offline review protected; do not rerun completed solver'}}
[void](New-Item -ItemType Directory -Path $review);$calls=@();$newData=Join-Path $folder 'data';$oldData=Join-Path $oldFolder 'data'
$batch=Join-Path $review 'batch';$calls+=InvokeOwned $native.program @('--batch-compare',$oldData,$newData,"$samples",$(if($observer){'1'}else{'0'}),$batch) ($name+'_batch')
$batchDone=J (Join-Path $batch 'batch_complete.json');if(!$batchDone.passed -or $batchDone.samples -ne $samples -or $batchDone.native_count -ne 512 -or [bool]$batchDone.observer -ne $observer -or $batchDone.retained_Compare_calls -ne $samples -or $batchDone.retained_ReadPoro_calls -ne $(if($observer){2*$samples}else{0}) -or !$batchDone.retained_functions_unchanged -or $batchDone.physical_program_executed){throw 'Offline retained-functions batch incomplete'}
for($part=0;$part -lt $samples;$part++){
  $tag=$part.ToString('D4');$json=Join-Path $batch ('typed_'+$tag+'.json')
  $r=J $json;$time=$part*$cadence;$step=if($part){[long][Math]::Round($time/$dt)-1}else{0}
  if(!$r.passed -or $r.arrays -ne 15 -or $r.native_count -ne 512 -or !$r.all_original_physical_array_bits_identical -or !$r.native_ID_aligned -or !$r.saved_time_step_dterror_exact -or !$r.no_exclusions -or [double]$r.actual_time_s -ne $time -or $r.saved_step -ne $step -or [double]$r.dterror_s -gt 1e-14 -or [bool]$r.observer_schema_a -ne $observer -or [bool]$r.observer_schema_b -ne $observer){throw 'Original15/clock/signed-error/schema bit regression failed'}
  if($observer){$pair=@();foreach($side in 'old','new'){$csv=Join-Path $batch ('poro_'+$side+'_'+$tag+'.csv');$pj=Join-Path $batch ('poro_'+$side+'_'+$tag+'.json');$p=J $pj;if(!$p.passed -or $p.double_arrays -ne 3 -or !$p.derived_n_exact -or $p.native_count -ne 512 -or $p.fixed_count -ne 0 -or [double]$p.n0 -ne .25 -or [double]$p.actual_time_s -ne $time -or $p.saved_step -ne $step){throw 'Actual observer Double J/n/theta ledger/clock invalid'};$pair+=E $csv};if($pair[0].sha256 -ne $pair[1].sha256 -or $pair[0].bytes -ne $pair[1].bytes){throw 'Every saved J/n/theta CSV must be byte-identical'}}
}
$additional=@();$liveEqual=@();$readCompletions=@()
if($observer){
  $leaf=if($feedback){'actual_complete.json'}else{'observer_complete.json'};$done=J (Join-Path $folder $leaf)
  $released=if($feedback){[bool]$done.predictor_histories_released}else{[bool]$done.predictor_history_released}
  if(!$done.passed -or !$done.actual_production_Run -or $done.physical_fields_rewritten_by_fixture -or $done.physical_acceptance -or $done.native_count -ne 512 -or $done.completed_steps -ne $steps -or !$done.live_GPU_download -or !$released){throw 'Actual final live scope/ownership failed'}
  if($feedback){if(!$done.private_feedback -or $done.public_GPU_dynamic_mode -or [double]$done.actual_end_s -ne [double]$j.end){throw 'Private k0 actual final scope differs'}}elseif(!$done.observer -or $done.feedback -or $done.public_dynamic_seepage -or [double]$done.actual_time_s -ne [double]$j.end){throw 'Observer-only final scope differs'}
  $csvLeaf=if($feedback){'live_final.csv'}else{'observer_final.csv'};$last=E (Join-Path $batch ('poro_new_'+($samples-1).ToString('D4')+'.csv'));$live=E (Join-Path $folder $csvLeaf);$oldLive=E (Join-Path $oldFolder $csvLeaf)
  if($last.bytes -ne $live.bytes -or $last.sha256 -ne $live.sha256 -or $oldLive.bytes -ne $live.bytes -or $oldLive.sha256 -ne $live.sha256){throw 'Saved/new-live/retained-live observer exports differ'};$liveEqual=@($last,$live,$oldLive);$additional+=E (Join-Path $folder $leaf)
}
if($feedback){
  foreach($side in 'old','new'){$data=if($side -eq 'old'){$oldData}else{$newData};$dest=Join-Path $review ($side+'_33');$argv=@($(if($smoke){'--read-smoke'}else{'--read'}),'GPU',$data,$dt.ToString('R',[Globalization.CultureInfo]::InvariantCulture),$dest);$calls+=InvokeOwned $h.program $argv ($name+'_read33_'+$side);$q=J (Join-Path $dest 'completion.json');if(!$q.passed -or $q.common_columns -ne 33 -or $q.samples -ne $samples -or $q.native_count -ne 512 -or $q.fixed_count -ne 0 -or !$q.saved_clock_step_exact -or !$q.native_ID_aligned -or !$q.no_exclusions -or $q.public_dynamic_metadata -or $q.native_J_arrays -ne 3 -or !$q.GPU_V_rho_k_derived_not_native_arrays -or $q.native_PosDiv_observed -or [double]$q.dt_s -ne $dt -or [double]$q.actual_end_s -ne [double]$j.end -or [double]$q.max_signed_dterror_s -gt 1e-14){throw 'Unchanged immutable33 single-run gates failed'};$readCompletions+=E (Join-Path $dest 'completion.json')}
  foreach($leaf in 'physical.bin','native_ids.csv','history.csv'){$a=E (Join-Path $review ('old_33\'+$leaf));$b=E (Join-Path $review ('new_33\'+$leaf));if($a.bytes -ne $b.bytes -or $a.sha256 -ne $b.sha256){throw "All saved immutable33 export must be byte-identical: $leaf"};$additional+=@($a,$b)}
}
VerifyAll;V @($tools.Values);V $run.files;V $oldRun.files;$files=@(Get-ChildItem -LiteralPath $review -Recurse -File|ForEach-Object {E $_.FullName})
$completionPath=Join-Path $review 'completion.json';Save $completionPath ([ordered]@{passed=$true;job=$Job;native_count=512;fixed_count=0;steps=$steps;samples=$samples;actual_end_s=[double]$j.end;dt_s=$dt;original_arrays=15;all_original15_exact=$true;all_actual_clock_step_signed_dterror_exact=$true;observer_arrays_present=$observer;all_observer_J_n_theta_exact=$observer;all_feedback_immutable_33_export_exact=$feedback;common_export_columns=$(if($feedback){33}else{0});DynamicPorePressure_enabled=$false;physical_acceptance=$false})
$files+=E $completionPath;Save $checkPath ([ordered]@{passed=$true;job=$Job;configuration=$cfg;steps=$steps;samples=$samples;all_original15_exact=$true;all_actual_clock_step_signed_dterror_exact=$true;all_observer_J_n_theta_exact=$observer;all_feedback_immutable_33_export_exact=$feedback;memcheck_zero_errors_and_leaks=($smoke -and $owned.memcheck_zero_errors_and_leaks);source_run=(E $runPath);source_build=(E $gpuPath);helper=(E $helperPath);completion=(E $completionPath);immutable33_completions=$readCompletions;adopted_control=@(E $oldCheckPath;E $oldRunPath);inputs=$recipe;dependencies=$dependencies;live_native_equal=$liveEqual;additional_exact_files=$additional;calls=$calls;files=$files;DynamicPorePressure_enabled=$false;new_complete_Darcy_branch_tested=$false;physical_acceptance=$false})
