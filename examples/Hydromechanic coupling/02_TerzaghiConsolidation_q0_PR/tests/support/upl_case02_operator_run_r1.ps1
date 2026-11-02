param([Parameter(Mandatory=$true)][ValidateSet('smoke','matrix')][string]$Mode)
# Frozen real force calls only: no time integration or physical acceptance.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$configuration=if($Mode -eq 'smoke'){'DebugCPU'}else{'ReleaseCPU'}
$tag='upl_case02_operator_'+$Mode+'_r1'
$record=Join-Path $tests ('logs\'+$tag+'.run.json')
$log=Join-Path $tests ('logs\'+$tag+'.log')
$out=Join-Path $tests ('outputs\'+$tag)
$buildPath=Join-Path $tests ('logs\upl_case02_operator_'+$configuration+'_r1.helper.json')
$inputsPath=Join-Path $tests 'logs\upl_case02_short_r1.inputs.json'
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($e in $items){$n=Entry $e.path;if($n.bytes -ne $e.bytes -or $n.sha256 -ine $e.sha256){throw "Changed evidence: $($e.path)"}}}
foreach($p in @($record,$log,$out)){if(Test-Path -LiteralPath $p){throw "Retained diagnostic protected: $p"}}
$build=Get-Content -Encoding UTF8 -Raw -LiteralPath $buildPath|ConvertFrom-Json
if(!$build.passed -or $build.configuration -cne $configuration -or !$build.build_and_source_bindings_unchanged -or $build.program_run -ne $false){throw 'Expected current isolated operator build'}
$inputs=Get-Content -Encoding UTF8 -Raw -LiteralPath $inputsPath|ConvertFrom-Json
$xml=Join-Path $tests 'outputs\upl_case02_short_r1_seed\upl_case02_short_coarse_r1.xml'
$prefix=$xml.Substring(0,$xml.Length-4)
$seed=@($inputs.jobs|Where-Object{$_.window -ceq 'coarse'})
if(!$inputs.prepared -or $seed.Count -ne 1 -or $seed[0].runtime.path -ine $xml){throw 'Expected the sealed original coarse seed'}
Verify @($seed[0].runtime,$seed[0].initial_BI4,$seed[0].normals)
$bindings=@((Entry $PSCommandPath),(Entry $buildPath),(Entry $inputsPath),$build.program)+@($build.author_files)+@($build.objects)+@($build.libraries)+@($build.canonical_programs_before)
foreach($pair in $build.source_snapshot){$bindings+=@($pair.original,$pair.snapshot)}
foreach($runtime in $build.runtime){$bindings+=@($runtime.original,$runtime.copy)}
$bindings+=@($seed[0].runtime,$seed[0].initial_BI4,$seed[0].normals)
if($Mode -eq 'matrix'){
  $prerequisite=Join-Path $tests 'logs\upl_case02_operator_smoke_r1.run.json'
  $smoke=Get-Content -Encoding UTF8 -Raw -LiteralPath $prerequisite|ConvertFrom-Json
  if(!$smoke.passed -or $smoke.exit_code -ne 0 -or !$smoke.bindings_unchanged){throw 'Debug frozen smoke must pass first'}
  $bindings+=@((Entry $prerequisite),$smoke.completion)
}
Verify $bindings
$argv=@(('--'+$Mode),'--input',$xml,'--out',$out)
$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
[IO.File]::WriteAllText($log,'',(New-Object Text.UTF8Encoding($false)))
Push-Location (Split-Path -Parent $build.program.path)
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}
catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$unchanged=$false;try{Verify $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$completionPath=Join-Path $out 'completion.json';$completion=$null;$component=$false
if(Test-Path -LiteralPath $completionPath){$completion=Entry $completionPath;$done=Get-Content -Encoding UTF8 -Raw -LiteralPath $completionPath|ConvertFrom-Json;$component=($done.passed -and $done.mode -ceq $Mode -and $done.actual_time_s -eq 0 -and $done.completed_physical_steps -eq 0 -and $done.physical_acceptance -eq $false)}
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -File|ForEach-Object{Entry $_.FullName})}
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $component)
$result=[ordered]@{stage=$tag;passed=$passed;mode=$Mode;configuration=$configuration;program=$build.program;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;bindings=$bindings;bindings_unchanged=$unchanged;completion=$completion;files=$files;log=(Entry $log);physical_steps=0;solver_trajectory_started=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 15)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Frozen diagnostic rejected; preserve outputs and inspect $record"}
Write-Output "Frozen force component completed, no physical trajectory: $record"
