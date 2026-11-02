param([Parameter(Mandatory=$true)][ValidateSet('constant_smoke','variable_smoke','constant_coarse','constant_half','variable_coarse','variable_half')][string]$Job,[switch]$ExecutionAuthorized)
# One independent saved-endpoint force audit only; never an integrator or automatic next job.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $t 'logs'
$model,$window=$Job.Split('_');$cfg=if($window-eq'smoke'){'Debug'}else{'Release'};$name='upl_gpu_gravity_endpoint_'+$Job+'_r1';$folder=Join-Path $t ('outputs\'+$name)
$note=Join-Path $t 'notes\upl_gpu_gravity_endpoint_runs_r1.json';$record=Join-Path $logs ($name+'.check.json');$callPath=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes-ne[long]$r.bytes-or$a.sha256-cne$r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained path protected: $p"}}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Need([string]$p){$v=J $p;if(!$v.passed-or$v.physical_acceptance){throw "Prior audit rejected: $p"};E $p}
if(!$ExecutionAuthorized){throw 'Root full recipe review and explicit one-audit authorization required'}
Fresh @($folder,$record,$callPath,$log)
$hp=Join-Path $logs ('upl_gpu_gravity_endpoint_'+$cfg+'_r1.helper.json');$h=J $hp;$bp=$h.source_build.path;$b=J $bp;$s=J $b.source_freeze.path
if($h.status-ne'actual_authoritative_GPU_objects_helper_linked_not_run'-or$h.fixture-ne'GravityPeriodicEndpoint'-or$h.configuration-ne$cfg-or!$h.exact_link_closure_verified-or$h.link_object_count-ne111-or@($b.objects).Count-ne110-or@($s.source).Count-ne265){throw 'Current endpoint helper and authoritative source/object closure required'}
$sp=Join-Path $logs ('upl_gpu_gravity_'+$Job+'_r1.check.json');$single=J $sp;$rp=$single.source_run.path;$run=J $rp;$owned=J $run.call.path;$done=J $run.actual_completion.path
if(!$single.passed-or$single.native_count-ne512-or$single.job-ne$Job-or!$owned.owned_call_exited-or$owned.exit_code-isnot[int]-or$owned.exit_code-ne0-or!$done.actual_production_Run-or!$done.passed-or$done.model-ne$model-or$done.window-ne$window){throw 'Completed sealed source solve required; never rerun it for analysis'}
$pp=Join-Path $logs 'upl_gpu_gravity_periodic_peer_r1.check.json';$peer=J $pp;if(!$peer.passed-or$peer.endpoint_force_audit_performed-or$peer.physical_acceptance){throw 'Passed bounded periodic review required'}
$seedName=if($window-eq'smoke'){'DebugCPU_smoke'}elseif($window-eq'coarse'){'ReleaseCPU_c'}else{'ReleaseCPU_h'};$seedp=Join-Path $logs ('upl_gravity_periodic_cpu_'+$seedName+'_r1.preflight.json');$seed=J $seedp
$xml=@($seed.inputs|Where-Object {$_.path.EndsWith('.xml')});$bi=@($seed.inputs|Where-Object {$_.path.EndsWith('.bi4')});if(!$seed.passed-or$xml.Count-ne1-or$bi.Count-ne1-or@($seed.inputs).Count-ne2){throw 'Exact retained XML/BI4 required'};$prefix=$xml[0].path.Substring(0,$xml[0].path.Length-4)
$prior=@();if($window-ne'smoke'){$prior+=Need (Join-Path $logs ('upl_gpu_gravity_endpoint_'+$model+'_smoke_r1.check.json'))};if($window-eq'half'){$prior+=Need (Join-Path $logs ('upl_gpu_gravity_endpoint_'+$model+'_coarse_r1.check.json'))}
$inputs=@(E $PSCommandPath;E $note;E $hp;E $bp;E $sp;E $rp;E $pp;E $seedp)+@($seed.inputs)+$prior
function Verify{
 V $inputs;V @($b.source_freeze,$h.program,$h.compile_call,$h.link_call,$run.call,$run.actual_completion);V $h.inputs;V $h.author_files;V $h.transitive_author_include_files;V $h.objects;V $h.tools;V $h.libraries;V $s.source;V $s.canonical_GPU_six_and_CPU_two;V $run.files;V $single.files
 foreach($r in $h.runtime){V @($r.original,$r.copy)}
}
Verify
$active=@(Get-CimInstance Win32_Process|Where-Object {$_.Name-like'DualSPHysics*'-or$_.Name-in@('upl_gpu_gravity_endpoint_r1.exe','upl_gravity_periodic_gpu_r1.exe','compute-sanitizer.exe')});if($active.Count){throw 'Existing native compute process; do not duplicate'}
$dt=if($window-eq'half'){'2.98023223876953125e-8'}else{'5.9604644775390625e-8'};$data=Join-Path (Split-Path -Parent $run.actual_completion.path) 'data'
$argv=@('--audit',$model,$window,$data,$dt,$xml[0].path,'--','-gpu:0','-stable',$prefix,$folder,'-dirdataout','data','-svres');$tool=$h.program;$callArgs=$argv;$mem=$window-eq'smoke';$memReceipt=$null
if($mem){$memReceipt=E (Join-Path $logs 'upl_gpu_perm_component_Debug_r1.call.json');$m=J $memReceipt.path;if(!$m.owned_call_exited-or$m.exit_code-ne0-or!$m.memcheck_zero_errors_and_leaks){throw 'Owned prior sanitizer identity required'};$tool=$m.program;V @($tool);$callArgs=@('--tool','memcheck','--leak-check','full','--error-exitcode','97',$h.program.path)+$argv}
[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
Push-Location (Join-Path $repo 'src');try{$global:LASTEXITCODE=$null;& $tool.path @callArgs 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$failure=[string]$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
$text=[IO.File]::ReadAllText($log);$zero=$mem-and$text-match'ERROR SUMMARY:\s*0 errors'-and$text-match'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'
V @($tool,$h.program);Save $callPath ([ordered]@{program=$tool;target_program=$h.program;arguments=$callArgs;working_directory=(Join-Path $repo 'src');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code-is[int]);owned_call_exited=($code-is[int]);exit_code=$code;invocation_failure=$failure;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;memcheck_tool_source=$memReceipt;physical_steps_advanced=0;physical_acceptance=$false})
$files=@();if(Test-Path -LiteralPath $folder){$files=@(Get-ChildItem -LiteralPath $folder -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})};$complete=$null;$d=$null;if(Test-Path -LiteralPath (Join-Path $folder 'completion.json')){$complete=E (Join-Path $folder 'completion.json');$d=J $complete.path}
$samples=if($mem){3}else{257};$pass=$code-is[int]-and$code-eq0-and!$failure-and(!$mem-or$zero)-and$d-and$d.passed-and$d.samples-eq$samples-and$d.native_count-eq512-and$d.model-eq$model-and$d.window-eq$window-and$d.actual_endpoint_force_calls-eq$samples-and$d.rate_rows-eq(512*$samples)-and$d.native33_rollback_frames-eq$samples-and$d.periodic_ghost_checks-gt0-and!$d.Run_or_ComputeStep_called-and$d.completed_physical_steps-eq0-and!$d.physical_acceptance
Verify
Save $record ([ordered]@{passed=[bool]$pass;job=$Job;configuration=$cfg;source_solve=(E $rp);source_single_check=(E $sp);source_build=(E $bp);helper=(E $hp);inputs=$inputs;call=(E $callPath);completion=$complete;files=$files;actual_endpoint_force_calls=if($d){$d.actual_endpoint_force_calls}else{0};physical_steps_advanced=0;source_saved_theta_is_original_force_observation=$false;old_solver_rerun=$false;source_outputs_unchanged=$true;wall_gravity_accepted=$false;public_nonzero_gravity_accepted=$false;physical_acceptance=$false})
if(!$pass){throw 'Saved-endpoint diagnostic rejected; preserve this label and all completed solver data'}
