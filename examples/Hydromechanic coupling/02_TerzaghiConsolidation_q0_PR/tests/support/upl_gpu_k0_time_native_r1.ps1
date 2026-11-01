param([Parameter(Mandatory=$true)][ValidateSet('Run','Review')][string]$Mode,[ValidateSet('Smoke','Extended')][string]$Window='Smoke',[ValidateSet('newoff','observer')][string]$Kind='newoff',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# One explicitly selected action only; no old solver, build, GenCase, feedback flag, retry, or Git action.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$preparedPath=Join-Path $logs 'upl_gpu_observer_native_r1.inputs.json'
$baselinePath=Join-Path $logs 'upl_gpu_k0_time_r1.baseline.json';$note=Join-Path $t 'notes\upl_gpu_k0_time_native_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){if(!$r -or !$r.path){throw 'Missing frozen binding'};$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){Get-Content -Raw -LiteralPath (ResolveArtifactPath $p)|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained evidence protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function ReviewPath([string]$w){Join-Path $logs ('upl_gpu_k0_time_'+$w+'_r1.review.check.json')}
function NeedSmoke {
  $p=ReviewPath 'Smoke';$r=J $p;if(!$r.passed -or !$r.all_original15_exact -or !$r.all_saved_observer_CSVs_exact -or !$r.final_live_native_csv_exact -or $r.private_feedback_tested){throw 'Fresh Smoke3 exact native review required'}
  V $r.files;V $r.calls;V $r.solvers;V @($r.completion,$r.build,$r.source_build);foreach($s in $r.solvers){$q=J $s.path;V $q.files;V @($q.call,$q.build,$q.source_build)};E $p
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root full source/recipe review and explicit single-action authorization required'}
$prepared=J $preparedPath;if($prepared.status -ne 'three_explicit_native_windows_prepared_not_run' -or @($prepared.jobs).Count -ne 3){throw 'Sealed native input manifest required'}
V $prepared.inputs;V $prepared.retained_seed;foreach($j in $prepared.jobs){V @($j.xml,$j.bi4)}
$selected=@($prepared.jobs|Where-Object {$_.window -ceq $Window});if($selected.Count -ne 1){throw 'Ambiguous frozen window'};$job=$selected[0];$cfg=$job.configuration
if($job.native -ne 512 -or $job.fixed -ne 0 -or [double]$job.n0 -ne .25 -or [double]$job.dt -ne [Math]::Pow(2,-24) -or $job.steps -ne $(if($Window -eq 'Smoke'){2}else{16}) -or $job.samples -ne $job.steps+1 -or [double]$job.end -ne $job.steps*[double]$job.dt -or ($job.prefix+'.xml') -cne $job.xml.path -or $cfg -ne $(if($Window -eq 'Smoke'){'Debug'}else{'Release'})){throw 'Exact Smoke3/Extended17 geometry and clock required'}
$b=J $baselinePath;if($b.git_base -ne 'bf5ef956d4ffaf91b0b52e57a740be03fc64cee4'){throw 'Current immutable k0-time baseline required'}
$gpuPath=Join-Path $logs ('upl_gpu_k0_time_'+$cfg+'_r1.build.json');$g=J $gpuPath
$helperPath=Join-Path $logs ('upl_gpu_k0_time_native_'+$cfg+'_r1.helper.json');$h=J $helperPath
if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $cfg -or !$g.objects_exclude_main -or !$g.canonical_GPU_unchanged -or $h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'Native' -or $h.configuration -ne $cfg -or $h.source_build.sha256 -ine (E $gpuPath).sha256){throw 'New GPU build and matching Native helper required'}
$oldReviewPath=Join-Path $logs ('upl_gpu_feedback_'+$Window+'_r2.review.check.json');$oldReview=J $oldReviewPath
if(!$oldReview.passed -or !$oldReview.all_original15_exact -or !$oldReview.all_saved_observer_CSVs_exact -or !$oldReview.final_live_native_csv_exact -or $oldReview.samples -ne $job.samples -or $oldReview.private_feedback_tested){throw 'Accepted P2 same-window control required'}
$readerPath=Join-Path $logs ('upl_gpu_feedback_Native_'+$cfg+'_r2.helper.json');$reader=J $readerPath
if($reader.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $reader.fixture -ne 'Native' -or $reader.configuration -ne $cfg){throw 'Immutable native reader recipe required'}
$dependencies=@(E $oldReviewPath);if($Window -eq 'Extended'){$dependencies+=NeedSmoke}
$recipe=@(E $PSCommandPath;E $note;E $preparedPath;E $baselinePath;E $gpuPath;E $helperPath;E $oldReviewPath;E $readerPath)
function VerifyAll {
  V $recipe;V $dependencies;V $b.inputs;V $b.other_source;V $b.canonical_GPU;V @($job.xml,$job.bi4)
  V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program);foreach($r in $g.runtime){V @($r.original,$r.copy)}
  V $h.inputs;V $h.author_files;V $h.tools;V $h.libraries;V @($h.source_build,$h.program,$h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}
  V $oldReview.files;V $oldReview.calls;V $oldReview.solvers;V $oldReview.live_native_equal;V @($oldReview.completion,$oldReview.build,$oldReview.source_build)
  V $reader.tools;V $reader.libraries;V @($reader.program,$reader.source_build,$reader.compile_call,$reader.link_call);foreach($r in $reader.runtime){V @($r.original,$r.copy)}
}
function Call([string]$exe,[string[]]$argv,[string]$label,[bool]$memcheck=$false){
  VerifyAll;$receipt=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($p in @($receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Owned call retained; never retry'}}
  $target=E $exe;$actual=$exe;$actualArgs=$argv;if($memcheck){$actual=Join-Path $env:CUDA_PATH_V11_7 'compute-sanitizer\compute-sanitizer.exe';$actualArgs=@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$exe)+$argv}
  $program=E $actual;$start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $actual @actualArgs 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old;V @($program,$target);$zero=$false
  if($memcheck){$text=[IO.File]::ReadAllText($log);$zero=$text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'}
  Save $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;target_program=$target;program=$program;arguments=$actualArgs;target_arguments=$argv;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);memcheck_executed=$memcheck;memcheck_zero_errors_and_leaks=$zero;source_build=(E $gpuPath);helper_build=(E $helperPath);recipe=$recipe;physical_acceptance=$false})
  if($code -ne 0 -or ($memcheck -and !$zero)){throw 'Owned call/memcheck failed; preserve evidence'};VerifyAll;E $receipt
}
$name='upl_gpu_k0_time_'+$Window+'_r1'
function Output([string]$kind){Join-Path $outputs ($name+'_'+$kind)}
function SolverCheck([string]$kind){Join-Path $logs ($name+'_'+$kind+'.solver.check.json')}
function OldSolver([string]$kind){
  $p=Join-Path $logs ('upl_gpu_feedback_'+$Window+'_r2_'+$kind+'.solver.check.json');$r=J $p
  if(!$r.passed -or $r.native_frames -ne $job.samples -or $r.private_feedback_enabled){throw 'Retained P2 native solver receipt unavailable'};V $r.files;V @($r.call,$r.build,$r.source_build);[pscustomobject]@{path=$p;value=$r}
}
function NeedSolver([string]$kind){
  $p=SolverCheck $kind;$r=J $p;if(!$r.passed -or $r.kind -cne $kind -or $r.native_frames -ne $job.samples -or $r.private_feedback_enabled){throw 'Fresh owned native solver receipt unavailable'}
  V $r.files;V @($r.call,$r.build,$r.source_build);$r
}
VerifyAll
if($Mode -eq 'Run'){
  $folder=Output $Kind;$check=SolverCheck $Kind;foreach($p in @($folder,$check)){if(Test-Path -LiteralPath $p){throw 'Retained solve protected'}}
  if($Kind -eq 'observer'){[void](NeedSolver 'newoff')};[void](OldSolver $Kind)
  $argv=@('-gpu','-stable',$job.prefix,$folder,'-dirdataout','data','-svres');$program=$g.isolated_GPU_program.path
  if($Kind -eq 'observer'){$program=$h.program.path;$argv=@('--solver','1')+$argv}
  $call=Call $program $argv ($name+'_'+$Kind) ($cfg -eq 'Debug');$parts=@(Get-ChildItem -LiteralPath (Join-Path $folder 'data') -Filter 'Part_????.bi4' -File)
  if($parts.Count -ne $job.samples){throw 'Actual native save count incomplete'};VerifyAll;$files=@(Get-ChildItem -LiteralPath $folder -Recurse -File|ForEach-Object {E $_.FullName})
  Save $check ([ordered]@{passed=$true;kind=$Kind;window=$Window;configuration=$cfg;build=(E $helperPath);source_build=(E $gpuPath);prepared_input=(E $preparedPath);dependencies=$dependencies;call=$call;files=$files;native_frames=$parts.Count;memcheck_executed=($cfg -eq 'Debug');memcheck_zero_errors_and_leaks=($cfg -eq 'Debug');native_review_passed=$false;private_feedback_enabled=$false;physical_acceptance=$false});exit 0
}
$newOff=NeedSolver 'newoff';$newOn=NeedSolver 'observer';$oldOff=OldSolver 'newoff';$oldOn=OldSolver 'observer'
if($cfg -eq 'Debug' -and (!$newOff.memcheck_zero_errors_and_leaks -or !$newOn.memcheck_zero_errors_and_leaks)){throw 'Both new Debug native memchecks required'}
$review=Join-Path $outputs ($name+'_review');$final=ReviewPath $Window;foreach($p in @($review,$final)){if(Test-Path -LiteralPath $p){throw 'Offline review retained; never rerun a completed solve'}}
[void](New-Item -ItemType Directory -Path $review);$calls=@();$maxJ=0.;$maxTheta=0.
for($part=0;$part -lt $job.samples;$part++){
  $tag=$part.ToString('D4');$time=$part*[double]$job.dt;$step=if($part){$part-1}else{0}
  foreach($kindValue in @('newoff','observer')){
    $oldData=Join-Path (Join-Path $outputs ('upl_gpu_feedback_'+$Window+'_r2_'+$kindValue)) 'data';$json=Join-Path $review ($kindValue+'_'+$tag+'.json')
    $calls+=Call $reader.program.path @('--compare',$oldData,(Join-Path (Output $kindValue) 'data'),"$part",'512',$json) ($name+'_compare_'+$kindValue+'_'+$tag)
    $r=J $json;if(!$r.passed -or $r.arrays -ne 15 -or $r.native_count -ne 512 -or !$r.all_original_physical_array_bits_identical -or !$r.native_ID_aligned -or !$r.saved_time_step_dterror_exact -or !$r.no_exclusions -or [double]$r.actual_time_s -ne $time -or $r.saved_step -ne $step -or [double]$r.dterror_s -gt 1e-14 -or [bool]$r.observer_schema_a -ne ($kindValue -eq 'observer') -or [bool]$r.observer_schema_b -ne ($kindValue -eq 'observer')){throw 'Original15/actualclock/signed-dterror exact regression failed'}
  }
  $pair=@();foreach($side in @('old','new')){
    $data=if($side -eq 'old'){Join-Path (Join-Path $outputs ('upl_gpu_feedback_'+$Window+'_r2_observer')) 'data'}else{Join-Path (Output 'observer') 'data'}
    $csv=Join-Path $review ('poro_'+$side+'_'+$tag+'.csv');$json=Join-Path $review ('poro_'+$side+'_'+$tag+'.json')
    $calls+=Call $reader.program.path @('--read-poro',$data,"$part",'512','0','.25',$csv,$json) ($name+'_poro_'+$side+'_'+$tag)
    $r=J $json;if(!$r.passed -or $r.double_arrays -ne 3 -or !$r.derived_n_exact -or $r.native_count -ne 512 -or $r.fixed_count -ne 0 -or [double]$r.n0 -ne .25 -or [double]$r.actual_time_s -ne $time -or $r.saved_step -ne $step){throw 'Observer double ledger/clock check failed'}
    $pair+=E $csv;$maxJ=[Math]::Max($maxJ,[Math]::Max([Math]::Abs([double]$r.min_J-1),[Math]::Abs([double]$r.max_J-1)));$maxTheta=[Math]::Max($maxTheta,[double]$r.max_abs_theta_s_inv)
  }
  $oldCsv=@($oldReview.files|Where-Object {[IO.Path]::GetFileName($_.path) -ceq ('poro_'+$tag+'.csv')});if($oldCsv.Count -ne 1){throw 'Retained observer CSV missing'};V $oldCsv
  if($pair[0].bytes -ne $pair[1].bytes -or $pair[0].sha256 -ne $pair[1].sha256 -or $pair[0].bytes -ne $oldCsv[0].bytes -or $pair[0].sha256 -ne $oldCsv[0].sha256){throw 'Every saved J/n/theta CSV must equal old/new and retained ledger'}
}
$donePath=Join-Path (Output 'observer') 'observer_complete.json';$done=J $donePath
if(!$done.passed -or !$done.observer -or !$done.actual_production_Run -or !$done.live_GPU_download -or !$done.predictor_history_released -or $done.public_dynamic_seepage -or $done.physical_fields_rewritten_by_fixture -or $done.feedback -or $done.physical_acceptance -or $done.native_count -ne 512 -or $done.fixed_count -ne 0 -or $done.completed_steps -ne $job.steps -or [double]$done.actual_time_s -ne [double]$job.end -or [double]$done.n0 -ne .25){throw 'Actual final observer scope/clock differs'}
$last=E (Join-Path $review ('poro_new_'+($job.samples-1).ToString('D4')+'.csv'));$live=E (Join-Path (Output 'observer') 'observer_final.csv');$oldLive=E (Join-Path $outputs ('upl_gpu_feedback_'+$Window+'_r2_observer\observer_final.csv'))
if($last.bytes -ne $live.bytes -or $last.sha256 -ne $live.sha256 -or $oldLive.bytes -ne $live.bytes -or $oldLive.sha256 -ne $live.sha256 -or $maxJ -le 0 -or $maxTheta -le 0){throw 'Saved/current/retained live CSV mismatch or empty observer'}
VerifyAll;foreach($r in @($newOff,$newOn,$oldOff.value,$oldOn.value)){V $r.files};$files=@(Get-ChildItem -LiteralPath $review -File|ForEach-Object {E $_.FullName})
Save $final ([ordered]@{passed=$true;window=$Window;configuration=$cfg;steps=$job.steps;samples=$job.samples;native=512;original_arrays=15;all_original15_exact=$true;all_actual_saved_time_step_signed_dterror_exact=$true;all_saved_observer_CSVs_exact=$true;old_new_PARTs_both_read_by_retained_reader=$true;final_live_native_csv_exact=$true;max_abs_J_minus_1=$maxJ;max_abs_theta=$maxTheta;completion=(E $donePath);live_native_equal=@($last,$live,$oldLive);build=(E $helperPath);source_build=(E $gpuPath);reader=(E $readerPath);solvers=@(E (SolverCheck 'newoff');E (SolverCheck 'observer'));adopted_controls=@(E $oldOff.path;E $oldOn.path;E $oldReviewPath);dependencies=$dependencies;calls=$calls;files=$files;canonical_GPU_unchanged=$true;private_feedback_tested=$false;current_J_acoustic_guard_tested=$false;physical_acceptance=$false})
