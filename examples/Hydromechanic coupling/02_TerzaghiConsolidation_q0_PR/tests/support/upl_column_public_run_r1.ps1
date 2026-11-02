param([Parameter(Mandatory=$true)][ValidateSet('CPU','GPU')][string]$Backend,[Parameter(Mandatory=$true)][ValidateSet('smoke','coarse')][string]$Window,[string]$PriorGateReceipt)
# One genuine public project-main call. No helper, reader, QC, build or following job.
$ErrorActionPreference='Stop';$Backend=$Backend.ToUpperInvariant();$Window=$Window.ToLowerInvariant();$smoke=$Window -ceq 'smoke';$mem=$smoke -and $Backend -ceq 'GPU'
$cfg=if($Backend -ceq 'CPU'){if($smoke){'DebugCPU'}else{'ReleaseCPU'}}else{if($smoke){'Debug'}else{'Release'}}
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $tests 'logs';$src=Join-Path $repo 'src';$tag='upl_column_public_'+$Backend+'_'+$Window+'_r1'
$folder=Join-Path $tests ('outputs\'+$tag);$record=Join-Path $logs ($tag+'.run.json');$callPath=Join-Path $logs ($tag+'.call.json');$log=Join-Path $logs ($tag+'.log')
function E([string]$p){$f=Get-Item -LiteralPath $p -Force;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Need([bool]$ok,[string]$why){if(!$ok){throw $why}}
function V($rows){foreach($r in $rows){Need ($r.path -and $null -ne $r.bytes -and $r.sha256) 'Missing bound Entry';$a=E $r.path;Need ($a.bytes -eq $r.bytes -and $a.sha256 -ieq $r.sha256) ('Changed bound artifact: '+$r.path)}}
function Fresh($paths){foreach($p in $paths){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$value){Fresh @($p);[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Owned($entry){V @($entry);$c=J $entry.path;Need ($c.owned_call_exited -and $c.typed_LASTEXITCODE_captured_immediately -and $c.exit_code -is [int] -and $c.exit_code -eq 0 -and !$c.invocation_failure) 'Owned typed exit0 required';V @($c.program,$c.log)}
function SameEntry($a,$b){return ($a.path -ieq $b.path -and $a.bytes -eq $b.bytes -and $a.sha256 -ieq $b.sha256)}
Fresh @($folder,$record,$callPath,$log)
$buildPath=Join-Path $logs $(if($Backend -ceq 'CPU' -and $smoke){'upl_column_public_default_DebugCPU_r1.build.json'}else{'upl_column_public_'+$cfg+'_r1.build.json'});$buildEntry=E $buildPath;$b=J $buildPath
Need ($b.passed -and $b.configuration -ceq $cfg -and !$b.helper_built -and !$b.canonical_program_installed) 'Passed isolated authoritative project-main build required'
$bindings=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_column_public_run_r1.json')),$buildEntry);$sourceFreeze=$null;$adoptedCPU=$null
if($Backend -ceq 'CPU'){
  Need ($b.direct_native_call -and $b.typed_LASTEXITCODE_captured_immediately -and $b.owned_call_exited -and $b.exit_code -is [int] -and $b.exit_code -eq 0 -and $b.source_bindings_unchanged -and $b.canonical_programs_unchanged -and @($b.objects).Count -eq 86) 'Current CPU build top-level typed exit/source/object gate rejected'
  $cpu=$b;if(!$smoke){$adoptedCPU=$b.adopted_Debug_source_build;V @($adoptedCPU);$cpu=J $adoptedCPU.path;$bindings+=@($adoptedCPU);Need ($cpu.passed -and $cpu.configuration -ceq 'DebugCPU' -and $cpu.source_bindings_unchanged -and $cpu.runtime_unchanged) 'Release adopts the same-round Debug documentation/runtime identities'}
  $pairs=@($b.source_snapshot);$doc=$cpu.documentation_snapshot;$canonical=@($b.canonical_programs_before);$runtimeBefore=@($cpu.runtime_before);$program=$b.program
}else{
  Need ($b.status -ceq 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -and $b.source_and_protected_artifacts_unchanged -and $b.canonical_programs_unchanged -and $b.objects_exclude_main -and @($b.objects).Count -eq 110 -and @($b.runtime).Count -eq 4 -and !$b.program_or_component_run) 'Current authoritative GPU110/main build rejected'
  Owned $b.project_call;$sourceFreeze=$b.source_freeze;V @($sourceFreeze);$s=J $sourceFreeze.path;$pairs=@($s.current_source_snapshot);$doc=$s.documentation_snapshot;$canonical=@($s.canonical_programs_before);$runtimeBefore=@($s.runtime_before);$program=$b.isolated_GPU_program
  Need (@($s.source).Count -eq 265) 'Current GPU source265 required';$bindings+=@($sourceFreeze,$b.project_call,$b.project_main_object)+@($b.inputs)+@($s.source)
}
Need ($pairs.Count -eq 265 -and @($pairs.original.path|Sort-Object -Unique).Count -eq 265 -and $canonical.Count -eq 7 -and $runtimeBefore.Count -eq 4 -and $doc.original.path -and $doc.snapshot.path) 'Current265/doc/canonical7/runtime4 closure required'
foreach($row in $pairs){Need ($row.original.bytes -eq $row.snapshot.bytes -and $row.original.sha256 -ieq $row.snapshot.sha256) 'Source original/snapshot identity differs';$bindings+=@($row.original,$row.snapshot)}
$bindings+=@($doc.original,$doc.snapshot,$program)+$canonical+$runtimeBefore+@($b.objects)+@($b.tools)+@($b.author_files)
$manifestPath=Join-Path $logs 'upl_column_public_r1.inputs.json';$manifest=J $manifestPath;Need ($manifest.stage -ceq 'upl_column_public_prepare_r1' -and $manifest.prepared -and $manifest.passed -and $manifest.physical_acceptance -eq $false -and @($manifest.jobs).Count -eq 3) 'Own prepared public-input manifest required'
$jobs=@($manifest.jobs|Where-Object {$_.window -ceq $Window});Need ($jobs.Count -eq 1) 'One exact public window input required';$job=$jobs[0]
$steps=if($smoke){2}else{10000};$samples=if($smoke){3}else{769};$dt=2.5e-6;$end=if($smoke){5e-6}else{0.025}
Need ($job.physical_XML_equal_except_master -eq $true -and $job.dt_s -eq $dt -and $job.end_s -eq $end -and $job.steps -eq $steps -and $job.expected_samples -eq $samples) 'Declared public master-only input/window differs'
$prefix=Join-Path (Split-Path -Parent $job.runtime.path) ([IO.Path]::GetFileNameWithoutExtension($job.runtime.path));Need ([IO.Path]::GetExtension($job.runtime.path) -ceq '.xml' -and ($prefix+'.xml') -ceq $job.runtime.path -and $prefix -ceq $job.input_prefix) 'Exact runtime XML prefix reconstruction rejected'
$bindings+=@((E $manifestPath),$job.configuration,$job.runtime,$job.initial_BI4,$job.normals)+@($manifest.inputs)+@($manifest.bindings)+@($manifest.files)
$priorGate=$null;$priorNative=$null;$priorRun=$null
if(!$smoke){
  Need (![string]::IsNullOrWhiteSpace($PriorGateReceipt)) 'Explicit root coarse admission required';$priorGate=E $PriorGateReceipt;$g=J $priorGate.path;$priorRun=E (Join-Path $logs ('upl_column_public_'+$Backend+'_smoke_r1.run.json'))
  Need ($g.passed -and $g.backend -ceq $Backend -and $g.window -ceq 'coarse' -and $g.physical_acceptance -eq $false -and (SameEntry $g.prior_run $priorRun)) 'Root gate must bind this backend own smoke Run'
  V @($g.prior_run,$g.native_qc);$p=J $priorRun.path;$priorNative=$g.native_qc;$q=J $priorNative.path
  Need ($p.passed -and $p.backend -ceq $Backend -and $p.window -ceq 'smoke' -and $p.source_inputs_objects_runtime_canonical_unchanged -and $q.passed -and $q.physical_acceptance -eq $false -and @($q.files).Count -gt 0 -and (SameEntry $q.source_run $priorRun)) 'Passed own-smoke native check with exact source_run required'
  if($Backend -ceq 'GPU'){Need ($p.memcheck_executed -and $p.memcheck_zero_errors_and_leaks) 'Own GPU smoke memcheck0/0 required'}
  Owned $p.call;V $p.inputs;V $p.files;V $q.inputs;V $q.files;V $g.inputs;$bindings+=@($priorGate,$priorRun,$priorNative)+@($g.inputs)
}
V $bindings
$runtime=@();$exeDir=Split-Path -Parent $program.path
if($Backend -ceq 'CPU'){
  foreach($r in $runtimeBefore){$dest=Join-Path $exeDir ([IO.Path]::GetFileName($r.path));$copied=$false;if(Test-Path -LiteralPath $dest){$a=E $dest;Need ($a.bytes -eq $r.bytes -and $a.sha256 -ieq $r.sha256) 'Existing CPU runtime differs; do not overwrite'}else{Copy-Item -LiteralPath $r.path -Destination $dest;$copied=$true};$a=E $dest;Need ($a.bytes -eq $r.bytes -and $a.sha256 -ieq $r.sha256) 'CPU runtime copy differs';$runtime+=@{original=$r;copy=$a;copied_by_this_action=$copied}}
}else{foreach($row in $b.runtime){$matchesRuntime=@($runtimeBefore|Where-Object {[IO.Path]::GetFileName($_.path) -ieq [IO.Path]::GetFileName($row.copy.path)});Need ($matchesRuntime.Count -eq 1 -and $matchesRuntime[0].bytes -eq $row.copy.bytes -and $matchesRuntime[0].sha256 -ieq $row.copy.sha256 -and (Split-Path -Parent $row.copy.path) -ieq $exeDir) 'Built GPU runtime identity/directory differs';$runtime+=@($row)}}
Need ($runtime.Count -eq 4) 'Exactly four executable-directory runtime files required'
$targetArgs=@(if($Backend -ceq 'CPU'){'-cpu';'-ompthreads:1'}else{'-gpu:0'});$targetArgs+=@('-stable','-mdbc_freeslip',$prefix,$folder,'-dirdataout','data','-svres',('-nsteps:'+$steps))
$tool=$program;$toolProof=$null;$argv=$targetArgs
if($mem){$toolProof=E (Join-Path $logs 'upl_gpu_perm_component_Debug_r1.call.json');$m=J $toolProof.path;Need ($m.owned_call_exited -and $m.exit_code -is [int] -and $m.exit_code -eq 0 -and $m.memcheck_zero_errors_and_leaks -and $m.program.path -ceq 'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe') 'Accepted CUDA11.7 memcheck program required';V @($m.program,$m.log);$tool=$m.program;$bindings+=@($toolProof,$tool,$m.log);$argv=@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$program.path)+$targetArgs}
function Verify{V $bindings;V @($tool);foreach($row in $runtime){V @($row.original,$row.copy)}}
Verify
[IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o');$code=$null;$launchFailure=$null;$saved=$ErrorActionPreference;Push-Location $src
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$launchFailure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
$text=[IO.File]::ReadAllText($log);$zero=$mem -and $text -match 'ERROR SUMMARY:\s*0 errors' -and $text -match 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'
Save $callPath ([ordered]@{program=$tool;target_program=$program;arguments=$argv;target_arguments=$targetArgs;working_directory=$src;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$launchFailure;log=(E $log);public_project_main=$true;fixture_or_Run_override=$false;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;memcheck_tool_source=$toolProof;direct_target_call=(!$mem);target_child_exit_separately_observed=$false;physical_acceptance=$false})
# The actual typed call is immutable before inspecting or hashing any solver output.
$failure=$launchFailure;$unchanged=$false;$files=@();$rawExact=$false;$runOut=$null;$rawCount=0
try{Need ($code -is [int] -and $code -eq 0 -and !$launchFailure -and (!$mem -or $zero)) 'Owned public project-main/tool exit rejected';$runOut=E (Join-Path $folder 'Run.out');$raw=@(Get-ChildItem -LiteralPath (Join-Path $folder 'data') -File -Filter 'Part_*.bi4');$rawCount=$raw.Count;$expected=@(0..($samples-1)|ForEach-Object {'Part_{0:D4}.bi4' -f $_});$names=@($raw|ForEach-Object {$_.Name});$rawExact=($raw.Count -eq $samples -and @(Compare-Object ($names|Sort-Object) ($expected|Sort-Object)).Count -eq 0);Need $rawExact 'Native saved frame sequence/count differs; pure reader review is still required'}catch{$failure=$_.Exception.Message}
try{Verify;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
if(Test-Path -LiteralPath $folder){$files=@(Get-ChildItem -LiteralPath $folder -File -Recurse|Sort-Object FullName|ForEach-Object {E $_.FullName})}
$passed=(!$failure -and $unchanged -and $rawExact -and $null -ne $runOut -and $code -is [int] -and $code -eq 0)
Save $record ([ordered]@{stage='upl_column_public_run_r1';passed=[bool]$passed;backend=$Backend;window=$Window;configuration=$cfg;inputs=$bindings;source_build=$buildEntry;source_freeze=$sourceFreeze;adopted_Debug_source_build=$adoptedCPU;program=$program;input_manifest=(E $manifestPath);runtime_input=$job.runtime;input_prefix=$prefix;call=(E $callPath);arguments=$targetArgs;runtime=$runtime;canonical_programs_before=$canonical;source_snapshot=$pairs;documentation_snapshot=$doc;files=$files;run_out=$runOut;planned_steps=$steps;planned_samples=$samples;planned_dt_s=$dt;planned_end_s=$end;native_frames=$rawCount;native_frame_sequence_exact=$rawExact;memcheck_executed=$mem;memcheck_zero_errors_and_leaks=$zero;prior_admission=$priorGate;prior_smoke_native=$priorNative;source_inputs_objects_runtime_canonical_unchanged=$unchanged;all_raw_outputs_hash_bound=$true;public_project_main=$true;fixture_or_Run_override=$false;private_actual_complete_required=$false;solver_backend_proved_by_program_build_and_arguments=$true;native_decoder_or_QC_invoked=$false;completed_steps_or_actual_end_verified_by_this_owner=$false;force_stage_load_budget_verified=$false;independent_half_performed=$false;physical_acceptance=$false;failure=$failure})
if(!$passed){throw "Public Run rejected; preserve $record and partial outputs, no automatic retry"};Write-Output "One public project-main Run sealed; pure native review remains separate: $record"
