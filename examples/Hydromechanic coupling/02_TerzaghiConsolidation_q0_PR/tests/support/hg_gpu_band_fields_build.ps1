param([ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1')
# Compile one read-only reader; reuse retained, source-verified BI4 dependencies.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Resolve-Path -LiteralPath (Join-Path $tests '..\..\..\..')).Path
$source=Join-Path $repo 'src\source'
$name="hg_gpu_band_fields_$Label"
$exe=Join-Path $tests "logs\$name.exe"
$obj=Join-Path $tests "logs\$name.obj"
$log=Join-Path $tests "logs\$name.build.log"
$manifest=Join-Path $tests "logs\$name.build.json"
foreach($p in @($exe,$obj,$log,$manifest)){if(Test-Path -LiteralPath $p){throw "Refusing $p"}}
$base=Join-Path $tests 'logs\hg_gpu_band_part_check_r1.build.json'
$old=Get-Content -LiteralPath $base -Raw|ConvertFrom-Json
foreach($h in $old.source_inputs){if((Get-FileHash -LiteralPath $h.path -Algorithm SHA256).Hash -ne $h.sha256){throw "Dependency input changed: $($h.path)"}}
$objects=@($old.dependencies|ForEach-Object{Join-Path (Split-Path -Parent $old.executable) "$_.obj"})
$reader=Join-Path $PSScriptRoot 'hg_gpu_band_fields.cpp'
$inputs=@($base,$reader,$PSCommandPath,(Join-Path $PSScriptRoot 'pore_double_vel0\export_state.cpp'))+$objects
$hashes=@($inputs|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$environment=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $environment){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
& cl.exe /nologo /EHsc /W3 /Od /RTC1 /MTd /fp:precise /DWIN32 /D_CONSOLE /D_MBCS /std:c++17 "/I$source" "/Fo$obj" "/Fe$exe" $reader @objects 2>&1|Tee-Object -FilePath $log
if($LASTEXITCODE){throw 'Reader compile/link failed'}
foreach($h in $hashes){if((Get-FileHash -LiteralPath $h.path -Algorithm SHA256).Hash -ne $h.sha256){throw "Reader input changed: $($h.path)"}}
[ordered]@{built=$true;inputs=$hashes;executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash;dependency_manifest=$base;dependency_source_hashes_verified=$true}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifest -Encoding UTF8
