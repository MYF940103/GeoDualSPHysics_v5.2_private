param([Parameter(Mandatory=$true)][ValidateSet('RunJob','ReviewJob')][string]$Mode,[ValidateSet('CPU_c','CPU_h','GPU_c','GPU_h')][string]$Job='CPU_c',[switch]$ExecutionAuthorized)
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
$prepared=ReadJson $manifest;Verify $prepared.inputs;Verify @($prepared.CPU_program);Verify $prepared.CPU_sources;Verify $prepared.GPU_helpers
$selected=@($prepared.jobs|Where-Object {$_.job -eq $Job});if($selected.Count -ne 1){throw 'Exactly one job required'};$j=$selected[0];Verify @($j.xml,$j.bi4)
$prerequisites=@();if($Job -ne 'Smoke'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_k0_actual_Smoke_r2.check.json')}
if($Job -eq 'CPU_h'){$prerequisites+=NeedCheck (Join-Path $logs 'upl_gpu_k0_actual_CPU_c_r3.check.json')}
if($Job -eq 'GPU_c'){$prerequisites+=NeedCheck (Join-Path $t 'figures\upl_gpu_k0_actual_CPU_half_r3.json')}
if($Job -eq 'GPU_h'){$prerequisites+=NeedCheck (Join-Path $t 'figures\upl_gpu_k0_actual_cross_c_r3.json')}
$name='upl_gpu_k0_actual_'+$Job+'_r3';$out=Join-Path $outputs $name;$run=Join-Path $logs ($name+'.run.json');$check=Join-Path $logs ($name+'.check.json');$review=Join-Path $outputs ($name+'_review')
function InvokeOwned($target,[string[]]$argv,[string]$label,[bool]$mem){
  $call=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($p in @($call,$log)){if(Test-Path -LiteralPath $p){throw 'Owned invocation retained'}}
  $tool=$target;$arguments=$argv;if($mem){$old=ReadJson (Join-Path $logs 'upl_gpu_k0_time_Debug_Scale_r1.call.json');$tool=$old.program;Verify @($tool);$arguments=@('--tool','memcheck','--leak-check','full','--error-exitcode','97',$target.path)+$argv}
  Verify @($target);[IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o');$preference=$ErrorActionPreference;$ErrorActionPreference='Continue';& $tool.path @arguments 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$preference
  $text=[IO.File]::ReadAllText($log);$zero=$mem -and $text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'
  Save $call ([ordered]@{owned_call_exited=$true;exit_code=$code;program=$tool;target_program=$target;arguments=$arguments;log=(Entry $log);started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;prepared_input=(Entry $manifest);recipe=(Entry $PSCommandPath);physical_acceptance=$false})
  if($code -ne 0 -or ($mem -and !$zero)){throw 'Owned call rejected; preserve partial evidence'};Verify @($target,$j.xml,$j.bi4);Verify $prepared.inputs;Entry $call
}
if($Mode -eq 'RunJob'){
  foreach($p in @($out,$run)){if(Test-Path -LiteralPath $p){throw 'Retained solver protected; use offline ReviewJob after postprocessing failure'}}
  $args=@('-stable',$j.prefix,$out,'-dirdataout','data','-svres');$target=$helper[$j.configuration].value.program
  if($j.backend -eq 'CPU'){$target=$prepared.CPU_program;$args=@('-cpu','-ompthreads:4')+$args}else{$args=@($(if($j.smoke){'--solver-smoke'}else{'--solver'}),'-gpu:0')+$args}
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
