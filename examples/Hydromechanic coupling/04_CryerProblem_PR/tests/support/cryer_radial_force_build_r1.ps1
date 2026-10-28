# New nonintegrating companion, linked to authoritative CPU Debug project objects.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src'
$out=Join-Path $tests 'outputs\cryer_radial_force_r1_dbg'
$log=Join-Path $tests 'logs\cryer_radial_force_r1.build.log'
$seal=Join-Path $tests 'logs\cryer_radial_force_r1.build.json'
foreach($p in @($out,$log,$seal)){if(Test-Path -LiteralPath $p){throw "Retained build exists: $p"}}
& 'D:\Program Files\VS2022\MSBuild\Current\Bin\MSBuild.exe' (Join-Path $src 'VS\DualSPHysics5ReCpu_vs2022.sln') /m /t:Build /p:Configuration=DebugCPU /p:Platform=x64 /v:minimal
if($LASTEXITCODE){throw 'Authoritative CPU Debug build failed'}
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$envLines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $envLines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
# Reuse the already verified project-link recipe, not its stale object hashes.
$recipePath=Join-Path $tests 'logs\cryer_force_cpu_r1_dbg.build.json'
$recipe=Get-Content -LiteralPath $recipePath -Raw | ConvertFrom-Json
if($recipe.configuration -ne 'DebugCPU'){throw 'Expected DebugCPU link recipe'}
$oldOut=Join-Path $tests 'outputs\cryer_force_cpu_r1_dbg'
$harness=Join-Path $PSScriptRoot 'cryer_radial_force_r1.cpp'
function Translate($arg){$arg.Replace($oldOut,$out).Replace('cryer_force_cpu_r1.cpp','cryer_radial_force_r1.cpp').Replace('cryer_force_cpu_r1.obj','cryer_radial_force_r1.obj').Replace('cryer_force_cpu_r1.exe','cryer_radial_force_r1.exe')}
$compile=@($recipe.compile | ForEach-Object {Translate $_})
$link=@($recipe.link | ForEach-Object {Translate $_})
$project=Join-Path $src 'VS\DualSPHysics5ReCpu.vcxproj'
$objects=@($link | Where-Object {$_ -like '*.obj' -and $_ -ne (Join-Path $out 'cryer_radial_force_r1.obj')})
$libs=@($link | Where-Object {$_ -like '*.lib'})
$headers=@(Get-ChildItem -LiteralPath (Join-Path $src 'source') -Recurse -File | Where-Object {$_.Extension -in '.h','.hpp','.inl'} | ForEach-Object {$_.FullName})
$sources=@(Get-ChildItem -LiteralPath (Join-Path $src 'source') -Filter '*.cpp' -File | ForEach-Object {$_.FullName})
$dlls=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File)
$compiler=(Get-Command cl.exe).Source;$linker=(Get-Command link.exe).Source
function HashFiles($paths){@($paths | Sort-Object -Unique | ForEach-Object {[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})}
$inputs=HashFiles (@($harness,$PSCommandPath,$recipePath,$project,$compiler,$linker)+$objects+$libs+$headers+$sources+@($dlls.FullName))
New-Item -ItemType Directory -Path $out | Out-Null
& $compiler @compile 2>&1 | Tee-Object -FilePath $log
if($LASTEXITCODE){throw 'Companion compile failed; preserve this attempt'}
& $linker @link 2>&1 | Tee-Object -FilePath $log -Append
if($LASTEXITCODE){throw 'Companion link failed; preserve this attempt'}
foreach($entry in $inputs){if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw 'Build input changed'}}
foreach($dll in $dlls){Copy-Item -LiteralPath $dll.FullName -Destination $out}
$runtime=HashFiles (@(Join-Path $out 'cryer_radial_force_r1.exe')+@(Get-ChildItem -LiteralPath $out -Filter '*.dll' -File | ForEach-Object {$_.FullName}))
[ordered]@{status='built_not_run';configuration='DebugCPU';solver_launched=$false;inputs=$inputs;compile=$compile;link=$link;runtime=$runtime;build_log_sha256=(Get-FileHash -LiteralPath $log -Algorithm SHA256).Hash} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $seal -Encoding UTF8
Write-Output "Built nonintegrating companion: $out"
