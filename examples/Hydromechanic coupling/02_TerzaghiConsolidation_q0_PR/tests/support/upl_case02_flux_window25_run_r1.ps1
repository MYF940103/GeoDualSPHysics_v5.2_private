param([Parameter(Mandatory=$true)][ValidateSet('coarse','half')][string]$Window)
# One reviewed short window only. No restart, pair execution, reader or QC follow-on.
$ErrorActionPreference='Stop';$Window=$Window.ToLowerInvariant();$tests=Split-Path -Parent $PSScriptRoot;$tag='upl_case02_flux_window25_'+$Window+'_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_flux_window25_actual_ReleaseCPU_r1.helper.json';$inputsPath=Join-Path $tests 'logs\upl_case02_flux_window25_r1.inputs.json'
$out=Join-Path $tests "outputs\$tag";$record=Join-Path $tests "logs\$tag.run.json";$callPath=Join-Path $tests "logs\$tag.solver.call.json";$log=Join-Path $tests "logs\$tag.log"
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($e in $items){$a=Entry $e.path;if($null -eq $e.bytes -or !$e.sha256 -or $a.bytes -ne $e.bytes -or $a.sha256 -ine $e.sha256){throw "Frozen artifact changed: $($e.path)"}}}
foreach($path in @($out,$record,$callPath,$log)){if(Test-Path -LiteralPath $path){throw "Retained short protected: $path"}}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json;$inputs=Get-Content -Raw -LiteralPath $inputsPath|ConvertFrom-Json
if(!$build.passed -or $build.status -cne 'current_CPU_flux_window25_helper_linked_not_run' -or $build.kind -cne 'actual' -or $build.configuration -cne 'ReleaseCPU' -or !$build.exact_link_closure_verified -or !$build.build_and_source_bindings_unchanged -or $build.source_build.path -ine (Join-Path $tests 'logs\upl_case02_flux_cpu_ReleaseCPU_r1.build.json') -or !$inputs.prepared){throw 'Passed matching flux Release actual helper and retained prepared inputs required'}
$selected=@($inputs.jobs|Where-Object{$_.window -ceq $Window});if($selected.Count -ne 1){throw 'Select one retained short input window'};$job=$selected[0]
$expectedSteps=if($Window -ceq 'coarse'){10000}else{20000};if($job.steps -ne $expectedSteps -or $job.expected_samples -ne 769){throw 'Retained short clocks/sample contract differs'}
$bindings=@((Entry $PSCommandPath),(Entry (Join-Path $tests 'notes\upl_case02_flux_window25_owners_r1.json')),(Entry $buildPath),(Entry $inputsPath),$build.program,$build.compile_call,$build.link_call,$build.source_build,$build.compiler_dependency_record,$job.configuration,$job.runtime,$job.initial_BI4,$job.normals)+@($build.author_files)
function Gate([string]$leaf,[string]$mode,[string]$name){
  $path=Join-Path $tests ('logs\'+$leaf);$q=Get-Content -Raw -LiteralPath $path|ConvertFrom-Json
  if(!$q.passed -or $q.stage -cne $(if($mode -ceq 'off'){'upl_case02_flux_qc_r1'}else{'upl_case02_flux_window25_qc_r1'}) -or $q.mode -cne $mode -or !$q.bindings_unchanged_after_QC -or $q.physical_acceptance -ne $false){throw "New flux QC prerequisite failed: $leaf"}
  $nativePath=Join-Path $tests ('logs\upl_case02_'+$name+'_r1.native.check.json');$solverPath=Join-Path $tests ('logs\upl_case02_'+$name+'_r1.run.json')
  $ne=@($q.inputs|Where-Object{$_.path -ieq $nativePath});$se=@($q.inputs|Where-Object{$_.path -ieq $solverPath});if($ne.Count -ne 1 -or $se.Count -ne 1){throw 'QC does not bind the corresponding new native/solver records'}
  Verify $q.inputs;$native=Get-Content -Raw -LiteralPath $nativePath|ConvertFrom-Json
  if(!$native.passed -or !$native.owned_reader_exit0 -or $native.job -cne $name -or $native.sealed_solver.path -ine $solverPath -or $native.sealed_solver.sha256 -ine $se[0].sha256){throw 'QC native/solver attribution differs'}
  if($mode -ceq 'off' -and !$q.all_original15_typed_prefix_byte_exact){throw 'New default-OFF exact comparison missing'}
  if($mode -ceq 'coarse'){
    Verify @($native.completion);$d=Get-Content -Raw -LiteralPath $native.completion.path|ConvertFrom-Json
    if($d.samples -ne 769 -or $d.max_activeDrainCount -le 0 -or $d.post_open_drained_particle_checks -le 0 -or $q.drainage_coarse.min_active_drained -le 0){throw 'New coarse drainage witness missing; hold half'}
  }
  return @((Entry $path))+@($q.inputs)
}
$bindings+=@(Gate 'upl_case02_flux_window25_smoke_r1.qc.json' 'smoke' 'flux_window25_smoke');$bindings+=@(Gate 'upl_case02_flux_legacy_off_r1.exact.json' 'off' 'flux_legacy_off')
if($Window -ceq 'half'){$bindings+=@(Gate 'upl_case02_flux_window25_coarse_r1.qc.json' 'coarse' 'flux_window25_coarse')}
function VerifyBuild{Verify $bindings;Verify $build.objects;Verify $build.canonical_programs_before;foreach($pair in $build.source_snapshot){Verify @($pair.original,$pair.snapshot)};Verify @($build.documentation_snapshot.original,$build.documentation_snapshot.snapshot);foreach($r in $build.runtime){Verify @($r.original,$r.copy)}}
VerifyBuild
if(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^DualSPHysics.*CPU.*\.exe$|^upl_case02_.*actual.*\.exe$'}){throw 'A CPU solver is active; do not duplicate'}
$prefix=[IO.Path]::Combine([IO.Path]::GetDirectoryName($job.runtime.path),[IO.Path]::GetFileNameWithoutExtension($job.runtime.path));$argv=@('--solver',$Window,'-cpu','-ompthreads:1','-stable','-mdbc_freeslip',$prefix,$out,'-dirdataout','data','-svres',('-nsteps:'+$job.steps))
[IO.File]::WriteAllBytes($log,[byte[]]@());$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location ([IO.Path]::GetDirectoryName($build.program.path))
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$ended=[DateTime]::UtcNow.ToString('o');$call=[ordered]@{program=$build.program;arguments=$argv;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;physical_acceptance=$false}
[IO.File]::WriteAllText($callPath,($call|ConvertTo-Json -Depth 6)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object{Entry $_.FullName})}
$unchanged=$false;try{VerifyBuild;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$completionPath=Join-Path $out 'actual_complete.json';$completion=$null;$done=$null;if(Test-Path -LiteralPath $completionPath){$completion=Entry $completionPath;$done=Get-Content -Raw -LiteralPath $completionPath|ConvertFrom-Json}
$parts=@($files|Where-Object{[IO.Path]::GetFileName($_.path) -cmatch '^Part_\d{4}\.bi4$'});$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $done.passed -and $done.window -ceq $Window -and $done.completed_steps -eq $job.steps -and $done.saved_parts -eq 769 -and $parts.Count -eq 769)
$result=[ordered]@{stage=$tag;passed=$passed;scope='One actual flux Release short solver; independent native/QC still required';window=$Window;build=(Entry $buildPath);input_manifest=(Entry $inputsPath);owned_exit_record=(Entry $callPath);program=$build.program;arguments=$argv;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;bindings=$bindings;bindings_unchanged=$unchanged;files=$files;native_frames=$parts.Count;completion=$completion;log=(Entry $log);post_Run_dterror_is_not_full_history_max=$true;native_review_passed=$false;independent_half_passed=$false;force_stage_load_budget_verified=$false;long_or_formal_admitted=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Flux short rejected; preserve evidence and inspect $record"};Write-Output "Flux short solver completed; native/QC not started: $record"
