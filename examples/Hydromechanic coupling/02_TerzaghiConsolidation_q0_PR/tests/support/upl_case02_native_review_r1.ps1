param([Parameter(Mandatory=$true)][ValidateSet('smoke','legacy_off','legacy_control','short_coarse','short_half')][string]$Job)
# One offline decode of an already completed solver; never rerun physics after analysis failure.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$tag='upl_case02_'+$Job+'_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_reader_ReleaseCPU_r2.helper.json'
$record=Join-Path $tests ('logs\'+$tag+'.native.check.json')
$log=Join-Path $tests ('logs\'+$tag+'.native.log')
$out=Join-Path $tests ('outputs\'+$tag+'_native')
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($item in $items){$now=Entry $item.path;if($now.bytes -ne $item.bytes -or $now.sha256 -ine $item.sha256){throw "Frozen artifact changed: $($item.path)"}}}
foreach($path in @($record,$log,$out)){if(Test-Path -LiteralPath $path){throw "Retained analysis protected: $path"}}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if(!$build.passed -or $build.kind -cne 'reader' -or $build.configuration -cne 'ReleaseCPU' -or !$build.exact_link_closure_verified){throw 'Passed current independent native reader required'}
$solverPath=Join-Path $tests ('logs\'+$tag+'.run.json')
$dataPath=Join-Path $tests ('outputs\'+$tag+'\data')
$samples=519;$dt='0.0000025';$mode='--read'
if($Job -eq 'smoke'){$samples=3}
if($Job -eq 'short_half'){$dt='0.00000125'}
if($Job -eq 'legacy_off'){$samples=21;$dt='0.00001';$mode='--read-off'}
if($Job -eq 'legacy_control'){
  $solverPath=Join-Path $tests 'logs\symc_1d_short_r1_cpu_old.completion.json'
  $dataPath=Join-Path $tests 'outputs\symc_1d_short_r1_cpu_old\data'
  $samples=151;$dt='0.00001';$mode='--read-off'
}
$solver=Get-Content -Raw -LiteralPath $solverPath|ConvertFrom-Json
if($Job -eq 'legacy_control'){
  if(!$solver.solver_finished -or !$solver.owned_exited -or $solver.exit_code -ne 0){throw 'Retained control did not finish normally'}
  $nativeInputs=@($solver.outputs);Verify @($solver.program,$solver.config,$solver.bat)
}else{
  if(!$solver.passed -or !$solver.typed_LASTEXITCODE_captured_immediately -or !$solver.owned_call_exited -or $solver.exit_code -ne 0 -or !$solver.bindings_unchanged -or $solver.native_frames -ne $samples){throw 'Completed bound solver exit/frame prerequisite failed'}
  Verify $solver.bindings;$nativeInputs=@($solver.files)
}
$bindings=@((Entry $PSCommandPath),(Entry $buildPath),(Entry $solverPath),$build.program,$build.compile_call,$build.link_call)+@($build.author_files)
foreach($runtime in $build.runtime){$bindings+=@($runtime.original,$runtime.copy)}
Verify $bindings;Verify $nativeInputs
$argv=@($mode,$dataPath,[string]$samples,$dt,$out)
$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location ([IO.Path]::GetDirectoryName($build.program.path))
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}
catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$unchanged=$false;try{Verify $bindings;Verify $nativeInputs;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -File|ForEach-Object{Entry $_.FullName})}
$completionPath=Join-Path $out 'completion.json';$completion=$null;$done=$null
if(Test-Path -LiteralPath $completionPath){$completion=Entry $completionPath;$done=Get-Content -Raw -LiteralPath $completionPath|ConvertFrom-Json}
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $done.passed -and $done.samples -eq $samples -and $done.total_native_count -eq 1040 -and $done.no_exclusions)
$result=[ordered]@{stage=$tag;passed=$passed;job=$Job;scope='Offline native decode and declared single-run gates, not physical/half/default-OFF comparison acceptance';sealed_solver=(Entry $solverPath);reader_build=(Entry $buildPath);program=$build.program;arguments=$argv;paths=@{native_dir=$out;solver_dir=(Split-Path -Parent $dataPath)};native_input_files=$nativeInputs;bindings=$bindings;bindings_unchanged=$unchanged;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);owned_reader_exit0=($code -is [int] -and $code -eq 0);exit_code=$code;failure=$failure;log=$(if(Test-Path -LiteralPath $log){Entry $log}else{$null});completion=$completion;files=$files;source_solver_exit_verified=$true;solver_started_by_this_action=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Native review rejected; repair offline only, inspect $record"}
Write-Output "Offline native review completed: $record"
