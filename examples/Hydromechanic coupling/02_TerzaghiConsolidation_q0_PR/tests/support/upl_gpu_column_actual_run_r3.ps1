param(
  [Parameter(Mandatory=$true)][ValidateSet('smoke','coarse','half')][string]$Window,
  [Parameter(Mandatory=$true)][string]$ComponentDebugReceipt,
  [string]$ComponentReleaseReceipt,
  [Parameter(Mandatory=$true)][string]$DefaultOffReceipt,
  [Parameter(Mandatory=$true)][string]$LegacyDynamicReceipt,
  [string]$PriorGateReceipt
)
# One actual GPU Run only; decoding, QC, cross and next-window admission are separate.
$ErrorActionPreference='Stop';$Window=$Window.ToLowerInvariant();$mem=$Window -ceq 'smoke';$cfg=if($mem){'Debug'}else{'Release'}
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $tests 'logs';$tag='upl_gpu_column_actual_'+$Window+'_r2'
$folder=Join-Path $tests ('outputs\'+$tag);$record=Join-Path $logs ($tag+'.run.json');$callPath=Join-Path $logs ($tag+'.call.json');$log=Join-Path $logs ($tag+'.log')
function E([string]$p){$f=Get-Item -LiteralPath $p -Force;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function V($rows){foreach($r in $rows){if(!$r.path){throw 'Missing bound Entry'};$a=E $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed artifact: $($r.path)"}}}
function Need([bool]$yes,[string]$why){if(!$yes){throw $why}}
function Fresh($paths){foreach($p in $paths){Need (!(Test-Path -LiteralPath $p)) ("Retained path protected: "+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function N($v){Need ($null -ne $v -and [string]$v -ne '') 'Missing number';$n=if($v -is [ValueType]){[double]$v}else{[double]::Parse([string]$v,[Globalization.CultureInfo]::InvariantCulture)};Need (![double]::IsNaN($n) -and ![double]::IsInfinity($n)) 'Nonfinite number';return $n}
function Owned($entry){V @($entry);$c=J $entry.path;Need ($c.owned_call_exited -and $c.typed_LASTEXITCODE_captured_immediately -and $c.exit_code -is [int] -and $c.exit_code -eq 0) 'Owned immediate typed exit0 required';V @($c.program,$c.log)}
Fresh @($folder,$record,$callPath,$log)
$hp=Join-Path $logs ('upl_gpu_column_actual_'+$cfg+'_r1.helper.json');$h=J $hp;$b=J $h.source_build.path;$s=J $h.source_freeze.path
Need ($h.passed -and $h.status -ceq 'current_column_GPU_helper_linked_not_run' -and $h.kind -ceq 'actual' -and $h.configuration -ceq $cfg -and $h.exact_link_closure_verified -and $h.link_object_count -eq 111 -and @($h.objects).Count -eq 110 -and @($h.runtime).Count -eq 4 -and $h.source_and_protected_artifacts_unchanged -and !$h.program_run -and !$h.solver_started) 'Passed current actual helper required'
Need ($b.passed -and $b.configuration -ceq $cfg -and $b.objects_exclude_main -and @($b.objects).Count -eq 110 -and $b.source_and_protected_artifacts_unchanged -and @($s.source).Count -eq 265 -and @($s.current_source_snapshot).Count -eq 265 -and @($s.canonical_programs_before).Count -eq 7 -and @($s.runtime_before).Count -eq 4) 'Current265source/110objects/7canonical/4runtime closure required'
Owned $h.compile_call;Owned $h.link_call
$sourceMap=@{};foreach($r in $s.source){Need (!$sourceMap.ContainsKey($r.path)) 'Duplicate current source identity';$sourceMap[$r.path]=$r}
function SameSource($entry){V @($entry);$x=J $entry.path;Need (@($x.source).Count -eq 265) 'Matching full source identity required';$seen=@{};foreach($r in $x.source){Need ($sourceMap.ContainsKey($r.path) -and !$seen.ContainsKey($r.path)) 'Source identity path differs';$a=$sourceMap[$r.path];Need ($r.bytes -eq $a.bytes -and $r.sha256 -ieq $a.sha256) 'Gate used different source bytes';$seen[$r.path]=$true}}
$inputs=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_gpu_column_actual_run_r3.json')),(E $hp))
function ComponentGate([string]$path,[string]$configuration){$e=E $path;$g=J $path;Need ($g.passed -and $g.configuration -ceq $configuration -and $g.source_inputs_objects_runtime_canonical_unchanged -and $g.physical_acceptance -eq $false) 'Explicit accepted component record required';if($configuration -ceq 'Debug'){Need ($g.memcheck_executed -and $g.memcheck_zero_errors_and_leaks) 'Component Debug memcheck0/0 required'};Owned $g.call;V @($g.completion,$g.helper,$g.source_build);V $g.files;SameSource $g.source_freeze;return $e}
$inputs+=@(ComponentGate $ComponentDebugReceipt 'Debug')
if(!$mem){Need (![string]::IsNullOrWhiteSpace($ComponentReleaseReceipt)) 'Explicit Release component receipt required';$inputs+=@(ComponentGate $ComponentReleaseReceipt 'Release')}
$off=E $DefaultOffReceipt;$o=J $off.path;Need ($o.passed -and $o.all_original15_typed_exact -eq $true -and $o.actual_clock_step_dterror_exact -eq $true -and $o.physical_acceptance -eq $false -and @($o.files).Count -gt 0) 'Independent current defaultOFF original15/clock/step/dterror exact check required';V $o.files;V $o.inputs;V @($o.source_build);$ob=J $o.source_build.path;Need ($ob.passed) 'OFF current source build rejected';SameSource $ob.source_freeze;$inputs+=@($off)
$legacy=E $LegacyDynamicReceipt;$l=J $legacy.path;Need ($l.passed -and $l.fresh_runs -eq 5 -and $l.complete_same_dt_trajectories_exact -and $l.actual_clock_step_dterror_exact -and $l.physical_acceptance -eq $false) 'Five old periodic/wall/gravity full native regressions required';V $l.inputs;V $l.files;V @($l.source_build);$lb=J $l.source_build.path;Need $lb.passed 'Legacy regression build rejected';SameSource $lb.source_freeze;$inputs+=@($legacy)
$priorRun=$null;$priorGate=$null;$priorProof=$null
if(!$mem){
  Need (![string]::IsNullOrWhiteSpace($PriorGateReceipt)) 'Explicit root window admission required';$priorGate=E $PriorGateReceipt;$g=J $priorGate.path;$priorWindow=if($Window -ceq 'coarse'){'smoke'}else{'coarse'};$priorPath=Join-Path $logs ('upl_gpu_column_actual_'+$priorWindow+'_r2.run.json')
  $priorRun=E $priorPath;Need ($g.passed -and $g.window -ceq $Window -and $g.physical_acceptance -eq $false -and $g.prior_run.path -ieq $priorRun.path -and $g.prior_run.sha256 -ieq $priorRun.sha256 -and $g.prior_run.bytes -eq $priorRun.bytes) 'Root admission must bind this owner prior window'
  V $g.inputs;$p=J $priorRun.path;Need ($p.passed -and $p.window -ceq $priorWindow -and $p.physical_acceptance -eq $false -and $p.source_inputs_objects_runtime_canonical_unchanged) 'Own preceding actual Run required';Owned $p.call;V @($p.actual_complete);V $p.files;SameSource $p.source_freeze
  if($Window -ceq 'coarse'){Need ($p.memcheck_zero_errors_and_leaks -and $g.native_qc.path) 'Smoke own memcheck/nativeQC required';$priorProof=$g.native_qc}else{Need ([bool]$g.cpu_cross.path) 'Own coarse nativeCPUcross required';$priorProof=$g.cpu_cross}
  V @($priorProof);$q=J $priorProof.path;Need ($q.passed -and $q.physical_acceptance -eq $false -and @($q.files).Count -gt 0) 'Sealed nativeQC/CPUcross passed proof required';V $q.files
  # The root gate binds the intended proof to this Run. Do not recurse old CPU helper source.
  $inputs+=@($priorGate,$priorRun,$priorProof)
}
$seedPath=Join-Path $logs $(if($mem){'upl_case02_smoke_r1.inputs.json'}else{'upl_case02_flux_window25_r1.inputs.json'});$seed=J $seedPath
Need ($seed.prepared -and $seed.physical_acceptance -eq $false) 'Retained prepared input required'
if($mem){$job=$seed;$dt=2.5e-6;$end=5e-6;$steps=2;$samples=3;$xmlSha='91361a48145bc12104484081172631dd3dde7667369a829ec733366139ab3336'}else{$jobs=@($seed.jobs|Where-Object {$_.window -ceq $Window});Need ($jobs.Count -eq 1) 'One retained matching window required';$job=$jobs[0];$dt=if($Window -ceq 'coarse'){2.5e-6}else{1.25e-6};$end=.025;$steps=if($Window -ceq 'coarse'){10000}else{20000};$samples=769;$xmlSha=if($Window -ceq 'coarse'){'c6108504dba705347308dfb3615c945d702efb2e137399237286558d62957bc1'}else{'e1871b60a83484775e37f89f3ce614a9629358c8e887b0c8dfce8ff779c54ad8'}}
Need ($job.runtime.sha256 -ceq $xmlSha -and $job.initial_BI4.sha256 -ceq 'f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac' -and $job.normals.sha256 -ceq '0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97' -and $job.dt_s -eq $dt -and $job.end_s -eq $end -and $job.steps -eq $steps) 'Exact accepted geometry/runtime/window required'
$inputs+=@((E $seedPath),$job.configuration,$job.runtime,$job.initial_BI4,$job.normals);$prefix=Join-Path (Split-Path -Parent $job.runtime.path) ([IO.Path]::GetFileNameWithoutExtension($job.runtime.path));Need (([IO.Path]::GetExtension($job.runtime.path) -ceq '.xml') -and ($prefix+'.xml' -ceq $job.runtime.path)) 'Exact XML prefix reconstruction required';$targetArgs=@('--solver',$Window,'-gpu:0','-stable','-mdbc_freeslip',$prefix,$folder,'-dirdataout','data','-svres',('-nsteps:'+$steps))
$tool=$h.program;$toolSource=$null;$argv=$targetArgs
if($mem){$toolSource=E (Join-Path $logs 'upl_gpu_perm_component_Debug_r1.call.json');$m=J $toolSource.path;Need ($m.owned_call_exited -and $m.exit_code -is [int] -and $m.exit_code -eq 0 -and $m.memcheck_zero_errors_and_leaks -and $m.program.path -ceq 'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe') 'Accepted CUDA11.7 sanitizer required';$tool=$m.program;$inputs+=@($toolSource,$tool);$argv=@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$h.program.path)+$targetArgs}
function Verify{
  V $inputs;V $h.inputs;V $h.author_files;V $h.objects;V $h.tools;V $h.libraries;V @($h.source_build,$h.source_freeze,$h.program,$h.helper_object,$h.compile_call,$h.link_call,$tool);V $s.source;V $s.canonical_programs_before;V $s.runtime_before;V @($s.documentation_snapshot.original,$s.documentation_snapshot.snapshot)
  foreach($r in $s.current_source_snapshot){V @($r.original,$r.snapshot)};foreach($r in $h.runtime){V @($r.original,$r.copy)};foreach($r in $b.runtime){V @($r.original,$r.copy)}
}
Verify
[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$launchFailure=$null;$saved=$ErrorActionPreference
Push-Location (Join-Path $repo 'src')
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$launchFailure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
$text=[IO.File]::ReadAllText($log);$zero=$mem -and $text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'
Save $callPath ([ordered]@{program=$tool;target_program=$h.program;arguments=$argv;target_arguments=$targetArgs;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');owned_call_exited=($code -is [int]);typed_LASTEXITCODE_captured_immediately=($code -is [int]);exit_code=$code;invocation_failure=$launchFailure;log=(E $log);actual_solver_call=$true;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;memcheck_tool_source=$toolSource;direct_target_call=(!$mem);target_child_exit_separately_observed=$false;physical_acceptance=$false})
$failure=$launchFailure;$completion=$null;$done=$null;$files=@();$postUnchanged=$false
try{
  Need ($code -is [int] -and $code -eq 0 -and !$launchFailure -and (!$mem -or $zero)) 'Owned actual Run/tool call rejected'
  $completion=E (Join-Path $folder 'actual_complete.json');$done=J $completion.path
  Need ($done.passed -and $done.stage -ceq 'upl_gpu_column_actual_r1' -and $done.backend -ceq 'GPU' -and $done.window -ceq $Window -and $done.model -ceq 'constant' -and $done.actual_production_Run -and $done.live_GPU_download -and $done.public_master -eq $false -and $done.private_feedback_complete_rate_wall -and !$done.physical_fields_rewritten_by_fixture -and !$done.integrator_overridden -and $done.native_count -eq 1000 -and $done.fixed_count -eq 40 -and $done.total_native_count -eq 1040 -and $done.completed_steps -eq $steps -and $done.saved_parts -eq $samples -and (N $done.dt_s) -eq $dt -and [Math]::Abs((N $done.actual_end_s)-$end) -le 1e-14 -and $done.predictor_histories_released -and $done.force_scratch_released -and $done.final_ledger_rows -eq 1000 -and $done.fixed_n_is_not_CPU_zero_marker -and $done.n_V_rho_k_derived_not_independent_device_arrays -and (N $done.max_solid_fraction_roundoff) -le 5e-13 -and (N $done.max_signed_dterror_s) -le 1e-14 -and !$done.all_saved_native_fields_reviewed -and !$done.independent_half_performed -and !$done.physical_acceptance) 'Actual Finish/window/domain/released-state contract rejected'
  V @((E (Join-Path $folder 'live_final.csv')),(E (Join-Path $folder 'Run.out')));Need (@(Import-Csv -LiteralPath (Join-Path $folder 'live_final.csv')).Count -eq 1000) 'Final soil live export coverage differs'
}catch{$failure=$_.Exception.Message}
try{Verify;$postUnchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
if(Test-Path -LiteralPath $folder){$files=@(Get-ChildItem -LiteralPath $folder -File -Recurse|Sort-Object FullName|ForEach-Object {E $_.FullName})}
$passed=(!$failure -and $postUnchanged -and $null -ne $done -and $code -is [int] -and $code -eq 0)
Save $record ([ordered]@{stage='upl_gpu_column_actual_run_r3';passed=[bool]$passed;window=$Window;configuration=$cfg;inputs=$inputs;helper=(E $hp);source_build=$h.source_build;source_freeze=$h.source_freeze;call=(E $callPath);actual_complete=$completion;files=$files;planned_steps=$steps;planned_samples=$samples;planned_dt_s=$dt;planned_end_s=$end;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;default_OFF_check=$off;prior_admission=$priorGate;source_inputs_objects_runtime_canonical_unchanged=$postUnchanged;all_raw_outputs_hash_bound=$true;native_decoder_or_QC_invoked=$false;independent_half_performed=$false;physical_acceptance=$false;failure=$failure})
if(!$passed){throw "Actual Run rejected; preserve $record and outputs, no automatic retry"}
Write-Output "One actual Run sealed, native review still separate: $record"
