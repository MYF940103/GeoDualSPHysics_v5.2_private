param([switch]$ExecutionAuthorized)
# Standalone frozen actual-header operator, not a project/physical solver or a wall implementation.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Authoring is not execution permission; wait for independent/root review'}
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$name='upl_p3_wall_mirror_r2';$dir=Join-Path $tests "outputs\$name"
$receipt=Join-Path $tests "logs\$name.check.json"
$cpp=Join-Path $PSScriptRoot ($name+'.cpp');$note=Join-Path $tests "notes\$name.json"
$freezePath=Join-Path $tests 'logs\upl_p3_time_build_r1.json'
function Entry([string]$path){$i=Get-Item -LiteralPath $path;[ordered]@{path=$i.FullName;bytes=$i.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.sha256 -ne $r.sha256 -or $a.bytes -ne $r.bytes){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$path,$value){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if((Test-Path -LiteralPath $dir) -or (Test-Path -LiteralPath $receipt)){throw 'Fresh offline label required; do not overwrite'}
$freeze=Get-Content -LiteralPath $freezePath -Raw|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'){throw 'Authoritative source freeze unavailable'}
foreach($pair in $freeze.source){Verify @($pair.original,$pair.snapshot)}
$paths=@($PSCommandPath,$cpp,$note,$freezePath,(Join-Path $source 'source\JSph.cpp'),(Join-Path $source 'source\JSphCpu.cpp'),(Join-Path $source 'source\JSphCpuSingle.cpp'))
$paths+=Get-ChildItem -LiteralPath (Join-Path $source 'source') -File|Where-Object {$_.Extension -eq '.h'}|ForEach-Object {$_.FullName}
$inputs=@($paths|Sort-Object -Unique|ForEach-Object {Entry $_})
New-Item -ItemType Directory -Path $dir|Out-Null
$snapshots=@(foreach($p in @($PSCommandPath,$cpp,$note)){$dest=Join-Path $dir ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$e=Entry $dest;if($e.sha256 -ne (Entry $p).sha256){throw 'Recipe snapshot mismatch'};$e})
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'Visual Studio environment setup failed'}
foreach($line in $lines){$at=$line.IndexOf('=');if($at -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$at),$line.Substring($at+1),'Process')}}
$exe=Join-Path $dir ($name+'.exe');$buildLog=Join-Path $tests "logs\$name.build.log";$runLog=Join-Path $tests "logs\$name.run.log"
if((Test-Path -LiteralPath $buildLog) -or (Test-Path -LiteralPath $runLog)){throw 'Retained logs protected'}
$compile=@('/nologo','/std:c++17','/EHsc','/W3','/O2','/MT','/fp:precise',"/I$source\source","/Fo$dir\mirror.obj","/Fe$exe",'/sourceDependencies',"$dir\compile.dependencies.json",$cpp)
$start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
& cl.exe @compile 2>&1|Tee-Object -FilePath $buildLog|Out-Host
$buildExit=$LASTEXITCODE;$runExit=$null;$completion=$null
if($buildExit -eq 0){
  & $exe $dir 2>&1|Tee-Object -FilePath $runLog|Out-Host;$runExit=$LASTEXITCODE
  if($runExit -eq 0){$completion=Get-Content -LiteralPath (Join-Path $dir 'complete.json') -Raw|ConvertFrom-Json}
}
$ErrorActionPreference=$old
Verify $inputs;Verify $snapshots;foreach($pair in $freeze.source){Verify @($pair.original,$pair.snapshot)}
$passed=$buildExit -eq 0 -and $runExit -eq 0 -and $completion.passed -and $completion.cases -eq 48 -and $completion.probe_pairs -eq 144 -and $completion.wrong_C_detected_probes -gt 0 -and !$completion.physical_acceptance
$files=@(Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Entry $_.FullName})
$logs=@(foreach($p in @($buildLog,$runLog)){if(Test-Path -LiteralPath $p){Entry $p}})
NewJson $receipt ([ordered]@{passed=$passed;offline_operator_only=$true;production_source_changed=$false;production_dynamic_function_called=$false;project_solver_or_GenCase_started=$false;actual_wall_or_mdbc_acceptance=$false;physical_acceptance=$false;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');build_exit=$buildExit;program_exit=$runExit;compile=$compile;program_arguments=@($dir);source_freeze=(Entry $freezePath);inputs=$inputs;snapshots=$snapshots;completion=$completion;files=$files;logs=$logs})
if(!$passed){throw 'Frozen mirror operator rejected; preserve all artifacts, do not retry this label or relax bounds'}
Write-Output "OFFLINE MIRROR OPERATOR COMPLETE $receipt"
