param([ValidateSet('CPU','GPU')][string]$Backend='CPU')
# Reuse the verified authoritative VS object/link set, never a new solver build system.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Resolve-Path -LiteralPath (Join-Path $tests '..\..\..\..')).Path
$baseName=if($Backend -eq 'CPU'){'spr_yao_step_r2rel'}else{'spr_yao_gpu_step_Release_op2'}
$baseFile=Join-Path $tests "logs\$baseName.build.json"
$base=Get-Content -LiteralPath $baseFile -Raw|ConvertFrom-Json
$name="spr_yao_axis_${Backend}_r1"
$out=Join-Path $tests "outputs\$name"
$log=Join-Path $tests "logs\$name.build.log"
$manifest=Join-Path $tests "logs\$name.build.json"
foreach($p in @($out,$log,$manifest)){if(Test-Path -LiteralPath $p){throw "Refusing overwrite: $p"}}
$superseded=@()
foreach($entry in $base.inputs){
  $current=(Get-FileHash -LiteralPath $entry.path).Hash
  if($current -ne $entry.sha256){
    # The CPU base predates the GPU port; its broad header inventory included
    # these two GPU-only files. Neither is a CPU fixture include. Bind their
    # current values to the later verified GPU build, not to the old CPU hash.
    $allowed=$Backend -eq 'CPU' -and ([IO.Path]::GetFileName($entry.path) -in @('JSphGpu.h','JSphGpu_ker.h'))
    if(!$allowed){throw "Base build input changed: $($entry.path)"}
    $deps=Get-Content -LiteralPath (Join-Path $tests "outputs\$baseName\compile.dependencies.json") -Raw|ConvertFrom-Json
    if($entry.path -in $deps.Data.Includes){throw 'Changed header is a CPU fixture dependency'}
    $gpu=Get-Content -LiteralPath (Join-Path $tests 'logs\spr_yao_gpu_step_Release_op2.build.json') -Raw|ConvertFrom-Json
    $proof=@($gpu.inputs|Where-Object{$_.path -eq $entry.path -and $_.sha256 -eq $current})
    if($proof.Count -ne 1){throw 'Current GPU-only header is not bound to the verified GPU build'}
    $superseded+=@{path=$entry.path;old_sha256=$entry.sha256;current_sha256=$current}
  }
}
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$oldSource=$base.compile[-1]
$oldObject=@($base.compile|Where-Object{$_ -like '/Fo*'})[0].Substring(3)
$oldExe=if($Backend -eq 'CPU'){Join-Path $tests "outputs\$baseName\spr_yao_step.exe"}else{$base.executable}
$source=Join-Path $PSScriptRoot 'spr_yao_axis_step.cpp'
$obj=Join-Path $out 'axis_step.obj';$exe=Join-Path $out 'axis_step.exe'
$compile=@($base.compile|ForEach-Object{
  if($_ -eq $oldSource){$source}elseif($_ -like '/Fo*'){"/Fo$obj"}elseif($_ -like '/Fd*'){"/Fd$out\compile.pdb"}
  elseif($_ -eq (Join-Path (Split-Path $oldExe) 'compile.dependencies.json')){Join-Path $out 'compile.dependencies.json'}else{$_}
})
$link=@($base.link|ForEach-Object{if($_ -eq $oldObject){$obj}elseif($_ -like '/OUT:*'){"/OUT:$exe"}else{$_}})
function Hashes($paths){@($paths|Sort-Object -Unique|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_).Hash}})}
$inputs=Hashes (@($base.inputs|ForEach-Object{$_.path})+@($source,$PSCommandPath,$baseFile,$oldExe))
$null=New-Item -ItemType Directory -Path $out
& cl.exe @compile 2>&1|Tee-Object -FilePath $log
if($LASTEXITCODE){throw 'Axis companion compile failed; preserve log'}
& link.exe @link 2>&1|Tee-Object -FilePath $log -Append
if($LASTEXITCODE){throw 'Axis companion link failed; preserve log'}
foreach($entry in $inputs){if((Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256){throw "Build input changed: $($entry.path)"}}
$dlls=@(Get-ChildItem -LiteralPath (Split-Path $oldExe) -Filter '*.dll' -File)
foreach($dll in $dlls){Copy-Item -LiteralPath $dll.FullName -Destination $out}
[ordered]@{built=$true;backend=$Backend;production_objects_reused=$true;superseded_gpu_only_headers=$superseded;inputs=$inputs;compile=$compile;link=$link;
  executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe).Hash;runtime=Hashes @($dlls|ForEach-Object{Join-Path $out $_.Name});
  log_sha256=(Get-FileHash -LiteralPath $log).Hash;git_head=(& git -C $repo rev-parse HEAD);utc=[DateTime]::UtcNow.ToString('o')
}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifest -Encoding UTF8
Write-Output "BUILT $Backend axis companion (not run): $exe"
