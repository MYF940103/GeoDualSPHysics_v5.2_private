param([ValidateSet('List','Seal','Stage')][string]$Mode='List',[switch]$CpuDebugExitObserved0,[switch]$IncludeValidationStatus,[switch]$StageAuthorized,[string]$ReviewedManifestSha256='')
# Inspect/hash and explicitly stage this whitelist only. Never builds, runs a program, commits or pushes.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$tag='upl_gpu_k0_time_';$base='bf5ef956d4ffaf91b0b52e57a740be03fc64cee4'
$manifest=Join-Path $logs ($tag+'publish_r1.json');$aggregate=Join-Path $logs ($tag+'stage_r1.check.json');$baseline=Join-Path $logs ($tag+'r1.baseline.json');$attempt=Join-Path $logs ($tag+'r1.baseline_attempt1.json')
$cpu=Join-Path $logs ($tag+'CPU_Debug_default_r1.build.log');$status=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
$four=@('JSphGpu.h','JSphGpu.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function ReadJson([string]$p){Get-Content -Raw -LiteralPath (ResolveArtifactPath $p)|ConvertFrom-Json}
function Entry([string]$p){$f=Get-Item -LiteralPath $p;if(!$f.FullName.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Escaped stage whitelist'};[ordered]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function VerifyTree($x){if($null -eq $x){return};if($x -is [array]){foreach($v in $x){VerifyTree $v};return};if($x -is [pscustomobject]){if($x.PSObject.Properties['path'] -and $x.PSObject.Properties['bytes'] -and $x.PSObject.Properties['sha256']){$p=ResolveArtifactPath $x.path;$f=Get-Item -LiteralPath $p;if($f.Length -ne $x.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ine $x.sha256){throw "Changed bound artifact: $p"};return};foreach($v in $x.PSObject.Properties){VerifyTree $v.Value}}}
function WriteFresh([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained publication protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 24)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function CheckCall($e,[bool]$mem=$false){VerifyTree $e;$c=ReadJson $e.path;VerifyTree $c;if(!$c.owned_call_exited -or $c.exit_code -ne 0){throw 'Actual owned exit0 required'};if($mem){$s=[IO.File]::ReadAllText((ResolveArtifactPath $c.log.path));if(!$c.memcheck_executed -or !$c.memcheck_zero_errors_and_leaks -or $s -notmatch 'ERROR SUMMARY:\s*0 errors' -or $s -notmatch 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'){throw 'Actual memcheck0 errors/0 bytes leaked required'}}}
function CheckHelper($e,[string]$fixture){VerifyTree $e;$h=ReadJson $e.path;VerifyTree $h;if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne $fixture -or !$h.only_chosen_helper_author_files_frozen -or $h.source_build.sha256 -ine $gpuIds[$h.configuration]){throw 'Wrong new helper/source identity'};CheckCall $h.compile_call;CheckCall $h.link_call;$h}
$checks=@(foreach($w in 'Smoke','Extended'){Join-Path $logs ($tag+$w+'_r1.review.check.json')};foreach($cfg in 'Debug','Release'){foreach($c in 'Scale','FirstCurrent','FirstRequested'){Join-Path $logs ($tag+$cfg+'_'+$c+'_r1.check.json')}})
function Paths {
  $p=@($four|ForEach-Object {Join-Path $repo ('src\source\'+$_)})+@($PSCommandPath)
  foreach($f in 'upl_gpu_k0_time_build_r1.ps1','upl_gpu_k0_time_helper_r1.ps1','upl_gpu_k0_time_native_r1.ps1','upl_gpu_k0_time_runs_r1.ps1','upl_gpu_k0_time_r1.cpp'){$p+=Join-Path $t ('support\'+$f)}
  foreach($f in 'upl_gpu_k0_time_r1.json','upl_gpu_k0_time_native_r1.json','upl_gpu_k0_time_component_r1.json'){$p+=Join-Path $t ('notes\'+$f)}
  $p+=Get-ChildItem -LiteralPath $logs -File|Where-Object {$_.Name -like 'upl_gpu_k0_time_*' -and $_.Extension -in '.json','.log' -and $_.Name -notmatch '_compare_|_poro_' -and $_.FullName -notin @($manifest,$aggregate)}|ForEach-Object {$_.FullName}
  foreach($w in 'Smoke','Extended'){
    foreach($kind in 'newoff','observer'){$d=Join-Path $out ($tag+$w+'_r1_'+$kind);foreach($f in 'Run.out','Run.csv'){$p+=Join-Path $d $f};if($kind -eq 'observer'){foreach($f in 'observer_complete.json','observer_final.csv'){$p+=Join-Path $d $f}}}
    $d=Join-Path $out ($tag+$w+'_r1_review');if(Test-Path -LiteralPath $d){$p+=Get-ChildItem -LiteralPath $d -File|Where-Object {$_.Extension -eq '.json' -or $_.Name -like 'poro_new_*.csv'}|ForEach-Object {$_.FullName}}
  }
  foreach($cfg in 'Debug','Release'){foreach($c in 'Scale','FirstCurrent','FirstRequested'){$d=Join-Path $out ($tag+$cfg+'_'+$c+'_r1');if(Test-Path -LiteralPath $d){$p+=Get-ChildItem -LiteralPath $d -File|Where-Object {$_.Extension -in '.csv','.json','.out'}|ForEach-Object {$_.FullName}}}}
  $p+=Join-Path $out 'upl_gpu_k0_time_seed_r1\CaseUplGpuK0Time.xml'
  if($IncludeValidationStatus){$p+=$status};@($p|Sort-Object -Unique)
}
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Explicit Stage authorization and reviewed manifest SHA required'}
  $m=ReadJson $manifest;VerifyTree $m.files;VerifyTree $m.aggregate;$a=ReadJson $m.aggregate.path;if(!$m.ready_for_root_review -or !$a.passed -or $a.physical_acceptance){throw 'Verified bounded aggregate required'}
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$index=@(& git -C $repo -c core.quotepath=false diff --cached --name-only);$ic=$LASTEXITCODE;$ErrorActionPreference=$old
  if($code -or $ic -or $head -ne $base -or $m.base -ne $base){throw 'Changed Git base/index'};$paths=@($m.files.path)+@($manifest.Substring($repo.Length+1).Replace('\','/'));foreach($f in $index){if($f -and $f -notin $paths){throw 'Unrelated staged changes preserved; stop'}}
  foreach($e in $m.files){VerifyTree ([pscustomobject]$e);$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$msg=& git -C $repo --literal-pathspecs add -f -- $e.path 2>&1;$code=$LASTEXITCODE;$ErrorActionPreference=$old;$msg|Out-Host;if($code){throw 'Preserve partial index; no automatic recovery'}}
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';$msg=& git -C $repo --literal-pathspecs add -f -- $paths[-1] 2>&1;$code=$LASTEXITCODE;$ErrorActionPreference=$old;$msg|Out-Host;if($code){throw 'Manifest staging failed; preserve index'};exit 0
}
$p=Paths;$missing=@(($p+$checks+@($baseline,$attempt,$cpu))|Sort-Object -Unique|Where-Object {!(Test-Path -LiteralPath $_)})
if($Mode -eq 'List'){$files=@($p|Where-Object {Test-Path -LiteralPath $_}|ForEach-Object {Entry $_});[pscustomobject]@{count=$files.Count;bytes=($files|ForEach-Object {[long]$_.bytes}|Measure-Object -Sum).Sum;missing=$missing;files=$files;Git_mutated=$false};return}
if($missing.Count -or !$CpuDebugExitObserved0 -or (Test-Path -LiteralPath $aggregate) -or (Test-Path -LiteralPath $manifest)){throw 'Fresh complete eight-gate evidence and root actual CPU Debug exit0 observation required'}
$b=ReadJson $baseline;if($b.git_base -ne $base){throw 'Wrong immutable base'};VerifyTree $b.inputs;VerifyTree $b.other_source;VerifyTree $b.canonical_GPU;VerifyTree $b.retained_P2_GPU_programs
# Historical P2 raw source bytes and Git LF blobs are separate identities, never compare old source entries against edited current files.
$first=ReadJson $attempt;if($first.owned_exit_code_observed_by_root -ne 1 -or $first.baseline_receipt_written -or $first.build_or_program_executed -or $first.physical_gate_changed){throw 'Retained pre-build newline-wrapper failure differs'}
if($IncludeValidationStatus){$st=ReadJson $status;if($st.limited_canonical_CPU_entry_review.private_raw_comparison -notmatch 'FALSE'){throw 'Historical CPU strict raw26 FALSE disclosure must remain'}}
$gpuIds=@{};$builds=@();foreach($cfg in 'Debug','Release'){
  $q=Join-Path $logs ($tag+$cfg+'_r1.build.json');$g=ReadJson $q;VerifyTree $g;if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $cfg -or !$g.objects_exclude_main -or @($g.objects).Count -ne 110 -or !$g.canonical_GPU_unchanged){throw 'Authoritative isolated GPU build rejected'}
  CheckCall $g.project_call;$s=ReadJson $g.source_freeze.path;VerifyTree $s;if(@($s.source).Count -ne 265 -or @($s.four_targets).Count -ne 4){throw 'Current four-target/full-source identities missing'}
  foreach($name in $four){$matches=@($s.four_targets|Where-Object {[IO.Path]::GetFileName($_.path) -eq $name});if($matches.Count -ne 1){throw 'Target source identity missing'}}
  $e=Entry $q;$gpuIds[$cfg]=$e.sha256;$builds+=$e
}
$native=@();$components=@();$totals=@{}
foreach($q in $checks){
  $r=ReadJson $q;VerifyTree $r;if(!$r.passed -or $r.physical_acceptance){throw 'Required bounded gate failed'};$d=ReadJson $r.completion.path;VerifyTree $d;if(!$d.passed -or $d.physical_acceptance){throw 'Completion rejected'}
  if($r.window){
    $h=CheckHelper $r.build 'Native';$n=if($r.window -eq 'Smoke'){3}else{17}
    if($r.samples -ne $n -or $r.native -ne 512 -or $r.original_arrays -ne 15 -or !$r.all_original15_exact -or !$r.all_actual_saved_time_step_signed_dterror_exact -or !$r.all_saved_observer_CSVs_exact -or !$r.old_new_PARTs_both_read_by_retained_reader -or !$r.final_live_native_csv_exact -or $r.private_feedback_tested -or $r.current_J_acoustic_guard_tested){throw 'Native typed-array/ledger/clock gate differs'}
    if(!$d.observer -or !$d.actual_production_Run -or !$d.live_GPU_download -or !$d.predictor_history_released -or $d.feedback -or $d.public_dynamic_seepage -or $d.native_count -ne 512 -or $d.fixed_count -ne 0 -or $d.completed_steps -ne $n-1){throw 'Native observer scope differs'}
    $reader=ReadJson $r.reader.path;VerifyTree @($reader.program,$reader.compile_call,$reader.link_call);foreach($e in $r.calls){CheckCall $e;$c=ReadJson $e.path;if($c.target_program.sha256 -ine $reader.program.sha256){throw 'Native offline reader identity differs'}}
    foreach($e in $r.solvers){$v=ReadJson $e.path;VerifyTree $v;if(!$v.passed -or $v.native_frames -ne $n -or $v.private_feedback_enabled){throw 'Incomplete native solve'};CheckCall $v.call ($r.window -eq 'Smoke');$call=ReadJson $v.call.path;$expected=if($v.kind -eq 'observer'){$h.program.sha256}else{(ReadJson $v.source_build.path).isolated_GPU_program.sha256};if($call.target_program.sha256 -ine $expected){throw 'Native actual program identity differs'}}
    foreach($e in $r.adopted_controls){VerifyTree (ReadJson $e.path)};$native+=@{review=(Entry $q);samples=$r.samples;native=$r.native;metrics=$d}
  }else{
    $h=CheckHelper $r.build 'Time';CheckCall $r.call ($r.configuration -eq 'Debug');$call=ReadJson $r.call.path
    if($call.target_program.sha256 -ine $h.program.sha256 -or $r.actual_physical_Run_completed -or $r.public_GPU_dynamic_accepted -or $d.mode -ne $r.case -or $d.native_count -ne 512 -or $d.fixed_count -ne 0 -or !$d.actual_DtVariable -or !$d.predictor_histories_absent -or $d.completed_physical_steps -ne 0 -or [double]$d.actual_time_s -ne 0 -or $d.Nstep -ne 0 -or $d.public_GPU_dynamic_mode -or $d.nonzero_k -or !$d.necessary_scale_not_sufficient_stability){throw 'Time component scope or actual program differs'}
    $scale=($r.case -eq 'Scale');if($d.kernel_cases -ne $(if($scale){12}else{0}) -or $d.class_scale_cases -ne $(if($scale){4}else{0}) -or $d.class_domain_rejections -ne $(if($scale){8}else{0}) -or $d.requested_step_cases -ne $(if($scale){12}else{0}) -or $d.initialization_hook_rejections -ne $(if($scale){18}else{0}) -or $d.actual_first_step_rejections -ne $(if($scale){0}else{1}) -or [bool]$d.actual_maxcu2_kernel -ne $scale -or [bool]$d.first_force_precedes_rejection -eq $scale){throw 'Predeclared actual time-component counters differ'}
    if(!$totals.ContainsKey($r.configuration)){$totals[$r.configuration]=@{kernel=0;class_scale=0;domain=0;requests=0;init_hooks=0;fresh_first_step_rejections=0}}
    $c=$totals[$r.configuration];$c.kernel+=$d.kernel_cases;$c.class_scale+=$d.class_scale_cases;$c.domain+=$d.class_domain_rejections;$c.requests+=$d.requested_step_cases;$c.init_hooks+=$d.initialization_hook_rejections;$c.fresh_first_step_rejections+=$d.actual_first_step_rejections
    $components+=@{check=(Entry $q);configuration=$r.configuration;case=$r.case;metrics=$d}
  }
}
foreach($cfg in 'Debug','Release'){$c=$totals[$cfg];if($c.kernel -ne 12 -or $c.class_scale -ne 4 -or $c.domain -ne 8 -or $c.requests -ne 12 -or $c.init_hooks -ne 18 -or $c.fresh_first_step_rejections -ne 2){throw 'Incomplete per-configuration actual tests'}}
$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$old;if($code -or $head -ne $base){throw 'Changed verified Git base'}
$files=@(Paths|ForEach-Object {$e=Entry $_;if($e.bytes -gt 2097152 -or [IO.Path]::GetExtension($_) -notin '.h','.cpp','.cu','.ps1','.json','.csv','.out','.log','.xml'){throw "Unapproved/large text: $_"};$e})
WriteFresh $aggregate ([ordered]@{passed=$true;base=$base;builds=$builds;native=$native;components=$components;counts_from_actual_completions=$true;counts_per_configuration=$totals;native_frame_instances=20;distinct_native_times=17;native_original15_frame_pairs=40;native_ID_pairs=20480;CPU_Debug=@{log=(Entry $cpu);exit0_root_direct_observed=$true;sessionID=$null;inferred_from_log=$false};baseline=(Entry $baseline);retained_newline_wrapper_failure=(Entry $attempt);full_feedback_trajectory_tested=$false;necessary_scale_not_sufficient_stability=$true;nonzero_k_tested=$false;public_GPU_dynamic_accepted=$false;physical_acceptance=$false})
$files+=Entry $aggregate;WriteFresh $manifest ([ordered]@{base=$base;ready_for_root_review=$true;aggregate=(Entry $aggregate);files=$files;count=$files.Count;bytes=($files|ForEach-Object {[long]$_.bytes}|Measure-Object -Sum).Sum;status_included=[bool]$IncludeValidationStatus;local_only='Raw BI4/exe/obj/lib/runtime/PDB/binlog; per-frame empty call logs/JSON and duplicate reread-old CSV. Their identities are retained locally in verified receipts; no raw cloud-backup claim.';no_duplicate_old_source_or_program_texts=$true;physical_acceptance=$false})
