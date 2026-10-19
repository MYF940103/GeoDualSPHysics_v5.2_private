param(
  [ValidateSet('Debug','Release')][string]$Configuration='Release',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1'
)
# Reuse the already-bound G2 load fixture's authoritative object/link inputs.
# Only the new diagnostic host file is compiled. No solver or fixture is run.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$basePath=Join-Path $tests "logs\hg_gpu_load_${Configuration}_r1.build.json"
$base=Get-Content -LiteralPath $basePath -Raw|ConvertFrom-Json
$name="hg_gpu_load_origin_${Configuration}_$Label"
$out=Join-Path $tests "outputs\$name"
$log=Join-Path $tests "logs\$name.build.log"
$recordPath=Join-Path $tests "logs\$name.build.json"
foreach($p in @($out,$log,$recordPath)){if(Test-Path -LiteralPath $p){throw "Refusing existing artifact: $p"}}
$harness=Join-Path $PSScriptRoot 'hg_gpu_load_origin_test.cpp'
$inputs=@($base.inputs)
foreach($p in @($basePath,$PSCommandPath,$harness)){$inputs+=([pscustomobject]@{path=$p;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash})}
function Verify {foreach($e in $inputs){if((Get-FileHash -LiteralPath $e.path -Algorithm SHA256).Hash -ne $e.sha256){throw "Changed bound input: $($e.path)"}}}
Verify
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$environment=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $environment){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
New-Item -ItemType Directory -Path $out|Out-Null
$oldDir=Split-Path -Parent $base.executable
$compile=@($base.compile_arguments|ForEach-Object {$_.Replace($oldDir,$out).Replace('hg_gpu_load_test','hg_gpu_load_origin_test')})
$link=@($base.link_arguments|ForEach-Object {$_.Replace($oldDir,$out).Replace('hg_gpu_load_test','hg_gpu_load_origin_test')})
& cl.exe @compile 2>&1|Tee-Object -FilePath $log
if($LASTEXITCODE){throw 'Diagnostic compile failed'}
& link.exe @link 2>&1|Tee-Object -FilePath $log -Append
if($LASTEXITCODE){throw 'Diagnostic link failed'}
Verify
foreach($dll in $base.runtime_dlls){Copy-Item -LiteralPath $dll.path -Destination $out}
$exe=Join-Path $out 'hg_gpu_load_origin_test.exe'
[ordered]@{
  status='built_not_run';configuration=$Configuration;inputs=$inputs
  base_build=$basePath;compile_arguments=$compile;link_arguments=$link
  executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  runtime_dlls=@(Get-ChildItem -LiteralPath $out -Filter '*.dll' -File|ForEach-Object {[ordered]@{path=$_.FullName;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}})
  scope='Zero-step existing FlexibleConfinement origin diagnosis; does not alter the failed all-raw 64-eps gate or establish physical acceptance.'
}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $recordPath -Encoding UTF8
Write-Output "BUILT, NOT RUN: $exe"
