param(
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [ValidatePattern('^[A-Za-z0-9_]+$')][string]$Label='r1',
  [Parameter(Mandatory=$true)][string]$ProductionBuildLog
)
# Only compile this host fixture and link authoritative VS objects. No MSBuild,
# canonical executable replacement, CUDA algorithm clone, or diagnostic launch.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Resolve-Path -LiteralPath (Join-Path $tests '..\..\..\..')).Path
$src=Join-Path $repo 'src';$project=Join-Path $src 'VS\DualSPHysics5Re.vcxproj'
$name="bv_pair_gpu_${Configuration}_$Label";$out=Join-Path $tests "outputs\$name"
$log=Join-Path $tests "logs\$name.build.log";$record=Join-Path $tests "logs\$name.build.json"
foreach($p in @($out,$log,$record)){if(Test-Path -LiteralPath $p){throw "Refusing overwrite: $p"}}
$productionLog=(Resolve-Path -LiteralPath $ProductionBuildLog).Path
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$cuda=$env:CUDA_PATH_V11_7
if(!(Test-Path -LiteralPath "$cuda\lib\x64\cudart_static.lib")){throw 'Authoritative CUDA 11.7 toolkit is missing'}
$objects=@();$sources=@();[xml]$xml=Get-Content -LiteralPath $project -Raw
$available=@(Get-ChildItem -LiteralPath "$src\VS\Intermediate\DualSPHysics_${Configuration}_x64" -Filter '*.obj' -File)+@(Get-ChildItem -LiteralPath "$src\VS\x64\$Configuration" -Filter '*.obj' -File)
foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include] | //*[local-name()='CudaCompile'][@Include]")){
  $excluded=$false
  foreach($entry in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){
    $condition=$entry.GetAttribute('Condition').Replace('$(Configuration)',$Configuration).Replace('$(Platform)','x64').Replace(' ','')
    if(!$condition -or $condition -eq "'$Configuration|x64'=='$Configuration|x64'"){$excluded=$entry.InnerText.Trim() -eq 'true'}
  }
  $include=$node.GetAttribute('Include');$base=[IO.Path]::GetFileNameWithoutExtension($include)
  if($excluded -or $base -eq 'main'){continue}
  $objname=if($node.LocalName -eq 'CudaCompile'){[IO.Path]::GetFileName($include)+'.obj'}else{$base+'.obj'}
  $found=@($available|Where-Object{$_.Name -eq $objname});if($found.Count -ne 1){throw "Missing/ambiguous object: $objname"}
  $objects+=$found[0].FullName;$sources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $include))
}
if($objects.Count -lt 80){throw 'Incomplete project object set'}
$harness=Join-Path $PSScriptRoot 'bv_pair_gpu_r1.cpp';$debug=$Configuration -eq 'Debug'
$suffix=if($debug){'Debug'}else{'Release'};$flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
$libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib")
$system=@('kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
$dlls=@(Get-ChildItem -LiteralPath "$repo\bin\windows" -Filter '*.dll' -File)
function Hashes($items){@($items|Sort-Object -Unique|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_).Hash;bytes=(Get-Item -LiteralPath $_).Length}})}
$paths=@($project,$harness,$PSCommandPath,$productionLog)+$objects+$sources+@(Get-ChildItem -LiteralPath "$src\source" -Filter '*.h' -File|ForEach-Object{$_.FullName})+@($dlls.FullName)+@($libs|ForEach-Object{"$src\lib\vs2022\$_"})+@("$cuda\lib\x64\cudart_static.lib")
$inputs=Hashes $paths
$null=New-Item -ItemType Directory -Path $out
$archive=Join-Path $out 'source';$null=New-Item -ItemType Directory -Path $archive
$captures=@($harness,$project,$PSCommandPath,"$src\source\JSphGpu_ker.cu","$src\source\JSphGpu_ker.h","$src\source\JCellSearch_iker.h","$src\source\FunSphKernel_iker.h","$src\source\FunSphKernel.h","$src\source\DualSphDef.h")
$snapshots=@();foreach($p in $captures){$copy=Join-Path $archive ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $copy;$snapshots+=[ordered]@{original=$p;archive=$copy;sha256=(Get-FileHash -LiteralPath $copy).Hash}}
$obj=Join-Path $out 'bv_pair_gpu_r1.obj';$exe=Join-Path $out 'bv_pair_gpu_r1.exe'
$compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/D_WITHGPU',"/I$src\source","/I$cuda\include","/Fo$obj","/Fd$out\compile.pdb")+$flags+@($harness)
$global:LASTEXITCODE=0;& cl.exe @compile 2>&1|Tee-Object -FilePath $log
if($LASTEXITCODE){throw 'Fixture compilation failed; preserve this label'}
$link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$src\lib\vs2022","/LIBPATH:$cuda\lib\x64",$obj)+$objects+$libs+$system+@('cudart_static.lib')
if($debug){$link+=@('/DEBUG',"/PDB:$out\link.pdb")}
$global:LASTEXITCODE=0;& link.exe @link 2>&1|Tee-Object -FilePath $log -Append
if($LASTEXITCODE){throw 'Fixture link failed; preserve this label'}
foreach($entry in $inputs){if((Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256){throw "Build input changed: $($entry.path)"}}
foreach($dll in $dlls){Copy-Item -LiteralPath $dll.FullName -Destination $out}
[ordered]@{built=$true;not_run=$true;configuration=$Configuration;fixture='bv_pair_gpu_r1';inputs=$inputs;source_snapshots=$snapshots;compile=$compile;link=$link;executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe).Hash;runtime=Hashes @($dlls|ForEach-Object{Join-Path $out $_.Name});log_sha256=(Get-FileHash -LiteralPath $log).Hash;production_build_log=$productionLog;production_object_freshness_automatically_verified=$false;physical_acceptance=$false;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Depth 7|Set-Content -LiteralPath $record -Encoding UTF8
Write-Output "BUILT ONLY: $exe"
