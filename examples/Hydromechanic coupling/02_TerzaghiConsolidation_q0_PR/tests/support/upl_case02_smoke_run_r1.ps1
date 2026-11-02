param([switch]$ExecutionAuthorized)
# One two-step DebugCPU startup only; no automatic short/half or canonical installation.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Explicit reviewed two-step startup action required'}
$tests=Split-Path -Parent $PSScriptRoot
$tag='upl_case02_smoke_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_actual_DebugCPU_r1.helper.json'
$inputsPath=Join-Path $tests 'logs\upl_case02_smoke_r1.inputs.json'
$out=Join-Path $tests ('outputs\'+$tag)
$log=Join-Path $tests ('logs\'+$tag+'.log')
$record=Join-Path $tests ('logs\'+$tag+'.run.json')
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($item in $items){$now=Entry $item.path;if($now.bytes -ne $item.bytes -or $now.sha256 -ine $item.sha256){throw "Frozen input changed: $($item.path)"}}}
foreach($path in @($out,$log,$record)){if(Test-Path -LiteralPath $path){throw "Retained output protected: $path"}}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
$inputs=Get-Content -Raw -LiteralPath $inputsPath|ConvertFrom-Json
if(!$build.passed -or $build.configuration -cne 'DebugCPU' -or $build.CPU_non_main_objects -ne 85 -or !$build.exact_link_object_closure_verified -or !$inputs.prepared -or $inputs.steps -ne 2 -or $inputs.expected_frames -ne 3){throw 'Reviewed DebugCPU build and two-step input required'}
$bindings=@((Entry $PSCommandPath),(Entry $buildPath),(Entry $inputsPath),$build.program,$build.compile_call,$build.link_call,$build.source_build,$build.compiler_dependency_record,$inputs.configuration,$inputs.runtime,$inputs.initial_BI4,$inputs.normals)+@($build.author_files)+@($build.objects)+@($build.canonical_programs_before)
foreach($pair in $build.source_snapshot){$bindings+=@($pair.original,$pair.snapshot)}
foreach($runtime in $build.runtime){$bindings+=@($runtime.original,$runtime.copy)}
Verify $bindings
if(Get-CimInstance Win32_Process|Where-Object{$_.Name -eq 'upl_case02_actual_r1.exe'}){throw 'A case02 private solver is already running; do not duplicate'}
$prefix=[IO.Path]::Combine([IO.Path]::GetDirectoryName($inputs.runtime.path),[IO.Path]::GetFileNameWithoutExtension($inputs.runtime.path))
$argv=@('--solver','smoke','-cpu','-ompthreads:1','-stable','-mdbc_freeslip',$prefix,$out,'-dirdataout','data','-svres','-nsteps:2')
$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o')
$oldPreference=$ErrorActionPreference
Push-Location ([IO.Path]::GetDirectoryName($build.program.path))
try{
  $ErrorActionPreference='Continue'
  $global:LASTEXITCODE=$null
  & $build.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host
  $code=$LASTEXITCODE
}catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object{Entry $_.FullName})}
$unchanged=$false
try{Verify $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$completePath=Join-Path $out 'actual_complete.json'
$completion=$null;$complete=$null
if(Test-Path -LiteralPath $completePath){$completion=Entry $completePath;$complete=Get-Content -Raw -LiteralPath $completePath|ConvertFrom-Json}
$parts=@($files|Where-Object{[IO.Path]::GetFileName($_.path) -match '^Part_\d{4}\.bi4$'})
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $complete.passed -and $complete.completed_steps -eq 2 -and $complete.saved_parts -eq 3 -and $parts.Count -eq 3)
$result=[ordered]@{stage=$tag;passed=$passed;scope='Actual DebugCPU two-step Run and final persistent-state checks only; native field audit still required';started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');program=$build.program;arguments=$argv;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;bindings=$bindings;bindings_unchanged=$unchanged;log=$(if(Test-Path -LiteralPath $log){Entry $log}else{$null});completion=$completion;files=$files;native_frames=$parts.Count;post_Run_dterror_note='The helper max_signed_dterror_s field is a post-final-save query and may be the -DBL_MAX empty-interval sentinel. It is NOT a full-history maximum or a passed native safety gate; read every saved noninitial frame independently.';native_review_passed=$false;half_or_long_admitted=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Startup rejected; inspect retained $record"}
Write-Output "Two-step actual Run completed; independent native review required: $record"
