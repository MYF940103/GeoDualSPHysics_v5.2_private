param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [switch]$ReviewedForExecution
)
# Standalone frozen-field screening. Never builds/replaces the production project or starts its solver.
$ErrorActionPreference='Stop'
if(!$ReviewedForExecution){throw 'Author-only until the root reviewer explicitly approves this exact screening recipe.'}
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$logs=Join-Path $tests 'logs'
$name="upl_p3_pair_${Configuration}_$Label"
$folder=Join-Path $tests "outputs\$name"
$harness=Join-Path $PSScriptRoot 'upl_p3_pair_r1.cpp'
$note=Join-Path $tests 'notes\upl_p3_pair_r1.json'
$exe=Join-Path $folder 'upl_p3_pair_r1.exe'
$buildReceipt=Join-Path $logs ($name+'.build.json')
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[pscustomobject][ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($entries){foreach($i in $entries){$f=Entry $i.path;if($f.sha256 -ne $i.sha256 -or $f.bytes -ne $i.bytes){throw "Frozen artifact changed: $($i.path)"}}}
function NewJson([string]$path,$value){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 14)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $buildReceipt)){throw 'Use a fresh label; no build overwrite'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'Visual Studio environment setup failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -File -Recurse|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($harness,$PSCommandPath,$note)+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  New-Item -ItemType Directory -Path $folder|Out-Null
  $snapshots=@();foreach($p in @($harness,$PSCommandPath,$note)){$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;if((Entry $dest).sha256 -ne (Entry $p).sha256){throw 'Used-recipe snapshot mismatch'};$snapshots+=Entry $dest}
  $log=Join-Path $logs ($name+'.build.log');if(Test-Path -LiteralPath $log){throw 'Retained build log protected'}
  [IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($Configuration -eq 'Debug'){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/std:c++17','/EHsc','/W3','/fp:precise',"/I$source\source","/Fo$folder\upl_p3_pair_r1.obj","/Fe$exe","/Fd$folder\compile.pdb",'/sourceDependencies',(Join-Path $folder 'compile.dependencies.json'))+$flags+@($harness,'/link','/MACHINE:X64','/SUBSYSTEM:CONSOLE')
  if($Configuration -eq 'Debug'){$compile+=@('/DEBUG',"/PDB:$folder\link.pdb")}
  $started=[DateTime]::UtcNow.ToString('o');$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log|Out-Host
  $exitCode=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  Verify $inputs;Verify $snapshots
  NewJson $buildReceipt ([ordered]@{status=if($exitCode -eq 0){'built_not_run'}else{'build_rejected_retained'};started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');exit_code=$exitCode;configuration=$Configuration;git_head=(& git -C $repo rev-parse HEAD);inputs=$inputs;snapshots=$snapshots;command=$compile;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};log=(Entry $log);production_objects_used=$false;production_program_replaced=$false;solver_started=$false;physical_acceptance=$false})
  if($exitCode -ne 0){throw 'Standalone screening compile rejected; preserve evidence and diagnose'}
  Write-Output "BUILT frozen-field standalone screening, not run: $exe";exit 0
}
if($Mode -eq 'Run'){
  $b=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
  if($b.status -ne 'built_not_run'){throw 'No successful frozen standalone build'}
  Verify $b.inputs;Verify $b.snapshots;Verify @($b.program)
  $runName=$name+'_run';$out=Join-Path $tests "outputs\$runName"
  $log=Join-Path $logs ($runName+'.log');$receipt=Join-Path $logs ($runName+'.run.json');$check=Join-Path $logs ($runName+'.check.json')
  if((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt) -or (Test-Path -LiteralPath $check)){throw 'Retained output protected; no automatic retry'}
  $program=Entry $exe;$arguments=@('--out',$out);$started=[DateTime]::UtcNow.ToString('o')
  [IO.File]::WriteAllBytes($log,[byte[]]@());$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @arguments 2>&1|Tee-Object -FilePath $log|Out-Host
  $exitCode=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  NewJson $receipt ([ordered]@{exit_code=$exitCode;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');owned_call_exited=$true;program=$program;build_receipt=(Entry $buildReceipt);arguments=$arguments;log=(Entry $log);solver_started=$false;physical_acceptance=$false})
  if($exitCode -ne 0){throw 'Frozen screening gate rejected; preserve data and diagnose without repeating this label'}
  Verify $b.inputs;Verify $b.snapshots;Verify @($b.program)
  $done=Get-Content -LiteralPath (Join-Path $out 'complete.json') -Raw|ConvertFrom-Json
  if(!$done.frozen_algebraic_gates_passed -or $done.patches -ne 4 -or $done.operators -ne 3 -or $done.fields_per_patch -ne 13 -or $done.node_operator_rows -ne 63180 -or $done.actual_production_rate_pass_called -or $done.production_overwrite_sentinel_verified -or $done.physical_acceptance){throw 'Completion disagrees with reviewed frozen-field scope'}
  $files=@(Get-ChildItem -LiteralPath $out -File|Sort-Object Name|ForEach-Object {Entry $_.FullName});Verify $files
  NewJson $check ([ordered]@{frozen_algebraic_gates_passed=$true;completion=$done;run_receipt=(Entry $receipt);build_receipt=(Entry $buildReceipt);files=$files;manifest_posthoc=$true;candidate_admission_requires_defect_review=$true;production_rate_overwrite_verified=$false;solver_started=$false;physical_acceptance=$false})
  Write-Output "Frozen algebraic gates passed; inspect constant-flux/core continuum defects before candidate admission: $check";exit 0
}
