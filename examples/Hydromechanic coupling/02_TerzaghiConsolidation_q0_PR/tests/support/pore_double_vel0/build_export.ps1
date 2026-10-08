# Build the standalone native BI4 reader without changing the solver or old tests.
$ErrorActionPreference='Stop'
$tests=(Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.FullName
$repository=Get-Item -LiteralPath $PSScriptRoot
while($repository -and !(Test-Path -LiteralPath (Join-Path $repository.FullName 'src\VS\DualSPHysics5ReCpu_vs2022.sln'))){$repository=$repository.Parent}
if(!$repository){throw 'Cannot locate authoritative repository'}
$source=Join-Path $repository.FullName 'src\source'
$output=Join-Path $tests 'outputs\pore_double_vel0\reader'
$logs=Join-Path $tests 'logs\pore_double_vel0'
$buildlog=Join-Path $logs 'reader.build.log'
$manifest=Join-Path $logs 'reader.build.json'
foreach($path in @($output,$buildlog,$manifest)){if(Test-Path -LiteralPath $path){throw "Refusing to overwrite $path"}}
New-Item -ItemType Directory -Path $output,$logs -Force | Out-Null
$setup='call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
$lines=& $env:ComSpec /d /c $setup
if($LASTEXITCODE -ne 0){throw 'Visual Studio environment setup failed'}
foreach($line in $lines){$split=$line.IndexOf('=');if($split -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$split),$line.Substring($split+1),'Process')}}
$names=@('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')
$sources=@($names|ForEach-Object{Join-Path $source "$_.cpp"})
$reader=Join-Path $PSScriptRoot 'export_state.cpp'
$inputs=$sources+@($names|ForEach-Object{Join-Path $source "$_.h"})+@($reader,$PSCommandPath,(Join-Path $source 'TypesDef.h'))
$hashes=@($inputs|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})
$flags=@('/nologo','/EHsc','/W3','/O2','/MT','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source",'/Fo.\')
Push-Location $output
try{
  & cl.exe @flags /std:c++14 /c @sources 2>&1 | Tee-Object -FilePath $buildlog
  if($LASTEXITCODE -ne 0){throw 'BI4 dependencies did not compile'}
  $objects=@($names|ForEach-Object{"$_.obj"})
  & cl.exe @flags /std:c++17 /Feexport_state.exe $reader @objects 2>&1 | Tee-Object -FilePath $buildlog -Append
  if($LASTEXITCODE -ne 0){throw 'Native reader compile/link failed'}
  foreach($entry in $hashes){if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw 'Source changed during build'}}
  $exe=Join-Path $output 'export_state.exe'
  [ordered]@{compiler=(Get-Command cl.exe).Source;compiler_version=(Get-Item -LiteralPath (Get-Command cl.exe).Source).VersionInfo.FileVersion;
    common_flags=$flags;production_standard='C++14';reader_standard='C++17';inputs=$hashes;executable=$exe;
    executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifest -Encoding UTF8
  Write-Output "BUILT: $exe"
}
finally{Pop-Location}
