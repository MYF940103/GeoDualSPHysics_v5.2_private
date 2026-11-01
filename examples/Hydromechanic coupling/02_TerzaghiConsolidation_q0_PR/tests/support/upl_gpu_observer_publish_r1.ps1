param([ValidateSet('List','Seal','Manifest','Stage')][string]$Mode='List',[switch]$CpuDebugExitObserved0,[switch]$StageAuthorized,[string]$ReviewedManifestSha256='')
# Aggregate/selective text publication only. No build, helper, solver, commit or push.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$base='18235c6d054958c60c1226872216ceb315f1966c'
$manifest=Join-Path $tests 'logs\upl_gpu_observer_publish_r1.json';$aggregate=Join-Path $tests 'logs\upl_gpu_observer_stage_r1.check.json'
$five=@('JSphGpu.h','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')
$baselinePath=Join-Path $tests 'logs\upl_gpu_observer_r1.baseline.json'
$cpuLog=Join-Path $tests 'logs\upl_gpu_observer_CPU_Debug_default_r1.build.log'
$statusPath=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;if(!$f.FullName.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Escaped repository'};[ordered]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Resolve([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function Verify($rows){foreach($r in $rows){$p=Resolve $r.path;$f=Get-Item -LiteralPath $p;if($f.Length -ne $r.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ine $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function Load([string]$p){Get-Content -Raw -LiteralPath (Resolve $p)|ConvertFrom-Json}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function NeedCall($r){Verify @($r);$c=Load $r.path;if(!$c.owned_call_exited -or $c.exit_code -ne 0){throw 'Owned call did not exit0'};Verify @($c.program,$c.log);$c}
function NeedMemcheck($call){$c=NeedCall $call;$text=[IO.File]::ReadAllText((Resolve $c.log.path));if($text -notmatch 'ERROR SUMMARY:\s*0 errors' -or $text -notmatch 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'){throw 'Actual zero-error/zero-byte-leak memcheck report missing'}}
function Candidates {
  $p=@($five|ForEach-Object {Join-Path $repo ('src\source\'+$_)})+@($statusPath)
  foreach($f in @('support\upl_gpu_observer_build_r1.ps1','support\upl_gpu_observer_native_r1.ps1','support\upl_gpu_observer_native_r1.cpp','support\upl_gpu_observer_components_r1.ps1','support\upl_gpu_observer_state_r1.cpp','support\upl_gpu_observer_theta_r1.cpp','support\upl_gpu_observer_publish_r1.ps1','notes\upl_gpu_observer_native_r1.json','notes\upl_gpu_observer_run_r1.json','notes\upl_gpu_observer_state_r1.json','notes\upl_gpu_observer_theta_r1.json','notes\upl_gpu_observer_review_r1.json')){$p+=Join-Path $tests $f}
  $p+=Get-ChildItem -LiteralPath (Join-Path $tests 'logs') -File|Where-Object {$_.Name -like 'upl_gpu_observer*' -and $_.Extension -eq '.json' -and $_.Name -notmatch '_compare_|_poro_' -and $_.FullName -ne $manifest}|ForEach-Object {$_.FullName}
  $p+=Get-ChildItem -LiteralPath (Join-Path $tests 'logs') -File|Where-Object {$_.Name -like 'upl_gpu_observer*' -and $_.Extension -eq '.log' -and ($_.Name -match '_project\.log$|_compile\.log$|_link\.log$|_memcheck\.log$|_component\.log$' -or $_.FullName -eq $cpuLog -or $_.Name -eq 'upl_gpu_observer_Smoke_r1_observer.log')}|ForEach-Object {$_.FullName}
  foreach($d in @('upl_gpu_observer_prebuild_r1','upl_gpu_observer_Debug_r1','upl_gpu_observer_Release_r1')){foreach($f in $five){$p+=Join-Path $tests ('outputs\'+$d+'\'+$f)}}
  foreach($w in @('Smoke','Short','Extended')){
    $p+=Join-Path $tests ('outputs\upl_gpu_observer_seed_'+$w+'_r1\CaseUplObserver.xml')
    foreach($k in @('oldoff','newoff','observer')){$d=Join-Path $tests ('outputs\upl_gpu_observer_'+$w+'_r1_'+$k);foreach($f in @('Run.out','Run.csv')){$p+=Join-Path $d $f};if($k -eq 'observer'){foreach($f in @('observer_final.csv','observer_complete.json')){$p+=Join-Path $d $f}}}
    $d=Join-Path $tests ('outputs\upl_gpu_observer_'+$w+'_r1_review');if(Test-Path -LiteralPath $d){$p+=Get-ChildItem -LiteralPath $d -File|Where-Object {$_.Extension -in '.json','.csv'}|ForEach-Object {$_.FullName}}
  }
  foreach($f in @('State','Theta')){foreach($c in @('Debug','Release')){$d=Join-Path $tests ('outputs\upl_gpu_observer_'+$f+'_'+$c+'_r1_data');if(Test-Path -LiteralPath $d){$p+=Get-ChildItem -LiteralPath $d -File|Where-Object {$_.Extension -in '.csv','.json' -or $_.Name -eq 'Run.out'}|ForEach-Object {$_.FullName}}}}
  @($p|Sort-Object -Unique)
}
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Explicit StageAuthorized and exact reviewed manifest SHA required'}
  $m=Load $manifest;$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$index=@(& git -C $repo -c core.quotepath=false diff --cached --name-only);$indexCode=$LASTEXITCODE;$ErrorActionPreference=$old
  if($code -or $indexCode -or $head -ne $base -or !$m.ready_for_root_review -or $m.base -ne $base){throw 'Changed base or unread manifest/index'}
  Verify $m.files;Verify @($m.aggregate);$paths=@($m.files.path)+@($manifest.Substring($repo.Length+1).Replace('\','/'))
  foreach($p in $index){if($p -and $p -notin $paths){throw 'Unrelated staged changes preserved; no stage attempted'}}
  for($i=0;$i -lt $paths.Count;$i+=20){$last=[Math]::Min($i+19,$paths.Count-1);$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$msg=& git -C $repo --literal-pathspecs add -f -- @($paths[$i..$last]) 2>&1;$code=$LASTEXITCODE;$ErrorActionPreference=$old;$msg|Out-Host;if($code){throw 'Stage failed; preserve partial index for root inspection'}}
  Write-Output "STAGED $($paths.Count) explicit paths; no commit/push";exit 0
}
$required=@($baselinePath,$cpuLog,$statusPath)
foreach($w in @('Smoke','Short','Extended')){$required+=Join-Path $tests ('logs\upl_gpu_observer_'+$w+'_r1.review.check.json')}
foreach($f in @('State','Theta')){foreach($c in @('Debug','Release')){$required+=Join-Path $tests ('logs\upl_gpu_observer_'+$f+'_'+$c+'_r1.check.json')}}
$candidate=Candidates;$missing=@(($required+$candidate)|Sort-Object -Unique|Where-Object {!(Test-Path -LiteralPath $_)})
if($Mode -eq 'List'){$files=@($candidate|Where-Object {Test-Path -LiteralPath $_}|ForEach-Object {Entry $_});[pscustomobject]@{base=$base;count=$files.Count;bytes=($files|ForEach-Object {[long]$_.bytes}|Measure-Object -Sum).Sum;missing=$missing;aggregate_created_only_at_Seal=$true;CPU_exit_requires_root_direct_observation=$true;files=$files;Git_mutated=$false};return}
$reuseAggregate=$Mode -eq 'Manifest'
if($missing.Count -or (Test-Path -LiteralPath $manifest) -or !$CpuDebugExitObserved0 -or ($reuseAggregate -and !(Test-Path -LiteralPath $aggregate)) -or (!$reuseAggregate -and (Test-Path -LiteralPath $aggregate))){throw 'Seal needs fresh outputs; Manifest needs only an existing verified aggregate. Complete evidence and root CPU exit0 observation required'}
$status=Load $statusPath;if($status.limited_canonical_CPU_entry_review.private_raw_comparison -notmatch 'FALSE'){throw 'Preserve the existing CPU full-raw comparison FALSE limitation'}
$b=Load $baselinePath
if($b.status -ne 'pre_five_observer_edits_source_and_retained_sort_GPU_programs_frozen' -or $b.root_verified_checkpoint -ne $base -or $b.old_five_sources.Count -ne 5){throw 'Wrong pre-edit observer baseline'}
Verify $b.inputs;Verify $b.canonical_GPU;Verify @($b.source|Where-Object {[IO.Path]::GetFileName($_.path) -notin $five})
foreach($r in $b.old_five_sources){Verify @($r.snapshot)}
foreach($r in $b.retained_sort_GPU_programs){Verify @($r.build,$r.check,$r.program.original,$r.program.snapshot);foreach($v in $r.runtime){Verify @($v.original,$v.snapshot)}}
$gpuBuilds=@();$source=@()
foreach($cfg in @('Debug','Release')){
  $p=Join-Path $tests ('logs\upl_gpu_observer_'+$cfg+'_r1.build.json');$g=Load $p
  if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_fixture_or_program_run' -or $g.configuration -ne $cfg -or !$g.objects_exclude_main -or !$g.canonical_GPU_unchanged -or $g.objects.Count -lt 80){throw 'Authoritative observer GPU build contract differs'}
  Verify $g.inputs;Verify $g.tools;Verify $g.objects;Verify @($g.baseline,$g.source_freeze,$g.isolated_GPU_program);[void](NeedCall $g.project_call)
  $s=Load $g.source_freeze.path;if($s.source.Count -ne 5){throw 'Exactly five new source snapshots required'}
  foreach($r in $s.source){if([IO.Path]::GetFileName($r.original.path) -notin $five){throw 'Unexpected source snapshot'};Verify @($r.original,$r.snapshot);if($cfg -eq 'Debug'){$source+=Entry (Resolve $r.original.path)}}
  foreach($r in $g.runtime){Verify @($r.original,$r.snapshot)};$gpuBuilds+=Entry $p
}
function VerifyLinkedBuild($entry){
  Verify @($entry);$l=Load $entry.path
  if($l.status -notin 'actual_authoritative_GPU_object_helper_linked_not_run','actual_authoritative_GPU_object_component_linked_not_run' -or !$l.canonical_GPU_unchanged){throw 'Unexpected actual-object helper/component build'}
  Verify $l.inputs;Verify $l.dependencies;Verify $l.tools;Verify $l.libraries;Verify @($l.source_build,$l.program);[void](NeedCall $l.compile_call);[void](NeedCall $l.link_call)
  foreach($r in $l.snapshots){Verify @($r.original,$r.copy)};foreach($r in $l.runtime){Verify @($r.original,$r.copy)}
  if($l.old_main){Verify @($l.old_main.original,$l.old_main.copy,$l.new_main.original,$l.new_main.copy,$l.prepared_inputs)}
}
$native=@()
foreach($w in @('Smoke','Short','Extended')){
  $p=Join-Path $tests ('logs\upl_gpu_observer_'+$w+'_r1.review.check.json');$r=Load $p;$count=if($w -eq 'Smoke'){3}elseif($w -eq 'Short'){9}else{17}
  if(!$r.passed -or $r.samples -ne $count -or $r.native -ne 512 -or $r.original_arrays -ne 15 -or !$r.all_original15_exact -or !$r.all_actual_saved_time_step_signed_dterror_exact -or !$r.three_native_double_observer_arrays_checked -or !$r.final_live_native_csv_exact -or $r.independent_theta_or_J_recurrence_tested -or $r.dynamic_feedback_tested -or $r.physical_acceptance){throw 'Native exact clock/15-array/observer scope gate differs'}
  Verify $r.files;Verify @($r.completion);Verify $r.live_native_equal;VerifyLinkedBuild $r.build
  foreach($c in $r.calls){[void](NeedCall $c)}
  foreach($e in $r.solvers){Verify @($e);$solver=Load $e.path;if(!$solver.passed -or $solver.native_frames -ne $count){throw 'Native solver not sealed complete'};Verify $solver.files;VerifyLinkedBuild $solver.build;[void](NeedCall $solver.call);if($w -eq 'Smoke' -and $solver.kind -eq 'observer'){if(!$solver.memcheck_zero_errors_and_leaks){throw 'Debug native memcheck flag missing'};NeedMemcheck $solver.call}}
  $native+=@{review=(Entry $p);samples=$r.samples;max_abs_J_minus_1=$r.max_abs_J_minus_1;max_abs_theta=$r.max_abs_theta}
}
$components=@()
foreach($fixture in @('State','Theta')){foreach($cfg in @('Debug','Release')){
  $p=Join-Path $tests ('logs\upl_gpu_observer_'+$fixture+'_'+$cfg+'_r1.check.json');$c=Load $p
  if(!$c.passed -or $c.fixture -ne $fixture -or $c.configuration -ne $cfg -or !$c.canonical_GPU_unchanged -or $c.physical_acceptance){throw 'Component gate identity differs'}
  Verify $c.files;Verify @($c.completion,$c.native_smoke);VerifyLinkedBuild $c.build;[void](NeedCall $c.call);if($cfg -eq 'Debug'){if(!$c.memcheck_zero_errors_and_leaks){throw 'Component Debug memcheck flag missing'};NeedMemcheck $c.call}
  $d=Load $c.completion.path;if(!$d.passed -or $d.physical_acceptance){throw 'Component completion rejected'}
  if($fixture -eq 'State'){
    if($d.native_count -ne 512 -or !$d.real_cell_reorder -or $d.actual_nonzero_prefix_cell_division -or !$d.periodic_JPre_with_PosPre_NULL -or $d.clone_of_clone_checks -le 0 -or !$d.live_JPre_resize_preserved -or !$d.corrector_recurrence_checked -or !$d.predictor_history_released -or $d.invalid_J_rejections -ne 3 -or !$d.native_plastic_rejected -or !$d.periodic_plastic_poison_ignored -or !$d.copy_sort_resize_bit_exact -or $d.actual_force_calls -ne 0 -or $d.completed_physics_steps -ne 0 -or [double]$d.actual_time_s -ne 0 -or $d.feedback){throw 'State lifecycle/recurrence/scope differs'}
  }elseif($d.cases -ne 10 -or $d.actual_kernel_calls -ne 30 -or $d.node_output_rows -ne 270 -or $d.native_OFF_ON_output_pairs -ne 180 -or $d.NULL_theta_sentinel_checks -ne 90 -or $d.same_stage_reset_theta_pairs -ne 90 -or $d.nonzero_trace_ON_checks -ne 8 -or $d.drained_nonzero_theta_zero_pore_rate_checks -ne 4 -or $d.nonempty_shear_stress_checks -ne 4 -or !$d.actual_force_kernel_only -or $d.general_C_matrix_solver_tested -or $d.physical_drained_run_admitted -or $d.time_integrated -or $d.feedback_tested){throw 'Theta manufactured/count/scope differs'}
  $components+=@{check=(Entry $p);completion=$c.completion}
}}
$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$branch=& git -C $repo branch --show-current;$branchCode=$LASTEXITCODE;$ErrorActionPreference=$old
if($code -or $branchCode -or $head -ne $base){throw 'Exact checkpoint Git base changed'}
$cpu=[ordered]@{log=(Entry $cpuLog);exit_code=0;provenance='Root actual direct default CPU Debug Build exit0 observed on2026-11-02; this action had no sessionID';exit_inferred_from_log_text=$false;old_session6934_attributed=$false;native_solver_regression_claimed=$false}
$expectedAggregate=[ordered]@{passed=$true;base=$base;source=$source;source_builds=$gpuBuilds;pre_edit_baseline=(Entry $baselinePath);all_other_source_and_old_canonical_GPU_hashes_unchanged=$true;CPU_default_Debug=$cpu;native=$native;saved_frame_instances=29;distinct_clock_times=17;original15_frame_pair_comparisons=58;native_ID_node_pairs=29696;components=$components;Debug_native_State_Theta_memcheck_zero_errors_and_leaks=$true;held='No feedback, complete GPU dynamic model, public GPU entry, physical accuracy/full-cycle or restart acceptance';context=(Entry (Join-Path $tests 'notes\upl_gpu_observer_review_r1.json'));validation_status=(Entry $statusPath);physical_acceptance=$false;public_GPU_dynamic_accepted=$false}
if($reuseAggregate){
  # Reconstruct the exact original aggregate from freshly reverified source/seven gates.
  # Never replace it or infer freshness from its passed flag alone.
  $text=($expectedAggregate|ConvertTo-Json -Depth 20)+[Environment]::NewLine
  $utf8=New-Object Text.UTF8Encoding($false);$sha=[Security.Cryptography.SHA256]::Create()
  try{$expectedSha=[BitConverter]::ToString($sha.ComputeHash($utf8.GetBytes($text))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
  if((Entry $aggregate).sha256 -cne $expectedSha){throw 'Retained aggregate differs from freshly reconstructed source/seven-gate content; no overwrite'}
}else{NewJson $aggregate $expectedAggregate}
$paths=Candidates;$files=@(foreach($p in $paths){$f=Entry $p;if($f.bytes -gt 2097152 -or [IO.Path]::GetExtension($p) -notin '.h','.cpp','.cu','.ps1','.json','.csv','.out','.log','.md','.xml'){throw "Unapproved/large candidate: $p"};$f})
$totalBytes=($files|ForEach-Object {[long]$_.bytes}|Measure-Object -Sum).Sum
NewJson $manifest ([ordered]@{base=$head;branch=$branch;ready_for_root_review=$true;aggregate=(Entry $aggregate);existing_aggregate_revalidated_without_overwrite=$reuseAggregate;scope='Private GPU nonfeedback J/theta/n observer implementation only';files=$files;count=$files.Count;bytes=$totalBytes;source_snapshot_policy='Exactly five old plus five Debug and five Release source texts, not an all-source text dump';local_hash_only_dependencies='Raw BI4, program/runtime/obj/lib/PDB/binlog/VTK, repeated author copies, per-frame helper call JSON and empty stdout logs; their immutable identities remain bound by published build/native receipts. Native duplicate solver stdout is local; native Run.out/Run.csv is published.';raw_program_or_data_cloud_backup_claimed=$false;all_seven_required_gates_passed=$true;independent_review_invented=$false;physical_acceptance=$false;public_GPU_dynamic_accepted=$false})
Write-Output "SEALED verified aggregate and $($files.Count) text paths/$($totalBytes)bytes; root must inspect manifest before explicit Stage"
