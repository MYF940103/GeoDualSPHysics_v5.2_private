param(
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1dbg',
  [switch]$ProductionBuildConfirmed
)
# Standalone manufactured-field companion, following hg_release_build.ps1.
# Link current authoritative CPU project objects. No solver is launched here.
$ErrorActionPreference='Stop'
if(!$ProductionBuildConfirmed){throw 'Build the matching CPU solution first, then pass -ProductionBuildConfirmed.'}
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$name="spr_pulse_$Label"
$output=Join-Path $tests "outputs\$name"
$logs=Join-Path $tests 'logs'
$buildLog=Join-Path $logs "$name.build.log"
$manifest=Join-Path $logs "$name.build.json"
foreach($path in @($output,$buildLog,$manifest)){
  if(Test-Path -LiteralPath $path){throw "Refusing overwrite: $path"}
}
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj'
$projectDir=Split-Path -Parent $project
[xml]$xml=Get-Content -LiteralPath $project -Raw
$objects=@()
$productionSources=@()
foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
  $excluded=$false
  foreach($entry in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){
    $condition=$entry.GetAttribute('Condition')
    if(!$condition -or $condition -eq "'`$(Configuration)|`$(Platform)'=='$Configuration|x64'"){$excluded=$entry.InnerText.Trim() -eq 'true'}
  }
  $objectName=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
  if(!$excluded -and $objectName -ne 'main'){
    $objects+=Join-Path $source "VS\Intermediate\DualSPHysics_${Configuration}_x64\$objectName.obj"
    $productionSources+=[IO.Path]::GetFullPath((Join-Path $projectDir $node.GetAttribute('Include')))
  }
}
$harness=Join-Path $PSScriptRoot 'spr_pulse_test.cpp'
$debug=$Configuration -eq 'DebugCPU'
$flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
$suffix=if($debug){'Debug'}else{'Release'}
$libNames=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
$libDirs=@((Join-Path $source 'lib\vs2022'))+@($env:LIB.Split(';')|Where-Object{$_})
$libs=@($libNames|ForEach-Object{
  $libName=$_
  $resolved=@($libDirs|ForEach-Object{Join-Path $_ $libName}|Where-Object{Test-Path -LiteralPath $_})
  if(!$resolved.Count){throw "Link library not found: $libName"}
  $resolved[0]
})
$dlls=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File)
$headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object{$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object{$_.FullName})
$compiler=(Get-Command cl.exe).Source
$linker=(Get-Command link.exe).Source
function HashFiles($paths){@($paths|Sort-Object -Unique|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})}
$inputs=HashFiles (@($project,$harness,$PSCommandPath,$compiler,$linker)+$objects+$productionSources+$headers+$libs+@($dlls.FullName))
New-Item -ItemType Directory -Path $output,$logs -Force | Out-Null
$started=[DateTime]::UtcNow.ToString('o')
$obj=Join-Path $output 'spr_pulse.obj'
$exe=Join-Path $output 'spr_pulse.exe'
$dependencies=Join-Path $output 'compile.dependencies.json'
$compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$output\compile.pdb",'/sourceDependencies',$dependencies)+$flags+@($harness)
& $compiler @compile 2>&1 | Tee-Object -FilePath $buildLog
if($LASTEXITCODE){throw 'Manufactured-field compile failed; retain the log and use a new label.'}
$link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/VERBOSE:LIB',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs
if($debug){$link+=@('/DEBUG',"/PDB:$output\link.pdb")}
& $linker @link 2>&1 | Tee-Object -FilePath $buildLog -Append
if($LASTEXITCODE){throw 'Manufactured-field link failed; retain the log and use a new label.'}
foreach($entry in $inputs){if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw 'Inputs changed during build; retain output and use a new label.'}}
$includes=(Get-Content -LiteralPath $dependencies -Raw|ConvertFrom-Json).Data.Includes
$implicitLibs=@([regex]::Matches((Get-Content -LiteralPath $buildLog -Raw),'(?im)([A-Z]:\\[^\r\n]*?\.lib)(?=[:(\s]|$)')|ForEach-Object{$_.Groups[1].Value}|Where-Object{Test-Path -LiteralPath $_})
$resolvedInputs=HashFiles (@($includes)+$implicitLibs+@($obj))
foreach($dll in $dlls){Copy-Item -LiteralPath $dll.FullName -Destination $output}
$runtime=HashFiles (@($exe)+@(Get-ChildItem -LiteralPath $output -Filter '*.dll' -File|ForEach-Object{$_.FullName}))
[ordered]@{
  status='built_not_run';started_utc=$started;finished_utc=[DateTime]::UtcNow.ToString('o')
  git_head=(& git -C $repo rev-parse HEAD);git_status=@(& git -C $repo status --short -- src)
  configuration=$Configuration;production_build_confirmed=[bool]$ProductionBuildConfirmed
  inputs=$inputs;resolved_compile_link_inputs=$resolvedInputs;compile=$compile;link=$link
  compiler=$compiler;linker=$linker;library_search_path=$libDirs;runtime=$runtime
  exe_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  build_log_sha256=(Get-FileHash -LiteralPath $buildLog -Algorithm SHA256).Hash
}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifest -Encoding UTF8
Write-Output "BUILT $exe (not run)"
