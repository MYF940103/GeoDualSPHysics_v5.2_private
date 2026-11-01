param([Parameter(Mandatory=$true)][ValidateSet('Prepare','RunJob','ReviewJob')][string]$Mode,[ValidateSet('Smoke','CPU_c','CPU_h','GPU_c','GPU_h')][string]$Job='Smoke',[switch]$ExecutionAuthorized)
# One fresh solver or one offline review only; failed postprocessing never restarts a solver.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$manifest=Join-Path $logs 'upl_gpu_k0_actual_r2.inputs.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($e in $rows){$v=Entry $e.path;if($v.bytes -ne $e.bytes -or $v.sha256 -ine $e.sha256){throw "Changed binding: $($e.path)"}}}
function ReadJson([string]$p){Get-Content -Raw -Encoding UTF8 -LiteralPath $p|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function NeedCheck([string]$p){$r=ReadJson $p;if(!$r.passed -or $r.physical_acceptance){throw "Prior bounded gate rejected: $p"};if($r.files){Verify $r.files};if($r.completion){Verify @($r.completion)};if($r.call){Verify @($r.call)};Entry $p}
if(!$ExecutionAuthorized){throw 'Explicit root action authorization required'}
$stagePath=Join-Path $logs 'upl_gpu_k0_time_stage_r1.check.json';$stage=ReadJson $stagePath;if(!$stage.passed -or @($stage.native).Count -ne 2 -or @($stage.components).Count -ne 6 -or $stage.physical_acceptance){throw 'Verified time-policy stage required'}
$helper=@{};foreach($cfg in @('Debug','Release')){$p=Join-Path $logs ('upl_gpu_k0_actual_'+$cfg+'_r2.helper.json');$h=ReadJson $p;if($h.fixture -ne 'Actual' -or $h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run'){throw 'Fresh r2 actual helper required'};Verify $h.inputs;Verify @($h.program,$h.source_build,$h.prerequisite_stage);Verify $h.libraries;foreach($r in $h.runtime){Verify @($r.original,$r.copy)};$g=ReadJson $h.source_build.path;Verify $g.inputs;Verify $g.objects;$helper[$cfg]=[pscustomobject]@{record=(Entry $p);value=$h}}
if($Mode -eq 'Prepare'){
  if(Test-Path -LiteralPath $manifest){throw 'Prepared inputs protected'}
  $basePath=Join-Path $logs 'upl_gpu_k0_time_r1.inputs.json';$seed=ReadJson $basePath;Verify @($seed.xml,$seed.bi4)
  $cpuPath=Join-Path $logs 'upl_cpu_public_build_r3.json';$cpu=ReadJson $cpuPath;if($cpu.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Accepted CPU Release build required'}
  $program=@($cpu.programs|Where-Object {[IO.Path]::GetFileName($_.path) -eq 'DualSPHysics5.2CPU_win64.exe'});if($program.Count -ne 1){throw 'Canonical CPU Release identity ambiguous'};Verify $program
  $cpuSources=@($cpu.source|Where-Object {$_.original.path -match '\\src\\source\\'}|ForEach-Object {$_.original});if($cpuSources.Count -ne 6){throw 'Six accepted CPU model sources required'};Verify $cpuSources
  $folder=Join-Path $outputs 'upl_gpu_k0_actual_seed_r2';if(Test-Path -LiteralPath $folder){throw 'Prepared runtime folder protected'};[void](New-Item -ItemType Directory -Path $folder)
  $jobs=@();foreach($name in @('Smoke','CPU_c','CPU_h','GPU_c','GPU_h')){
    $smoke=$name -eq 'Smoke';$backend=if($name.StartsWith('CPU')){'CPU'}else{'GPU'};$half=$name.EndsWith('_h');$dt=[Math]::Pow(2,$(if($half){-25}else{-24}));$end=[Math]::Pow(2,$(if($smoke){-23}else{-15}));$cadence=if($smoke){$dt}else{[Math]::Pow(2,-23)}
    $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($seed.xml.path)
    foreach($pair in @(@('DtIni',$dt),@('DtFixed',$dt),@('TimeMax',$end),@('TimeOut',$cadence))){$nodes=$doc.SelectNodes('//parameters/parameter[@key="'+$pair[0]+'"]');if($nodes.Count -ne 1){throw 'Ambiguous runtime time parameter'};$nodes[0].SetAttribute('value',([double]$pair[1]).ToString('R',[Globalization.CultureInfo]::InvariantCulture))}
    $hydro=$doc.SelectNodes('//hydromechanics');if($hydro.Count -ne 1 -or $hydro[0].SelectSingleNode('HydraulicConductivity').GetAttribute('value') -ne '0' -or $hydro[0].SelectNodes('HydroMechDynamicSeepage').Count){throw 'Expected private k0 seed without public master'}
    if($backend -eq 'CPU'){foreach($pair in @(@('HydroMechDynamicSeepage','1'),@('HydroMechConductivityModel','0'),@('HydroMechConductivityCk','0'))){$element=$doc.CreateElement($pair[0]);$element.SetAttribute('value',$pair[1]);$element.SetAttribute('comment','Matched bounded CPU k=0 dynamic benchmark');$tail=$hydro[0].LastChild;[void]$hydro[0].InsertBefore($doc.CreateWhitespace("`r`n                "),$tail);[void]$hydro[0].InsertBefore($element,$tail)}}
    $prefix=Join-Path $folder ('CaseUplGpuK0_'+$name);[IO.File]::WriteAllText($prefix+'.xml',$doc.OuterXml,(New-Object Text.UTF8Encoding($false)));Copy-Item -LiteralPath $seed.bi4.path -Destination ($prefix+'.bi4');$bi=Entry ($prefix+'.bi4');if($bi.sha256 -ine $seed.bi4.sha256){throw 'Native initial BI4 changed'}
    $jobs+=@{job=$name;backend=$backend;configuration=$(if($smoke){'Debug'}else{'Release'});smoke=$smoke;dt=$dt;end=$end;cadence=$cadence;samples=$(if($smoke){3}else{257});steps=[int]($end/$dt);prefix=$prefix;xml=(Entry ($prefix+'.xml'));bi4=$bi}
  }
  Save $manifest ([ordered]@{prepared_only=$true;code_checkpoint_verified_local_remote_by_root='7a758f3d3c04e379fc272f0f38fbc47e7eb13397';inputs=@(Entry $PSCommandPath;Entry $basePath;Entry $stagePath;Entry $cpuPath);CPU_program=$program[0];CPU_sources=$cpuSources;GPU_helpers=@($helper.Debug.record,$helper.Release.record);jobs=$jobs;native_initial_BI4_all_exact=$true;public_GPU_master_enabled=$false;physical_acceptance=$false});exit 0
}
$prepared=ReadJson $manifest;Verify $prepared.inputs;Verify @($prepared.CPU_program);Verify $prepared.CPU_sources;Verify $prepared.GPU_helpers
$selected=@($prepared.jobs|Where-Object {$_.job -eq $Job});if($selected.Count -ne 1){throw 'Exactly one job required'};$j=$selected[0];Verify @($j.xml,$j.bi4)
$prerequisites=@();if($Job -ne 'Smoke'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_k0_actual_Smoke_r2.check.json')}
if($Job -eq 'CPU_h'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_k0_actual_CPU_c_r2.check.json')}
if($Job -eq 'GPU_c'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_k0_actual_CPU_half_r2.check.json')}
if($Job -eq 'GPU_h'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_k0_actual_cross_c_r2.check.json')}
$name='upl_gpu_k0_actual_'+$Job+'_r2';$out=Join-Path $outputs $name;$run=Join-Path $logs ($name+'.run.json');$check=Join-Path $logs ($name+'.check.json');$review=Join-Path $outputs ($name+'_review')
function InvokeOwned($target,[string[]]$argv,[string]$label,[bool]$mem){
  $call=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($p in @($call,$log)){if(Test-Path -LiteralPath $p){throw 'Owned invocation retained'}}
  $tool=$target;$arguments=$argv;if($mem){$old=ReadJson (Join-Path $logs 'upl_gpu_k0_time_Debug_Scale_r1.call.json');$tool=$old.program;Verify @($tool);$arguments=@('--tool','memcheck','--leak-check','full','--error-exitcode','97',$target.path)+$argv}
  Verify @($target);[IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o');$preference=$ErrorActionPreference;$ErrorActionPreference='Continue';& $tool.path @arguments 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$preference
  $text=[IO.File]::ReadAllText($log);$zero=$mem -and $text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'
  Save $call ([ordered]@{owned_call_exited=$true;exit_code=$code;program=$tool;target_program=$target;arguments=$arguments;log=(Entry $log);started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;prepared_input=(Entry $manifest);physical_acceptance=$false})
  if($code -ne 0 -or ($mem -and !$zero)){throw 'Owned call rejected; preserve partial evidence'};Verify @($target,$j.xml,$j.bi4);Verify $prepared.inputs;Entry $call
}
if($Mode -eq 'RunJob'){
  foreach($p in @($out,$run)){if(Test-Path -LiteralPath $p){throw 'Retained solver protected; use offline ReviewJob after postprocessing failure'}}
  $args=@('-stable',$j.prefix,$out,'-dirdataout','data','-svres');$target=$helper[$j.configuration].value.program
  if($j.backend -eq 'CPU'){$target=$prepared.CPU_program;$args=@('-cpu','-omp:4')+$args}else{$args=@($(if($j.smoke){'--solver-smoke'}else{'--solver'}),'-gpu:0')+$args}
  $call=InvokeOwned $target $args $name ([bool]$j.smoke);$parts=@(Get-ChildItem -LiteralPath (Join-Path $out 'data') -Filter 'Part_????.bi4' -File);if($parts.Count -ne $j.samples){throw 'Incomplete native output after normal owned exit'}
  $files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object {Entry $_.FullName});Save $run ([ordered]@{owned_solver_exit0=$true;job=$Job;backend=$j.backend;call=$call;input=(Entry $manifest);selected_input=$j;helper=$helper[$j.configuration].record;files=$files;native_frames=$parts.Count;prerequisites=$prerequisites;solver_completed_before_analysis=$true;physical_acceptance=$false});exit 0
}
$r=ReadJson $run;if(!$r.owned_solver_exit0 -or $r.native_frames -ne $j.samples){throw 'Sealed completed solve required; never infer it from native files'};Verify @($r.call,$r.input,$r.helper);Verify $r.files
$callInfo=ReadJson $r.call.path;if($callInfo.exit_code -ne 0 -or ($j.smoke -and !$callInfo.memcheck_zero_errors_and_leaks)){throw 'Owned solver/memcheck receipt rejected'}
foreach($p in @($review,$check)){if(Test-Path -LiteralPath $p){throw 'Offline review protected; repair analysis with a new label, never rerun solver'}}
$reader=$helper[$j.configuration].value.program;$args=@($(if($j.smoke){'--read-smoke'}else{'--read'}),$j.backend,(Join-Path $out 'data'),([double]$j.dt).ToString('R',[Globalization.CultureInfo]::InvariantCulture),$review)
$call=InvokeOwned $reader $args ($name+'_review') $false;$completion=Join-Path $review 'completion.json';$d=ReadJson $completion
if(!$d.passed -or $d.samples -ne $j.samples -or $d.actual_end_s -ne $j.end -or $d.dt_s -ne $j.dt -or $d.native_count -ne 512 -or !$d.saved_clock_step_exact -or $d.physical_acceptance){throw 'Native single-run gate rejected'}
if($j.backend -eq 'GPU'){$actual=ReadJson (Join-Path $out 'actual_complete.json');if(!$actual.passed -or !$actual.actual_production_Run -or !$actual.private_feedback -or $actual.public_GPU_dynamic_mode -or $actual.physical_fields_rewritten_by_fixture -or $actual.completed_steps -ne $j.steps -or $actual.actual_end_s -ne $j.end){throw 'Actual GPU final state receipt rejected'}}
$files=@(Get-ChildItem -LiteralPath $review -File|ForEach-Object {Entry $_.FullName});Save $check ([ordered]@{passed=$true;job=$Job;backend=$j.backend;source_run=(Entry $run);call=$call;completion=(Entry $completion);files=$files;input=(Entry $manifest);physical_acceptance=$false;full_cycle_accepted=$false;public_GPU_accepted=$false})
