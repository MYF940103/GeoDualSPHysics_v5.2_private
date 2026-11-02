param([switch]$ExecutionAuthorized)
# Independent default-u-pw regression. The old 151-frame result is never rerun or overwritten.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Explicit independent default-OFF regression required'}
$tests=Split-Path -Parent $PSScriptRoot
$tag='upl_case02_legacy_off_r1'
$buildPath=Join-Path $tests 'logs\upl_case02_cpu_ReleaseCPU_r1.build.json'
$runtimePath=Join-Path $tests 'logs\upl_case02_actual_DebugCPU_r1.helper.json'
$controlPath=Join-Path $tests 'logs\symc_1d_short_r1_cpu_old.completion.json'
$seed=Join-Path $tests 'outputs\symc_1d_short_r1_cpu_old\symc_1d_short_r1_cpu_old'
$seedDir=Join-Path $tests ('outputs\'+$tag+'_seed')
$prefix=Join-Path $seedDir $tag
$config=Join-Path $tests ('configs\'+$tag+'.xml')
$out=Join-Path $tests ('outputs\'+$tag)
$record=Join-Path $tests ('logs\'+$tag+'.run.json')
$log=Join-Path $tests ('logs\'+$tag+'.log')
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($item in $items){$now=Entry $item.path;if($now.bytes -ne $item.bytes -or $now.sha256 -ine $item.sha256){throw "Frozen artifact changed: $($item.path)"}}}
foreach($path in @($seedDir,$config,$out,$record,$log)){if(Test-Path -LiteralPath $path){throw "Retained regression protected: $path"}}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
$runtime=Get-Content -Raw -LiteralPath $runtimePath|ConvertFrom-Json
$control=Get-Content -Raw -LiteralPath $controlPath|ConvertFrom-Json
if(!$build.passed -or $build.configuration -cne 'ReleaseCPU' -or $build.exit_code -ne 0 -or !$build.source_bindings_unchanged -or !$build.exact_object_basename_closure -or !$runtime.passed -or $runtime.runtime.Count -ne 4 -or !$control.solver_finished -or !$control.owned_exited -or $control.exit_code -ne 0){throw 'Actual Release build, matching runtime and completed old native control required'}
$bindings=@((Entry $PSCommandPath),(Entry $buildPath),(Entry $runtimePath),(Entry $controlPath),$build.program)
$seeds=@(Entry ($seed+'.xml');Entry ($seed+'.bi4');Entry ($seed+'_Normals.nbi4'))
$expected=@('06ea556c3555ad86d53491984897120119596bc90f209c0545196a4f3beced9c','f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac','0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97')
for($i=0;$i -lt 3;$i++){if($seeds[$i].sha256 -cne $expected[$i]){throw 'Original case02 seed differs'}}
$bindings+=$seeds
function VerifyBuild{
  Verify $bindings;Verify $build.objects;Verify $build.canonical_programs_before
  foreach($pair in $build.source_snapshot){Verify @($pair.original,$pair.snapshot)}
}
VerifyBuild
if(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^DualSPHysics.*CPU.*\.exe$|^upl_case02_actual.*\.exe$'}){throw 'A CPU physical solver is already running; avoid an unintended duplicate'}
$runtimeCopies=@()
foreach($r in $runtime.runtime){
  Verify @($r.original,$r.copy)
  $target=Join-Path ([IO.Path]::GetDirectoryName($build.program.path)) ([IO.Path]::GetFileName($r.copy.path))
  if(Test-Path -LiteralPath $target){throw 'New isolated Release runtime unexpectedly already exists'}
  Copy-Item -LiteralPath $r.copy.path -Destination $target
  $copied=Entry $target;if($copied.sha256 -ine $r.copy.sha256){throw 'Runtime copy differs'}
  $runtimeCopies+=@{source=$r.copy;copy=$copied};$bindings+=@($r.original,$r.copy,$copied)
}
$xml=New-Object Xml.XmlDocument;$xml.PreserveWhitespace=$true;$xml.Load($seed+'.xml')
$nodes=$xml.SelectNodes('/case/execution/parameters/parameter[@key="TimeMax"]')
if($nodes.Count -ne 1 -or $nodes[0].GetAttribute('value') -cne '0.15' -or $xml.SelectNodes('//HydroMechDynamicSeepage').Count){throw 'Original default-OFF runtime differs'}
$nodes[0].SetAttribute('value','0.02')
$nodes[0].SetAttribute('comment','Default-u-pw regression only; retained actual final state follows 2001 steps, not a rounded nominal clock')
[void](New-Item -ItemType Directory -Path $seedDir)
$xml.Save($config);Copy-Item -LiteralPath $config -Destination ($prefix+'.xml')
foreach($suffix in @('.bi4','_Normals.nbi4')){Copy-Item -LiteralPath ($seed+$suffix) -Destination ($prefix+$suffix)}
$prepared=@(Entry $config;Entry ($prefix+'.xml');Entry ($prefix+'.bi4');Entry ($prefix+'_Normals.nbi4'))
if($prepared[2].sha256 -cne $seeds[1].sha256 -or $prepared[3].sha256 -cne $seeds[2].sha256){throw 'Copied initial state or normals differ'}
$bindings+=$prepared;VerifyBuild
# Old frame20 is step2000 at .020009999999999355, not step1999 at nominal .02.
$argv=@('-cpu','-ompthreads:1','-stable','-mdbc',$prefix,$out,'-dirdataout','data','-svres','-svextraparts:1','-nsteps:2001')
$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location ([IO.Path]::GetDirectoryName($build.program.path))
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}
catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$files=@();if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object{Entry $_.FullName})}
$unchanged=$false;try{VerifyBuild;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$parts=@($files|Where-Object{[IO.Path]::GetFileName($_.path) -match '^Part_\d{4}\.bi4$'})
$finished=(Test-Path -LiteralPath (Join-Path $out 'Run.out')) -and (Select-String -LiteralPath (Join-Path $out 'Run.out') -SimpleMatch '[Simulation finished' -Quiet)
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $parts.Count -eq 21 -and $finished)
$result=[ordered]@{stage=$tag;passed=$passed;scope='Owned default-OFF Release solve and output sealing only; exact native comparison pending';source_build=(Entry $buildPath);retained_control=(Entry $controlPath);program=$build.program;runtime=$runtimeCopies;prepared_inputs=$prepared;input_differences='Runtime TimeMax .15 to .02 plus explanatory comment only; unchanged original HG/SPR/viscosity/damping/Vel0 and absent dynamic XML master';new_GenCase_run=$false;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;normal_finish_marker=$finished;bindings=$bindings;bindings_unchanged=$unchanged;files=$files;native_frames=$parts.Count;log=$(if(Test-Path -LiteralPath $log){Entry $log}else{$null});exact_native_comparison_passed=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Default-OFF regression run rejected; inspect $record"}
Write-Output "Default-OFF solve completed; exact native comparison still required: $record"
