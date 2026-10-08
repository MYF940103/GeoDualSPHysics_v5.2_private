param(
  [ValidateSet('ReleaseCPU','DebugCPU','Release','Debug')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [switch]$ProductionBuildConfirmed
)
# Links only enabled authoritative project objects; never modifies solver source.
$ErrorActionPreference='Stop'
if(!$ProductionBuildConfirmed){throw 'Build the matching authoritative solution first, then pass -ProductionBuildConfirmed.'}
$gpu=$Configuration -in @('Release','Debug')
$backend=if($gpu){'gpu'}else{'cpu'}
$tests=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$repositoryDirectory=Get-Item -LiteralPath $PSScriptRoot
while($repositoryDirectory -and !(Test-Path -LiteralPath (Join-Path $repositoryDirectory.FullName 'src\VS\DualSPHysics5ReCpu_vs2022.sln'))){$repositoryDirectory=$repositoryDirectory.Parent}
if(!$repositoryDirectory){throw 'Repository not found'}
$repo=$repositoryDirectory.FullName
$sourceRoot=Join-Path $repo 'src'
$name="${backend}_state_${Configuration}_$Label"
$artifacts=Join-Path $tests "outputs\pore_double_stage1\$name"
$logs=Join-Path $tests 'logs\pore_double_stage1'
if(Test-Path -LiteralPath $artifacts){throw "Refusing overwrite: $artifacts"}
New-Item -ItemType Directory -Path $artifacts,$logs -Force | Out-Null
$environmentCommand='call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
$environmentLines=& $env:ComSpec /d /c $environmentCommand
if($LASTEXITCODE -ne 0){throw 'VS environment setup failed'}
foreach($line in $environmentLines){$split=$line.IndexOf('=');if($split -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$split),$line.Substring($split+1),'Process')}}
$project=Join-Path $sourceRoot $(if($gpu){'VS\DualSPHysics5Re.vcxproj'}else{'VS\DualSPHysics5ReCpu.vcxproj'})
[xml]$projectXml=Get-Content -LiteralPath $project -Raw
$objectNames=@()
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
  $base=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
  $sourceName=[IO.Path]::GetFileName($node.GetAttribute('Include'))
  if(!$excluded -and $base -ne 'main'){$objectNames+=$(if($node.LocalName -eq 'CudaCompile'){"$sourceName.obj"}else{"$base.obj"})}
}
if(@($objectNames|Select-Object -Unique).Count -ne $objectNames.Count){throw 'Duplicate object names'}
$production=Join-Path $sourceRoot "VS\Intermediate\DualSPHysics_${Configuration}_x64"
$available=@(Get-ChildItem -LiteralPath $production -Filter '*.obj' -File)
if($gpu){$available+=@(Get-ChildItem -LiteralPath (Join-Path $sourceRoot "VS\x64\$Configuration") -Filter '*.obj' -File)}
$objects=@($objectNames|Sort-Object|ForEach-Object{
  $objectName=$_
  $matches=@($available|Where-Object {$_.Name -eq $objectName})
  if($matches.Count -ne 1){throw "Expected one enabled object: $objectName, found $($matches.Count)"}
  $matches[0].FullName
})
if($objects.Count -lt 80){throw 'Incomplete production object set'}
$hashes=@($objects|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})
$debug=$Configuration -in @('DebugCPU','Debug')
$suffix=if($debug){'Debug'}else{'Release'}
$flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
$harness=Join-Path $PSScriptRoot "${backend}_state_harness.cpp"
$obj=Join-Path $artifacts "$name.obj"
$exe=Join-Path $artifacts "$name.exe"
$compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$sourceRoot\source","/Fo$obj","/Fd$artifacts\$name.pdb")+$flags+@($harness)
if($gpu){
  $cudaRoot=if($env:CUDA_PATH_V11_7){$env:CUDA_PATH_V11_7}else{'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7'}
  $compile+=@('/D_WITHGPU',"/I$cudaRoot\include")
  $gpuInputNames=@('JSphGpu_ker.cu','JSphGpu_ker.h','JCellDivGpu_ker.cu','JCellDivGpu_ker.h','DualSphDef.h','JDsDcellDef.h')
  $gpuInputPaths=@($gpuInputNames|ForEach-Object{Join-Path $sourceRoot "source\$_"})+@($harness,$PSCommandPath,$project)
  $gpuInputHashes=@($gpuInputPaths|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})
}
& cl.exe @compile
if($LASTEXITCODE -ne 0){throw 'Harness compile failed'}
$libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
$link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$sourceRoot\lib\vs2022",$obj)+$objects+$libs
if($gpu){$link+=@("/LIBPATH:$cudaRoot\lib\x64",'cudart_static.lib')}
if($debug){$link+=@('/DEBUG',"/PDB:$artifacts\$name.link.pdb")}
& link.exe @link
if($LASTEXITCODE -ne 0){throw 'Harness link failed'}
foreach($entry in $hashes){if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw "Production object changed during build: $($entry.path)"}}
Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File | ForEach-Object{Copy-Item -LiteralPath $_.FullName -Destination $artifacts}
$manifest=[ordered]@{configuration=$Configuration;executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash;harness_sha256=(Get-FileHash -LiteralPath $harness -Algorithm SHA256).Hash;project_sha256=(Get-FileHash -LiteralPath $project -Algorithm SHA256).Hash;objects=$hashes;compile_arguments=$compile;link_arguments=$link}
if($gpu){
  foreach($entry in $gpuInputHashes){if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw "GPU source input changed during harness build: $($entry.path)"}}
  $manifest.gpu_source_inputs=$gpuInputHashes
  $manifest.cuda_root=$cudaRoot
  $manifest.device_code_provenance='Unmodified nvcc-built objects from the authoritative GPU project; fixture contains host calls only.'
}
$manifest|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $logs "$name.build.json") -Encoding UTF8
$json=Join-Path $logs "$name.json"
& $exe --json $json
if($LASTEXITCODE -ne 0){throw "Harness failed; retained results: $json"}
Write-Output "PASS: $json"
