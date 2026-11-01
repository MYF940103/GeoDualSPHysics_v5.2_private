param([Parameter(Mandatory=$true)][ValidateSet('PrepareInput','RunTime')][string]$Mode,[ValidateSet('Debug','Release')][string]$Configuration='Debug',[ValidateSet('Scale','FirstCurrent','FirstRequested')][string]$Case='Scale',[switch]$ExecutionAuthorized)
# Explicit single actions only; no long solver, old worker, notifier, or Git mutation.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($e in $rows){$v=Entry $e.path;if($v.bytes -ne $e.bytes -or $v.sha256 -ine $e.sha256){throw "Changed binding: $($e.path)"}}}
function ReadJson([string]$p){Get-Content -Raw -Encoding UTF8 -LiteralPath $p | ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if(!$ExecutionAuthorized){throw 'Explicit root execution authorization required'}
$prepared=Join-Path $logs 'upl_gpu_k0_time_r1.inputs.json'
if($Mode -eq 'PrepareInput'){
  $oldPath=Join-Path $logs 'upl_gpu_observer_native_r1.inputs.json';$old=ReadJson $oldPath;$seed=@($old.jobs|Where-Object {$_.window -eq 'Smoke'});if($seed.Count -ne 1){throw 'One retained Smoke seed required'};Verify @($seed[0].xml,$seed[0].bi4)
  $folder=Join-Path $outputs 'upl_gpu_k0_time_seed_r1';if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $prepared)){throw 'Prepared input protected'}
  $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($seed[0].xml.path);$k=$doc.SelectNodes('//hydromechanics/HydraulicConductivity');if($k.Count -ne 1 -or $k[0].GetAttribute('value') -ne '0.0001'){throw 'Expected original k1e-4 runtime seed'};$k[0].SetAttribute('value','0')
  [void](New-Item -ItemType Directory -Path $folder);$prefix=Join-Path $folder 'CaseUplGpuK0Time';[IO.File]::WriteAllText($prefix+'.xml',$doc.OuterXml,(New-Object Text.UTF8Encoding($false)));Copy-Item -LiteralPath $seed[0].bi4.path -Destination ($prefix+'.bi4');$bi=Entry ($prefix+'.bi4');if($bi.sha256 -ine $seed[0].bi4.sha256){throw 'Native initial particle bytes changed'}
  Save $prepared ([ordered]@{status='k0_component_input_prepared_not_run';prefix=$prefix;native=512;inputs=@(Entry $PSCommandPath;Entry $oldPath;$seed[0].xml;$seed[0].bi4);xml=(Entry ($prefix+'.xml'));bi4=$bi;sole_runtime_parameter_change='HydraulicConductivity0.0001to0';native_initial_fields_rewritten=$false;public_GPU_dynamic_accepted=$false;physical_acceptance=$false});exit 0
}
$input=ReadJson $prepared;Verify $input.inputs;Verify @($input.xml,$input.bi4)
$cases=@('Scale','FirstCurrent','FirstRequested');$position=[array]::IndexOf($cases,$Case)
$prior=@();if($Configuration -eq 'Release'){$prior+=foreach($c in $cases){Join-Path $logs ('upl_gpu_k0_time_Debug_'+$c+'_r1.check.json')}}
if($position -gt 0){$prior+=foreach($c in $cases[0..($position-1)]){Join-Path $logs ('upl_gpu_k0_time_'+$Configuration+'_'+$c+'_r1.check.json')}}
foreach($p in $prior){$r=ReadJson $p;Verify @($r.completion,$r.call);Verify $r.files;if(!$r.passed -or $r.physical_acceptance){throw 'Earlier component gate rejected'}}
$helperPath=Join-Path $logs ('upl_gpu_k0_time_component_'+$Configuration+'_r1.helper.json');$h=ReadJson $helperPath
if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.configuration -ne $Configuration){throw 'Fresh source-bound time helper required'}
Verify $h.inputs;Verify @($h.program,$h.source_build);Verify $h.libraries;foreach($r in $h.runtime){Verify @($r.original,$r.copy)}
$g=ReadJson $h.source_build.path;Verify $g.inputs;Verify @($g.source_freeze,$g.isolated_GPU_program);Verify $g.objects
$name='upl_gpu_k0_time_'+$Configuration+'_'+$Case+'_r1';$out=Join-Path $outputs $name;$callPath=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log');$check=Join-Path $logs ($name+'.check.json')
foreach($p in @($out,$callPath,$log,$check)){if(Test-Path -LiteralPath $p){throw 'Retained component action protected'}}
$target=$h.program;$tool=$target;$args=@('--time',$Case,'-gpu:0',$input.prefix,$out,'-dirdataout','data','-svres');$mem=($Configuration -eq 'Debug')
if($mem){$oldCall=ReadJson (Join-Path $logs 'upl_gpu_feedback_Feedback_Debug_r2_component.call.json');$tool=$oldCall.program;Verify @($tool);$args=@('--tool','memcheck','--leak-check','full','--error-exitcode','97',$target.path)+$args}
[IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference;$ErrorActionPreference='Continue';& $tool.path @args 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$oldPreference
$text=[IO.File]::ReadAllText($log);$zero=($mem -and $text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations')
Save $callPath ([ordered]@{owned_call_exited=$true;exit_code=$code;program=$tool;target_program=$target;arguments=$args;helper=(Entry $helperPath);prepared_input=(Entry $prepared);log=(Entry $log);started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;physical_acceptance=$false})
if($code -ne 0 -or ($mem -and !$zero)){throw 'Component or memcheck rejected; preserve partial output'}
Verify $h.inputs;Verify @($h.program,$h.source_build,$input.xml,$input.bi4);Verify $g.inputs
$completion=Join-Path $out 'completion.json';$r=ReadJson $completion;if(!$r.passed -or $r.physical_acceptance){throw 'Component completion rejected'}
$files=@(Get-ChildItem -LiteralPath $out -File | Where-Object {$_.Extension -in '.csv','.json','.out'} | ForEach-Object {Entry $_.FullName})
Save $check ([ordered]@{passed=$true;configuration=$Configuration;case=$Case;build=(Entry $helperPath);input=(Entry $prepared);call=(Entry $callPath);completion=(Entry $completion);files=$files;earlier_gates=@($prior|ForEach-Object {Entry $_});actual_physical_Run_completed=$false;public_GPU_dynamic_accepted=$false;physical_acceptance=$false})
