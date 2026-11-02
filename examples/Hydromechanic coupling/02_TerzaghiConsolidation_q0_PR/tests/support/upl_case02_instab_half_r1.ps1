# Fresh time-step diagnostic after reviewed coarse rejection, NOT a half-step acceptance sequence.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$tag='upl_case02_instab_half_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_actual_ReleaseCPU_r2.helper.json'
$planPath=Join-Path $tests 'logs\upl_case02_short_r1.inputs.json'
$rejectedPath=Join-Path $tests 'logs\upl_case02_short_coarse_r1.run.json'
$out=Join-Path $tests ('outputs\'+$tag)
$record=Join-Path $tests ('logs\'+$tag+'.run.json')
$callPath=Join-Path $tests ('logs\'+$tag+'.solver.call.json')
$log=Join-Path $tests ('logs\'+$tag+'.log')
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($item in $items){$now=Entry $item.path;if($now.bytes -ne $item.bytes -or $now.sha256 -ine $item.sha256){throw "Frozen diagnostic input changed: $($item.path)"}}}
foreach($path in @($out,$record,$callPath,$log)){if(Test-Path -LiteralPath $path){throw "Retained diagnostic protected: $path"}}
$build=Get-Content -Encoding UTF8 -Raw -LiteralPath $buildPath|ConvertFrom-Json
$plan=Get-Content -Encoding UTF8 -Raw -LiteralPath $planPath|ConvertFrom-Json
$old=Get-Content -Encoding UTF8 -Raw -LiteralPath $rejectedPath|ConvertFrom-Json
if(!$build.passed -or $build.configuration -cne 'ReleaseCPU' -or $old.passed -ne $false -or $old.exit_code -ne 1 -or !$old.owned_call_exited -or $old.native_frames -ne 76){throw 'Reviewed failed coarse and actual unchanged Release helper required'}
Verify $old.files
$selected=@($plan.jobs|Where-Object{$_.window -ceq 'half'});if($selected.Count -ne 1){throw 'One unchanged prepared half-dt input required'}
$job=$selected[0]
$bindings=@((Entry $PSCommandPath),(Entry $buildPath),(Entry $planPath),(Entry $rejectedPath),$build.program,$job.configuration,$job.runtime,$job.initial_BI4,$job.normals)+@($build.author_files)
foreach($r in $build.runtime){$bindings+=@($r.original,$r.copy)}
function VerifyBuild{Verify $bindings;Verify $build.objects;Verify $build.canonical_programs_before;foreach($p in $build.source_snapshot){Verify @($p.original,$p.snapshot)}}
VerifyBuild
if(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^DualSPHysics.*CPU.*\.exe$|^upl_case02_actual.*\.exe$'}){throw 'Existing CPU solver is active; no duplicate'}
$prefix=[IO.Path]::Combine([IO.Path]::GetDirectoryName($job.runtime.path),[IO.Path]::GetFileNameWithoutExtension($job.runtime.path))
$argv=@('--solver','half','-cpu','-ompthreads:1','-stable','-mdbc_freeslip',$prefix,$out,'-dirdataout','data','-svres','-nsteps:10000')
$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location ([IO.Path]::GetDirectoryName($build.program.path))
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}
catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$call=[ordered]@{program=$build.program;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;diagnostic_only=$true;half_validation_or_physical_acceptance=$false}
[IO.File]::WriteAllText($callPath,($call|ConvertTo-Json -Depth 6)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object{Entry $_.FullName})}
$unchanged=$false;try{VerifyBuild;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$parts=@($files|Where-Object{[IO.Path]::GetFileName($_.path) -match '^Part_\d{4}\.bi4$'})
$completed=Test-Path -LiteralPath (Join-Path $out 'actual_complete.json')
$result=[ordered]@{stage=$tag;status='diagnostic_call_sealed_pending_failure_or_success_review';owned_exit_record=(Entry $callPath);exit_code=$code;owned_call_exited=($code -is [int]);bindings=$bindings;bindings_unchanged=$unchanged;files=$files;native_frames=$parts.Count;actual_complete_exists=$completed;failure=$failure;reason='Only dt is reduced2x after reviewed early coarse growth; same model/geometry/load/drainage and all original production guards. This is not admission past a failed coarse gate.';source_build=(Entry $buildPath);input_manifest=(Entry $planPath);rejected_control=(Entry $rejectedPath);solver_restarted_from_PART=$false;accepted_half_pair=$false;long_or_formal_admitted=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if($code -isnot [int] -or $failure -or !$unchanged){throw "Diagnostic ownership/binding failure; inspect $record"}
Write-Output "Diagnostic actual exit $code retained; no physical or half acceptance: $record"
