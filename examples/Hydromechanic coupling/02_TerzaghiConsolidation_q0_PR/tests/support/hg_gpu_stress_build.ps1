param(
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [switch]$ProductionBuildConfirmed
)
# G1 preparation only. Link the enabled authoritative GPU objects; do not run
# MSBuild, recompile CUDA, start a fixture/solver, or modify VS project files.
# TODO(G1): production double stress/pool/sort/wrapper interfaces must land first.
$ErrorActionPreference='Stop'
if(!$ProductionBuildConfirmed){throw 'After G1 implementation, build the authoritative GPU solution, then pass -ProductionBuildConfirmed. This script never builds or runs the solver.'}
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Resolve-Path -LiteralPath (Join-Path $tests '..\..\..\..')).Path
$source=Join-Path $repo 'src'
$poolHeader=Get-Content -LiteralPath (Join-Path $source 'source\JArraysGpu.h') -Raw
$gpuHeader=Get-Content -LiteralPath (Join-Path $source 'source\JSphGpu.h') -Raw
if($poolHeader -notmatch 'ReserveSymatrix3d' -or $poolHeader -notmatch 'SIZE_48B' -or $gpuHeader -notmatch 'tsymatrix3d\s*\*\s*Sigmag'){
  throw 'G1 double stress interfaces are not implemented yet. Prepared test is deliberately not buildable against the float production ABI.'
}
$project=Join-Path $source 'VS\DualSPHysics5Re.vcxproj'
$harness=Join-Path $PSScriptRoot 'hg_gpu_stress_test.cpp'
$name="hg_gpu_stress_${Configuration}_$Label"
$output=Join-Path $tests "outputs\$name"
$logs=Join-Path $tests 'logs'
$buildLog=Join-Path $logs "$name.build.log"
$manifest=Join-Path $logs "$name.build.json"
foreach($p in @($output,$buildLog,$manifest)){if(Test-Path -LiteralPath $p){throw "Refusing existing artifact: $p"}}
$environment=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $environment){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$cudaRoot=$env:CUDA_PATH_V11_7
if(!$cudaRoot -or !(Test-Path -LiteralPath (Join-Path $cudaRoot 'lib\x64\cudart_static.lib'))){throw 'CUDA_PATH_V11_7 must identify the toolkit selected by the authoritative GPU project.'}
[xml]$projectXml=Get-Content -LiteralPath $project -Raw
$available=@()
foreach($dir in @("VS\Intermediate\DualSPHysics_${Configuration}_x64","VS\x64\$Configuration")){
  $path=Join-Path $source $dir
  if(Test-Path -LiteralPath $path){$available+=@(Get-ChildItem -LiteralPath $path -Filter '*.obj' -File)}
}
$objects=@();$enabledSources=@()
foreach($node in $projectXml.SelectNodes("//*[local-name()='ClCompile'][@Include] | //*[local-name()='CudaCompile'][@Include]")){
  $excluded=$false
  foreach($exclude in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){
    $condition=$exclude.GetAttribute('Condition')
    if($condition){
      $expanded=$condition.Replace('$(Configuration)',$Configuration).Replace('$(Platform)','x64').Replace(' ','')
      if($expanded -notmatch "^'[^']+'=='[^']+'$"){throw "Unsupported project condition: $condition"}
      if($expanded -ne "'$Configuration|x64'=='$Configuration|x64'"){continue}
    }
    $excluded=$exclude.InnerText.Trim() -eq 'true'
  }
  $include=$node.GetAttribute('Include');$base=[IO.Path]::GetFileNameWithoutExtension($include)
  if($excluded -or $base -eq 'main'){continue}
  $file=[IO.Path]::GetFileName($include)
  $objectName=if($node.LocalName -eq 'CudaCompile'){"$file.obj"}else{"$base.obj"}
  $found=@($available|Where-Object {$_.Name -eq $objectName})
  if($found.Count -ne 1){throw "Expected one enabled production object $objectName, found $($found.Count)"}
  $objects+=$found[0].FullName
  $enabledSources+=(Resolve-Path -LiteralPath (Join-Path (Split-Path -Parent $project) $include)).Path
}
if($objects.Count -lt 80 -or @($objects|Select-Object -Unique).Count -ne $objects.Count){throw 'Incomplete or duplicated enabled GPU project object set'}
if(!($objects|Where-Object {$_ -like '*JSphCpu.obj'}) -or !($objects|Where-Object {$_ -like '*JSphGpuSimple_ker.cu.obj'})){throw 'Real CPU reference or GPU integrator object missing'}
$debug=$Configuration -eq 'Debug'
$suffix=if($debug){'Debug'}else{'Release'}
$flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
$libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib")
$systemLibs=@('kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
$libPaths=@($libs|ForEach-Object{Join-Path $source "lib\vs2022\$_"})+@(Join-Path $cudaRoot 'lib\x64\cudart_static.lib')
$headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Filter '*.h' -File|ForEach-Object {$_.FullName})
$dlls=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File)
$inputs=@($objects)+$enabledSources+$headers+$libPaths+@($dlls|ForEach-Object {$_.FullName})+@($project,$harness,$PSCommandPath)
$hashes=@($inputs|Sort-Object -Unique|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})
New-Item -ItemType Directory -Path $output,$logs -Force|Out-Null
$obj=Join-Path $output 'hg_gpu_stress_test.obj'
$exe=Join-Path $output 'hg_gpu_stress_test.exe'
$compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/D_WITHGPU',"/I$source\source","/I$cudaRoot\include","/Fo$obj","/Fd$output\compile.pdb")+$flags+@($harness)
& cl.exe @compile 2>&1|Tee-Object -FilePath $buildLog
if($LASTEXITCODE){throw 'Fixture compile failed; retain artifacts and choose a fresh label after repair'}
$link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022","/LIBPATH:$cudaRoot\lib\x64",$obj)+$objects+$libs+$systemLibs+@('cudart_static.lib')
if($debug){$link+=@('/DEBUG',"/PDB:$output\link.pdb")}
& link.exe @link 2>&1|Tee-Object -FilePath $buildLog -Append
if($LASTEXITCODE){throw 'Fixture link failed; retain artifacts and choose a fresh label after repair'}
foreach($entry in $hashes){if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw "Build input changed: $($entry.path)"}}
foreach($dll in $dlls){Copy-Item -LiteralPath $dll.FullName -Destination $output}
$result=Join-Path $logs "$name.check.json"
[ordered]@{
  status='built_not_run';configuration=$Configuration;source_head=(& git -C $repo rev-parse HEAD)
  source_diff=((& git -C $repo diff -- src/source) -join "`n")
  inputs=$hashes;compile_arguments=$compile;link_arguments=$link;cuda_root=$cudaRoot
  compiler=(Get-Command cl.exe).Source;compiler_version=(Get-Item -LiteralPath (Get-Command cl.exe).Source).VersionInfo.FileVersion
  executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  runtime_dlls=@(Get-ChildItem -LiteralPath $output -Filter '*.dll' -File|ForEach-Object{[ordered]@{path=$_.FullName;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}})
  suggested_command=('"'+$exe+'" --json "'+$result+'"')
  device_code_provenance='Enabled authoritative GPU project objects, including actual CUDA wrappers; host fixture only, no copied device algorithms.'
  limitations=@('Build success is not execution or physical acceptance.','Actual GPU PART SaveData precision still requires stress_io_harness inspect on the new short case.','GPU G2/G3 and CPU/GPU coupled comparison are outside this fixture.','ProductionBuildConfirmed is operator confirmation; object hashes do not by themselves prove source-to-object freshness.')
}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifest -Encoding UTF8
Write-Output "BUILT, NOT RUN: $exe"
Write-Output "MANIFEST: $manifest"
