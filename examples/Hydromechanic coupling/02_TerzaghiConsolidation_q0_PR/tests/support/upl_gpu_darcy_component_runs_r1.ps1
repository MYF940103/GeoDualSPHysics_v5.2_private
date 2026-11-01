param([ValidateSet('RunComponent')][string]$Mode='RunComponent',[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ExecutionAuthorized)
# One component invocation only; no Build, physical solver, notifier, old worker, or Git call.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$recipeNote=Join-Path $t 'notes\upl_gpu_darcy_component_runs_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((ResolveArtifactPath $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function N($v){$n=[double]::Parse([string]$v,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture);if([double]::IsNaN($n) -or [double]::IsInfinity($n)){throw 'Unexpected nonfinite diagnostic metric'};$n}
function Rows([string]$name,[int]$count){$r=@(Import-Csv -LiteralPath (Join-Path $runOut $name));if($r.Count -ne $count){throw "Wrong CSV count: $name"};$r}
function Files(){if(Test-Path -LiteralPath $runOut){@(Get-ChildItem -LiteralPath $runOut -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})}else{@()}}
if(!$ExecutionAuthorized){throw 'Root full component/driver review and explicit single-run authorization required'}
$helperPath=Join-Path $logs ('upl_gpu_darcy_component_'+$Configuration+'_r1.helper.json');$h=J $helperPath
if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'Darcy' -or $h.configuration -ne $Configuration -or !$h.exact_link_closure_verified -or $h.link_object_count -ne 111 -or $h.GPU_object_substitutions -ne 110 -or !$h.GPU_object_directory_changed){throw 'Fresh exact-closure Darcy helper required'}
V $h.inputs;V $h.author_files;V $h.transitive_project_include_files;V $h.tools;V $h.libraries;V $h.objects;V @($h.program,$h.helper_object,$h.source_build,$h.compile_call,$h.link_call,$h.prerequisite_stage)
foreach($r in $h.runtime){V @($r.original,$r.copy)}
foreach($p in @($h.compile_call.path,$h.link_call.path)){$c=J $p;if(!$c.owned_call_exited -or $c.exit_code -ne 0){throw 'Owned component compile/link did not pass'};V @($c.program,$c.log)}
$gpuPath=Join-Path $logs ('upl_gpu_darcy_'+$Configuration+'_r2.build.json');if($h.source_build.sha256 -ine (E $gpuPath).sha256){throw 'Wrong authoritative source build'};$g=J $gpuPath
if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $Configuration -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main){throw 'Successful frozen Darcy r2 full build required'}
V $g.inputs;V $g.tools;V $g.objects;V @($g.source_freeze,$g.project_call,$g.isolated_GPU_program,$g.baseline);foreach($r in $g.runtime){V @($r.original,$r.copy)}
$source=J $g.source_freeze.path;V $source.source;V $source.five_targets;if(@($source.source).Count -ne 265 -or @($source.five_targets).Count -ne 5){throw 'Current source closure differs'}
$baseline=J $g.baseline.path;V $baseline.inputs;V $baseline.other_source;V $baseline.canonical_GPU;if(@($baseline.other_source).Count -ne 260){throw 'Unchanged source closure differs'}
$stage=J $h.prerequisite_stage.path;if(!$stage.passed -or $stage.physical_acceptance -or $stage.public_GPU_dynamic_accepted){throw 'Accepted bounded prior stage required'}
$preparedPath=Join-Path $logs 'upl_gpu_k0_time_r1.inputs.json';$seed=J $preparedPath;V $seed.inputs;V @($seed.xml,$seed.bi4)
if($seed.status -ne 'k0_component_input_prepared_not_run' -or $seed.native -ne 512 -or $seed.native_initial_fields_rewritten -or $seed.xml.path -ine ($seed.prefix+'.xml') -or $seed.bi4.path -ine ($seed.prefix+'.bi4')){throw 'Exact retained periodic512 runtime XML/BI4 required'}
$prior=@();if($Configuration -eq 'Release'){
  $debugPath=Join-Path $logs 'upl_gpu_darcy_component_Debug_run_r1.check.json';$d=J $debugPath
  if(!$d.passed -or !$d.memcheck_zero_errors_and_leaks -or $d.completed_physical_steps -ne 0 -or $d.physical_acceptance -or $d.public_GPU_dynamic_accepted){throw 'Passed Debug component and zero-error/leak memcheck required first'}
  V $d.inputs;V $d.files;V @($d.call,$d.completion,$d.helper,$d.source_build);$dc=J $d.call.path;if(!$dc.owned_call_exited -or $dc.exit_code -ne 0){throw 'Debug owned invocation did not pass'};$prior=@(E $debugPath)
}
$name='upl_gpu_darcy_component_'+$Configuration+'_run_r1';$runOut=Join-Path $outputs $name;$callPath=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log');$checkPath=Join-Path $logs ($name+'.check.json')
foreach($p in @($runOut,$callPath,$log,$checkPath)){if(Test-Path -LiteralPath $p){throw 'Retained component action protected; no rerun/overwrite'}}
$target=$h.program;$tool=$target;$targetArgs=@('--darcy','-gpu:0','-stable',$seed.prefix,$runOut,'-dirdataout','data','-svres');$argv=$targetArgs;$mem=($Configuration -eq 'Debug');$toolReceipt=$null
if($mem){
  $toolReceipt=E (Join-Path $logs 'upl_gpu_feedback_Feedback_Debug_r2_component.call.json');$oldCall=J $toolReceipt.path
  if(!$oldCall.owned_call_exited -or $oldCall.exit_code -ne 0 -or !$oldCall.memcheck_zero_errors_and_leaks){throw 'Successful retained compute-sanitizer tool receipt required'}
  $tool=$oldCall.program;V @($tool);if([IO.Path]::GetFileName($tool.path) -ine 'compute-sanitizer.exe'){throw 'Unexpected memcheck tool'}
  $argv=@('--tool','memcheck','--leak-check','full','--error-exitcode','97',$target.path)+$targetArgs
}
$inputs=@(E $PSCommandPath;E $recipeNote;E $helperPath;E $gpuPath;E $preparedPath;$seed.xml;$seed.bi4)+$prior;if($toolReceipt){$inputs+=@($toolReceipt)}
[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$exited=$false;$launchError=$null;$oldPreference=$ErrorActionPreference;$ErrorActionPreference='Continue'
try{Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$exited=$true}finally{Pop-Location}}catch{$launchError=$_.Exception.Message}finally{$ErrorActionPreference=$oldPreference}
$text=[IO.File]::ReadAllText($log);$zero=($mem -and $text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations')
Save $callPath ([ordered]@{owned_call_exited=$exited;exit_code=$code;launch_error=$launchError;program=$tool;target_program=$target;arguments=$argv;target_arguments=$targetArgs;helper=(E $helperPath);source_build=(E $gpuPath);prepared_input=(E $preparedPath);recipe=$inputs;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);memcheck_tool_source_call=$toolReceipt;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;physical_solver_invoked=$false;physical_acceptance=$false})
$completion=Join-Path $runOut 'completion.json'
try{
  if(!$exited -or $code -ne 0 -or ($mem -and !$zero)){throw 'Owned component or memcheck rejected; preserve partial output'}
  V $inputs;V $h.inputs;V $h.author_files;V $h.transitive_project_include_files;V $g.inputs;V $g.objects;V @($h.program,$h.source_build,$seed.xml,$seed.bi4);V $baseline.canonical_GPU;foreach($r in $h.runtime){V @($r.original,$r.copy)}
  $done=J $completion
  $counts=[ordered]@{prefix_stage_cases=6;owner_negative_cases=4;finite_patch_cases=12;finite_patch_rate_rows=108;actual_host_periodic_cases=2;actual_host_periodic_rate_rows=1920;class_scale_cases=4;positive_k_domain_rejections=1;actual_DtVariable_cases=12}
  foreach($key in $counts.Keys){if($done.$key -ne $counts[$key]){throw "Component count differs: $key"}}
  if(!$done.passed -or $done.stage -ne 'upl_gpu_darcy_component_r1' -or !$done.actual_private_rate_kernel -or !$done.actual_host_owner_and_rate_helpers -or !$done.independent_all_particle_reference -or !$done.kernel_float_factor_budget_predeclared -or !$done.full_rate_overwrite -or !$done.actual_LoadConfig_ConfigDomain_InitRunGpu -or $done.actual_ComputeStep_Sym_called -or $done.completed_physical_steps -ne 0 -or $done.public_GPU_dynamic_mode -or $done.variable_k_tested -or $done.physical_acceptance -or $done.corner_clone_witnesses -le 0){throw 'Invalid bounded component completion scope'}
  $reportedRatio=N $done.max_error_over_budget;$reportedError=N $done.max_rate_reference_error_pa_s;if($reportedRatio -lt 0 -or $reportedRatio -gt 1 -or $reportedError -lt 0){throw 'Original complete-rate budget rejected'}
  $prefix=Rows 'prefix.csv' 6;foreach($r in $prefix){if($r.all_active_and_tail_bits_exact -ne 'true' -or $r.prefix -ne '2' -or $r.native_owners -ne '4' -or $r.periodic_images -ne '4'){throw 'Prefix/owner exact-copy gate failed'}}
  $owner=Rows 'owner_negatives.csv' 3;foreach($r in $owner){if($r.actual_invalid -ne '2' -or $r.expected_invalid -ne '2' -or $r.negative_nonempty -ne 'true'){throw 'Owner negative did not reject intended slot'}}
  $hostNegative=Rows 'host_owner_negative.csv' 1;if($hostNegative[0].rejected -ne 'true' -or $hostNegative[0].map_flag_pool_released -ne 'true'){throw 'Actual host owner error/pool-release gate failed'}
  $patch=Rows 'patch_rates.csv' 108;$periodic=Rows 'periodic_rates.csv' 1920;$maxRatio=0.;$maxError=0.
  foreach($r in @($patch)+@($periodic)){
    $a=N $r.actual;$b=N $r.reference;$budget=N $r.budget;$error=N $r.error;$ratio=N $r.error_over_budget;[void](N $r.pressure_source);[void](N $r.acceleration_source)
    $e=[Math]::Abs($a-$b);if($budget -le 0 -or $a -eq 1234567 -or $e -gt $budget -or $ratio -lt 0 -or $ratio -gt 1 -or $error -ne $e -or [Math]::Abs($ratio-$e/$budget) -gt 64*2.2204460492503131e-16*[Math]::Max(1.,$ratio)){throw 'Per-row original propagated rate budget failed'}
    $maxRatio=[Math]::Max($maxRatio,$ratio);$maxError=[Math]::Max($maxError,$e)
  }
  if($maxRatio -ne $reportedRatio -or $maxError -ne $reportedError){throw 'Completion summary differs from all CSV rate rows'}
  $patchSummary=Rows 'patch_summary.csv' 12;foreach($r in $patchSummary){if($r.rows -ne '9'){throw 'Patch field sample count differs'};[void](N $r.max_pressure_source);[void](N $r.max_acceleration_source)}
  $periodicSummary=Rows 'periodic_summary.csv' 2;foreach($r in $periodicSummary){if($r.slots -ne '960' -or [int]$r.ghosts -le 0 -or [int]$r.corners -le 0 -or (N $r.min_owner_C_norm) -le 0 -or $r.pre_rate_sentinel_preserved -ne 'true'){throw 'Periodic owner/source evidence is empty'}}
  $scales=Rows 'scales.csv' 5;if(@($scales|Where-Object {$_.rejected -eq 'true'}).Count -ne 1){throw 'Expected one strict positive-k domain rejection'}
  foreach($r in $scales){foreach($key in @('J','k','wave','pore','wave_independent','pore_independent')){[void](N $r.$key)}}
  $requests=Rows 'requests.csv' 12;$nanCount=0
  foreach($r in $requests){
    if($r.rejected -ne $r.expected_reject -or $r.physical_unchanged -ne 'true'){throw 'Actual DtVariable expected rejection or unchanged state failed'}
    foreach($key in @('bound','independent_bound','fixed','DtMin','selected','signed_fixed_error')){[void](N $r.$key)}
    if($r.case -eq 'current_nan'){if($r.current -notmatch '^(?i:nan)$' -or $r.rejected -ne '1') {throw 'Deliberate NaN locked-step negative missing'};$nanCount++}else{[void](N $r.current)}
  }
  if($nanCount -ne 1){throw 'Exactly one declared nonfinite request input required'}
  if(@(Get-ChildItem -LiteralPath $runOut -Recurse -File|Where-Object {$_.Extension -eq '.bi4'}).Count){throw 'Unexpected native PART output from a component-only call'}
  $files=Files;Save $checkPath ([ordered]@{passed=$true;configuration=$Configuration;stage='upl_gpu_darcy_component_r1';helper=(E $helperPath);source_build=(E $gpuPath);input=(E $preparedPath);inputs=$inputs;call=(E $callPath);completion=(E $completion);files=$files;earlier_gates=$prior;counts=$counts;CSV_rate_rows_recomputed=2028;max_rate_reference_error_pa_s=$maxError;max_error_over_budget=$maxRatio;corner_clone_witnesses=$done.corner_clone_witnesses;device_name=$done.device_name;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;deliberate_nonfinite_request_input='current_nan/current only; expected rejection';actual_ComputeStep_Sym_called=$false;completed_physical_steps=0;public_GPU_dynamic_accepted=$false;variable_k_tested=$false;full_cycle_accepted=$false;physical_acceptance=$false})
}catch{
  if(!(Test-Path -LiteralPath $checkPath)){Save $checkPath ([ordered]@{passed=$false;configuration=$Configuration;failure=$_.Exception.Message;helper=(E $helperPath);source_build=(E $gpuPath);inputs=$inputs;call=(E $callPath);completion=$(if(Test-Path -LiteralPath $completion){E $completion}else{$null});files=@(Files);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;physical_acceptance=$false;public_GPU_dynamic_accepted=$false;completed_physical_steps_claimed=$false})};throw
}
