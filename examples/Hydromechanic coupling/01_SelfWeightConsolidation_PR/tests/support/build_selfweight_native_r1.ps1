# Build only this read-only exporter; no solver, canonical program or VS project edits.
# Same direct MSVC/JPartDataBi4 recipe as case05 tests/scripts/build_hydro_native.ps1.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$case=Split-Path -Parent $tests
$repo=(Get-Item -LiteralPath $case).Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src\source'
$output=Join-Path $tests 'outputs\sw_native_r1'
$manifest=Join-Path $tests 'logs\sw_native_r1.build.json'
$log=Join-Path $tests 'logs\sw_native_r1.build.log'
if((Test-Path -LiteralPath $output) -or (Test-Path -LiteralPath $manifest) -or (Test-Path -LiteralPath $log)){throw 'Reader build evidence exists; preserve it'}
$null=New-Item -ItemType Directory -Path $output
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$sources=@((Join-Path $PSScriptRoot 'read_selfweight_native_r1.cpp'))+@('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions'|ForEach-Object{Join-Path $source "$_.cpp"})
$headers=@(Get-ChildItem -LiteralPath $source -Filter '*.h' -File|ForEach-Object{$_.FullName})
$inputs=@(@($sources+$headers+@($PSCommandPath))|ForEach-Object{[ordered]@{path=$_;bytes=(Get-Item -LiteralPath $_).Length;sha256=(Get-FileHash -LiteralPath $_).Hash}})
$exe=Join-Path $output 'ReadSelfWeightNative.exe'
$exitCode=-1
Push-Location $output
try{
  & cl.exe /nologo /O2 /MT /EHsc /std:c++14 /DWIN32 /D_CONSOLE /D_MBCS /W3 /fp:precise "/I$source" "/Fe$exe" @sources 2>&1|Tee-Object -FilePath $log
  $exitCode=$LASTEXITCODE
}finally{Pop-Location}
foreach($e in $inputs){if((Get-FileHash -LiteralPath $e.path).Hash -ne $e.sha256){throw 'Reader build input changed; retained output is not accepted'}}
$program=if(Test-Path -LiteralPath $exe){[ordered]@{path=$exe;bytes=(Get-Item -LiteralPath $exe).Length;sha256=(Get-FileHash -LiteralPath $exe).Hash}}else{$null}
[ordered]@{built=($exitCode -eq 0);exit_code=$exitCode;inputs=$inputs;program=$program;log=[ordered]@{path=$log;bytes=(Get-Item -LiteralPath $log).Length;sha256=(Get-FileHash -LiteralPath $log).Hash};production_modified=$false;program_executed=$false;physical_acceptance=$false}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $manifest -Encoding UTF8
if($exitCode){throw "Native reader build failed (exit=$exitCode); evidence retained"}
