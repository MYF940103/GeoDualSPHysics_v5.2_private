param([switch]$ExecutionAuthorized)
# One new endpoint audit on retained half data. No physical solver, build or automatic A review.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $t 'logs'
$name='upl_gpu_gravity_endpoint_variable_half_r2';$folder=Join-Path $t ('outputs\'+$name);$record=Join-Path $logs ($name+'.check.json');$callPath=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes-ne[long]$r.bytes-or$a.sha256-cne$r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained path protected: $p"}}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Need([string]$p){$v=J $p;if(!$v.passed-or$v.physical_acceptance){throw "Prior audit rejected: $p"};E $p}
if(!$ExecutionAuthorized){throw 'Root full review and explicit one-half-endpoint authorization required'}
Fresh @($folder,$record,$callPath,$log)
$gate=E (Join-Path $t 'notes\upl_gpu_gravity_gate_components_r2.json');$g=J $gate.path;if($g.thresholds_relaxed-or$g.physical_acceptance-or$g.public_gravity_accepted-or$g.wall_trajectory_accepted){throw 'Versioned bounded A/B split required'}
$ap=Need (Join-Path $logs 'upl_gpu_gravity_component_A_coarse_r2.check.json');$a=J $ap.path
if($a.component-ne'A'-or$a.window-ne'coarse'-or$a.original_combined_passed-ne$false-or$a.original_owned_endpoint_exit-ne1-or!$a.only_exact_terminal_signal_failure_accepted_for_A-or$a.original_combined_failure_overridden){throw 'Coarse A only, with historical combined false/owned1 preserved, required'}
$bppeer=Need (Join-Path $logs 'upl_gpu_gravity_witness_peer_r1.check.json');$witness=J $bppeer.path
if($witness.coverage.fresh_jobs-ne4-or!$witness.coverage.all_native_owned_typed_exits_zero-or$witness.preserved_failure.failure_overridden){throw 'Independent four-job actual B peer required'}
$retired=E (Join-Path $logs 'upl_gpu_gravity_endpoint_variable_coarse_r1.check.json');$old=J $retired.path;if($old.passed-ne$false-or$old.completion){throw 'Original combined coarse rejection must remain false'}
$hp=Join-Path $logs 'upl_gpu_gravity_endpoint_Release_r1.helper.json';$h=J $hp;$b=J $h.source_build.path;$s=J $b.source_freeze.path
if($h.status-ne'actual_authoritative_GPU_objects_helper_linked_not_run'-or$h.fixture-ne'GravityPeriodicEndpoint'-or$h.configuration-ne'Release'-or!$h.exact_link_closure_verified-or$h.link_object_count-ne111-or@($h.objects).Count-ne110-or@($s.source).Count-ne265){throw 'Frozen original Release endpoint helper/current closure required'}
$sp=Join-Path $logs 'upl_gpu_gravity_variable_half_r1.check.json';$single=J $sp;$rp=$single.source_run.path;$run=J $rp;$owned=J $run.call.path;$done=J $run.actual_completion.path
if(!$single.passed-or$single.native_count-ne512-or$single.job-ne'variable_half'-or!$owned.owned_call_exited-or$owned.exit_code-isnot[int]-or$owned.exit_code-ne0-or!$done.passed-or!$done.actual_production_Run-or$done.model-ne'variable'-or$done.window-ne'half'){throw 'Completed sealed physical half source required; never rerun it'}
$pp=Need (Join-Path $logs 'upl_gpu_gravity_periodic_peer_r1.check.json');$seedp=Join-Path $logs 'upl_gravity_periodic_cpu_ReleaseCPU_h_r1.preflight.json';$seed=J $seedp
$xml=@($seed.inputs|Where-Object {$_.path.EndsWith('.xml')});$bi=@($seed.inputs|Where-Object {$_.path.EndsWith('.bi4')});if(!$seed.passed-or$xml.Count-ne1-or$bi.Count-ne1-or@($seed.inputs).Count-ne2){throw 'Exact retained half XML/initial BI4 required'};$prefix=$xml[0].path.Substring(0,$xml[0].path.Length-4)
$smoke=Need (Join-Path $logs 'upl_gpu_gravity_endpoint_variable_smoke_r1.check.json')
$inputs=@(E $PSCommandPath;E (Join-Path $t 'notes\upl_gpu_gravity_endpoint_variable_half_r2.json');E $hp;$h.source_build;E $sp;E $rp;$pp;E $seedp;$gate;$ap;$bppeer;$retired;$smoke)+@($seed.inputs)
function Verify{
 V $inputs;V $a.files;V $witness.inputs;V $witness.current_production_targets;V @($b.source_freeze,$h.program,$h.compile_call,$h.link_call,$run.call,$run.actual_completion)
 V $h.inputs;V $h.author_files;V $h.transitive_author_include_files;V $h.objects;V $h.tools;V $h.libraries;V $s.source;V $s.canonical_GPU_six_and_CPU_two;V $run.files;V $single.files
 foreach($r in $h.runtime){V @($r.original,$r.copy)}
}
Verify
$active=@(Get-CimInstance Win32_Process|Where-Object {$_.Name-like'DualSPHysics*'-or$_.Name-in@('upl_gpu_gravity_endpoint_r1.exe','upl_gravity_periodic_gpu_r1.exe','compute-sanitizer.exe')});if($active.Count){throw 'Existing native compute process; do not duplicate'}
$data=Join-Path (Split-Path -Parent $run.actual_completion.path) 'data';$argv=@('--audit','variable','half',$data,'2.98023223876953125e-8',$xml[0].path,'--','-gpu:0','-stable',$prefix,$folder,'-dirdataout','data','-svres');$tool=$h.program
[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
Push-Location (Join-Path $repo 'src');try{$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$failure=[string]$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
V @($tool);Save $callPath ([ordered]@{program=$tool;target_program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code-is[int]);owned_call_exited=($code-is[int]);exit_code=$code;invocation_failure=$failure;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);memcheck_executed=$false;physical_steps_advanced=0;physical_acceptance=$false})
$files=@();if(Test-Path -LiteralPath $folder){$files=@(Get-ChildItem -LiteralPath $folder -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})};$complete=$null;$d=$null;if(Test-Path -LiteralPath (Join-Path $folder 'completion.json')){$complete=E (Join-Path $folder 'completion.json');$d=J $complete.path}
$pass=$code-is[int]-and$code-eq0-and!$failure-and$d-and$d.passed-and$d.samples-eq257-and$d.native_count-eq512-and$d.model-eq'variable'-and$d.window-eq'half'-and$d.actual_endpoint_force_calls-eq257-and$d.rate_rows-eq131584-and$d.native33_rollback_frames-eq257-and$d.periodic_ghost_checks-gt0-and!$d.Run_or_ComputeStep_called-and$d.completed_physical_steps-eq0-and!$d.physical_acceptance
Verify
Save $record ([ordered]@{passed=[bool]$pass;job='variable_half';configuration='Release';source_solve=(E $rp);source_single_check=(E $sp);source_build=$h.source_build;helper=(E $hp);inputs=$inputs;call=(E $callPath);completion=$complete;files=$files;actual_endpoint_force_calls=if($d){$d.actual_endpoint_force_calls}else{$null};component_A_evaluated=$false;component_A_coarse=$ap;component_B_peer=$bppeer;split_gate_decision=$gate;original_coarse_combined_passed=$false;original_coarse_failure_overridden=$false;physical_steps_advanced=0;source_saved_theta_is_original_force_observation=$false;old_solver_rerun=$false;source_outputs_unchanged=$true;wall_gravity_accepted=$false;public_nonzero_gravity_accepted=$false;physical_acceptance=$false})
if(!$pass){throw 'Original combined half endpoint rejected; preserve it. Only separate offline A may evaluate an exact terminal-signal failure.'}
