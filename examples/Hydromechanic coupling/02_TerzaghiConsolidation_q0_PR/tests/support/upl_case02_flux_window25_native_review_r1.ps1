param([Parameter(Mandatory=$true)][ValidateSet('smoke','coarse','half')][string]$Job)
# One current-window structural decode only; no solver or numerical pair comparison.
$ErrorActionPreference='Stop';$Job=$Job.ToLowerInvariant();$tests=Split-Path -Parent $PSScriptRoot;$tag='upl_case02_flux_window25_'+$Job+'_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_flux_window25_reader_ReleaseCPU_r1.helper.json';$solverPath=Join-Path $tests "logs\$tag.run.json";$dataPath=Join-Path $tests "outputs\$tag\data"
$record=Join-Path $tests "logs\$tag.native.check.json";$callPath=Join-Path $tests "logs\$tag.reader.call.json";$log=Join-Path $tests "logs\$tag.native.log";$out=Join-Path $tests "outputs\${tag}_native"
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($e in $items){$a=Entry $e.path;if($null -eq $e.bytes -or !$e.sha256 -or $a.bytes -ne $e.bytes -or $a.sha256 -ine $e.sha256){throw "Frozen artifact changed: $($e.path)"}}}
foreach($path in @($record,$callPath,$log,$out)){if(Test-Path -LiteralPath $path){throw "Retained native review protected: $path"}}
$readerIdentity=Entry $buildPath
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json;if(!$build.passed -or $build.kind -cne 'reader' -or $build.configuration -cne 'ReleaseCPU' -or $build.stage -cne 'upl_case02_flux_window25_build_r1' -or !$build.build_and_source_bindings_unchanged -or !$build.exact_link_closure_verified){throw 'Passed retained independent structural reader required'}
$samples=769;$dt='0.0000025';$mode='--read';if($Job -ceq 'smoke'){$samples=3};if($Job -ceq 'half'){$dt='0.00000125'}
$solver=Get-Content -Raw -LiteralPath $solverPath|ConvertFrom-Json
if(!$solver.passed -or $solver.stage -cne $tag -or !$solver.typed_LASTEXITCODE_captured_immediately -or !$solver.owned_call_exited -or $solver.exit_code -ne 0 -or !$solver.bindings_unchanged -or $solver.native_frames -ne $samples -or !$solver.owned_exit_record){throw 'New completed bound solver and sealed owned exit/frame prerequisite failed'}
Verify @($solver.owned_exit_record);$owned=Get-Content -Raw -LiteralPath $solver.owned_exit_record.path|ConvertFrom-Json
if(!$owned.direct_native_call -or !$owned.typed_LASTEXITCODE_captured_immediately -or !$owned.owned_call_exited -or $owned.exit_code -ne 0 -or $owned.invocation_failure -or $owned.program.sha256 -ine $solver.program.sha256){throw 'Actual sealed typed solver call differs'}
$nativeInputs=@($solver.files);$bindings=@((Entry $PSCommandPath),(Entry (Join-Path $tests 'notes\upl_case02_flux_window25_owners_r1.json')),$readerIdentity,(Entry $solverPath),$solver.owned_exit_record,$build.program,$build.compile_call,$build.link_call,$build.source_build)+@($build.author_files)+@($solver.bindings)
foreach($r in $build.runtime){$bindings+=@($r.original,$r.copy)}
# Solver bindings already bind current source snapshots; this reader has a separate sealed helper build.
Verify $bindings;Verify $nativeInputs;$argv=@($mode,$dataPath,[string]$samples,$dt,$out)
[IO.File]::WriteAllBytes($log,[byte[]]@());$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location ([IO.Path]::GetDirectoryName($build.program.path))
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$ended=[DateTime]::UtcNow.ToString('o');$call=[ordered]@{program=$build.program;arguments=$argv;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;offline_reader_only=$true;solver_started=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($callPath,($call|ConvertTo-Json -Depth 6)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
$unchanged=$false;try{Verify $bindings;Verify $nativeInputs;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -File|ForEach-Object{Entry $_.FullName})};$completionPath=Join-Path $out 'completion.json';$completion=$null;$done=$null
if(Test-Path -LiteralPath $completionPath){$completion=Entry $completionPath;$done=Get-Content -Raw -LiteralPath $completionPath|ConvertFrom-Json}
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $done.passed -and $done.samples -eq $samples -and $done.total_native_count -eq 1040 -and $done.no_exclusions)
$result=[ordered]@{stage=$tag;passed=$passed;job=('flux_window25_'+$Job);scope='Offline structural native decode only; no physical/half/default-OFF comparison acceptance';sealed_solver=(Entry $solverPath);reader_build=$readerIdentity;owned_exit_record=(Entry $callPath);program=$build.program;arguments=$argv;paths=@{native_dir=$out;solver_dir=(Split-Path -Parent $dataPath)};native_input_files=$nativeInputs;bindings=$bindings;bindings_unchanged=$unchanged;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);owned_reader_exit0=($code -is [int] -and $code -eq 0);exit_code=$code;failure=$failure;log=(Entry $log);completion=$completion;files=$files;retained_structural_reader_reused=$false;same_solver_and_reader_source_build_claimed=$false;source_solver_exit_verified=$true;solver_started_by_this_action=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Flux native review rejected; repair offline only, inspect $record"};Write-Output "Flux native review completed; QC not started: $record"
