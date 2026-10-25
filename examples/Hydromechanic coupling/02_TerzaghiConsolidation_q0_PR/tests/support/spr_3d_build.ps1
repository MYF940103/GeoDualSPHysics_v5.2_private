param([ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU', [string]$Label='r1')
# Build only this observer against authoritative, freshly built CPU objects.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Resolve-Path -LiteralPath (Join-Path $tests '..\..\..\..')).Path
$src=Join-Path $repo 'src';$project=Join-Path $src 'VS\DualSPHysics5ReCpu.vcxproj'
$name="spr_3d_${Configuration}_$Label";$out=Join-Path $tests "outputs\$name"
$log=Join-Path $tests "logs\$name.build.log";$record=Join-Path $tests "logs\$name.build.json"
foreach($p in @($out,$log,$record)){if(Test-Path -LiteralPath $p){throw "Refusing overwrite: $p"}}
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$objects=@();$sources=@();[xml]$xml=Get-Content -LiteralPath $project -Raw
foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
  $excluded=$false
  foreach($entry in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){
    $condition=$entry.GetAttribute('Condition').Replace('$(Configuration)',$Configuration).Replace('$(Platform)','x64').Replace(' ','')
    if(!$condition -or $condition -eq "'$Configuration|x64'=='$Configuration|x64'"){$excluded=$entry.InnerText.Trim() -eq 'true'}
  }
  $include=$node.GetAttribute('Include');$base=[IO.Path]::GetFileNameWithoutExtension($include)
  if(!$excluded -and $base -ne 'main'){
    $objects+=Join-Path $src "VS\Intermediate\DualSPHysics_${Configuration}_x64\$base.obj"
    $sources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $include))
  }
}
$debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
$flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
$libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib")
$system=@('kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
$harness=Join-Path $PSScriptRoot 'spr_3d_test.cpp';$dlls=@(Get-ChildItem -LiteralPath "$repo\bin\windows" -Filter '*.dll' -File)
function Hashes($items){@($items|Sort-Object -Unique|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_).Hash}})}
$inputs=Hashes (@($project,$harness,$PSCommandPath,(Join-Path $PSScriptRoot 'spr_planes_test.cpp'))+$objects+$sources+@(Get-ChildItem -LiteralPath "$src\source" -Recurse -File|Where-Object{$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object{$_.FullName})+@($dlls.FullName)+@($libs|ForEach-Object{"$src\lib\vs2022\$_"}))
$null=New-Item -ItemType Directory -Path $out
$obj=Join-Path $out 'spr_3d.obj';$exe=Join-Path $out 'spr_3d.exe'
& cl.exe /nologo /c /std:c++17 /EHsc /W3 /openmp /fp:precise /DWIN32 /D_CONSOLE /D_MBCS "/I$src\source" "/Fo$obj" "/Fd$out\compile.pdb" @flags $harness 2>&1|Tee-Object -FilePath $log
if($LASTEXITCODE){throw 'Observer compile failed'}
$link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$src\lib\vs2022",$obj)+$objects+$libs+$system
if($debug){$link+=@('/DEBUG',"/PDB:$out\link.pdb")}
& link.exe @link 2>&1|Tee-Object -FilePath $log -Append
if($LASTEXITCODE){throw 'Observer link failed'}
foreach($entry in $inputs){if((Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256){throw "Changed build input: $($entry.path)"}}
foreach($dll in $dlls){Copy-Item -LiteralPath $dll.FullName -Destination $out}
[ordered]@{built=$true;configuration=$Configuration;inputs=$inputs;executable=$exe;executable_sha256=(Get-FileHash -LiteralPath $exe).Hash;runtime=Hashes @($dlls|ForEach-Object{Join-Path $out $_.Name});log_sha256=(Get-FileHash -LiteralPath $log).Hash}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $record -Encoding UTF8
Write-Output "BUILT $exe (not run)"
