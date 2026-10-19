param([ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1')
# Build the read-only BI4 comparator only; no solver, CUDA build or execution.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Resolve-Path -LiteralPath (Join-Path $tests '..\..\..\..')).Path
$source=Join-Path $repo 'src\source'
$name="hg_gpu_off_compare_$Label"
$output=Join-Path $tests "outputs\$name"
$log=Join-Path $tests "logs\$name.build.log"
$manifest=Join-Path $tests "logs\$name.build.json"
foreach($p in @($output,$log,$manifest)){if(Test-Path -LiteralPath $p){throw "Refusing existing artifact: $p"}}
$names=@('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')
$sources=@($names|ForEach-Object{Join-Path $source "$_.cpp"})
$reader=Join-Path $PSScriptRoot 'hg_gpu_off_compare.cpp'
$inputs=$sources+@($names|ForEach-Object{Join-Path $source "$_.h"})+@($reader,$PSCommandPath)+@(Get-ChildItem -LiteralPath $source -File -Filter '*.h'|ForEach-Object{$_.FullName})
$hashes=@($inputs|Sort-Object -Unique|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})
$environment=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $environment){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
New-Item -ItemType Directory -Path $output|Out-Null
$flags=@('/nologo','/EHsc','/W3','/Od','/Zi','/RTC1','/MTd','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source",'/Fo.\')
$exe=Join-Path $output 'hg_gpu_off_compare.exe'
Push-Location $output
try{
  & cl.exe @flags /std:c++14 /c @sources 2>&1|Tee-Object -FilePath $log
  if($LASTEXITCODE){throw 'BI4 dependency compile failed'}
  $objects=@($names|ForEach-Object{"$_.obj"})
  & cl.exe @flags /std:c++17 /Fehg_gpu_off_compare.exe $reader @objects 2>&1|Tee-Object -FilePath $log -Append
  if($LASTEXITCODE){throw 'Read-only comparator compile/link failed'}
}finally{Pop-Location}
foreach($h in $hashes){if((Get-FileHash -LiteralPath $h.path -Algorithm SHA256).Hash -ne $h.sha256){throw "Build input changed: $($h.path)"}}
[ordered]@{
  status='built_not_run';source_inputs=$hashes;source_unchanged=$true
  compiler=(Get-Command cl.exe).Source;compiler_version=(Get-Item -LiteralPath (Get-Command cl.exe).Source).VersionInfo.FileVersion
  flags=$flags;dependencies=$names;executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  build_log=$log;build_log_sha256=(Get-FileHash -LiteralPath $log -Algorithm SHA256).Hash
  limitations=@('Comparator is built independently from production BI4 sources; no solver or CUDA build is performed.','Build success is not comparison success.')
}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifest -Encoding UTF8
Write-Output "BUILT, NOT RUN: $exe"
