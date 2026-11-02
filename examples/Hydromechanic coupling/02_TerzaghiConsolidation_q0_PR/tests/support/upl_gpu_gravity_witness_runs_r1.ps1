param([Parameter(Mandatory=$true)][ValidateSet('constant_debug','variable_debug','constant_release','variable_release')][string]$Job)
# One prescribed-J static GPU operator call; never Run, ComputeStep or a PART restart.
$ErrorActionPreference='Stop'
$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$model,$mode=$Job.Split('_');$cfg=if($mode-eq'debug'){'Debug'}else{'Release'}
$name='upl_gpu_gravity_witness_'+$Job+'_r1';$logs=Join-Path $t 'logs';$folder=Join-Path $t ('outputs\'+$name)
$record=Join-Path $logs ($name+'.check.json');$callPath=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes-ne$r.bytes-or$a.sha256-cne$r.sha256){throw "Changed frozen file: $($r.path)"}}}
function Save($p,$v){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
foreach($p in @($folder,$record,$callPath,$log)){if(Test-Path -LiteralPath $p){throw "Fresh label required: $p"}}
$hp=Join-Path $logs ('upl_gpu_gravity_witness_'+$cfg+'_r1.helper.json');$h=J $hp
if($h.status-ne'static_operator_witness_linked_not_run'-or$h.configuration-ne$cfg-or$h.link_object_count-ne111){throw 'Frozen witness build required'}
$b=J $h.source_build.path;$s=J $h.source_freeze.path
$seedp=Join-Path $logs 'upl_gravity_periodic_cpu_ReleaseCPU_c_r1.preflight.json';$seed=J $seedp
$xml=@($seed.inputs|Where-Object {$_.path.EndsWith('.xml')});$bi=@($seed.inputs|Where-Object {$_.path.EndsWith('.bi4')})
if(!$seed.passed-or$xml.Count-ne1-or$bi.Count-ne1){throw 'Unchanged retained geometry/runtime seed required'}
$prior=@()
$need=@();if($Job-eq'variable_debug'){$need+='constant_debug'}elseif($mode-eq'release'){$need+=@('constant_debug','variable_debug');if($model-eq'variable'){$need+='constant_release'}}
foreach($p in $need){$path=Join-Path $logs ('upl_gpu_gravity_witness_'+$p+'_r1.check.json');$v=J $path;if(!$v.passed-or$v.physical_acceptance){throw "Prior component rejected: $p"};V @($v.call,$v.completion);V $v.files;$prior+=E $path}
$inputs=@(E $PSCommandPath;E (Join-Path $t 'notes\upl_gpu_gravity_witness_runs_r1.json');E $hp;E $seedp)+@($seed.inputs)+$prior
function Verify{V $inputs;V $h.inputs;V $h.author_files;V $s.source;V $s.canonical_GPU_six_and_CPU_two;V $h.objects;V $h.tools;V $h.libraries;V @($h.source_build,$h.source_freeze,$h.program,$h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}}
Verify
$active=@(Get-CimInstance Win32_Process|Where-Object {$_.Name-like'DualSPHysics*'-or$_.Name-in@('upl_gpu_gravity_witness_r1.exe','compute-sanitizer.exe')})
if($active.Count){throw 'Existing native compute process; do not duplicate'}
$prefix=$xml[0].path.Substring(0,$xml[0].path.Length-4)
$argv=@('--audit',$model,'--','-gpu:0','-stable',$prefix,$folder,'-dirdataout','data','-svres')
$tool=$h.program;$callArgs=$argv;$mem=$mode-eq'debug';$memSource=$null
if($mem){$memSource=E (Join-Path $logs 'upl_gpu_perm_component_Debug_r1.call.json');$m=J $memSource.path;if(!$m.owned_call_exited-or$m.exit_code-ne0-or!$m.memcheck_zero_errors_and_leaks){throw 'Prior sanitizer identity missing'};$tool=$m.program;V @($tool);$callArgs=@('--tool','memcheck','--leak-check','full','--error-exitcode','97',$h.program.path)+$argv}
[IO.File]::WriteAllBytes($log,[byte[]]@())
$start=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
Push-Location (Join-Path $repo 'src')
try{$global:LASTEXITCODE=$null;& $tool.path @callArgs 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$failure=[string]$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
$text=Get-Content -LiteralPath $log -Raw
$zero=$mem-and$text-match'ERROR SUMMARY:\s*0 errors'-and$text-match'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'
Save $callPath ([ordered]@{program=$tool;target_program=$h.program;arguments=$callArgs;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');owned_call_exited=($code-is[int]);typed_LASTEXITCODE_captured_immediately=($code-is[int]);exit_code=$code;invocation_failure=$failure;log=(E $log);memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;memcheck_tool_source=$memSource;physical_steps_advanced=0;physical_acceptance=$false})
$files=@();if(Test-Path -LiteralPath $folder){$files=@(Get-ChildItem -LiteralPath $folder -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})}
$done=$null;$completion=$null;if(Test-Path -LiteralPath (Join-Path $folder 'completion.json')){$completion=E (Join-Path $folder 'completion.json');$done=J $completion.path}
$pass=$code-is[int]-and$code-eq0-and!$failure-and(!$mem-or$zero)-and$done-and$done.passed-and$done.model-eq$model-and$done.native_count-eq512-and$done.actual_endpoint_force_calls-eq1-and$done.actual_negative_complete_rate_calls-eq2-and$done.physical_steps_advanced-eq0-and!$done.physical_acceptance
Verify
Save $record ([ordered]@{passed=[bool]$pass;job=$Job;inputs=$inputs;build=(E $hp);call=(E $callPath);completion=$completion;files=$files;prescribed_J_operator_only=$true;physical_trajectory_solved=$false;old_variable_coarse_rejection_overridden=$false;public_gravity_accepted=$false;wall_gravity_accepted=$false;physical_acceptance=$false})
if(!$pass){throw 'Static witness rejected; preserve outputs and original gates'}
