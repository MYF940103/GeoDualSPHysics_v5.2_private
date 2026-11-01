param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [string]$ExpectedBuildStatus='DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests',
  [switch]$ProductionBuildConfirmed
)
# Bounded actual timeguard component only, never invokes a formal solver.
$ErrorActionPreference='Stop';$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$name="upl_p3_timeguard_${Configuration}_$Label";$buildOut=Join-Path $tests "outputs\$name"
$harness=Join-Path $PSScriptRoot 'upl_p3_timeguard_r1.cpp';$base=Join-Path $PSScriptRoot 'upl_p2_feedback_harness_r1.cpp'
$notes=Join-Path $tests 'notes\upl_p3_timeguard_r1.json';$authPath=Join-Path $logs 'upl_p3_time_build_r1.json'
$exe=Join-Path $buildOut 'upl_p3_timeguard_r1.exe';$buildPath=Join-Path $logs ($name+'.build.json')
function Entry([string]$p){$a=Get-Item -LiteralPath $p;[ordered]@{path=$a.FullName;bytes=$a.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($a in $items){$b=Entry $a.path;if($a.sha256 -ne $b.sha256 -or $a.bytes -ne $b.bytes){throw "Frozen artifact changed: $($a.path)"}}}
function NewJson($p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if(!$ProductionBuildConfirmed){throw 'Root must finish authoritative builds and freeze sources first'}
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $buildOut) -or (Test-Path -LiteralPath $buildPath)){throw 'Use a fresh build label'}
  $auth=Get-Content -LiteralPath $authPath -Raw|ConvertFrom-Json
  if($auth.status -ne $ExpectedBuildStatus){throw 'Root authoritative build receipt not admitted'}
  foreach($a in $auth.source){Verify @($a.original,$a.snapshot)};Verify $auth.logs;Verify $auth.programs
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment setup failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj';[xml]$xml=Get-Content -LiteralPath $project -Raw;$objects=@();$sources=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false;foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq "'`$(Configuration)|`$(Platform)'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){$objects+=Join-Path $source "VS\Intermediate\DualSPHysics_${Configuration}_x64\$stem.obj";$sources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))}
  }
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -File -Recurse|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($project,$harness,$base,$notes,$PSCommandPath,$authPath)+$objects+$sources+$headers+@($auth.logs|ForEach-Object {$_.path})+@($auth.programs|ForEach-Object {$_.path})|Sort-Object -Unique|ForEach-Object {Entry $_})
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")});New-Item -ItemType Directory -Path $buildOut|Out-Null;$snapshots=@()
  foreach($p in @($harness,$base,$notes,$PSCommandPath,$authPath)){$dest=Join-Path $buildOut ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;if((Entry $p).sha256 -ne (Entry $dest).sha256){throw 'Recipe/source snapshot mismatch'};$snapshots+=Entry $dest}
  $obj=Join-Path $buildOut 'upl_p3_timeguard_r1.obj';$log=Join-Path $logs ($name+'.build.log');[IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$buildOut\compile.pdb",'/sourceDependencies',(Join-Path $buildOut 'compile.dependencies.json'))+$flags+@($harness)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs;if($debug){$link+=@('/DEBUG',"/PDB:$buildOut\link.pdb")}
  $started=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$ce=$LASTEXITCODE;$le=$null
  if($ce -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$le=$LASTEXITCODE};$ErrorActionPreference=$old
  Verify $inputs;Verify $libraries;Verify $snapshots;$runtime=@()
  if($ce -eq 0 -and $le -eq 0){foreach($p in (@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml'))){$original=Entry $p;$dest=Join-Path $buildOut ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$copy=Entry $dest;if($original.sha256 -ne $copy.sha256){throw 'Runtime copy mismatch'};$runtime+=@{original=$original;copy=$copy}}}
  NewJson $buildPath ([ordered]@{status=if($ce -eq 0 -and $le -eq 0){'built_not_run'}else{'build_failed_retained'};configuration=$Configuration;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');compile_exit=$ce;link_exit=$le;inputs=$inputs;libraries=$libraries;snapshots=$snapshots;runtime=$runtime;compile=$compile;link=$link;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};log=(Entry $log);physical_acceptance=$false})
  if($ce -ne 0 -or $le -ne 0){throw 'Timeguard companion build failed; preserve label'};Write-Output "BUILT $exe";exit 0
}
$build=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json;if($build.status -ne 'built_not_run'){throw 'No successful frozen companion build'}
function VerifyAll{Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program);foreach($r in $build.runtime){Verify @($r.original,$r.copy)}}
VerifyAll;$runName=$name+'_run';$out=Join-Path $tests "outputs\$runName";$log=Join-Path $logs ($runName+'.log');$receipt=Join-Path $logs ($runName+'.run.json');$check=Join-Path $logs ($runName+'.check.json')
foreach($p in @($out,$log,$receipt,$check)){if(Test-Path -LiteralPath $p){throw 'Fresh run label required; no retry or overwrite'}}
$started=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
& $exe '--out' $out 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
NewJson $receipt ([ordered]@{exit_code=$code;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');owned_call_exited=$true;program=(Entry $exe);build_receipt=(Entry $buildPath);arguments=@('--out',$out);log=(Entry $log);physical_acceptance=$false})
if($code -ne 0){throw 'Timeguard component failed; preserve outputs and diagnose, no later stage admitted'};VerifyAll
$done=Get-Content -LiteralPath (Join-Path $out 'complete.json') -Raw|ConvertFrom-Json
if(!$done.passed -or $done.scale_cases -ne 16 -or $done.domain_cases -ne 12 -or $done.requested_step_cases -ne 20 -or $done.actual_first_step_rejections -ne 4 -or !$done.actual_ComputeStep_Sym_rejected_before_Pre -or $done.physical_acceptance){throw 'Timeguard completion disagrees with predeclared scope'}
$files=@(Get-ChildItem -LiteralPath $out -File -Recurse|Sort-Object FullName|ForEach-Object {Entry $_.FullName});Verify $files
NewJson $check ([ordered]@{passed=$true;configuration=$Configuration;scope='necessary private current-state time guards; rejected first predictor before update, no complete trajectory';completion=$done;run_receipt=(Entry $receipt);build_receipt=(Entry $buildPath);files=$files;output_manifest_posthoc=$true;pre_run_output_attestation=$false;physical_acceptance=$false})
Write-Output "PASSED $check"
