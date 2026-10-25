$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$case=Split-Path -Parent $tests
$repo=(Get-Item -LiteralPath $case).Parent.Parent.Parent.FullName
$output=Join-Path $tests 'outputs\lian_mirror_build_r1'
$manifest=Join-Path $tests 'logs\lian_mirror_build_r1.json'
if((Test-Path -LiteralPath $output) -or (Test-Path -LiteralPath $manifest)){throw 'Preserve existing build; never restart this entry'}
if(Get-CimInstance Win32_Process | Where-Object Name -Like 'DualSPHysics*.exe'){throw 'Do not build during a physical solve'}
$null=New-Item -ItemType Directory -Path $output
$originals=@()
foreach($name in @('DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2CPU_win64_debug.exe')){
 $original=Join-Path $repo "bin\windows\$name"
 $copy=Join-Path $output ('control_'+$name)
 Copy-Item -LiteralPath $original -Destination $copy
 $hash=(Get-FileHash -LiteralPath $original).Hash
 if((Get-FileHash -LiteralPath $copy).Hash -ne $hash){throw 'Control program copy mismatch'}
 $originals+=@{original=$original;retained=$copy;sha256=$hash}
}
$inputs=@('src\source\JSphCpu.cpp','src\source\JSphGpu_ker.cu','doc\xml_format\_FmtXML_ElastoplasticSoil.xml' | ForEach-Object {
 $p=Join-Path $repo $_;@{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash}
})
$builder='D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe'
$builds=@()
foreach($config in @('DebugCPU','Release','Debug')){
 $solution=Join-Path $repo ('src\VS\'+$(if($config -eq 'DebugCPU'){'DualSPHysics5ReCpu_vs2022.sln'}else{'DualSPHysics5Re.sln'}))
 $log=Join-Path $tests "logs\lian_mirror_build_r1_$config.log"
 $args=@($solution,'/m','/t:Build',"/p:Configuration=$config",'/p:Platform=x64','/v:minimal')
 if($config -ne 'DebugCPU'){$args+=('/p:OutDir='+$output.Replace('\','/')+'/')}
 & $builder @args 2>&1 | Tee-Object -FilePath $log
 $code=$LASTEXITCODE
 $builds+=@{configuration=$config;exit_code=$code;log=$log;sha256=(Get-FileHash -LiteralPath $log).Hash}
 if($code -ne 0){throw "Build failed: $config"}
}
foreach($e in $inputs){if((Get-FileHash -LiteralPath $e.path).Hash -ne $e.sha256){throw 'Source changed during build'}}
$programs=@((Join-Path $repo 'bin\windows\DualSPHysics5.2CPU_win64_debug.exe'),(Join-Path $output 'DualSPHysics5.2_GEO_win64.exe'),(Join-Path $output 'DualSPHysics5.2_win64_debug.exe')) | ForEach-Object {@{path=$_;sha256=(Get-FileHash -LiteralPath $_).Hash}}
@{built=$true;scope='Mode4 mirrored-footprint candidate only, not physical acceptance';inputs=$inputs;controls=$originals;builds=$builds;programs=@($programs)} | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $manifest -Encoding UTF8
