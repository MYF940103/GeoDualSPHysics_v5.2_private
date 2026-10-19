param(
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1dbg',
  [ValidateRange(20,10000)][int]$Repeat=200,
  [switch]$Run
)
# Standalone class comparison only. Does not build or run the physical solver.
# The caller separately performs the authoritative CPU Debug solution build.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src\source'
$name="hg_cpu_cache_$Label"
$output=Join-Path $tests "outputs\$name"
$logs=Join-Path $tests 'logs'
$buildLog=Join-Path $logs "$name.build.log"
$manifest=Join-Path $logs "$name.build.json"
$check=Join-Path $logs "$name.check.json"
$runLog=Join-Path $logs "$name.run.log"
$runRecord=Join-Path $logs "$name.run.json"
foreach($path in @($output,$buildLog,$manifest,$check,$runLog,$runRecord)){
  if(Test-Path -LiteralPath $path){throw "Refusing overwrite: $path"}
}
$snapshotRecord=Join-Path $logs 'hg_release_base.json'
$snapshot=Get-Content -LiteralPath $snapshotRecord -Raw -Encoding UTF8|ConvertFrom-Json
$oldFiles=@('source\JSphHourglassCpu.h','source\JSphHourglassCpu.cpp')
foreach($relative in $oldFiles){
  $entry=@($snapshot.entries|Where-Object{$_.relative -eq $relative})
  if($entry.Count -ne 1){throw "Missing frozen HG source: $relative"}
  $path=Join-Path $snapshot.snapshot $relative
  if((Get-FileHash -LiteralPath $path).Hash -ne $entry[0].sha256){throw "Frozen HG source changed: $path"}
}
$expectedSnapshot=Join-Path $tests 'outputs\hg_release_base'
if([IO.Path]::GetFullPath($snapshot.snapshot) -ne [IO.Path]::GetFullPath($expectedSnapshot)){
  throw 'Fixture include requires the retained hg_release_base snapshot.'
}
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$compiler=(Get-Command cl.exe).Source
$linker=(Get-Command link.exe).Source
$fixture=Join-Path $PSScriptRoot 'hg_cpu_cache_test.cpp'
$reference=Join-Path $PSScriptRoot 'hg_cpu_cache_reference.cpp'
$candidate=Join-Path $source 'JSphHourglassCpu.cpp'
$debug=$Configuration -eq 'DebugCPU'
$flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
function HashFiles($paths){@($paths|Sort-Object -Unique|ForEach-Object{[ordered]@{
  path=$_;bytes=(Get-Item -LiteralPath $_).Length;sha256=(Get-FileHash -LiteralPath $_).Hash
}})}
$inputs=HashFiles (@($PSCommandPath,$fixture,$reference,$candidate,(Join-Path $source 'JSphHourglassCpu.h'),
  $snapshotRecord,$compiler,$linker)+@($oldFiles|ForEach-Object{Join-Path $snapshot.snapshot $_}))
$null=New-Item -ItemType Directory -Path $output
$started=[DateTime]::UtcNow.ToString('o')
$commands=@()
$objects=@()
$dependencyFiles=@()
foreach($unit in @($fixture,$reference,$candidate)){
  $stem=[IO.Path]::GetFileNameWithoutExtension($unit)
  $object=Join-Path $output "$stem.obj"
  $dependencies=Join-Path $output "$stem.dependencies.json"
  $args=@('/nologo','/c','/std:c++17','/EHsc','/W4','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',
    "/I$source","/Fo$object","/Fd$output\compile.pdb",'/sourceDependencies',$dependencies)+$flags+@($unit)
  $commands+= ,(@($compiler)+$args)
  & $compiler @args 2>&1 | Tee-Object -FilePath $buildLog -Append
  if($LASTEXITCODE){throw 'Cache fixture compilation failed; retain evidence and choose a fresh label.'}
  $objects+=$object;$dependencyFiles+=$dependencies
}
$exe=Join-Path $output 'hg_cpu_cache_test.exe'
$link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/VERBOSE:LIB',"/OUT:$exe")+$objects+@('kernel32.lib')
if($debug){$link+=@('/DEBUG',"/PDB:$output\link.pdb")}
& $linker @link 2>&1 | Tee-Object -FilePath $buildLog -Append
if($LASTEXITCODE){throw 'Cache fixture link failed; retain evidence and choose a fresh label.'}
foreach($entry in $inputs){if((Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256){throw "Build input changed: $($entry.path)"}}
$includes=@($dependencyFiles|ForEach-Object{(Get-Content -LiteralPath $_ -Raw|ConvertFrom-Json).Data.Includes})
$implicitLibs=@([regex]::Matches((Get-Content -LiteralPath $buildLog -Raw),'(?im)([A-Z]:\\[^\r\n]*?\.lib)(?=[:(\s]|$)')|
  ForEach-Object{$_.Groups[1].Value}|Where-Object{Test-Path -LiteralPath $_})
$resolved=HashFiles ($includes+$implicitLibs+$objects)
[ordered]@{
  status='built_not_run';configuration=$Configuration;started_utc=$started;finished_utc=[DateTime]::UtcNow.ToString('o')
  fixture=$fixture;reference_class='JSphHourglassCpuReference';candidate_class='JSphHourglassCpu'
  reference_snapshot=$snapshot.snapshot;inputs=$inputs;resolved_compile_link_inputs=$resolved
  compile_commands=$commands;link_command=@($linker)+$link;exe=$exe;exe_sha256=(Get-FileHash -LiteralPath $exe).Hash
  build_log_sha256=(Get-FileHash -LiteralPath $buildLog).Hash
  limitations=@('Standalone class arithmetic/guard regression; no physical solver or whole-run timing.',
    'JObject exception presentation stubbed as runtime_error; original rejection texts checked.',
    'Production CPU Debug build and coupled trajectory regression remain separate acceptance requirements.')
}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $manifest -Encoding UTF8
Write-Output "BUILT $exe"
if($Run){
  $runStarted=[DateTime]::UtcNow.ToString('o')
  $clock=[Diagnostics.Stopwatch]::StartNew()
  & $exe $check $Repeat 2>&1|Tee-Object -FilePath $runLog
  $exitCode=$LASTEXITCODE;$clock.Stop()
  $unchanged=$true
  foreach($entry in @($inputs)+@($resolved)){
    if((Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256){$unchanged=$false}
  }
  $outputs=@($runLog);if(Test-Path -LiteralPath $check){$outputs+=$check}
  [ordered]@{
    status=if($exitCode -eq 0 -and $unchanged){'standalone_check_completed'}else{'failed_or_changed'}
    started_utc=$runStarted;finished_utc=[DateTime]::UtcNow.ToString('o');elapsed_seconds=$clock.Elapsed.TotalSeconds
    command=@($exe,$check,[string]$Repeat);exit_code=$exitCode;inputs_unchanged=$unchanged
    build_record=$manifest;build_record_sha256=(Get-FileHash -LiteralPath $manifest).Hash
    executable_sha256=(Get-FileHash -LiteralPath $exe).Hash;outputs=(HashFiles $outputs)
  }|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $runRecord -Encoding UTF8
  if($exitCode -ne 0 -or !$unchanged){throw 'Cache regression failed or inputs changed; inspect retained records.'}
}
