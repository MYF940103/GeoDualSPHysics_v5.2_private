param([switch]$ExecutionAuthorized)
# One separately authorized two-step startup; no reader/QC/short follow-on.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Explicit root-reviewed flux smoke action required'}
$tests=Split-Path -Parent $PSScriptRoot;$tag='upl_case02_flux_smoke_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_flux_actual_DebugCPU_r1.helper.json';$inputsPath=Join-Path $tests 'logs\upl_case02_smoke_r1.inputs.json'
$out=Join-Path $tests "outputs\$tag";$log=Join-Path $tests "logs\$tag.log";$record=Join-Path $tests "logs\$tag.run.json";$callPath=Join-Path $tests "logs\$tag.solver.call.json"
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($e in $items){$a=Entry $e.path;if($null -eq $e.bytes -or !$e.sha256 -or $a.bytes -ne $e.bytes -or $a.sha256 -ine $e.sha256){throw "Frozen input changed: $($e.path)"}}}
foreach($path in @($out,$log,$record,$callPath)){if(Test-Path -LiteralPath $path){throw "Retained smoke protected: $path"}}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json;$inputs=Get-Content -Raw -LiteralPath $inputsPath|ConvertFrom-Json
if(!$build.passed -or $build.status -cne 'current_CPU_flux_helper_linked_not_run' -or $build.kind -cne 'actual' -or $build.configuration -cne 'DebugCPU' -or $build.CPU_non_main_objects -ne 85 -or !$build.exact_link_closure_verified -or !$build.build_and_source_bindings_unchanged -or $build.source_build.path -ine (Join-Path $tests 'logs\upl_case02_flux_cpu_DebugCPU_r1.build.json') -or !$inputs.prepared -or $inputs.steps -ne 2 -or $inputs.expected_frames -ne 3){throw 'Passed matching flux Debug actual helper and unchanged two-step input required'}
$bindings=@((Entry $PSCommandPath),(Entry (Join-Path $tests 'notes\upl_case02_flux_owners_r1.json')),(Entry $buildPath),(Entry $inputsPath),$build.program,$build.compile_call,$build.link_call,$build.source_build,$build.compiler_dependency_record,$inputs.configuration,$inputs.runtime,$inputs.initial_BI4,$inputs.normals)+@($build.author_files)+@($build.objects)+@($build.canonical_programs_before)
foreach($pair in $build.source_snapshot){$bindings+=@($pair.original,$pair.snapshot)};$bindings+=@($build.documentation_snapshot.original,$build.documentation_snapshot.snapshot)
foreach($r in $build.runtime){$bindings+=@($r.original,$r.copy)}
Verify $bindings
if(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^DualSPHysics.*CPU.*\.exe$|^upl_case02_actual.*\.exe$'}){throw 'A CPU solver is active; do not duplicate'}
$prefix=[IO.Path]::Combine([IO.Path]::GetDirectoryName($inputs.runtime.path),[IO.Path]::GetFileNameWithoutExtension($inputs.runtime.path))
$argv=@('--solver','smoke','-cpu','-ompthreads:1','-stable','-mdbc_freeslip',$prefix,$out,'-dirdataout','data','-svres','-nsteps:2')
[IO.File]::WriteAllBytes($log,[byte[]]@());$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location ([IO.Path]::GetDirectoryName($build.program.path))
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$ended=[DateTime]::UtcNow.ToString('o')
# Seal ownership before any output inspection/hash can fail.
$call=[ordered]@{program=$build.program;arguments=$argv;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;physical_acceptance=$false}
[IO.File]::WriteAllText($callPath,($call|ConvertTo-Json -Depth 6)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object{Entry $_.FullName})}
$unchanged=$false;try{Verify $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$completePath=Join-Path $out 'actual_complete.json';$completion=$null;$done=$null;if(Test-Path -LiteralPath $completePath){$completion=Entry $completePath;$done=Get-Content -Raw -LiteralPath $completePath|ConvertFrom-Json}
$parts=@($files|Where-Object{[IO.Path]::GetFileName($_.path) -cmatch '^Part_\d{4}\.bi4$'})
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $done.passed -and $done.window -ceq 'smoke' -and $done.completed_steps -eq 2 -and $done.saved_parts -eq 3 -and $parts.Count -eq 3)
$result=[ordered]@{stage=$tag;passed=$passed;scope='Flux candidate Debug two-step actual Run only; separate native/QC required';build=(Entry $buildPath);input_manifest=(Entry $inputsPath);owned_exit_record=(Entry $callPath);started_utc=$started;ended_utc=$ended;program=$build.program;arguments=$argv;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;bindings=$bindings;bindings_unchanged=$unchanged;log=(Entry $log);completion=$completion;files=$files;native_frames=$parts.Count;post_Run_dterror_is_not_full_history_max=$true;native_review_passed=$false;half_or_long_admitted=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Flux startup rejected; retain outputs and inspect $record"};Write-Output "Flux smoke solver completed; native/QC not started: $record"
