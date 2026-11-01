param(
  [Parameter(Mandatory=$true)][ValidateSet('RunComponent','RunNative','ReviewNative')][string]$Mode,
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [ValidateSet('State','Theta','Feedback')][string]$Fixture='Feedback',
  [ValidateSet('Smoke','Extended')][string]$Window='Smoke',
  [ValidateSet('newoff','observer')][string]$Kind='newoff',
  [switch]$Integrate,
  [switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized
)
# Exactly one explicit r2 run/review. No build, GenCase, old-solver rerun, retry, chain or Git.
# Retain failed r1 evidence. Only r2 build/helpers/results may satisfy new gates; old observer r1 is the immutable control.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $tests 'logs';$outputs=Join-Path $tests 'outputs'
$preparedPath=Join-Path $logs 'upl_gpu_observer_native_r1.inputs.json'
$baselinePath=Join-Path $logs 'upl_gpu_feedback_r1.baseline.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Resolve([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function Verify($rows){foreach($r in $rows){if(!$r -or !$r.path){throw 'Missing frozen binding'};$a=Entry (Resolve $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function NeedCheck([string]$p){$r=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json;if(!$r.passed -or $r.physical_acceptance){throw "Prior bounded gate unavailable: $p"};Verify $r.files;foreach($key in @('build','completion','call')){if($r.$key){Verify @($r.$key)}};Entry $p}
function NativeReviewPath([string]$w){Join-Path $logs ('upl_gpu_feedback_'+$w+'_r2.review.check.json')}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root full source/recipe review and explicit single-action authorization required'}
if($Integrate -and ($Mode -ne 'RunComponent' -or $Fixture -ne 'Feedback')){throw 'Integrate is only the separately admitted feedback component'}
$prepared=Get-Content -Raw -LiteralPath $preparedPath|ConvertFrom-Json
if($prepared.status -ne 'three_explicit_native_windows_prepared_not_run' -or $prepared.jobs.Count -ne 3){throw 'Retained three-window input manifest required'}
Verify $prepared.inputs;Verify $prepared.retained_seed;foreach($j in $prepared.jobs){Verify @($j.xml,$j.bi4)}
$selected=@($prepared.jobs|Where-Object {$_.window -ceq $Window});if($selected.Count -ne 1){throw 'Ambiguous retained window'};$job=$selected[0]
if($job.native -ne 512 -or $job.fixed -ne 0 -or [double]$job.n0 -ne .25 -or [double]$job.dt -ne [Math]::Pow(2,-24) -or $job.steps -ne $(if($Window -eq 'Smoke'){2}else{16}) -or $job.samples -ne $job.steps+1 -or [double]$job.end -ne $job.steps*[double]$job.dt -or ($job.prefix+'.xml') -cne $job.xml.path){throw 'Retained Smoke3/Extended17 seed/clock differs'}
if($Mode -ne 'RunComponent'){$Configuration=$job.configuration}
$baseline=Get-Content -Raw -LiteralPath $baselinePath|ConvertFrom-Json
if($baseline.status -ne 'pre_five_feedback_edits_source_and_retained_observer_GPU_programs_frozen' -or $baseline.old_five_sources.Count -ne 5){throw 'Pre-feedback immutable baseline required'}
$gpuPath=Join-Path $logs ('upl_gpu_feedback_'+$Configuration+'_r2.build.json')
$gpu=Get-Content -Raw -LiteralPath $gpuPath|ConvertFrom-Json
if($gpu.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $gpu.configuration -ne $Configuration -or !$gpu.objects_exclude_main -or !$gpu.canonical_GPU_unchanged){throw 'New authoritative isolated feedback GPU build required'}
$recipe=@(Entry $PSCommandPath;Entry $preparedPath;Entry $baselinePath;Entry $gpuPath)
function Helper([string]$fixture){
  $p=Join-Path $logs ('upl_gpu_feedback_'+$fixture+'_'+$Configuration+'_r2.helper.json')
  $h=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
  if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne $fixture -or $h.configuration -ne $Configuration -or !$h.only_chosen_helper_author_files_frozen){throw 'Chosen actual-object helper unavailable'}
  if($h.source_build.sha256 -ne (Entry $gpuPath).sha256){throw 'Chosen helper does not match this GPU source build'}
  Verify $h.inputs;Verify $h.tools;Verify $h.libraries;Verify @($h.source_build,$h.program,$h.compile_call,$h.link_call)
  foreach($r in $h.runtime){Verify @($r.original,$r.copy)};foreach($r in $h.snapshots){Verify @($r.original,$r.copy)}
  [pscustomobject]@{path=$p;value=$h}
}
$selectedHelper=if($Mode -eq 'RunComponent'){Helper $Fixture}else{Helper 'Native'}
$helper=$selectedHelper.value;$recipe+=Entry $selectedHelper.path
function VerifyAll {
  Verify $recipe;Verify $gpu.inputs;Verify $gpu.tools;Verify $gpu.objects
  Verify @($gpu.baseline,$gpu.source_freeze,$gpu.project_call,$gpu.isolated_GPU_program)
  Verify $baseline.canonical_GPU;foreach($r in $baseline.old_five_sources){Verify @($r.copy)}
  foreach($r in $baseline.retained_observer_GPU_programs){Verify @($r.program.original,$r.program.copy);foreach($v in $r.runtime){Verify @($v.original,$v.copy)}}
  foreach($r in $gpu.runtime){Verify @($r.original,$r.copy)}
  Verify $helper.inputs;Verify $helper.tools;Verify $helper.libraries;Verify @($helper.source_build,$helper.program,$helper.compile_call,$helper.link_call)
  foreach($r in $helper.runtime){Verify @($r.original,$r.copy)};foreach($r in $helper.snapshots){Verify @($r.original,$r.copy)}
  Verify @($job.xml,$job.bi4)
}
function Call([string]$exe,[string[]]$argv,[string]$label,[bool]$memcheck=$false){
  VerifyAll;$receipt=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log')
  foreach($p in @($receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Owned call retained; no retry'}}
  $target=Entry $exe;$actual=$exe;$actualArgs=$argv;$tool=$null
  if($memcheck){$actual=Join-Path $env:CUDA_PATH_V11_7 'compute-sanitizer\compute-sanitizer.exe';$tool=Entry $actual;$actualArgs=@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$exe)+$argv}
  $program=Entry $actual;$start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@())
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';& $actual @actualArgs 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  Verify @($program,$target);$zero=$false
  if($memcheck){$text=[IO.File]::ReadAllText($log);$zero=$text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'}
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;target_program=$target;program=$program;arguments=$actualArgs;target_arguments=$argv;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);memcheck_executed=$memcheck;memcheck_zero_errors_and_leaks=$zero;source_build=(Entry $gpuPath);helper_build=(Entry $selectedHelper.path);recipe=$recipe;physical_acceptance=$false})
  if($code -ne 0 -or ($memcheck -and !$zero)){throw "Owned call/memcheck failed; preserve $receipt"};VerifyAll;Entry $receipt
}
function NeedNative([string]$w){
  $p=NativeReviewPath $w;$r=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
  if(!$r.passed -or !$r.all_original15_exact -or !$r.all_saved_observer_CSVs_exact -or !$r.final_live_native_csv_exact){throw 'New Debug smoke native review required'}
  [void](NeedCheck $p);Verify $r.calls;Verify $r.solvers;Entry $p
}
$dependencies=@()
if($Mode -eq 'RunComponent'){
  $dependencies+=NeedNative 'Smoke'
  $staticName='upl_gpu_feedback_'+$Fixture+'_'+$Configuration+'_r2'
  if($Configuration -eq 'Release'){
    if($Fixture -eq 'Feedback'){
      # Both fresh Debug r2 gates precede either Release feedback mode, not failed/adopted r1.
      $dependencies+=NeedCheck (Join-Path $logs 'upl_gpu_feedback_Feedback_Debug_r2.check.json')
      $dependencies+=NeedCheck (Join-Path $logs 'upl_gpu_feedback_Feedback_Debug_r2_integrated.check.json')
    }else{$dependencies+=NeedCheck (Join-Path $logs ('upl_gpu_feedback_'+$Fixture+'_Debug_r2.check.json'))}
  }
  if($Integrate){$dependencies+=NeedCheck (Join-Path $logs ($staticName+'.check.json'))}
  $name=$staticName+$(if($Integrate){'_integrated'}else{''});$out=Join-Path $outputs ($name+'_data');$check=Join-Path $logs ($name+'.check.json')
  foreach($p in @($out,$check)){if(Test-Path -LiteralPath $p){throw 'Component evidence retained'}}
  if($Fixture -eq 'State'){$argv=@('--state','-gpu','-stable',$job.prefix,$out,'-dirdataout','data','-svres');$completion=Join-Path $out 'state_complete.json'}
  else{$argv=@('--out',$out,'--device','0');if($Integrate){$argv+='--integrate'};$completion=Join-Path $out 'completion.json'}
  $call=Call $helper.program.path $argv ($name+'_component') ($Configuration -eq 'Debug')
  $done=Get-Content -Raw -LiteralPath $completion|ConvertFrom-Json
  if(!$done.passed -or $done.physical_acceptance){throw 'Component failed or physical scope changed'}
  if($Fixture -eq 'State'){
    if($done.native_count -ne 512 -or $done.fixed_count -ne 0 -or !$done.real_cell_reorder -or $done.actual_nonzero_prefix_cell_division -or !$done.periodic_JPre_with_PosPre_NULL -or $done.clone_of_clone_checks -le 0 -or !$done.live_JPre_resize_preserved -or $done.new_GPU_capacity -le $done.old_GPU_capacity -or !$done.corrector_recurrence_checked -or !$done.predictor_history_released -or $done.invalid_J_rejections -ne 3 -or !$done.native_plastic_rejected -or !$done.periodic_plastic_poison_ignored -or $done.periodic_plastic_poison_slots -le 0 -or !$done.copy_sort_resize_bit_exact -or $done.corrector_tail_guard_slots -ne 7 -or $done.component_extra_RunCellDivide_calls -ne 3 -or !$done.actual_LoadConfig_ConfigDomain_InitRunGpu -or !$done.actual_J_host_and_CUDA_helpers -or $done.actual_force_calls -ne 0 -or $done.completed_physics_steps -ne 0 -or [double]$done.actual_time_s -ne 0 -or $done.Nstep -ne 0 -or $done.public_GPU_dynamic_mode -or $done.feedback){throw 'Original State lifecycle gates differ'}
  }elseif($Fixture -eq 'Theta'){
    if($done.cases -ne 10 -or $done.actual_kernel_calls -ne 30 -or $done.node_output_rows -ne 270 -or $done.native_OFF_ON_output_pairs -ne 180 -or $done.NULL_theta_sentinel_checks -ne 90 -or $done.same_stage_reset_theta_pairs -ne 90 -or $done.nonzero_trace_ON_checks -ne 8 -or $done.drained_nonzero_theta_zero_pore_rate_checks -ne 4 -or $done.nonempty_shear_stress_checks -ne 4 -or !$done.actual_force_kernel_only -or $done.general_C_matrix_solver_tested -or $done.physical_drained_run_admitted -or $done.time_integrated -or $done.feedback_tested){throw 'Original Theta gates differ'}
  }else{
    if($done.dimension -ne 2 -or $done.pair_rows -ne 4 -or $done.affine_rows -ne 27 -or $done.static_force_calls -ne 10 -or $done.static_actual_FS_calls -ne 6 -or $done.positive_oldrho_poison_node_pairs -ne 31 -or !$done.six_stress_components_per_affine_node -or !$done.mixed_XZ_shear_nonempty -or [bool]$done.optional_integration_executed -ne [bool]$Integrate -or $done.physical_outer_loop_used -or !$done.prescribed_kinematics -or $done.dynamic_Darcy_tested){throw 'Predeclared feedback component scope/counts differ'}
    if($Integrate -and ($done.independent_half_pairs -ne 260 -or !$done.actual_pressure_J_update_kernels -or [double]$done.max_pressure_log_reference_error_pa -gt 1 -or [double]$done.max_half_pressure_difference_pa -gt .5 -or [double]$done.max_null_pressure_pa -gt .02)){throw 'Original optional prescribed-component gates failed'}
  }
  VerifyAll;Verify $dependencies;$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object {Entry $_.FullName})
  NewJson $check ([ordered]@{passed=$true;fixture=$Fixture;configuration=$Configuration;integrated_component=[bool]$Integrate;build=(Entry $selectedHelper.path);source_build=(Entry $gpuPath);completion=(Entry $completion);call=$call;dependencies=$dependencies;files=$files;memcheck_executed=($Configuration -eq 'Debug');memcheck_zero_errors_and_leaks=($Configuration -eq 'Debug');feedback_outer_loop_admitted=$false;physical_acceptance=$false})
  Write-Output 'PASSED selected bounded component only';exit 0
}
if($Configuration -eq 'Release'){$dependencies+=NeedNative 'Smoke'}
$name='upl_gpu_feedback_'+$Window+'_r2'
function Output([string]$kind){Join-Path $outputs ($name+'_'+$kind)}
function SolverCheck([string]$kind){Join-Path $logs ($name+'_'+$kind+'.solver.check.json')}
function NeedSolver([string]$kind){
  $p=SolverCheck $kind;$r=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
  if(!$r.passed -or $r.kind -cne $kind -or $r.native_frames -ne $job.samples){throw 'New owned native solve receipt unavailable'}
  Verify $r.files;Verify @($r.call,$r.build,$r.source_build);$r
}
function OldSolver([string]$kind){
  $p=Join-Path $logs ('upl_gpu_observer_'+$Window+'_r1_'+$kind+'.solver.check.json');$r=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
  if(!$r.passed -or $r.native_frames -ne $job.samples){throw 'Retained completed observer native control missing'}
  Verify $r.files;Verify @($r.call,$r.build);[pscustomobject]@{path=$p;value=$r}
}
$oldReviewPath=Join-Path $logs ('upl_gpu_observer_'+$Window+'_r1.review.check.json')
$oldReview=Get-Content -Raw -LiteralPath $oldReviewPath|ConvertFrom-Json
if(!$oldReview.passed -or !$oldReview.all_original15_exact -or !$oldReview.final_live_native_csv_exact){throw 'Accepted retained original observer review required'}
Verify $oldReview.files;Verify @($oldReview.completion);$dependencies+=Entry $oldReviewPath
if($Mode -eq 'RunNative'){
  $out=Output $Kind;$check=SolverCheck $Kind;foreach($p in @($out,$check)){if(Test-Path -LiteralPath $p){throw 'New native solve output/receipt retained'}}
  if($Kind -eq 'observer'){[void](NeedSolver 'newoff')};[void](OldSolver $Kind)
  $argv=@('-gpu','-stable',$job.prefix,$out,'-dirdataout','data','-svres')
  if($Kind -eq 'observer'){$program=$helper.program.path;$argv=@('--solver','1')+$argv}else{$program=$gpu.isolated_GPU_program.path}
  $call=Call $program $argv ($name+'_'+$Kind) ($Configuration -eq 'Debug')
  $parts=@(Get-ChildItem -LiteralPath (Join-Path $out 'data') -Filter 'Part_????.bi4' -File)
  if($parts.Count -ne $job.samples){throw 'Actual native save count incomplete'}
  VerifyAll;$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object {Entry $_.FullName})
  NewJson $check ([ordered]@{passed=$true;kind=$Kind;window=$Window;configuration=$Configuration;build=(Entry $selectedHelper.path);source_build=(Entry $gpuPath);prepared_input=(Entry $preparedPath);dependencies=$dependencies;call=$call;files=$files;native_frames=$parts.Count;memcheck_executed=($Configuration -eq 'Debug');memcheck_zero_errors_and_leaks=($Configuration -eq 'Debug');native_review_passed=$false;private_feedback_enabled=$false;physical_acceptance=$false})
  Write-Output 'SEALED new native solve only; explicitly choose next action or ReviewNative';exit 0
}
$newOff=NeedSolver 'newoff';$newOn=NeedSolver 'observer';$oldOff=OldSolver 'newoff';$oldOn=OldSolver 'observer'
$review=Join-Path $outputs ($name+'_review');$final=NativeReviewPath $Window
foreach($p in @($review,$final)){if(Test-Path -LiteralPath $p){throw 'Offline review retained; never rerun a completed solver'}}
if($Configuration -eq 'Debug' -and (!$newOff.memcheck_zero_errors_and_leaks -or !$newOn.memcheck_zero_errors_and_leaks)){throw 'Both new Debug native memchecks required'}
[void](New-Item -ItemType Directory -Path $review);$calls=@();$reports=@();$maxJ=0.;$maxTheta=0.
for($part=0;$part -lt $job.samples;$part++){
  $tag=$part.ToString('D4');$time=$part*[double]$job.dt;$step=if($part){$part-1}else{0}
  foreach($kindValue in @('newoff','observer')){
    $oldData=Join-Path (Join-Path $outputs ('upl_gpu_observer_'+$Window+'_r1_'+$kindValue)) 'data'
    $json=Join-Path $review ($kindValue+'_'+$tag+'.json')
    $calls+=Call $helper.program.path @('--compare',$oldData,(Join-Path (Output $kindValue) 'data'),"$part",'512',$json) ($name+'_compare_'+$kindValue+'_'+$tag)
    $r=Get-Content -Raw -LiteralPath $json|ConvertFrom-Json
    if(!$r.passed -or $r.arrays -ne 15 -or $r.native_count -ne 512 -or !$r.all_original_physical_array_bits_identical -or !$r.native_ID_aligned -or !$r.saved_time_step_dterror_exact -or !$r.no_exclusions -or [double]$r.actual_time_s -ne $time -or $r.saved_step -ne $step -or [double]$r.dterror_s -gt 1e-14 -or [bool]$r.observer_schema_a -ne ($kindValue -eq 'observer') -or [bool]$r.observer_schema_b -ne ($kindValue -eq 'observer')){throw 'Immutable original15/actualclock/signed-dterror exact regression failed'};$reports+=Entry $json
  }
  $csv=Join-Path $review ('poro_'+$tag+'.csv');$json=Join-Path $review ('poro_'+$tag+'.json')
  $calls+=Call $helper.program.path @('--read-poro',(Join-Path (Output 'observer') 'data'),"$part",'512','0','.25',$csv,$json) ($name+'_poro_'+$tag)
  $r=Get-Content -Raw -LiteralPath $json|ConvertFrom-Json
  if(!$r.passed -or $r.double_arrays -ne 3 -or !$r.derived_n_exact -or $r.native_count -ne 512 -or $r.fixed_count -ne 0 -or [double]$r.n0 -ne .25 -or [double]$r.actual_time_s -ne $time -or $r.saved_step -ne $step){throw 'Observer native double ledger/clock check failed'}
  $oldCsv=@($oldReview.files|Where-Object {[IO.Path]::GetFileName($_.path) -ceq ('poro_'+$tag+'.csv')});if($oldCsv.Count -ne 1){throw 'Retained own-time observer CSV missing'}
  Verify $oldCsv;$now=Entry $csv;if($now.bytes -ne $oldCsv[0].bytes -or $now.sha256 -ne $oldCsv[0].sha256){throw 'J/n/theta CSV differs from retained same-input observer'}
  $maxJ=[Math]::Max($maxJ,[Math]::Max([Math]::Abs([double]$r.min_J-1),[Math]::Abs([double]$r.max_J-1)));$maxTheta=[Math]::Max($maxTheta,[double]$r.max_abs_theta_s_inv);$reports+=@(Entry $csv;Entry $json)
}
$donePath=Join-Path (Output 'observer') 'observer_complete.json';$done=Get-Content -Raw -LiteralPath $donePath|ConvertFrom-Json
if(!$done.passed -or !$done.observer -or !$done.actual_production_Run -or !$done.live_GPU_download -or !$done.predictor_history_released -or $done.public_dynamic_seepage -or $done.physical_fields_rewritten_by_fixture -or $done.feedback -or $done.physical_acceptance -or $done.native_count -ne 512 -or $done.fixed_count -ne 0 -or $done.completed_steps -ne $job.steps -or [double]$done.actual_time_s -ne [double]$job.end -or [double]$done.n0 -ne .25){throw 'Actual final observer scope/clock differs'}
$last=Entry (Join-Path $review ('poro_'+($job.samples-1).ToString('D4')+'.csv'));$live=Entry (Join-Path (Output 'observer') 'observer_final.csv')
$oldLive=Entry (Join-Path $outputs ('upl_gpu_observer_'+$Window+'_r1_observer\observer_final.csv'))
if($last.bytes -ne $live.bytes -or $last.sha256 -ne $live.sha256 -or $oldLive.bytes -ne $live.bytes -or $oldLive.sha256 -ne $live.sha256 -or $maxJ -le 0 -or $maxTheta -le 0){throw 'Current/retained native/live observer mismatch or empty J/theta'}
VerifyAll;foreach($r in @($newOff,$newOn,$oldOff.value,$oldOn.value)){Verify $r.files};Verify $oldReview.files;Verify $dependencies
$files=@(Get-ChildItem -LiteralPath $review -File|ForEach-Object {Entry $_.FullName})
NewJson $final ([ordered]@{passed=$true;window=$Window;configuration=$Configuration;steps=$job.steps;samples=$job.samples;native=512;original_arrays=15;all_original15_exact=$true;all_actual_saved_time_step_signed_dterror_exact=$true;all_saved_observer_CSVs_exact=$true;final_live_native_csv_exact=$true;max_abs_J_minus_1=$maxJ;max_abs_theta=$maxTheta;completion=(Entry $donePath);live_native_equal=@($last,$live,$oldLive);build=(Entry $selectedHelper.path);source_build=(Entry $gpuPath);solvers=@(Entry (SolverCheck 'newoff');Entry (SolverCheck 'observer'));adopted_controls=@(Entry $oldOff.path;Entry $oldOn.path;Entry $oldReviewPath);dependencies=$dependencies;calls=$calls;files=$files;canonical_GPU_unchanged=$true;private_feedback_tested=$false;physical_acceptance=$false})
Write-Output 'PASSED new OFF and observer-only implementation invariance; not feedback/physics acceptance'
