$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$folder=Join-Path $tests 'outputs\lian_mirror_build_r1'
$receipt=Join-Path $tests 'logs\lian_mirror_runtime_r1.json'
if(Test-Path -LiteralPath $receipt){throw 'Runtime receipt exists; preserve it'}
$files=@()
foreach($name in @('dsphchrono.dll','ChronoEngine.dll','vcomp140.dll','DsphConfig.xml')){
 $source=Join-Path $repo "bin\windows\$name";$target=Join-Path $folder $name
 if(Test-Path -LiteralPath $target){throw "Preserve existing target: $target"}
 Copy-Item -LiteralPath $source -Destination $target
 $hash=(Get-FileHash -LiteralPath $source).Hash
 if((Get-FileHash -LiteralPath $target).Hash -ne $hash){throw 'Runtime copy mismatch'}
 $files+=@{path=$target;source=$source;sha256=$hash}
}
& (Join-Path $folder 'DualSPHysics5.2_win64_debug.exe') -h > $null
$debugExit=$LASTEXITCODE
if($debugExit -ne 0){throw "GPU Debug help still fails: $debugExit"}
& (Join-Path $folder 'DualSPHysics5.2_GEO_win64.exe') -h > $null
$releaseExit=$LASTEXITCODE
if($releaseExit -ne 0){throw "GPU Release help fails: $releaseExit"}
@{passed=$true;cause='Isolated output lacked canonical dsphchrono/Chrono DLL runtime; direct help exited0xc0000135 before CUDA';files=$files;debug_help_exit=$debugExit;release_help_exit=$releaseExit;physics_or_executable_changed=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receipt -Encoding UTF8
