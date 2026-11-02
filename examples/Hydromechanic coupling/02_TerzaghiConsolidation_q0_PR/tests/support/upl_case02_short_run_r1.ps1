param([Parameter(Mandatory=$true)][ValidateSet('coarse','half')][string]$Window)
# One fresh private CPU short window; no restart, automatic pair or long admission.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$tag='upl_case02_short_'+$Window+'_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_actual_ReleaseCPU_r2.helper.json'
$inputsPath=Join-Path $tests 'logs\upl_case02_short_r1.inputs.json'
$smokePath=Join-Path $tests 'logs\upl_case02_smoke_r1.qc.json'
$offPath=Join-Path $tests 'logs\upl_case02_legacy_off_r1.exact.json'
$record=Join-Path $tests ('logs\'+$tag+'.run.json')
$callPath=Join-Path $tests ('logs\'+$tag+'.solver.call.json')
$log=Join-Path $tests ('logs\'+$tag+'.log')
$out=Join-Path $tests ('outputs\'+$tag)
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($item in $items){$now=Entry $item.path;if($now.bytes -ne $item.bytes -or $now.sha256 -ine $item.sha256){throw "Frozen artifact changed: $($item.path)"}}}
foreach($path in @($out,$record,$log,$callPath)){if(Test-Path -LiteralPath $path){throw "Retained short output protected: $path"}}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
$inputs=Get-Content -Raw -LiteralPath $inputsPath|ConvertFrom-Json
$smoke=Get-Content -Raw -LiteralPath $smokePath|ConvertFrom-Json
$off=Get-Content -Raw -LiteralPath $offPath|ConvertFrom-Json
if(!$build.passed -or $build.kind -cne 'actual' -or $build.configuration -cne 'ReleaseCPU' -or !$build.exact_link_closure_verified -or !$inputs.prepared -or !$smoke.passed -or !$off.passed){throw 'Actual Release helper, prepared input, native smoke and exact default-OFF gates required'}
$selected=@($inputs.jobs|Where-Object{$_.window -ceq $Window})
if($selected.Count -ne 1){throw 'Select exactly one predeclared short window'}
$job=$selected[0]
$bindings=@((Entry $PSCommandPath),(Entry $buildPath),(Entry $inputsPath),(Entry $smokePath),(Entry $offPath),$build.program,$build.compile_call,$build.link_call,$build.source_build,$build.compiler_dependency_record,$job.configuration,$job.runtime,$job.initial_BI4,$job.normals)+@($build.author_files)
foreach($runtime in $build.runtime){$bindings+=@($runtime.original,$runtime.copy)}
if($Window -eq 'half'){
  $coarsePath=Join-Path $tests 'logs\upl_case02_short_coarse_r1.native.check.json'
  $coarse=Get-Content -Raw -LiteralPath $coarsePath|ConvertFrom-Json
  if(!$coarse.passed -or !$coarse.owned_reader_exit0 -or $coarse.job -cne 'short_coarse'){throw 'Completed coarse native safety is required before half'}
  Verify $coarse.files;Verify @($coarse.completion,$coarse.sealed_solver)
  $coarseDone=Get-Content -Raw -LiteralPath $coarse.completion.path|ConvertFrom-Json
  if($coarseDone.samples -ne 519 -or $coarseDone.max_activeDrainCount -le 0 -or $coarseDone.post_open_drained_particle_checks -le 0){throw 'Coarse drainage witness missing; hold half for review'}
  $bindings+=@(Entry $coarsePath)+@($coarse.files)+@($coarse.completion,$coarse.sealed_solver)
}
function VerifyBuild{
  Verify $bindings;Verify $build.objects;Verify $build.canonical_programs_before
  foreach($pair in $build.source_snapshot){Verify @($pair.original,$pair.snapshot)}
}
VerifyBuild
if(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^DualSPHysics.*CPU.*\.exe$|^upl_case02_actual.*\.exe$'}){throw 'A CPU solver is still active; do not duplicate'}
$prefix=[IO.Path]::Combine([IO.Path]::GetDirectoryName($job.runtime.path),[IO.Path]::GetFileNameWithoutExtension($job.runtime.path))
$argv=@('--solver',$Window,'-cpu','-ompthreads:1','-stable','-mdbc_freeslip',$prefix,$out,'-dirdataout','data','-svres',('-nsteps:'+ $job.steps))
$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location ([IO.Path]::GetDirectoryName($build.program.path))
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}
catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
# Seal the actual exit before any output hashing or analysis can fail.
$call=[ordered]@{program=$build.program;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;physical_acceptance=$false}
[IO.File]::WriteAllText($callPath,($call|ConvertTo-Json -Depth 6)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object{Entry $_.FullName})}
$unchanged=$false;try{VerifyBuild;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$completionPath=Join-Path $out 'actual_complete.json';$completion=$null;$done=$null
if(Test-Path -LiteralPath $completionPath){$completion=Entry $completionPath;$done=Get-Content -Raw -LiteralPath $completionPath|ConvertFrom-Json}
$parts=@($files|Where-Object{[IO.Path]::GetFileName($_.path) -match '^Part_\d{4}\.bi4$'})
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $done.passed -and $done.window -ceq $Window -and $done.completed_steps -eq $job.steps -and $parts.Count -eq 519 -and $done.saved_parts -eq 519)
$result=[ordered]@{stage=$tag;passed=$passed;scope='Actual ReleaseCPU short solver exit and final-state checks only; independent full native review required';window=$Window;build=(Entry $buildPath);input_manifest=(Entry $inputsPath);program=$build.program;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;bindings=$bindings;bindings_unchanged=$unchanged;files=$files;native_frames=$parts.Count;completion=$completion;log=$(if(Test-Path -LiteralPath $log){Entry $log}else{$null});post_Run_dterror_is_not_full_history_max=$true;native_review_passed=$false;independent_half_passed=$false;force_stage_load_budget_verified=$false;long_or_formal_admitted=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Short Run rejected; preserve result and inspect $record"}
Write-Output "Short solver completed; decode every native frame before proceeding: $record"
