param([Parameter(Mandatory=$true)][ValidateSet('Run','Review')][string]$Mode,[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ExecutionAuthorized)
# One owned component invocation OR an offline review. No build, solver, GenCase, automatic next action or Git.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$note=Join-Path $t 'notes\upl_gpu_perm_component_runs_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function P([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){if(!$r -or !$r.path){throw 'Missing frozen binding'};$a=E (P $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((P $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function N($v){$n=[double]::Parse([string]$v,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture);if([double]::IsNaN($n) -or [double]::IsInfinity($n)){throw 'Unexpected nonfinite or missing diagnostic'};$n}
function B($o,[string]$key,[bool]$expected){if(!$o.PSObject.Properties[$key] -or $o.$key -isnot [bool] -or [bool]$o.$key -ne $expected){throw "Missing/wrong Boolean scope: $key"}}
function Rows([string]$leaf,[int]$count){$r=@(Import-Csv -LiteralPath (Join-Path $runOut $leaf));if($r.Count -ne $count){throw "Wrong CSV count: $leaf"};$r}
function Files(){if(Test-Path -LiteralPath $runOut){@(Get-ChildItem -LiteralPath $runOut -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})}else{@()}}
function Near([double]$a,[double]$b,[double]$relative=1.4210854715202004e-14){[Math]::Abs($a-$b) -le $relative*[Math]::Max([double]::Epsilon,[Math]::Abs($b))}
if(!$ExecutionAuthorized){throw 'Root full source/recipe review and explicit one-action authorization required'}
$helperPath=Join-Path $logs ('upl_gpu_perm_component_'+$Configuration+'_r1.helper.json');$h=J $helperPath;$gpuPath=Join-Path $logs ('upl_gpu_perm_'+$Configuration+'_r1.build.json');$g=J $gpuPath
if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'Component' -or $h.configuration -ne $Configuration -or !$h.exact_link_closure_verified -or $h.link_object_count -ne 111 -or $h.GPU_object_substitutions -ne 110 -or $h.compiler_source_remaps -ne 1 -or $h.source_build.sha256 -ine (E $gpuPath).sha256){throw 'Fresh same-source111-object smooth-k helper required'}
if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $Configuration -or !$g.private_smooth_k_GPU_candidate_build_only -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main){throw 'Authoritative full GPU Rebuild required'}
$source=J $g.source_freeze.path;$baseline=J $g.baseline.path
if(@($source.source).Count -ne 265 -or @($source.four_targets).Count -ne 4 -or $source.unchanged_source_count -ne 261 -or @($baseline.other_source).Count -ne 261 -or @($baseline.canonical_GPU).Count -ne 6 -or $source.baseline.sha256 -ine $g.baseline.sha256){throw 'Four/261/265 source closure differs'}
$preparedPath=Join-Path $logs 'upl_gpu_k0_time_r1.inputs.json';$seed=J $preparedPath
if($seed.status -ne 'k0_component_input_prepared_not_run' -or $seed.native -ne 512 -or $seed.native_initial_fields_rewritten -or $seed.xml.path -ine ($seed.prefix+'.xml') -or $seed.bi4.path -ine ($seed.prefix+'.bi4')){throw 'Exact retained periodic512 input required'}
[xml]$xml=[IO.File]::ReadAllText($seed.xml.path);$hydraulicSafety=[double]([single](N $xml.SelectSingleNode('//execution/special/hydromechanics/PoreDtSafety').value));$loadedH=[double]([single](N $xml.SelectSingleNode('//execution/constants/h').value))
if($hydraulicSafety -ne [double]([single]0.1) -or $loadedH -ne [double]([single]0.00703125)){throw 'Frozen component h/PoreDtSafety differs'}
$prior=@();if($Configuration -eq 'Release'){
  $debugPath=Join-Path $logs 'upl_gpu_perm_component_Debug_r1.check.json';$d=J $debugPath
  if(!$d.passed -or !$d.memcheck_zero_errors_and_leaks -or $d.completed_physical_steps -ne 0 -or $d.physical_acceptance -or $d.public_GPU_dynamic_accepted){throw 'Passed fresh Debug component+memcheck required first'}
  V $d.inputs;V $d.files;V @($d.call,$d.completion,$d.original_completion,$d.helper,$d.source_build);$dc=J $d.call.path
  if(!$dc.owned_call_exited -or $dc.exit_code -ne 0 -or !$dc.memcheck_zero_errors_and_leaks){throw 'Debug owned exit/memcheck invalid'};$prior=@(E $debugPath)
}
$controlPath=Join-Path $logs $(if($Configuration -eq 'Debug'){'upl_gpu_darcy_component_Debug_review_r4.check.json'}else{'upl_gpu_darcy_component_Release_run_r4.check.json'});$control=J $controlPath
if(!$control.passed -or $control.completed_physical_steps -ne 0 -or $control.physical_acceptance -or $control.public_GPU_dynamic_accepted){throw 'Retained accepted original component control required'}
$originalLeaves=@('completion.json','prefix.csv','owner_negatives.csv','host_owner_negative.csv','patch_rates.csv','patch_summary.csv','periodic_rates.csv','periodic_summary.csv','scales.csv','requests.csv')
$controlFiles=@();foreach($leaf in $originalLeaves){$entries=@($control.files|Where-Object {[IO.Path]::GetFileName($_.path) -ceq $leaf});if($entries.Count -ne 1){throw "Retained original file binding not unique: $leaf"};$controlFiles+=$entries[0]}
$name='upl_gpu_perm_component_'+$Configuration+'_r1';$runOut=Join-Path $outputs ('upl_gpu_perm_component_'+$Configuration+'_run_r1');$callPath=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log');$runPath=Join-Path $logs ($name+'.run.json');$checkPath=Join-Path $logs ($name+'.check.json')
$completion=Join-Path $runOut 'perm_completion.json';$originalCompletion=Join-Path $runOut 'completion.json'
$inputs=@(E $PSCommandPath;E $note;E $helperPath;E $gpuPath;E $preparedPath;E $controlPath;$seed.xml;$seed.bi4)+$prior
function VerifyAll {
  V $inputs;V $controlFiles;V $seed.inputs;V @($seed.xml,$seed.bi4);V $h.inputs;V $h.author_files;V $h.transitive_author_include_files;V $h.transitive_project_include_files;V $h.tools;V $h.libraries;V $h.objects;V @($h.program,$h.helper_object,$h.source_build,$h.compile_call,$h.link_call,$h.prerequisite_stage,$h.replayed_helper)
  V $g.inputs;V $g.tools;V $g.objects;V @($g.source_freeze,$g.project_call,$g.isolated_GPU_program,$g.baseline);V $source.source;V $source.four_targets;V $baseline.inputs;V $baseline.source_control_receipts;V $baseline.other_source;V $baseline.canonical_GPU
  foreach($r in @($g.runtime)+@($h.runtime)){V @($r.original,$r.copy)}
}
VerifyAll
foreach($p in @($h.compile_call.path,$h.link_call.path,$g.project_call.path)){$c=J $p;if(!$c.owned_call_exited -or $c.exit_code -ne 0){throw 'Owned build/compile/link exit0 required'};V @($c.program,$c.log)}
$mem=($Configuration -eq 'Debug');$zero=$false
if($Mode -eq 'Run'){
  foreach($p in @($runOut,$callPath,$log,$runPath,$checkPath)){if(Test-Path -LiteralPath $p){throw 'Retained invocation/output protected; completed component needs offline Review, not another Run'}}
  $target=$h.program;$targetArgs=@('--darcy','-gpu:0','-stable',$seed.prefix,$runOut,'-dirdataout','data','-svres');$program=$target;$argv=$targetArgs;$toolSource=$null
  if($mem){$toolSource=$control.call;V @($toolSource);$oldCall=J $toolSource.path;$program=$oldCall.program;if([IO.Path]::GetFileName($program.path) -ine 'compute-sanitizer.exe' -or !$oldCall.memcheck_zero_errors_and_leaks){throw 'Retained actual memcheck tool receipt required'};$argv=@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$target.path)+$targetArgs}
  V @($program,$target);[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$exited=$false;$launchFailure=$null;$preference=$ErrorActionPreference;$ErrorActionPreference='Continue'
  try{Push-Location (Join-Path $repo 'src');try{& $program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$exited=$true}finally{Pop-Location}}catch{$launchFailure=$_.Exception.Message}finally{$ErrorActionPreference=$preference}
  if($mem){$text=[IO.File]::ReadAllText($log);$zero=$text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'}
  Save $callPath ([ordered]@{owned_call_exited=$exited;exit_code=$code;launch_error=$launchFailure;program=$program;target_program=$target;arguments=$argv;target_arguments=$targetArgs;helper=(E $helperPath);source_build=(E $gpuPath);prepared_input=(E $preparedPath);recipe=$inputs;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);memcheck_tool_source_call=$toolSource;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;physical_solver_invoked=$false;physical_acceptance=$false})
  Save $runPath ([ordered]@{owned_component_exit0=($exited -and $code -eq 0 -and !$launchFailure);configuration=$Configuration;call=(E $callPath);helper=(E $helperPath);source_build=(E $gpuPath);input=(E $preparedPath);inputs=$inputs;earlier_gates=$prior;files=@(Files);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;program_completed_before_offline_review=($exited -and $code -eq 0 -and !$launchFailure);completed_physical_steps=0;physical_acceptance=$false})
  try{if(!$exited -or $code -ne 0 -or $launchFailure -or ($mem -and !$zero)){throw 'Owned component/memcheck failed; preserve all partial output'};VerifyAll;V @($program,$target)}catch{Save $checkPath ([ordered]@{passed=$false;mode=$Mode;configuration=$Configuration;failure=$_.Exception.Message;call=(E $callPath);source_run=(E $runPath);helper=(E $helperPath);source_build=(E $gpuPath);inputs=$inputs;completion=$(if(Test-Path -LiteralPath $completion){E $completion}else{$null});files=@(Files);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;physical_acceptance=$false});throw};exit 0
}
if(Test-Path -LiteralPath $checkPath){throw 'Retained review protected; repair analysis with a fresh offline label, never rerun a completed component'}
$run=J $runPath;$owned=J $callPath
if(!$run.owned_component_exit0 -or $run.configuration -ne $Configuration -or $run.source_build.sha256 -ine (E $gpuPath).sha256 -or $run.helper.sha256 -ine (E $helperPath).sha256 -or !$owned.owned_call_exited -or $owned.exit_code -ne 0 -or $owned.launch_error -or $owned.target_program.sha256 -ine $h.program.sha256 -or $owned.helper.sha256 -ine (E $helperPath).sha256 -or $owned.source_build.sha256 -ine (E $gpuPath).sha256 -or $owned.prepared_input.sha256 -ine (E $preparedPath).sha256 -or $owned.physical_solver_invoked){throw 'Completed same-helper owned component required'}
V $run.inputs;V $run.files;V @($run.call,$run.helper,$run.source_build,$run.input);V $owned.recipe;V @($owned.program,$owned.target_program,$owned.log)
$expectedArgs=@('--darcy','-gpu:0','-stable',$seed.prefix,$runOut,'-dirdataout','data','-svres')
if(@($owned.target_arguments).Count -ne $expectedArgs.Count){throw 'Owned target argv length differs'};for($i=0;$i -lt $expectedArgs.Count;$i++){if($owned.target_arguments[$i] -cne $expectedArgs[$i]){throw 'Owned target argv differs'}}
if($mem){V @($owned.memcheck_tool_source_call);$text=[IO.File]::ReadAllText($log);$zero=$text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations';if(!$owned.memcheck_executed -or !$owned.memcheck_zero_errors_and_leaks -or !$zero -or [IO.Path]::GetFileName($owned.program.path) -ine 'compute-sanitizer.exe'){throw 'Actual Debug memcheck0/0 required'}}
try{
  $original=J $originalCompletion
  $originalCounts=[ordered]@{prefix_stage_cases=6;owner_negative_cases=4;finite_patch_cases=12;finite_patch_rate_rows=108;actual_host_periodic_cases=2;actual_host_periodic_rate_rows=1920;class_scale_cases=4;positive_k_domain_rejections=1;actual_DtVariable_cases=12}
  foreach($key in $originalCounts.Keys){if($original.$key -ne $originalCounts[$key]){throw "Component count differs: $key"}}
  if(!$original.passed -or $original.stage -ne 'upl_gpu_darcy_component_r3' -or !$original.actual_private_rate_kernel -or !$original.actual_host_owner_and_rate_helpers -or !$original.independent_all_particle_reference -or !$original.kernel_float_factor_budget_predeclared -or !$original.full_rate_overwrite -or !$original.actual_LoadConfig_ConfigDomain_InitRunGpu -or $original.actual_ComputeStep_Sym_called -or $original.completed_physical_steps -ne 0 -or $original.public_GPU_dynamic_mode -or $original.variable_k_tested -or $original.physical_acceptance -or $original.corner_clone_witnesses -le 0){throw 'Invalid bounded component completion scope'}
  $reportedRatio=N $original.max_error_over_budget;$reportedError=N $original.max_rate_reference_error_pa_s;if($reportedRatio -lt 0 -or $reportedRatio -gt 1 -or $reportedError -lt 0){throw 'Original complete-rate budget rejected'}
  $prefix=Rows 'prefix.csv' 6;foreach($r in $prefix){if($r.all_active_and_tail_bits_exact -ne 'true' -or $r.prefix -ne '2' -or $r.native_owners -ne '4' -or $r.periodic_images -ne '4'){throw 'Prefix/owner exact-copy gate failed'}}
  $owner=Rows 'owner_negatives.csv' 3;foreach($r in $owner){if($r.actual_invalid -ne '2' -or $r.expected_invalid -ne '2' -or $r.negative_nonempty -ne 'true'){throw 'Owner negative did not reject intended slot'}}
  $hostNegative=Rows 'host_owner_negative.csv' 1;if($hostNegative[0].rejected -ne 'true' -or $hostNegative[0].map_flag_pool_released -ne 'true'){throw 'Actual host owner error/pool-release gate failed'}
  $patch=Rows 'patch_rates.csv' 108;$periodic=Rows 'periodic_rates.csv' 1920;$maxRatio=0.;$maxError=0.
  foreach($r in @($patch)+@($periodic)){
    $a=N $r.actual;$b=N $r.reference;$budget=N $r.budget;$rateResidual=N $r.error;$ratio=N $r.error_over_budget;[void](N $r.pressure_source);[void](N $r.acceleration_source)
    $e=[Math]::Abs($a-$b);if($budget -le 0 -or $a -eq 1234567 -or $e -gt $budget -or $ratio -lt 0 -or $ratio -gt 1 -or $rateResidual -ne $e -or [Math]::Abs($ratio-$e/$budget) -gt 64*2.2204460492503131e-16*[Math]::Max(1.,$ratio)){throw 'Per-row original propagated rate budget failed'}
    $maxRatio=[Math]::Max($maxRatio,$ratio);$maxError=[Math]::Max($maxError,$e)
  }
  if($maxRatio -ne $reportedRatio -or $maxError -ne $reportedError){throw 'Completion summary differs from all CSV rate rows'}
  $patchSummary=Rows 'patch_summary.csv' 12;foreach($r in $patchSummary){if($r.rows -ne '9'){throw 'Patch field sample count differs'};[void](N $r.max_pressure_source);[void](N $r.max_acceleration_source)}
  $periodicSummary=Rows 'periodic_summary.csv' 2;foreach($r in $periodicSummary){if($r.slots -ne '960' -or [int]$r.ghosts -le 0 -or [int]$r.corners -le 0 -or (N $r.min_owner_C_norm) -le 0 -or $r.pre_rate_sentinel_preserved -ne 'true'){throw 'Periodic owner/source evidence is empty'}}
  $scales=Rows 'scales.csv' 5;if(@($scales|Where-Object {$_.rejected -eq 'true'}).Count -ne 1){throw 'Expected one strict positive-k domain rejection'}
  foreach($r in $scales){foreach($key in @('J','k','wave','pore','wave_independent','pore_independent')){[void](N $r.$key)}}
  foreach($r in $scales){if($r.rejected -eq 'false' -and (!(Near (N $r.wave) (N $r.wave_independent)) -or !(Near (N $r.pore) (N $r.pore_independent)))){throw 'Original wave/pore64DBL_EPS closure changed'}}
  $requests=Rows 'requests.csv' 12;$nanCount=0
  foreach($r in $requests){
    if($r.rejected -ne $r.expected_reject -or $r.physical_unchanged -ne 'true'){throw 'Actual DtVariable expected rejection or unchanged state failed'}
    foreach($key in @('bound','independent_bound','fixed','DtMin','selected','signed_fixed_error')){[void](N $r.$key)}
    if(!(Near (N $r.bound) (N $r.independent_bound)) -or (N $r.signed_fixed_error) -ne $(if((N $r.fixed)){(N $r.fixed)-(N $r.bound)}else{0.})){throw 'Original full-bound or signed FixedDt telemetry differs'}
    if($r.case -eq 'current_nan'){if($r.current -notmatch '^(?i:nan)$' -or $r.rejected -ne '1') {throw 'Deliberate NaN locked-step negative missing'};$nanCount++}else{[void](N $r.current)}
  }
  if($nanCount -ne 1){throw 'Exactly one declared nonfinite request input required'}
  foreach($key in 'passed','actual_private_rate_kernel','actual_host_owner_and_rate_helpers','independent_all_particle_reference','kernel_float_factor_budget_predeclared','full_rate_overwrite','actual_LoadConfig_ConfigDomain_InitRunGpu'){B $original $key $true}
  foreach($key in 'actual_ComputeStep_Sym_called','public_GPU_dynamic_mode','variable_k_tested','physical_acceptance'){B $original $key $false}
  $done=J $completion;$counts=[ordered]@{law_patch_cases=16;law_patch_rows=144;law_periodic_cases=2;law_periodic_rows=1920;direct_rate_kernel_calls=26;actual_host_rate_calls=7;uniform_scale_cases=4;guard_cases=11;cache_cases=5;actual_gradient_DtVariable_cases=8}
  foreach($key in $counts.Keys){if($done.$key -ne $counts[$key]){throw "Added component count differs: $key"}}
  if($done.stage -cne 'upl_gpu_perm_component_r1' -or $done.original_completion_stage -cne 'upl_gpu_darcy_component_r3' -or $done.completed_physical_steps -ne 0 -or $done.corner_witnesses -le 0){throw 'Variable-k completion stage/scope differs'}
  foreach($key in 'passed','original_constant_suite_retained','ki_GJ_chain_are_independent_reference_not_native_output','actual_rate_speed_scales_measured','native_periodic_host_component_not_Run'){B $done $key $true}
  foreach($key in 'actual_ComputeStep_Sym_called','public_GPU_dynamic_accepted','physical_acceptance'){B $done $key $false}
  $lawPatch=Rows 'law_rates.csv' 144;$lawPeriodic=Rows 'law_periodic_rates.csv' 1920;$lawMaxError=0.;$lawMaxRatio=0.
  foreach($r in @($lawPatch)+@($lawPeriodic)){
    foreach($property in $r.PSObject.Properties){if($property.Name -ne 'field'){[void](N $property.Value)}}
    $a=N $r.actual;$b=N $r.reference;$budget=N $r.budget;$residual=N $r.error;$ratio=N $r.error_over_budget;$rateDifference=[Math]::Abs($a-$b)
    if($a -eq 1234567 -or $budget -le 0 -or $rateDifference -gt $budget -or $residual -ne $rateDifference -or $ratio -lt 0 -or $ratio -gt 1 -or [Math]::Abs($ratio-$rateDifference/$budget) -gt 64*2.2204460492503131e-16*[Math]::Max(1.,$ratio) -or (N $r.reference_k) -lt 0 -or (N $r.reference_n) -le 0 -or (N $r.reference_n) -ge 1 -or (N $r.reference_V) -le 0 -or (N $r.reference_rho) -le 0 -or (N $r.reference_speed) -lt 0 -or (N $r.speed_budget) -le 0){throw 'Added per-row finite ledger or original propagated rate budget failed'}
    $lawMaxError=[Math]::Max($lawMaxError,$rateDifference);$lawMaxRatio=[Math]::Max($lawMaxRatio,$ratio)
  }
  if($lawMaxError -ne (N $done.max_rate_reference_error_pa_s) -or $lawMaxRatio -ne (N $done.max_rate_error_over_budget)){throw 'Added completion rate maxima differ from every CSV row'}
  $lawSummary=Rows 'law_summary.csv' 16;$lawPeriodicSummary=Rows 'law_periodic_summary.csv' 2
  foreach($summary in @($lawSummary)+@($lawPeriodicSummary)){
    foreach($property in $summary.PSObject.Properties){if($property.Name -notin 'field','owner_copy_exact'){[void](N $property.Value)}}
    if($summary.PSObject.Properties['rows']){
      if($summary.rows -ne '9'){throw 'Added patch summary count differs'};$group=@($lawPatch|Where-Object {$_.field -ceq $summary.field})
    }else{
      if($summary.slots -ne '960' -or [int]$summary.ghosts -le 0 -or [int]$summary.corners -le 0 -or $summary.owner_copy_exact -cne 'true'){throw 'Added periodic owner/corner evidence is empty'}
      $label=if($summary.field -eq '0'){'k0_law'}elseif($summary.field -eq '1'){'positive_law'}else{throw 'Unknown law periodic label'};$group=@($lawPeriodic|Where-Object {$_.field -ceq $label})
    }
    $expectedRows=if($summary.PSObject.Properties['rows']){9}else{960};if($group.Count -ne $expectedRows){throw 'Summary rate group missing or duplicated'}
    $refSpeed=0.;$speedBudget=0.;$chainP=0.;$chainA=0.;$maxRateBudget=0.
    foreach($r in $group){$refSpeed=[Math]::Max($refSpeed,(N $r.reference_speed));$speedBudget=[Math]::Max($speedBudget,(N $r.speed_budget));$chainP=[Math]::Max($chainP,[Math]::Abs((N $r.reference_pressure_chain)));$chainA=[Math]::Max($chainA,[Math]::Abs((N $r.reference_acceleration_chain)));$maxRateBudget=[Math]::Max($maxRateBudget,(N $r.budget))}
    if((N $summary.reference_speed) -ne $refSpeed -or (N $summary.speed_budget) -ne $speedBudget){throw 'Independent native speed maximum/budget summary differs'}
    if($summary.PSObject.Properties['rows']){
      if((N $summary.reference_pressure_chain) -ne $chainP -or (N $summary.reference_acceleration_chain) -ne $chainA){throw 'Chain source maxima differ from all nine patch rows'}
      if($summary.field -match 'affineJ_pressure_chain$|nonlinear_complete$'){if($chainP -le 10*$maxRateBudget){throw 'Pressure coefficient-gradient chain is empty'}}
      if($summary.field -match 'affineJ_acceleration_chain$|nonlinear_complete$'){if($chainA -le 10*$maxRateBudget){throw 'Acceleration coefficient-gradient chain is empty'}}
      if($summary.field -match 'affineJ_pressure_chain$|affineJ_acceleration_chain$|nonlinear_complete$|zero_driving_nonzero_speed$'){if((N $summary.actual_speed) -le 10*$speedBudget){throw 'Added gradient-speed evidence is empty'}}
      if($summary.field -match 'affineJ_R0$'){foreach($r in $group){if([Math]::Abs((N $r.actual)) -gt (N $r.budget) -or [Math]::Abs((N $r.reference)) -gt (N $r.budget)){throw 'Variable-k affine R0 exceeds original budget'}}}
      if($summary.field -match 'zero_driving_nonzero_speed$'){foreach($r in $group){if((N $r.actual) -ne 0){throw 'Zero-driving actual rate is not exactly zero'}}}
    }elseif($summary.field -eq '0'){if((N $summary.actual_speed) -ne 0){throw 'k0 periodic speed is nonzero'}}elseif((N $summary.actual_speed) -le 10*$speedBudget){throw 'Positive periodic speed evidence is empty'}
  }
  $lawScales=Rows 'law_scales.csv' 4
  foreach($r in $lawScales){
    foreach($property in $r.PSObject.Properties){if($property.Name -ne 'field'){[void](N $property.Value)}}
    $j=N $r.J;$n=1.-.75/$j;$rho=1000.+1048./$j;$k=N $r.reference_k;$expectedK=[double]([single]0.0001)*[Math]::Exp(($j-1.)/(.75*.125));$expectedCu2=(89478488.+4.*134217728./3.+67108864./$n)/$rho;$expectedD=67108864./$n*$k/(1000.*9.80665)
    if(!($j -eq 1. -or $j -eq 1.01) -or !(Near $k $expectedK 5e-13) -or !(Near (N $r.actual_maxcu2) $expectedCu2) -or !(Near (N $r.inferred_k_from_actual_Dmax) $k 5e-13) -or !(Near (N $r.actual_Dmax) $expectedD 5e-13) -or !(Near (N $r.reference_Dmax) $expectedD)){throw 'Uniform current-k diffusion/mixture-wave closure failed'}
  }
  $lawGuards=Rows 'law_guards.csv' 11;$hostRejects=0;$deviceRejects=0;$offControls=0
  foreach($r in $lawGuards){
    if((N $r.actual_invalid) -ne 0 -or $r.covered_state_unchanged -cne 'true'){throw 'Conductivity guard touched covered state or wrong invalid slot'}
    if($r.API -ceq 'host_Init' -and $r.case -ceq 'OFF_ignores_Ck_nan'){if($r.rejected -cne 'false'){throw 'Unused OFF Ck positive control rejected'};$offControls++}
    elseif($r.API -ceq 'host_Init'){if($r.rejected -cne 'true' -or $r.case -notin 'Ck_zero','Ck_negative','Ck_nan','Ck_infinite','alpha_overflow','requires_dynamic'){throw 'Unknown or un-rejected host law parameter guard'};$hostRejects++}
    elseif($r.API -ceq 'device_rate_and_scale'){if($r.rejected -cne 'true' -or $r.case -notmatch '^(regular|jitter)_(underflow|overflow)$'){throw 'Unknown or un-rejected device conductivity guard'};$deviceRejects++}else{throw 'Unknown conductivity guard API'}
  }
  if($hostRejects -ne 6 -or $deviceRejects -ne 4 -or $offControls -ne 1 -or @($lawGuards.case|Sort-Object -Unique).Count -ne 11){throw 'Declared parameter/device guard coverage incomplete'}
  $cache=Rows 'law_cache.csv' 5;$expectedCache=@('active','OFF_reset','k0_reset','uniform_reset','active_recomputed')
  for($i=0;$i -lt 5;$i++){if($cache[$i].case -cne $expectedCache[$i] -or $cache[$i].geometry -cne 'periodic' -or $cache[$i].passed -cne 'true'){throw 'Cache sequence differs'};foreach($property in $cache[$i].PSObject.Properties){if($property.Name -notin 'geometry','case','passed'){[void](N $property.Value)}}}
  $active=$cache[0];$activeSpeed=N $active.actual_speed;$activeBudget=N $active.speed_budget;$oldBound=N $active.old_bound;$newBound=N $active.new_bound
  if($activeSpeed -le 10*$activeBudget -or (N $active.wave) -le 0 -or (N $active.pore) -le 0 -or $oldBound -ne [Math]::Min(.2*(N $active.wave),(N $active.pore)) -or $newBound -ne [Math]::Min($oldBound,$hydraulicSafety*$loadedH/$activeSpeed) -or $newBound -le 0 -or $newBound -gt .5*$oldBound){throw 'Actual gradient-bound cache is empty or necessary bound not active'}
  foreach($i in 1,2,3){if((N $cache[$i].actual_speed) -ne 0){throw 'OFF/k0/uniform actual rate failed stale-cache reset'}}
  if((N $cache[4].actual_speed) -ne $activeSpeed){throw 'Actual active cache recomputation is not identical'}
  $lawMaxSpeedError=0.;$lawMaxSpeedRatio=0.
  foreach($r in @($lawSummary)+@($lawPeriodicSummary)+@($active)){
    $a=N $r.actual_speed;$b=N $r.reference_speed;$budget=N $r.speed_budget;$speedDifference=[Math]::Abs($a-$b)
    if($a -lt 0 -or $budget -le 0 -or $speedDifference -gt $budget -or ($r.PSObject.Properties['speed_error'] -and (N $r.speed_error) -ne $speedDifference)){throw 'Independent actual/referenced native speed budget failed'}
    $lawMaxSpeedError=[Math]::Max($lawMaxSpeedError,$speedDifference);$lawMaxSpeedRatio=[Math]::Max($lawMaxSpeedRatio,$speedDifference/$budget)
  }
  if($lawMaxSpeedError -ne (N $done.max_speed_reference_error_m_s) -or $lawMaxSpeedRatio -ne (N $done.max_speed_error_over_budget)){throw 'Completion speed maxima differ from all nineteen measured cases'}
  $lawRequests=Rows 'law_requests.csv' 8;$requestNames=@('variable_safe','fixed_safe','fixed_bound','locked_midway','requested_midway','DtMin_midway','DtMin_above_fixed','locked_bound')
  for($i=0;$i -lt 8;$i++){
    $r=$lawRequests[$i];if($r.case -cne $requestNames[$i] -or $r.rejected -ne $r.expected_reject -or $r.physical_unchanged -cne 'true'){throw 'Gradient request/rejection or covered-state guard failed'}
    foreach($key in 'old_bound','new_bound','current','fixed','DtMin','selected','signed_fixed_error'){[void](N $r.$key)}
    $reject=$i -in 3,4,5,6;if($r.rejected -cne $(if($reject){'1'}else{'0'}) -or (N $r.old_bound) -ne $oldBound -or (N $r.new_bound) -ne $newBound){throw 'Declared active-bound request identity differs'}
    $selected=N $r.selected;$fixed=N $r.fixed
    if(!$reject -and $selected -ne $(if($i -eq 1){.5*$newBound}else{$newBound})){throw 'Accepted actual step was clipped or uplifted'}
    if((N $r.signed_fixed_error) -ne $(if($fixed){$fixed-$newBound}else{0.})){throw 'FixedDt did not receive the full gradient-aware bound'}
  }
  if(@(Get-ChildItem -LiteralPath $runOut -Recurse -File|Where-Object {$_.Extension -eq '.bi4'}).Count){throw 'Unexpected native PART output from component-only call'}
  $comparisons=@();foreach($old in $controlFiles){$leaf=[IO.Path]::GetFileName($old.path);$new=E (Join-Path $runOut $leaf);$comparisons+=[ordered]@{leaf=$leaf;retained=$old;current=$new;byte_identical=($old.bytes -eq $new.bytes -and $old.sha256 -ieq $new.sha256);comparison_is_descriptive_not_admission_gate=$true}}
  VerifyAll;V $run.files;V @($owned.program,$owned.target_program,$owned.log);$files=@(Files)
  Save $checkPath ([ordered]@{passed=$true;stage='upl_gpu_perm_component_r1';configuration=$Configuration;mode=$Mode;helper=(E $helperPath);source_build=(E $gpuPath);input=(E $preparedPath);inputs=$inputs;source_run=(E $runPath);call=(E $callPath);completion=(E $completion);original_completion=(E $originalCompletion);files=$files;earlier_gates=$prior;original_counts=$originalCounts;counts=$counts;original_CSV_rate_rows_recomputed=2028;law_CSV_rate_rows_recomputed=2064;max_original_rate_error_over_budget=$maxRatio;max_law_rate_reference_error_pa_s=$lawMaxError;max_law_rate_error_over_budget=$lawMaxRatio;max_law_speed_reference_error_m_s=$lawMaxSpeedError;max_law_speed_error_over_budget=$lawMaxSpeedRatio;original_configuration_matched_file_comparisons=$comparisons;old_component_reference_byte_identity_is_not_required=$true;all_native_trajectory_0ULP_gates_relaxed=$false;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;completed_physical_steps=0;actual_ComputeStep_Sym_called=$false;public_GPU_dynamic_accepted=$false;general_variable_coefficient_stability_proven=$false;physical_acceptance=$false})
}catch{
  if(!(Test-Path -LiteralPath $checkPath)){Save $checkPath ([ordered]@{passed=$false;stage='upl_gpu_perm_component_r1';mode=$Mode;configuration=$Configuration;failure=$_.Exception.Message;helper=(E $helperPath);source_build=(E $gpuPath);inputs=$inputs;source_run=(E $runPath);call=(E $callPath);completion=$(if(Test-Path -LiteralPath $completion){E $completion}else{$null});original_completion=$(if(Test-Path -LiteralPath $originalCompletion){E $originalCompletion}else{$null});files=@(Files);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;completed_physical_steps_claimed=$false;physical_acceptance=$false})};throw
}

