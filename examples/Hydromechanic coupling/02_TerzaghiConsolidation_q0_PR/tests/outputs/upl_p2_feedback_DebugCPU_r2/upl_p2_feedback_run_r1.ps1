param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [switch]$ProductionBuildConfirmed
)
# Bounded prescribed-kinematics component fixture, not a coupled physical run.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$logs=Join-Path $tests 'logs'
$name="upl_p2_feedback_${Configuration}_$Label"
$buildOut=Join-Path $tests "outputs\$name"
$harness=Join-Path $PSScriptRoot 'upl_p2_feedback_harness_r1.cpp'
$notes=Join-Path $tests 'notes\upl_p2_feedback_r1.json'
$addendum=Join-Path $tests 'notes\upl_p2_feedback_r2.json'
$exe=Join-Path $buildOut 'upl_p2_feedback_harness_r1.exe'
$buildReceipt=Join-Path $logs ($name+'.build.json')
function Entry([string]$path){
  $item=Get-Item -LiteralPath $path
  [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function NewJson([string]$path,$value){
  if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"}
  [IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
}
function Verify($entries){
  foreach($item in $entries){
    $now=Entry $item.path
    if($now.sha256 -ne $item.sha256 -or $now.bytes -ne $item.bytes){throw "Frozen artifact changed: $($item.path)"}
  }
}
if($Mode -eq 'Build'){
  if(!$ProductionBuildConfirmed){throw 'Wait for the root agent to finish and freeze both authoritative CPU builds.'}
  if((Test-Path -LiteralPath $buildOut) -or (Test-Path -LiteralPath $buildReceipt)){throw 'Use a fresh label; never overwrite a build.'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'Visual Studio environment setup failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj'
  [xml]$xml=Get-Content -LiteralPath $project -Raw
  $objects=@();$sourceFiles=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false
    foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){
      if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq "'`$(Configuration)|`$(Platform)'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}
    }
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){
      $objects+=Join-Path $source "VS\Intermediate\DualSPHysics_${Configuration}_x64\$stem.obj"
      $sourceFiles+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))
    }
  }
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($project,$harness,$PSCommandPath,$notes,$addendum)+$objects+$sourceFiles+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $buildOut|Out-Null
  $snapshots=@()
  foreach($path in @($harness,$PSCommandPath,$notes,$addendum)){
    $dest=Join-Path $buildOut ([IO.Path]::GetFileName($path))
    Copy-Item -LiteralPath $path -Destination $dest
    if((Entry $dest).sha256 -ne (Entry $path).sha256){throw 'Build recipe snapshot mismatch'}
    $snapshots+=Entry $dest
  }
  $obj=Join-Path $buildOut 'upl_p2_feedback_harness_r1.obj'
  $log=Join-Path $logs ($name+'.build.log')
  if(Test-Path -LiteralPath $log){throw 'Build log already exists'}
  [IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$buildOut\compile.pdb",'/sourceDependencies',(Join-Path $buildOut 'compile.dependencies.json'))+$flags+@($harness)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs
  if($debug){$link+=@('/DEBUG',"/PDB:$buildOut\link.pdb")}
  $started=[DateTime]::UtcNow.ToString('o')
  $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host
  $compileExit=$LASTEXITCODE;$linkExit=$null
  if($compileExit -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$linkExit=$LASTEXITCODE}
  $ErrorActionPreference=$oldAction
  Verify $inputs;Verify $libraries;Verify $snapshots
  $runtime=@()
  if($compileExit -eq 0 -and $linkExit -eq 0){
    $runtimeSources=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml')
    foreach($path in $runtimeSources){
      $original=Entry $path;$dest=Join-Path $buildOut ([IO.Path]::GetFileName($path));Copy-Item -LiteralPath $path -Destination $dest
      $copy=Entry $dest;if($copy.sha256 -ne $original.sha256 -or (Entry $path).sha256 -ne $original.sha256){throw 'Runtime changed during copy'}
      $runtime+=@{original=$original;copy=$copy}
    }
  }
  NewJson $buildReceipt ([ordered]@{status=if($compileExit -eq 0 -and $linkExit -eq 0){'built_not_run'}else{'build_failed_retained'};configuration=$Configuration;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');git_head=(& git -C $repo rev-parse HEAD);compile_exit=$compileExit;link_exit=$linkExit;inputs=$inputs;libraries=$libraries;snapshots=$snapshots;compile=$compile;link=$link;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};log=(Entry $log);runtime=$runtime;physical_acceptance=$false})
  if($compileExit -ne 0 -or $linkExit -ne 0){throw 'Fixture build failed; inspect retained log and receipt. Do not overwrite.'}
  Write-Output "BUILT $exe";exit 0
}
if($Mode -eq 'Run'){
  if(!$ProductionBuildConfirmed){throw 'The root must confirm the source/build freeze before running this component fixture.'}
  $build=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
  if($build.status -ne 'built_not_run'){throw 'No successful frozen fixture build'}
  Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program)
  foreach($item in $build.runtime){Verify @($item.copy)}
  $runName=$name+'_run';$out=Join-Path $tests "outputs\$runName"
  $log=Join-Path $logs ($runName+'.log');$receipt=Join-Path $logs ($runName+'.run.json');$check=Join-Path $logs ($runName+'.check.json')
  if((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt) -or (Test-Path -LiteralPath $check)){throw 'Retained run protected; no automatic retry'}
  $program=Entry $exe;$arguments=@('--out',$out);$started=[DateTime]::UtcNow.ToString('o')
  [IO.File]::WriteAllBytes($log,[byte[]]@())
  $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @arguments 2>&1|Tee-Object -FilePath $log|Out-Host
  $code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  NewJson $receipt ([ordered]@{exit_code=$code;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');program=$program;build_receipt=(Entry $buildReceipt);arguments=$arguments;log=(Entry $log);owned_call_exited=$true;prescribed_kinematics=$true;physical_outer_loop=$false;physical_acceptance=$false})
  if($code -ne 0){throw "Fixture rejected ($code); preserve output and diagnose, do not rerun"}
  Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program)
  foreach($item in $build.runtime){Verify @($item.copy)}
  $done=Get-Content -LiteralPath (Join-Path $out 'complete.json') -Raw|ConvertFrom-Json
  if(!$done.passed -or $done.half_pairs -ne 520 -or $done.scope_guards -ne 30 -or !$done.actual_feedback_ct_and_state_helpers -or !$done.old_positive_rho_poison_0ULP -or $done.physical_outer_loop_used -or $done.periodic_affine_claimed -or $done.physical_acceptance){throw 'Completion metadata disagrees with predeclared component scope'}
  $files=@(Get-ChildItem -LiteralPath $out -Recurse -File|Sort-Object FullName|ForEach-Object {Entry $_.FullName})
  Verify $files
  NewJson $check ([ordered]@{passed=$true;configuration=$Configuration;scope='actual CPU component operators and prescribed p/J integration; not a coupled physical trajectory';completion=$done;run_receipt=(Entry $receipt);build_receipt=(Entry $buildReceipt);files=$files;output_manifest_posthoc=$true;pre_run_output_attestation=$false;no_old_controls_rerun=$true;physical_acceptance=$false})
  Write-Output "PASSED bounded feedback component gates: $check";exit 0
}
