param([Parameter(Mandatory=$true)][ValidateSet('smoke','legacy_off','short_coarse','short_half')][string]$Job)
# One offline decode only. The old structural reader is sealed, not claimed to share the new solver source build.
$ErrorActionPreference='Stop';$Job=$Job.ToLowerInvariant();$tests=Split-Path -Parent $PSScriptRoot;$tag='upl_case02_flux_'+$Job+'_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_reader_ReleaseCPU_r2.helper.json';$solverPath=Join-Path $tests "logs\$tag.run.json";$dataPath=Join-Path $tests "outputs\$tag\data"
$record=Join-Path $tests "logs\$tag.native.check.json";$callPath=Join-Path $tests "logs\$tag.reader.call.json";$log=Join-Path $tests "logs\$tag.native.log";$out=Join-Path $tests "outputs\${tag}_native"
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($e in $items){$a=Entry $e.path;if($null -eq $e.bytes -or !$e.sha256 -or $a.bytes -ne $e.bytes -or $a.sha256 -ine $e.sha256){throw "Frozen artifact changed: $($e.path)"}}}
foreach($path in @($record,$callPath,$log,$out)){if(Test-Path -LiteralPath $path){throw "Retained native review protected: $path"}}
$readerIdentity=Entry $buildPath;if($readerIdentity.bytes -ne 357285 -or $readerIdentity.sha256 -ine '51b88f7431ce6afc7de621baf1ecd0540d55d7faebdde17093093950ad78fece'){throw 'Retained actual structural-reader identity differs'}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json;if(!$build.passed -or $build.kind -cne 'reader' -or $build.configuration -cne 'ReleaseCPU' -or !$build.exact_link_closure_verified){throw 'Passed retained independent structural reader required'}
$samples=519;$dt='0.0000025';$mode='--read';if($Job -ceq 'smoke'){$samples=3};if($Job -ceq 'short_half'){$dt='0.00000125'};if($Job -ceq 'legacy_off'){$samples=21;$dt='0.00001';$mode='--read-off'}
$solver=Get-Content -Raw -LiteralPath $solverPath|ConvertFrom-Json
if(!$solver.passed -or $solver.stage -cne $tag -or !$solver.typed_LASTEXITCODE_captured_immediately -or !$solver.owned_call_exited -or $solver.exit_code -ne 0 -or !$solver.bindings_unchanged -or $solver.native_frames -ne $samples -or !$solver.owned_exit_record){throw 'New completed bound solver and sealed owned exit/frame prerequisite failed'}
Verify @($solver.owned_exit_record);$owned=Get-Content -Raw -LiteralPath $solver.owned_exit_record.path|ConvertFrom-Json
if(!$owned.direct_native_call -or !$owned.typed_LASTEXITCODE_captured_immediately -or !$owned.owned_call_exited -or $owned.exit_code -ne 0 -or $owned.invocation_failure -or $owned.program.sha256 -ine $solver.program.sha256){throw 'Actual sealed typed solver call differs'}
$nativeInputs=@($solver.files);$bindings=@((Entry $PSCommandPath),(Entry (Join-Path $tests 'notes\upl_case02_flux_owners_r1.json')),$readerIdentity,(Entry $solverPath),$solver.owned_exit_record,$build.program,$build.compile_call,$build.link_call,$build.source_build)+@($build.author_files)+@($solver.bindings)
foreach($r in $build.runtime){$bindings+=@($r.original,$r.copy)}
# Do not rebind the historical reader's old CPU source original as the current solver source.
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
$result=[ordered]@{stage=$tag;passed=$passed;job=('flux_'+$Job);scope='Offline structural native decode only; no physical/half/default-OFF comparison acceptance';sealed_solver=(Entry $solverPath);reader_build=$readerIdentity;owned_exit_record=(Entry $callPath);program=$build.program;arguments=$argv;paths=@{native_dir=$out;solver_dir=(Split-Path -Parent $dataPath)};native_input_files=$nativeInputs;bindings=$bindings;bindings_unchanged=$unchanged;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);owned_reader_exit0=($code -is [int] -and $code -eq 0);exit_code=$code;failure=$failure;log=(Entry $log);completion=$completion;files=$files;retained_structural_reader_reused=$true;same_solver_and_reader_source_build_claimed=$false;source_solver_exit_verified=$true;solver_started_by_this_action=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Flux native review rejected; repair offline only, inspect $record"};Write-Output "Flux native review completed; QC not started: $record"
