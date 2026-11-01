param([ValidateSet('List','Seal')][string]$Mode='List')
# Author-only preparation: later root may inspect/seal exact evidence. No Git/build/solver calls.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$fig=Join-Path $t 'figures';$tag='upl_gpu_k0_actual_'
$aggregate=Join-Path $logs ($tag+'stage_r2.check.json');$manifest=Join-Path $logs ($tag+'publish_r2.json');$base='7a758f3d3c04e379fc272f0f38fbc47e7eb13397'
$verified=@{};$jobs=@('Smoke','CPU_c','CPU_h','GPU_c','GPU_h');$pairs=@('CPU_half','GPU_half','cross_c','cross_h')
function ResolveArtifact([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function ReadJson([string]$p){Get-Content -Raw -Encoding UTF8 -LiteralPath (ResolveArtifact $p)|ConvertFrom-Json}
function BoundEntry([string]$p){$f=Get-Item -LiteralPath (ResolveArtifact $p);[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Entry([string]$p){
  $e=BoundEntry $p;if(!$e.path.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Whitelist target escaped repository'}
  $e.path=$e.path.Substring($repo.Length+1).Replace('\','/');$e
}
function VerifyTree($x){
  if($null -eq $x){return};if($x -is [array]){foreach($v in $x){VerifyTree $v};return}
  if($x -is [pscustomobject]){
    if($x.PSObject.Properties['path'] -and $x.PSObject.Properties['bytes'] -and $x.PSObject.Properties['sha256']){
      $p=ResolveArtifact $x.path;$key=$p.ToLowerInvariant();$expected=([string]$x.sha256).ToLowerInvariant()
      if($verified.ContainsKey($key)){if($verified[$key].sha256 -ne $expected -or $verified[$key].bytes -ne $x.bytes){throw "Conflicting retained identity: $p"};return}
      $e=BoundEntry $p;if($e.bytes -ne $x.bytes -or $e.sha256 -ne $expected){throw "Changed bound artifact: $p"};$verified[$key]=$e;return
    }
    foreach($property in $x.PSObject.Properties){VerifyTree $property.Value}
  }
}
function ReadBound($entry){VerifyTree $entry;$r=ReadJson $entry.path;VerifyTree $r;$r}
function SaveFresh([string]$p,$value){if(Test-Path -LiteralPath $p){throw 'Retained aggregate/manifest protected'};[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 28)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($entry,[int]$exit=0,[bool]$mem=$false,[string]$targetSha=''){
  $c=ReadBound $entry;if(!$c.owned_call_exited -or $c.exit_code -ne $exit){throw 'Wrong exact owned call exit'}
  if($targetSha -and $c.target_program.sha256 -ine $targetSha){throw 'Wrong actual target program'}
  if($mem){$raw=[IO.File]::ReadAllText((ResolveArtifact $c.log.path));if(!$c.memcheck_executed -or !$c.memcheck_zero_errors_and_leaks -or $raw -notmatch 'ERROR SUMMARY:\s*0 errors' -or $raw -notmatch 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'){throw 'Actual Debug memcheck zero-errors/zero-leaks required'}}
  $c
}
function Num($x){$v=[double]::Parse([string]$x,[Globalization.CultureInfo]::InvariantCulture);if([double]::IsNaN($v) -or [double]::IsInfinity($v)){throw 'Nonfinite numeric evidence'};$v}
function CheckPath([string]$job){$version=if($job -eq 'Smoke'){'r2'}else{'r3'};Join-Path $logs ($tag+$job+'_'+$version+'.check.json')}
function Paths {
  $p=@($PSCommandPath, (Join-Path $t 'support\upl_gpu_k0_actual_publish_r1.ps1'))
  foreach($name in 'upl_gpu_k0_actual_build_r1.ps1','upl_gpu_k0_actual_build_r2.ps1','upl_gpu_k0_actual_runs_r2.ps1','upl_gpu_k0_actual_runs_r3.ps1','upl_gpu_k0_actual_r1.cpp','upl_gpu_k0_actual_r2.cpp','upl_gpu_k0_actual_review_r2.py'){$p+=Join-Path $t ('support\'+$name)}
  foreach($name in 'upl_gpu_k0_actual_r1.json','upl_gpu_k0_actual_r2.json','upl_gpu_k0_actual_runs_r3.json','upl_gpu_k0_actual_publish_r1.json','upl_gpu_k0_actual_publish_r2.json'){$p+=Join-Path $t ('notes\'+$name)}
  $p+=Join-Path $t 'notes\upl_gpu_k0_actual_root_review_r3.json'
  $p+=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
  $p+=Join-Path $logs ($tag+'r2.inputs.json');$p+=Join-Path $logs ($tag+'CPU_c_r2.call.json');$p+=Join-Path $logs ($tag+'CPU_c_r2.log')
  foreach($cfg in 'Debug','Release'){
    foreach($suffix in '_r1_compile.call.json','_r1_compile.log','_r2.helper.json','_r2_compile.call.json','_r2_compile.log','_r2_link.call.json','_r2_link.log'){$p+=Join-Path $logs ($tag+$cfg+$suffix)}
  }
  foreach($job in $jobs){
    $version=if($job -eq 'Smoke'){'r2'}else{'r3'};$name=$tag+$job+'_'+$version;$d=Join-Path $out $name;$r=Join-Path $out ($name+'_review')
    foreach($suffix in '.call.json','.log','.run.json','.check.json','_review.call.json','_review.log'){$p+=Join-Path $logs ($name+$suffix)}
    foreach($name2 in 'Run.out','Run.csv'){$p+=Join-Path $d $name2}
    if($job -notlike 'CPU_*'){foreach($name2 in 'actual_complete.json','live_final.csv'){$p+=Join-Path $d $name2}}
    foreach($name2 in 'completion.json','history.csv','native_ids.csv'){$p+=Join-Path $r $name2}
    $p+=Join-Path $out ('upl_gpu_k0_actual_seed_r2\CaseUplGpuK0_'+$job+'.xml')
  }
  foreach($pair in $pairs){foreach($ext in '.json','.csv','.png'){$p+=Join-Path $fig ($tag+$pair+'_r3'+$ext)}}
  @($p|Sort-Object -Unique)
}
$required=@(Paths)+@(Join-Path $logs 'upl_gpu_k0_time_stage_r1.check.json')
$missing=@($required|Where-Object {!(Test-Path -LiteralPath $_)})
if($Mode -eq 'List'){
  $files=@(Paths|Where-Object {Test-Path -LiteralPath $_}|ForEach-Object {Entry $_})
  [pscustomobject]@{mode='List';ready=$missing.Count -eq 0;required_missing=$missing;files=$files;Git_mutated=$false;programs_executed=$false};return
}
if($missing.Count -or (Test-Path -LiteralPath $aggregate) -or (Test-Path -LiteralPath $manifest)){throw 'Fresh complete five-single/four-pair evidence required'}
$time=ReadJson (Join-Path $logs 'upl_gpu_k0_time_stage_r1.check.json');VerifyTree $time
if(!$time.passed -or @($time.native).Count -ne 2 -or @($time.components).Count -ne 6 -or $time.physical_acceptance -or $time.nonzero_k_tested -or $time.public_GPU_dynamic_accepted){throw 'Reviewed prior necessary-time stage required'}
$helpers=@{};$builds=@()
foreach($cfg in 'Debug','Release'){
  $path=Join-Path $logs ($tag+$cfg+'_r2.helper.json');$h=ReadJson $path;VerifyTree $h
  if($h.fixture -ne 'Actual' -or $h.configuration -ne $cfg -or $h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or !$h.only_chosen_helper_author_files_frozen -or !$h.canonical_GPU_unchanged -or $h.GPU_object_substitutions -ne 110 -or $h.GPU_object_directory_changed -or $h.physical_acceptance){throw 'Fresh isolated actual helper identity/scope rejected'}
  $compile=Call $h.compile_call;$link=Call $h.link_call;$g=ReadBound $h.source_build
  if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $cfg -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main -or !$g.canonical_GPU_unchanged){throw 'Authoritative GPU objects/build incomplete'}
  # Remapping the replay recipe is expected: verify the actual complete link closure.
  $sourceObjects=@{};foreach($object in $g.objects){$key=[IO.Path]::GetFullPath((ResolveArtifact $object.path)).ToLowerInvariant();if($sourceObjects.ContainsKey($key)){throw 'Duplicate authoritative object identity'};$sourceObjects[$key]=$true}
  $linkObjects=@($link.arguments|Where-Object {[IO.Path]::GetExtension([string]$_) -ieq '.obj'});$linked=@{};$extra=@()
  if($sourceObjects.Count -ne 110 -or $linkObjects.Count -ne 111){throw 'Expected 110 authoritative objects plus one isolated helper object'}
  foreach($object in $linkObjects){$key=[IO.Path]::GetFullPath([string]$object).ToLowerInvariant();if($linked.ContainsKey($key)){throw 'Duplicate actual link object'};$linked[$key]=$true;if(!$sourceObjects.ContainsKey($key)){$extra+=$key}}
  foreach($key in $sourceObjects.Keys){if(!$linked.ContainsKey($key)){throw 'Actual link omitted or substituted an authoritative object'}}
  $helperObject=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $h.program.path) 'helper.obj')).ToLowerInvariant()
  if($extra.Count -ne 1 -or $extra[0] -ne $helperObject -or @($compile.arguments|Where-Object {[string]$_ -ieq ('/Fo'+$helperObject)}).Count -ne 1){throw 'Unexpected non-authoritative link object or helper compile output'}
  $null=Call $g.project_call;$source=ReadBound $g.source_freeze
  if(@($source.four_targets).Count -ne 4 -or @($source.source).Count -ne 265){throw 'Frozen time-source identity incomplete'}
  $helpers[$cfg]=$h;$builds+=Entry $path
}
$preparedPath=Join-Path $logs ($tag+'r2.inputs.json');$prepared=ReadJson $preparedPath;VerifyTree $prepared
if(!$prepared.prepared_only -or !$prepared.native_initial_BI4_all_exact -or $prepared.public_GPU_master_enabled -or $prepared.physical_acceptance -or @($prepared.jobs).Count -ne 5){throw 'Prepared exact-geometry private-GPU inputs rejected'}
# Keep both compile failures and the pre-solver OpenMP spelling error as failures, not admitted runs.
$failures=@(@{kind='offline_r1_publisher_object_remap_count_assumption';root_reported_owned_exit_code=1;report_provenance='Root direct tool observation, not a fabricated new machine receipt';aggregate_written=$false;solver_or_source_restarted=$false;admitted=$false})
foreach($cfg in 'Debug','Release'){
  $entry=Entry (Join-Path $logs ($tag+$cfg+'_r1_compile.call.json'));$call=Call ([pscustomobject]$entry) 2
  $raw=[IO.File]::ReadAllText((ResolveArtifact $call.log.path));if($raw -notmatch 'error C2668' -or $raw -notmatch 'Finite'){throw 'Original ADL compile failure diagnosis changed'}
  $failures+=@{kind='helper_compile_ADL_C2668';configuration=$cfg;call=$entry;exit_code=2;physics_started=$false;admitted=$false}
}
$badEntry=Entry (Join-Path $logs ($tag+'CPU_c_r2.call.json'));$bad=Call ([pscustomobject]$badEntry) 1
$badText=[IO.File]::ReadAllText((ResolveArtifact $bad.log.path));if('-omp:4' -notin $bad.arguments -or $badText -notmatch 'Parameter "-omp:4" unrecognised or invalid' -or $badText -match 'Initialising simulation'){throw 'Retained pre-native OpenMP option failure differs'}
$failures+=@{kind='pre_native_CPU_option_spelling';call=$badEntry;exit_code=1;physics_started=$false;admitted=$false}
$single=@();$singleByJob=@{};$nativeFrameInstances=0
foreach($job in $jobs){
  $path=CheckPath $job;$check=ReadJson $path;VerifyTree $check
  if(!$check.passed -or $check.job -ne $job -or $check.physical_acceptance -or $check.full_cycle_accepted -or $check.public_GPU_accepted){throw 'Native single-run check rejected'}
  $r=ReadBound $check.source_run;$j=$r.selected_input;$smoke=($job -eq 'Smoke');$n=if($smoke){3}else{257};$cfg=if($smoke){'Debug'}else{'Release'}
  if(!$r.owned_solver_exit0 -or !$r.solver_completed_before_analysis -or $r.job -ne $job -or $r.native_frames -ne $n -or $r.physical_acceptance -or $j.samples -ne $n -or [bool]$j.smoke -ne $smoke){throw 'Exact completed native solve required'}
  $dt=if($job -like '*_h'){[math]::Pow(2.,-25)}else{[math]::Pow(2.,-24)};$end=if($smoke){[math]::Pow(2.,-23)}else{[math]::Pow(2.,-15)};$steps=if($smoke){2}elseif($job -like '*_h'){1024}else{512}
  if([double]$j.dt -ne $dt -or [double]$j.end -ne $end -or $j.steps -ne $steps){throw 'Declared native time/step window changed'}
  $helper=$helpers[$cfg];$expected=if($j.backend -eq 'CPU'){$prepared.CPU_program.sha256}else{$helper.program.sha256};$call=Call $r.call 0 $smoke $expected
  if($j.backend -eq 'CPU' -and ('-ompthreads:4' -notin $call.arguments -or '-omp:4' -in $call.arguments)){throw 'CPU native run did not use corrected actual thread option'}
  $null=Call $check.call 0 $false $helper.program.sha256;$d=ReadBound $check.completion
  if(!$d.passed -or $d.backend -ne $j.backend -or [bool]$d.smoke -ne $smoke -or $d.native_count -ne 512 -or $d.fixed_count -ne 0 -or $d.samples -ne $n -or $d.common_columns -ne 33 -or [double]$d.dt_s -ne $dt -or [double]$d.actual_end_s -ne $end -or !$d.saved_clock_step_exact -or !$d.native_ID_aligned -or !$d.no_exclusions -or $d.native_ledger_checks -ne 512*$n -or $d.physical_acceptance){throw 'Full native reader completion incomplete'}
  $cpu=($j.backend -eq 'CPU');if($d.native_J_arrays -ne $(if($cpu){6}else{3}) -or [bool]$d.native_PosDiv_observed -ne $cpu -or [bool]$d.public_dynamic_metadata -ne $cpu -or [bool]$d.GPU_V_rho_k_derived_not_native_arrays -eq $cpu){throw 'CPU/GPU native schema attribution differs'}
  if([double]$d.max_energy_ratio -gt 1.1 -or [double]$d.max_saved_coupled_CFL -gt .01 -or [double]$d.max_ledger_relative_error -gt 5e-13 -or [double]$d.max_signed_dterror_s -gt 1e-14 -or [double]$d.max_abs_J_minus_1 -le $(if($smoke){0.}else{1e-8})){throw 'Original single-run energy/ledger/time/nonempty gate failed'}
  if(!$cpu){
    $matches=@($r.files|Where-Object {[IO.Path]::GetFileName($_.path) -eq 'actual_complete.json'});if($matches.Count -ne 1){throw 'Actual GPU completion binding missing'};$actual=ReadBound $matches[0]
    if(!$actual.passed -or [bool]$actual.smoke -ne $smoke -or !$actual.actual_production_Run -or !$actual.private_feedback -or $actual.public_GPU_dynamic_mode -or $actual.physical_fields_rewritten_by_fixture -or $actual.native_count -ne 512 -or $actual.completed_steps -ne $steps -or [double]$actual.actual_end_s -ne $end -or [double]$actual.dt_s -ne $dt -or !$actual.predictor_histories_released -or !$actual.live_GPU_download -or $actual.physical_acceptance){throw 'Actual successful GPU Run/lifecycle scope differs'}
  }
  $row=@{job=$job;backend=$j.backend;check=(Entry $path);run=$check.source_run;reader_completion=$check.completion;samples=$n;completed_steps=$steps;metrics=$d}
  $single+=$row;$singleByJob[$job]=$row;$nativeFrameInstances+=$n
}
$pairResults=@();$plans=@{CPU_half=@('CPU_c','CPU_h');GPU_half=@('GPU_c','GPU_h');cross_c=@('CPU_c','GPU_c');cross_h=@('CPU_h','GPU_h')}
foreach($pair in $pairs){
  $path=Join-Path $fig ($tag+$pair+'_r3.json');$p=ReadJson $path;VerifyTree $p;$half=$pair -like '*_half'
  if(!$p.passed -or $p.pair -ne $pair -or $p.native_count -ne 512 -or $p.samples -ne 257 -or $p.common_columns -ne 33 -or !$p.all_actual_times_and_native_IDs_matched -or !$p.absolute_gates_passed -or [double]$p.pressure_RMS_limit_Pa -ne 5. -or [double]$p.max_material_displacement_limit_mm -ne .005 -or [bool]$p.normalized_half_gates_applied -ne $half -or [bool]$p.normalized_cross_metrics_descriptive_only -eq $half -or $p.passive_density_exactness_required -or $p.raw_BI4_reparsed -or $p.physical_acceptance){throw 'Pair kind/original gates/attribution differs'}
  if([double]$p.maxima.pressure_RMS_Pa -gt 5. -or [double]$p.maxima.max_material_u_difference_mm -gt .005){throw 'Original absolute pair gate failed'}
  if($half -and ([double]$p.normalized_half_limit -ne 1e-4 -or [double]$p.maxima.pressure_RMS_over_Pstar -gt 1e-4 -or [double]$p.maxima.velocity_RMS_over_A -gt 1e-4 -or [double]$p.maxima.material_u_RMS_over_Ustar -gt 1e-4)){throw 'Original independent normalized half gate failed'}
  foreach($side in 'a','b'){$idx=if($side -eq 'a'){0}else{1};$expectedJob=$plans[$pair][$idx];$expectedDir=Split-Path -Parent (ResolveArtifact $singleByJob[$expectedJob].reader_completion.path);if([IO.Path]::GetFullPath($p.$side.folder) -ine [IO.Path]::GetFullPath($expectedDir) -or $p.$side.backend -ne $singleByJob[$expectedJob].backend -or [double]$p.$side.dt -ne [double]$singleByJob[$expectedJob].metrics.dt_s){throw 'Pair used wrong native controls'}}
  $csv=Join-Path $fig ($tag+$pair+'_r3.csv');$rows=@(Import-Csv -LiteralPath $csv);if($rows.Count -ne 257){throw 'Pair CSV must retain every sample'}
  for($part=0;$part -lt 257;$part++){
    foreach($v in $rows[$part].PSObject.Properties){$null=Num $v.Value};if((Num $rows[$part].part) -ne $part -or (Num $rows[$part].time_s) -ne $part*[math]::Pow(2.,-23)){throw 'Actual pair CSV time/part mismatch'}
    if((Num $rows[$part].pressure_RMS_Pa) -gt 5. -or (Num $rows[$part].max_material_u_difference_mm) -gt .005){throw 'Pair CSV absolute gate failed'}
    if($half -and ((Num $rows[$part].pressure_RMS_over_Pstar) -gt 1e-4 -or (Num $rows[$part].velocity_RMS_over_A) -gt 1e-4 -or (Num $rows[$part].material_u_RMS_over_Ustar) -gt 1e-4)){throw 'Pair CSV independent half gate failed'}
  }
  $pairResults+=@{pair=$pair;record=(Entry $path);independent_half=$half;normalized_cross_descriptive_only=(!$half);maxima=$p.maxima;continuum_reference=$p.continuum_reference}
}
$files=@(Paths|ForEach-Object {
  $e=Entry $_;$ext=[IO.Path]::GetExtension($_).ToLowerInvariant()
  if($e.bytes -gt 2097152 -or $ext -notin '.cpp','.py','.ps1','.json','.csv','.png','.out','.log','.xml' -or [IO.Path]::GetFileName($_) -eq 'cpu_posdiv.csv'){throw "Unapproved/large stage file: $_"};$e
})
# Rehash every distinct current/local binding once more before creating either new sealed artifact.
foreach($value in $verified.Values){$e=BoundEntry $value.path;if($e.bytes -ne $value.bytes -or $e.sha256 -ne $value.sha256){throw 'Input changed during publication audit'}}
SaveFresh $aggregate ([ordered]@{passed=$true;code_checkpoint_verified_local_remote_by_root=$base;production_source_modified_in_this_stage=$false;prior_time_stage=(Entry (Join-Path $logs 'upl_gpu_k0_time_stage_r1.check.json'));helpers=$builds;authoritative_GPU_link_objects_per_configuration=110;actual_link_closure_verified=$true;prepared_inputs=(Entry $preparedPath);single_runs=$single;independent_halves=@($pairResults|Where-Object {$_.independent_half});same_dt_backend_cross=@($pairResults|Where-Object {!$_.independent_half});native_frame_instances=$nativeFrameInstances;distinct_actual_saved_times=258;native_node_frame_instances=512*$nativeFrameInstances;pair_sample_instances=1028;native_node_pair_instances=526336;hash_bindings_verified=$verified.Count;retained_failures=$failures;successful_Debug_Pre_Corr_smoke=$true;full_window_seconds=[math]::Pow(2.,-15);weak_continuum_diagnostic_only=$true;passive_rho_backend_exactness_required=$false;nonzero_k_tested=$false;public_GPU_dynamic_accepted=$false;general_boundary_accepted=$false;full_cycle_accepted=$false;physical_acceptance=$false;solver_or_build_or_Git_invoked_by_publisher=$false})
$files+=Entry $aggregate;$self=$manifest.Substring($repo.Length+1).Replace('\','/');$gitPaths=@($files.path)+@($self)
SaveFresh $manifest ([ordered]@{ready_for_root_review=$true;base_checkpoint=$base;aggregate=(Entry $aggregate);files=$files;git_paths=$gitPaths;count_including_manifest=$gitPaths.Count;manifest_self_path=$self;manifest_self_not_self_hashed=$true;bytes_excluding_manifest=($files|ForEach-Object {[long]$_.bytes}|Measure-Object -Sum).Sum;Git_mutated=$false;programs_executed=$false;local_hash_bound_only='Raw BI4, executable/runtime/object/PDB/library files, physical.bin and large CPU PosDiv sidecars. Their retained identities were verified through current receipts; no cloud raw-data backup claim.';previous_stage_source_or_evidence_not_readded=$true;physical_acceptance=$false})
