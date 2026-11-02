param([Parameter(Mandatory=$true)][ValidateSet('wall_zero','wall_tangent','wall_normal','wall_gy','wall_nan','wall_tiny','observer_zero','observer_gravity')][string]$Case,[ValidateSet('Debug','Release')][string]$Configuration='Release')
# One fresh initialization-only guard probe; no Run, force, ComputeStep or PART restart.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $t 'logs'
$name='upl_gpu_gravity_init_'+$Configuration+'_'+$Case+'_r1';$out=Join-Path $t ('outputs\'+$name);$record=Join-Path $logs ($name+'.check.json');$callPath=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes-ne$r.bytes-or$a.sha256-cne$r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function Save($p,$v){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
foreach($p in @($out,$record,$callPath,$log)){if(Test-Path -LiteralPath $p){throw "Fresh output required: $p"}}
if($Configuration-eq'Debug'-and$Case-notin@('wall_zero','wall_tiny','observer_gravity')){throw 'Debug memcheck matrix is limited to three reviewed representative paths'}
$hp=Join-Path $logs ('upl_gpu_gravity_init_probe_'+$Configuration+'_r1.helper.json');$h=J $hp;$s=J $h.source_freeze.path
if($h.status-ne'init_guard_probe_linked_not_run'-or$h.fixture-ne'GravityInitProbe'-or$h.configuration-ne$Configuration-or$h.link_object_count-ne111){throw 'Exact frozen Init probe build required'}
$wall=$Case.StartsWith('wall_');$seedp=Join-Path $logs $(if($wall){'upl_gravity_wall_cpu_DebugCPU_constant_smoke_r1.run.json'}else{'upl_gravity_periodic_cpu_ReleaseCPU_c_r1.preflight.json'});$seed=J $seedp
if(!$seed.passed-or($wall-and!$seed.owned_solver_exit0)){throw 'Retained seed provenance rejected'}
$xml=@($seed.inputs|Where-Object {$_.path.EndsWith('.xml')});$bi=@($seed.inputs|Where-Object {$_.path.EndsWith('.bi4')})
if($xml.Count-ne1-or$bi.Count-ne1){throw 'One exact retained XML/BI4 pair required'}
$expectedPrefix=Join-Path $t $(if($wall){'outputs\upl_gravity_wall_seed_r1\CaseGravityWall_constant_smoke'}else{'outputs\upl_gravity_periodic_seed_r1\CaseGravity_c'})
if($xml[0].path-ine($expectedPrefix+'.xml')-or$bi[0].path-ine($expectedPrefix+'.bi4')){throw 'Seed prefix differs'}
$prior=@();$wp=Join-Path $logs 'upl_gpu_gravity_witness_peer_r1.check.json';$w=J $wp;if(!$w.passed-or$w.physical_acceptance){throw 'Reviewed independent operator witness required'};$prior+=E $wp
if($Configuration-eq'Release'){
 foreach($c in @('wall_zero','wall_tiny','observer_gravity')){$p=Join-Path $logs ('upl_gpu_gravity_init_Debug_'+$c+'_r1.check.json');$q=J $p;if(!$q.passed-or$q.physical_acceptance){throw 'All three Debug representative probes required'};V @($q.call,$q.completion);V $q.files;$prior+=E $p}
}
$inputs=@(E $PSCommandPath;E (Join-Path $t 'notes\upl_gpu_gravity_init_probe_runs_r1.json');E $hp;E $seedp)+@($xml[0],$bi[0])+$prior
function Verify{V $inputs;V $h.inputs;V $h.author_files;V $s.source;V $s.canonical_GPU_six_and_CPU_two;V $h.objects;V $h.tools;V $h.libraries;V @($h.program,$h.source_build,$h.source_freeze,$h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}}
Verify
$active=@(Get-CimInstance Win32_Process|Where-Object {$_.Name-like'DualSPHysics*'-or$_.Name-in@('upl_gpu_gravity_init_probe_r1.exe','compute-sanitizer.exe')});if($active.Count){throw 'Existing native compute process; do not duplicate'}
$argv=@('--probe',$Case,'--','-gpu:0','-stable');if($wall){$argv+='-mdbc_freeslip'};$argv+=@($expectedPrefix,$out,'-dirdataout','data','-svres')
$tool=$h.program;$callArgs=$argv;$mem=$Configuration-eq'Debug';$memSource=$null
if($mem){$memSource=E (Join-Path $logs 'upl_gpu_perm_component_Debug_r1.call.json');$m=J $memSource.path;if(!$m.owned_call_exited-or$m.exit_code-ne0-or!$m.memcheck_zero_errors_and_leaks){throw 'Original successful sanitizer identity required'};$tool=$m.program;V @($tool);$callArgs=@('--tool','memcheck','--leak-check','full','--error-exitcode','97',$h.program.path)+$argv}
[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
Push-Location (Join-Path $repo 'src')
try{$global:LASTEXITCODE=$null;& $tool.path @callArgs 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$failure=[string]$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
$text=Get-Content -LiteralPath $log -Raw;$zero=$mem-and$text-match'ERROR SUMMARY:\s*0 errors'-and$text-match'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'
Save $callPath ([ordered]@{program=$tool;target_program=$h.program;arguments=$callArgs;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');owned_call_exited=($code-is[int]);typed_LASTEXITCODE_captured_immediately=($code-is[int]);exit_code=$code;invocation_failure=$failure;log=(E $log);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;memcheck_tool_source=$memSource;physical_steps_advanced=0;physical_acceptance=$false})
$completion=$null;$done=$null;if(Test-Path -LiteralPath (Join-Path $out 'completion.json')){$completion=E (Join-Path $out 'completion.json');$done=J $completion.path}
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})}
$expectedCalls=if($Case-in@('wall_zero','observer_zero')){1}elseif($Case-eq'wall_tiny'){3}else{2};$reject=if($Case-in@('wall_normal','wall_gy','wall_nan','wall_tiny','observer_gravity')){1}else{0}
$pass=$code-is[int]-and$code-eq0-and!$failure-and(!$mem-or$zero)-and$done-and$done.passed-and$done.case-eq$Case-and$done.actual_full_initializations-eq1-and$done.actual_Init_guard_recheck_calls-eq$expectedCalls-and$done.expected_exact_method_message_rejections-eq$reject-and$done.physical_steps_advanced-eq0-and$done.actual_force_calls-eq0-and!$done.Run_or_ComputeStep_called-and!$done.physical_acceptance-and$done.all_guard_host_pointers_alive_and_restored-and$done.device_input_J_theta_bits_unchanged
Verify
Save $record ([ordered]@{passed=[bool]$pass;case=$Case;configuration=$Configuration;inputs=$inputs;build=(E $hp);call=(E $callPath);completion=$completion;files=$files;wall_trajectory_accepted=$false;public_gravity_accepted=$false;physical_acceptance=$false})
if(!$pass){throw 'Actual initialization probe rejected; preserve all evidence'}
