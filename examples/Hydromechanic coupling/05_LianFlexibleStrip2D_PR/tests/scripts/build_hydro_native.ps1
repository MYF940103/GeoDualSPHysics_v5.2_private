$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$case=Split-Path -Parent $tests
$repo=(Get-Item -LiteralPath $case).Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src\source'
$output=Join-Path $tests 'outputs\hydro_native_r1'
$manifest=Join-Path $tests 'logs\hydro_native_r1.build.json'
if((Test-Path -LiteralPath $output) -or (Test-Path -LiteralPath $manifest)){throw 'Reader already exists; preserve retained build'}
$null=New-Item -ItemType Directory -Path $output
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$sources=@((Join-Path $PSScriptRoot 'read_hydro_native.cpp'))+@('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions'|ForEach-Object{Join-Path $source "$_.cpp"})
$headers=@(Get-ChildItem -LiteralPath $source -Filter '*.h' -File|ForEach-Object{$_.FullName})
$inputs=@(@($sources+$headers+@($PSCommandPath))|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_).Hash}})
$exe=Join-Path $output 'ReadHydroNative.exe'
Push-Location $output
try{
  & cl.exe /nologo /O2 /MT /EHsc /std:c++14 /DWIN32 /D_CONSOLE /D_MBCS /W3 /fp:precise "/I$source" "/Fe$exe" @sources 2>&1|Tee-Object -FilePath (Join-Path $output 'build.log')
  if($LASTEXITCODE){throw 'Native reader build failed'}
}finally{Pop-Location}
foreach($e in $inputs){if((Get-FileHash -LiteralPath $e.path).Hash -ne $e.sha256){throw 'Reader build input changed'}}
[ordered]@{built=$true;inputs=$inputs;executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe).Hash;production_modified=$false}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $manifest -Encoding UTF8
