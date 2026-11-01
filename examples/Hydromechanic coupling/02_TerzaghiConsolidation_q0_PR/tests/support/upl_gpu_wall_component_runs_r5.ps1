param([Parameter(Mandatory=$true)][ValidateSet('Run','Review')][string]$Mode,[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ExecutionAuthorized)
# One owned component invocation OR offline Review. Never build, integrate, GenCase, notify or Git.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$note=Join-Path $t 'notes\upl_gpu_wall_component_runs_r5.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function P([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){if(!$r -or !$r.path){throw 'Missing frozen binding'};$a=E (P $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((P $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function N($v){$n=if($v -is [ValueType]){[double]$v}else{[double]::Parse([string]$v,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture)};if([double]::IsNaN($n) -or [double]::IsInfinity($n)){throw 'Missing/nonfinite diagnostic'};$n}
function B($o,[string]$key,[bool]$expected){if(!$o.PSObject.Properties[$key] -or $o.$key -isnot [bool] -or [bool]$o.$key -ne $expected){throw "Missing/wrong Boolean scope: $key"}}
function Rows([string]$leaf,[int]$count){$r=@(Import-Csv -LiteralPath (Join-Path $runOut $leaf));if($r.Count -ne $count){throw "Wrong CSV count: $leaf"};$r}
function Finite($r,[string[]]$except=@()){foreach($p in $r.PSObject.Properties){if($p.Name -notin $except){[void](N $p.Value)}}}
function Close([double]$a,[double]$b){[Math]::Abs($a-$b) -le 64*2.2204460492503131e-16*[Math]::Max(1.,[Math]::Max([Math]::Abs($a),[Math]::Abs($b)))}
function FloatBits([double]$v){[BitConverter]::ToUInt32([BitConverter]::GetBytes([single]$v),0)}
function Files(){if(Test-Path -LiteralPath $runOut){@(Get-ChildItem -LiteralPath $runOut -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})}else{@()}}
if(!$ExecutionAuthorized){throw 'Root full source/recipe review and explicit single-action authorization required'}
$helperPath=Join-Path $logs ('upl_gpu_wall_component_'+$Configuration+'_r1.helper.json');$h=J $helperPath
$gpuPath=Join-Path $logs ('upl_gpu_wall_'+$Configuration+'_r1.build.json');$g=J $gpuPath
if($h.status -cne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -cne 'Component' -or $h.configuration -cne $Configuration -or !$h.exact_link_closure_verified -or $h.link_object_count -ne 111 -or $h.GPU_object_substitutions -ne 110 -or $h.compiler_source_remaps -ne 1 -or $h.source_build.sha256 -ine (E $gpuPath).sha256){throw 'Fresh wall111-object helper required'}
if($g.status -cne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -cne $Configuration -or !$g.private_static_wall_GPU_candidate_build_only -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main){throw 'Current authoritative full GPU Rebuild required'}
$source=J $g.source_freeze.path;$baseline=J $g.baseline.path
if(@($source.source).Count -ne 265 -or @($source.five_targets).Count -ne 5 -or $source.unchanged_source_count -ne 260 -or @($baseline.other_source).Count -ne 260 -or @($baseline.canonical_GPU).Count -ne 6 -or $source.baseline.sha256 -ine $g.baseline.sha256){throw 'Five/260/265 source closure differs'}
$fixtureCpp=Join-Path $t 'support\upl_gpu_wall_component_r1.cpp';$fixtureNote=Join-Path $t 'notes\upl_gpu_wall_component_r1.json'
if((E $fixtureCpp).sha256 -cne 'cb8ac53a2e733bad6994e6db29475eef545b92459fc5f0faf28bdff1ee66817b' -or (E $fixtureNote).sha256 -cne 'c635e2ab936cbd169c1bf92b8f8b5959da6b152806d6e2bf1d00942791484539'){throw 'Root-reviewed final wall component author identity differs'}
$preparedPath=Join-Path $logs 'upl_p3_wall_wave_seed_r3.inputs.json';$seed=J $preparedPath
$prefix=Join-Path $outputs 'upl_p3_wall_wave_seed_r3_h\CaseUplWall_h'
$seedXml=E ($prefix+'.xml');$seedBi4=E ($prefix+'.bi4');$geometryPath=Join-Path $logs 'upl_p3_wall_wave_seed_r3_h.geometry.check.json';$runtimePath=Join-Path $logs 'upl_p3_wall_wave_seed_r3_h.runtime.json'
if($seed.new_solver_calls -ne 0 -or $seedXml.sha256 -cne '1004f6a3dcd31ba8ddd8af1e8c264982c3f43d47defbd45a48985cd7a53b0a58' -or $seedBi4.bytes -ne 57736 -or $seedBi4.sha256 -cne '76ead35508f882ff8d3ac8c890a57b77120d610f04d9f3d802c17103077a932f'){throw 'Immutable h seed identity differs; h is initialization only, not half validation'}
foreach($r in @($seedXml,$seedBi4,(E $geometryPath),(E $runtimePath))){$m=@(@($seed.files)+@($seed.jobs)|Where-Object {$_.path -ieq $r.path -and $_.sha256 -ieq $r.sha256 -and $_.bytes -eq $r.bytes});if($m.Count -ne 1){throw 'Selected seed dependency not uniquely sealed'}}
$geometry=J $geometryPath;$runtime=J $runtimePath
if(!$geometry.passed -or $geometry.total -ne 1280 -or $geometry.soil -ne 1024 -or $geometry.left -ne 128 -or $geometry.right -ne 128 -or !$geometry.exact_half_dp_lattice -or !$runtime.only_runtime_xml_dp_changed -or $runtime.runtime_bi4.sha256 -ine $seedBi4.sha256 -or $runtime.runtime_xml.sha256 -ine $seedXml.sha256){throw 'Retained wall geometry/runtime guard differs'}
$prior=@();if($Configuration -eq 'Release'){
  $debugPath=Join-Path $logs 'upl_gpu_wall_component_Debug_r5.check.json';$d=J $debugPath
  if(!$d.passed -or !$d.memcheck_zero_errors_and_leaks -or $d.completed_physical_steps -ne 0 -or $d.physical_acceptance -or $d.public_GPU_dynamic_accepted){throw 'Passed fresh Debug wall component+memcheck required'}
  V $d.inputs;V $d.files;V @($d.call,$d.completion,$d.helper,$d.source_build);$dc=J $d.call.path
  if(!$dc.owned_call_exited -or $dc.exit_code -ne 0 -or !$dc.memcheck_zero_errors_and_leaks){throw 'Fresh Debug owned exit/memcheck differs'};$prior=@(E $debugPath)
}
$toolCallPath=Join-Path $logs 'upl_gpu_perm_component_Debug_r1.call.json';$toolCall=J $toolCallPath
if(!$toolCall.owned_call_exited -or $toolCall.exit_code -ne 0 -or !$toolCall.memcheck_zero_errors_and_leaks -or [IO.Path]::GetFileName($toolCall.program.path) -ine 'compute-sanitizer.exe'){throw 'Retained actual memcheck tool provenance required'}
$name='upl_gpu_wall_component_'+$Configuration+'_r2';$runOut=Join-Path $outputs ('upl_gpu_wall_component_'+$Configuration+'_run_r2')
$callPath=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log');$runPath=Join-Path $logs ($name+'.run.json');$checkPath=Join-Path $logs ('upl_gpu_wall_component_'+$Configuration+'_r5.check.json');$completion=Join-Path $runOut 'completion.json'
$inputs=@(E $PSCommandPath;E $note;E $helperPath;E $gpuPath;E $preparedPath;E $geometryPath;E $runtimePath;E $fixtureCpp;E $fixtureNote;E $toolCallPath;$seedXml;$seedBi4)+$prior
function VerifyAll {
  V $inputs;V $seed.inputs;V @($seedXml,$seedBi4,$geometry.xml,$geometry.vtk,$runtime.raw_bi4,$runtime.raw_xml);V @($toolCall.program,$toolCall.log)
  V $h.inputs;V $h.author_files;V $h.transitive_author_include_files;V $h.transitive_project_include_files;V $h.tools;V $h.libraries;V $h.objects;V @($h.program,$h.helper_object,$h.source_build,$h.compile_call,$h.link_call,$h.prerequisite_stage,$h.replayed_helper)
  V $g.inputs;V $g.tools;V $g.objects;V @($g.source_freeze,$g.project_call,$g.isolated_GPU_program,$g.baseline);V $source.source;V $source.five_targets
  V $baseline.inputs;V $baseline.source_control_receipts;V $baseline.other_source;V $baseline.canonical_GPU
  foreach($r in @($g.runtime)+@($h.runtime)){V @($r.original,$r.copy)}
}
VerifyAll
foreach($p in @($h.compile_call.path,$h.link_call.path,$g.project_call.path)){$c=J $p;if(!$c.owned_call_exited -or $c.exit_code -ne 0){throw 'Owned build/compile/link exit0 required'};V @($c.program,$c.log)}
$mem=($Configuration -eq 'Debug');$zero=$false
$targetArgs=@('--wall','-gpu:0','-stable','-mdbc_freeslip',$prefix,$runOut)
if($Mode -eq 'Run'){
  if($Configuration -eq 'Debug'){throw 'Completed r2 Debug is adopted for offline Review only; never rerun it'}
  foreach($p in @($runOut,$callPath,$log,$runPath,$checkPath)){if(Test-Path -LiteralPath $p){throw 'Retained invocation protected; completed component requires offline Review, never another Run'}}
  $target=$h.program;$program=$target;$argv=$targetArgs;if($mem){$program=$toolCall.program;$argv=@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$target.path)+$targetArgs}
  V @($program,$target);[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$exited=$false;$launchFailure=$null;$preference=$ErrorActionPreference;$ErrorActionPreference='Continue'
  try{Push-Location (Join-Path $repo 'src');try{& $program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$exited=$true}finally{Pop-Location}}catch{$launchFailure=$_.Exception.Message}finally{$ErrorActionPreference=$preference}
  if($mem){$text=[IO.File]::ReadAllText($log);$zero=$text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'}
  Save $callPath ([ordered]@{owned_call_exited=$exited;exit_code=$code;launch_error=$launchFailure;program=$program;target_program=$target;arguments=$argv;target_arguments=$targetArgs;helper=(E $helperPath);source_build=(E $gpuPath);prepared_input=(E $preparedPath);selected_seed_XML=$seedXml;selected_seed_BI4=$seedBi4;recipe=$inputs;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);memcheck_tool_source_call=(E $toolCallPath);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;physical_solver_invoked=$false;physical_acceptance=$false})
  Save $runPath ([ordered]@{owned_component_exit0=($exited -and $code -eq 0 -and !$launchFailure);configuration=$Configuration;call=(E $callPath);helper=(E $helperPath);source_build=(E $gpuPath);input=(E $preparedPath);inputs=$inputs;earlier_gates=$prior;files=@(Files);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;program_completed_before_offline_review=($exited -and $code -eq 0 -and !$launchFailure);completed_physical_steps=0;physical_acceptance=$false})
  try{if(!$exited -or $code -ne 0 -or $launchFailure -or ($mem -and !$zero)){throw 'Owned wall component/memcheck failed; preserve partial evidence'};VerifyAll;V @($program,$target)}
  catch{Save $checkPath ([ordered]@{passed=$false;mode=$Mode;configuration=$Configuration;failure=$_.Exception.Message;call=(E $callPath);source_run=(E $runPath);helper=(E $helperPath);source_build=(E $gpuPath);inputs=$inputs;completion=$(if(Test-Path -LiteralPath $completion){E $completion}else{$null});files=@(Files);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;physical_acceptance=$false});throw};exit 0
}
if(Test-Path -LiteralPath $checkPath){throw 'Retained review protected; use a fresh offline analysis label, never rerun a completed component'}
$run=J $runPath;$owned=J $callPath
if(!$run.owned_component_exit0 -or $run.configuration -cne $Configuration -or $run.source_build.sha256 -ine (E $gpuPath).sha256 -or $run.helper.sha256 -ine (E $helperPath).sha256 -or !$owned.owned_call_exited -or $owned.exit_code -ne 0 -or $owned.launch_error -or $owned.target_program.sha256 -ine $h.program.sha256 -or $owned.helper.sha256 -ine (E $helperPath).sha256 -or $owned.source_build.sha256 -ine (E $gpuPath).sha256 -or $owned.physical_solver_invoked){throw 'Completed same-helper owned wall component required'}
V $run.inputs;V $run.files;V @($run.call,$run.helper,$run.source_build,$run.input);V $owned.recipe;V @($owned.program,$owned.target_program,$owned.log,$owned.selected_seed_XML,$owned.selected_seed_BI4)
if(@($owned.target_arguments).Count -ne $targetArgs.Count){throw 'Owned argv length differs'};for($i=0;$i -lt $targetArgs.Count;$i++){if($owned.target_arguments[$i] -cne $targetArgs[$i]){throw 'Owned argv differs'}}
if($mem){$text=[IO.File]::ReadAllText($log);$zero=$text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations';if(!$owned.memcheck_executed -or !$owned.memcheck_zero_errors_and_leaks -or !$zero -or $owned.program.sha256 -ine $toolCall.program.sha256){throw 'Actual Debug memcheck0/0 required'}}
try{
  $done=J $completion;$counts=[ordered]@{native_soil=1024;native_fixed=256;affine_cases=2;affine_wall_rows=512;coincident_pressure_rows=256;complete_rate_cases=2;complete_rate_rows=2048;wrong_wall_rate_cases=3;real_owner_negative_cases=1;actual_force_component_audits=1;persistent_rollback_checks=2;completed_physical_steps=0}
  foreach($key in $counts.Keys){if($done.$key -ne $counts[$key]){throw "Component count differs: $key"}}
  if($done.stage -cne 'upl_gpu_wall_component_r1' -or $done.actual_np -lt 1280 -or $done.actual_nonzero_Npb -lt 256 -or $done.actual_NpbOk -lt 256 -or $done.actual_NpbOk -gt $done.actual_nonzero_Npb -or $done.fluid_periodic_slots -le 0 -or $done.wall_periodic_slots -le 0){throw 'Wall stage/native-prefix scope differs'}
  foreach($key in 'passed','actual_LoadConfig_ConfigDomain_InitRunGpu','actual_private_wall_host_helpers','actual_complete_rate_kernel','actual_nonzero_fixed_prefix_and_wall_neighbors','Dp_over_8_noncoincident_affine_witness','coincident_nonlinear_pressure_anchor_bits_exact','all_real_positions_and_normal_bytes_restored','covered_native26_and_persistent_boundary_rollback_exact','first_force_statistics_computed_not_read_before_force','extra_force_is_not_an_integrator_stage','J_C_Ace_rate_references_use_actual_conditional_C'){B $done $key $true}
  foreach($key in 'actual_ComputeStep_Sym_called','actual_production_Run_called','physical_trajectory_or_energy_acceptance','native_BI4_serialization_tested','full_force_stage_call_counts_directly_observed','public_GPU_dynamic_mode','physical_acceptance'){B $done $key $false}
  $epsD=2.2204460492503131e-16;$epsF=1.1920928955078125e-7;$dp=1./512.;$A=1./512.;$maxAffine=0.;$anchorBudget=@{}
  foreach($leaf in 'affine.csv','offgrid_affine.csv'){
    $rows=Rows $leaf 256;$ids=@{}
    foreach($r in $rows){
      Finite $r;$id=N $r.id;if($id -ne [int]$id -or $id -lt 0 -or $id -ge 256 -or $ids.ContainsKey([int]$id)){throw 'Affine true fixed IDs missing/duplicated'};$ids[[int]$id]=$true
      $cond=N $r.condition;$td=N $r.double_base_tol;$tf=N $r.float_base_tol
      if($cond -lt 1 -or $td -ne 32768*$epsD*$cond -or $tf -ne 64*$epsF*$cond -or (N $r.nearest_distance_m) -ne $(if($leaf -ceq 'affine.csv'){0.}else{$dp/8})){throw 'Original affine budgets/distance differ'}
      if($leaf -ceq 'affine.csv'){$anchorBudget[[int]$id]=256*$tf}
      foreach($p in @(@('J_error',(2*$td)),@('p_error',(256*$tf)),@('v_error',$tf),@('sigma_error',(128*$td)),@('C_error',(4*$td)),@('ace_error',$tf))){
        $e=N $r.($p[0]);if($e -lt 0 -or $e -gt $p[1]){throw 'Original affine field budget failed'};$maxAffine=[Math]::Max($maxAffine,$e/$p[1])
      }
      if((N $r.wrong_copy_C_error) -le 4*$td -or (N $r.wrong_copy_Ace_error) -le $tf){throw 'Nonreflection affine counterfactual is empty'}
    }
  }
  $anchor=Rows 'coincident_pressure_anchor.csv' 256;$anchorIDs=@{};$bareDouble=0;$bareFloat=0
  foreach($r in $anchor){
    Finite $r @('bits_exact');$id=N $r.id
    if($id -ne [int]$id -or $id -lt 0 -or $id -ge 256 -or $anchorIDs.ContainsKey([int]$id)){throw 'Anchor fixed ID attribution failed'};$anchorIDs[[int]$id]=$true
    $actual=N $r.actual_pressure;$nearest=N $r.nearest_native_float;$bare=N $r.bare_intercept_counterfactual;$bareResidual=[Math]::Abs($bare-$nearest);$budget=N $r.original_float_pressure_budget;$bf=N $r.bare_float_write;$different=(FloatBits $bf) -ne (FloatBits $nearest)
    if($r.bits_exact -cne 'true' -or (N $r.nearest_distance_m) -ne 0 -or $actual -ne $nearest -or (FloatBits $actual) -ne (FloatBits $nearest) -or $bf -ne [double]([single]$bare) -or $budget -ne $anchorBudget[[int]$id] -or (N $r.bare_error) -ne $bareResidual -or !(Close (N $r.bare_error_over_budget) ($bareResidual/$budget)) -or $r.bare_float_bits_differ -cne $(if($different){'1'}else{'0'})){throw 'Coincident native-float anchor/counterfactual write proof failed'}
    if($bareResidual -gt 0){$bareDouble++};if($different){$bareFloat++}
  }
  if($bareDouble -eq 0 -or $bareFloat -eq 0){throw 'Bare-intercept actual float-write counterfactual is empty'}
  $owners=Rows 'owners.csv' 2;$ownerCases=@{};$ownerPerm=0
  foreach($r in $owners){
    Finite $r @('case','all_C_Ace_theta_rate_owners_exact')
    if($r.case -notin 'constant','smooth' -or $ownerCases.ContainsKey($r.case) -or (N $r.np) -ne (N $done.actual_np) -or (N $r.npb) -ne (N $done.actual_nonzero_Npb) -or (N $r.npbok) -ne (N $done.actual_NpbOk) -or $r.normal_soil -cne '1024' -or $r.normal_fixed -cne '256' -or (N $r.fluid_periodic) -ne (N $done.fluid_periodic_slots) -or (N $r.wall_periodic) -ne (N $done.wall_periodic_slots) -or $r.all_C_Ace_theta_rate_owners_exact -cne 'true'){throw 'Actual true-prefix/periodic owner closure failed'}
    $ownerCases[$r.case]=$true;$ownerPerm=[Math]::Max($ownerPerm,(N $r.permuted_owner_slots))
  }
  if($ownerPerm -ne (N $done.permuted_owner_slots_observed)){throw 'Observed owner permutation summary differs'}
  $rates=Rows 'rates.csv' 2048;$maxRate=0.;$maxRatio=0.;$caseIDs=@{constant=@{};smooth=@{}};$wallWitness=@{constant=0;smooth=0};$periodicWallWitness=@{constant=0;smooth=0}
  foreach($r in $rates){
    Finite $r @('case');if($r.case -notin 'constant','smooth'){throw 'Unknown complete-rate case'};$id=N $r.id;$slot=N $r.slot
    if($id -ne [int]$id -or $id -lt 256 -or $id -ge 1280 -or $slot -ne [int]$slot -or $slot -lt (N $done.actual_nonzero_Npb) -or $slot -ge (N $done.actual_np) -or $caseIDs[$r.case].ContainsKey([int]$id)){throw 'Actual normal-fluid typed ID/slot attribution failed'};$caseIDs[$r.case][[int]$id]=$true
    $a=N $r.actual;$b=N $r.reference;$budget=N $r.budget;$e=[Math]::Abs($a-$b);$ratio=N $r.error_over_budget
    if($a -eq 1234567 -or $budget -le 0 -or $e -gt $budget -or (N $r.error) -ne $e -or $ratio -lt 0 -or $ratio -gt 1 -or !(Close $ratio ($e/$budget)) -or (N $r.wall_neighbors) -lt 0 -or (N $r.periodic_wall_neighbors) -lt 0){throw 'Original complete-rate finite/overwrite/budget gate failed'}
    $maxRate=[Math]::Max($maxRate,$e);$maxRatio=[Math]::Max($maxRatio,$ratio)
    if((N $r.wall_neighbors) -gt 0){$wallWitness[$r.case]++};if((N $r.periodic_wall_neighbors) -gt 0){$periodicWallWitness[$r.case]++}
  }
  foreach($c in 'constant','smooth'){if($caseIDs[$c].Count -ne 1024 -or $wallWitness[$c] -eq 0 -or $periodicWallWitness[$c] -eq 0){throw 'True wall/periodic-wall complete-rate support is empty'}}
  if(!(Close $maxRate (N $done.max_actual_rate_reference_error_Pa_s)) -or !(Close $maxRatio (N $done.max_rate_error_over_original_budget))){throw 'Complete-rate maxima differ from all2048 rows'}
  $negative=Rows 'negative_rates.csv' 3;$negativeNames=@{}
  foreach($r in $negative){Finite $r @('case');if($r.case -notin 'zero_wall_C','zero_wall_Ace','copy_instead_of_reflect_wall_Ace' -or $negativeNames.ContainsKey($r.case) -or (N $r.native_changed) -le 0 -or (N $r.native_changed) -gt 1024 -or (N $r.max_rate_change_Pa_s) -le 0 -or (N $r.max_change_over_combined_original_budget) -le 1 -or (N $r.max_bad_actual_reference_error_Pa_s) -lt 0){throw 'Wrong-wall conditional-rate counterfactual is empty'};$negativeNames[$r.case]=$true}
  $forceRates=Rows 'force_rates.csv' 1024;$forceIDs=@{};$maxForceRateRatio=0.;$forceWall=0
  foreach($r in $forceRates){
    Finite $r;$id=N $r.id;$slot=N $r.slot;$a=N $r.actual;$b=N $r.reference;$budget=N $r.budget;$e=[Math]::Abs($a-$b);$ratio=N $r.error_over_budget
    if($id -ne [int]$id -or $id -lt 256 -or $id -ge 1280 -or $forceIDs.ContainsKey([int]$id) -or $slot -ne [int]$slot -or $slot -lt (N $done.actual_nonzero_Npb) -or $slot -ge (N $done.actual_np) -or $a -eq 1234567 -or $budget -le 0 -or $e -gt $budget -or (N $r.error) -ne $e -or $ratio -lt 0 -or $ratio -gt 1 -or !(Close $ratio ($e/$budget))){throw 'Actual full-force complete rate/typed native IDs failed'}
    $forceIDs[[int]$id]=$true;$maxForceRateRatio=[Math]::Max($maxForceRateRatio,$ratio);if((N $r.wall_neighbors) -gt 0){$forceWall++}
  }
  if($forceWall -eq 0){throw 'Full-force wall-neighbor reference empty'}
  $faces=Rows 'face_force.csv' 2;$planes=@{};$maxQ=0.;$maxV=0.;$maxBad0=0.;$maxBadCopy=0.;$maxReaction=0.
  $cu=[Math]::Sqrt((89478488.+4.*134217728./3.+67108864./.25)/2048.);$wave=2*[Math]::PI/.125;$kh=[double]([single]0.0001);$pstar=67108864./.25*$A/$cu;$qstar=$kh/(1000.*9.80665)*($wave*$pstar+1000.*$A*$cu*$wave)
  foreach($r in $faces){
    Finite $r;$plane=N $r.plane_x;if($plane -notin 0.,.0625 -or $planes.ContainsKey([string]$plane)){throw 'Physical face location missing/duplicated'};$planes[[string]$plane]=$true
    $bv=N $r.vn_bound;$bq=N $r.qn_bound;$fb=N $r.force_bound;$residual=[Math]::Sqrt([Math]::Pow((N $r.fluid_force_x)+(N $r.wall_reaction_x),2)+[Math]::Pow((N $r.fluid_force_z)+(N $r.wall_reaction_z),2))
    if((N $r.condition) -lt 1 -or (N $r.neighbors) -le 6 -or $bv -le 0 -or $bv -ge .01*$A -or $bq -le 0 -or $bq -ge .01*$qstar -or [Math]::Abs((N $r.vn)) -gt $bv -or [Math]::Abs((N $r.qn)) -gt $bq -or $fb -le 0 -or (N $r.force_residual) -gt $fb -or !(Close (N $r.force_residual) $residual) -or !(Close (N $r.wrong_zero_over_bound) ([Math]::Abs((N $r.wrong_zero_wall_Ace_qn))/$bq)) -or !(Close (N $r.wrong_copy_over_bound) ([Math]::Abs((N $r.wrong_copy_wall_Ace_qn))/$bq))){throw 'Original physical-plane flux/velocity or wall reaction budget failed'}
    $maxQ=[Math]::Max($maxQ,[Math]::Abs((N $r.qn))/$bq);$maxV=[Math]::Max($maxV,[Math]::Abs((N $r.vn))/$bv);$maxReaction=[Math]::Max($maxReaction,(N $r.force_residual)/$fb);$maxBad0=[Math]::Max($maxBad0,(N $r.wrong_zero_over_bound));$maxBadCopy=[Math]::Max($maxBadCopy,(N $r.wrong_copy_over_bound))
  }
  if($maxBad0 -le 1 -or $maxBadCopy -le 1 -or !(Close $maxQ (N $done.max_face_qn_over_original_budget)) -or !(Close $maxV (N $done.max_face_vn_over_original_budget)) -or !(Close $maxReaction (N $done.force_reaction_over_original_budget)) -or !(Close $maxBad0 (N $done.max_wrong_zero_face_qn_over_budget)) -or !(Close $maxBadCopy (N $done.max_wrong_copy_face_qn_over_budget))){throw 'Physical-plane summary or wrong-Ace negative nonemptiness failed'}
  if(@(Get-ChildItem -LiteralPath $runOut -Recurse -File|Where-Object {$_.Extension -eq '.bi4'}).Count){throw 'Unexpected PART serialization in0step component'}
  VerifyAll;V $run.files;V @($owned.program,$owned.target_program,$owned.log)
  Save $checkPath ([ordered]@{passed=$true;stage='upl_gpu_wall_component_r1';configuration=$Configuration;mode=$Mode;helper=(E $helperPath);source_build=(E $gpuPath);input=(E $preparedPath);selected_seed_XML=$seedXml;selected_seed_BI4=$seedBi4;h_seed_is_initialization_not_half_validation=$true;inputs=$inputs;source_run=(E $runPath);call=(E $callPath);completion=(E $completion);files=@(Files);earlier_gates=$prior;counts=$counts;CSV_rows_recomputed=3847;affine_rows=512;coincident_anchor_rows=256;complete_rate_rows=2048;owner_rows=2;negative_rows=3;physical_face_rows=2;full_force_rate_rows=1024;max_affine_error_over_original_budget=$maxAffine;bare_intercept_double_difference_rows=$bareDouble;bare_intercept_float_write_difference_rows=$bareFloat;max_rate_error_over_original_budget=$maxRatio;max_full_force_rate_error_over_original_budget=$maxForceRateRatio;max_physical_face_flux_over_original_budget=$maxQ;max_physical_face_velocity_over_original_budget=$maxV;force_reaction_over_original_budget=$maxReaction;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;completed_physical_steps=0;actual_ComputeStep_Sym_called=$false;public_GPU_dynamic_accepted=$false;general_wall_or_boundary_accepted=$false;physical_acceptance=$false})
}catch{
  if(!(Test-Path -LiteralPath $checkPath)){Save $checkPath ([ordered]@{passed=$false;stage='upl_gpu_wall_component_r1';mode=$Mode;configuration=$Configuration;failure=$_.Exception.Message;helper=(E $helperPath);source_build=(E $gpuPath);inputs=$inputs;source_run=(E $runPath);call=(E $callPath);completion=$(if(Test-Path -LiteralPath $completion){E $completion}else{$null});files=@(Files);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;completed_physical_steps_claimed=$false;physical_acceptance=$false})};throw
}
