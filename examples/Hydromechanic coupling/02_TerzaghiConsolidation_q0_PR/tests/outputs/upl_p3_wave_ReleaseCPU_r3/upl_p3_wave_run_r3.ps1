param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r3',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Bounded actual-step wave. Prepare/Run require explicit root authorization.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$logs=Join-Path $tests 'logs'
$name="upl_p3_wave_${Configuration}_$Label"
$buildOut=Join-Path $tests "outputs\$name"
$harness=Join-Path $PSScriptRoot 'upl_p3_wave_harness_r1.cpp'
$notes=Join-Path $tests 'notes\upl_p3_wave_r3.json'
$coarse=Join-Path $tests 'configs\upl_p3_wave_c_r1_Def.xml'
$addendum=Join-Path $tests 'configs\upl_p3_wave_h_r1_Def.xml'
$exe=Join-Path $buildOut 'upl_p3_wave_harness_r1.exe'
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


$freezePath=Join-Path $logs 'upl_p3_actual_build_r2.json'
$freeze=Get-Content -LiteralPath $freezePath -Raw|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'){throw 'Authoritative source is not frozen'}
foreach($entry in $freeze.source){Verify @($entry.original,$entry.snapshot)}

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
  $inputs=@(@($project,$harness,$PSCommandPath,$notes,$coarse,$addendum,(Join-Path $logs 'upl_p3_actual_build_r2.json'))+$objects+$sourceFiles+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $buildOut|Out-Null
  $snapshots=@()
  foreach($path in @($harness,$PSCommandPath,$notes,$coarse,$addendum)){
    $dest=Join-Path $buildOut ([IO.Path]::GetFileName($path))
    Copy-Item -LiteralPath $path -Destination $dest
    if((Entry $dest).sha256 -ne (Entry $path).sha256){throw 'Build recipe snapshot mismatch'}
    $snapshots+=Entry $dest
  }
  $obj=Join-Path $buildOut 'upl_p3_wave_harness_r1.obj'
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
  if(!$ExecutionAuthorized -or !$ProductionBuildConfirmed){throw 'Wait for explicit root run authorization and authoritative build freeze.'}
  $build=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
  if($build.status -ne 'built_not_run'){throw 'No successful frozen build.'}
  Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program)
  foreach($item in $build.runtime){Verify @($item.copy)}
  $prepPath=Join-Path $logs 'upl_p3_wave_seed_r1.inputs.json';$prep=Get-Content -LiteralPath $prepPath -Raw|ConvertFrom-Json
  Verify $prep.inputs;Verify $prep.jobs;Verify $prep.files
  $oldPrepPath=Join-Path $logs 'upl_p2_wave_seed_r2.inputs.json';$oldPrep=Get-Content -LiteralPath $oldPrepPath -Raw|ConvertFrom-Json
  Verify $oldPrep.inputs;Verify $oldPrep.jobs;Verify $oldPrep.files
  $oldWavePath=Join-Path $logs 'upl_p3_wave_preclear_source_hold_r1.json'
  $oldWave=Get-Content -LiteralPath $oldWavePath -Raw|ConvertFrom-Json
  Verify @($oldWave.build,$oldWave.r1_interruption);Verify $oldWave.inputs;Verify $oldWave.checks
  foreach($old in $oldWave.jobs){Verify $old.files;if($old.receipt){Verify @($old.receipt)}}
  $oldSource=Get-Content -LiteralPath (Join-Path $logs 'upl_p3_actual_build_r1.json') -Raw|ConvertFrom-Json
  foreach($entry in $oldSource.source){Verify @($entry.snapshot)}
  $oldProgram=Get-Content -LiteralPath $oldWave.build.path -Raw|ConvertFrom-Json
  Verify @($oldProgram.program);Verify $oldProgram.snapshots;foreach($runtime in $oldProgram.runtime){Verify @($runtime.copy)}
  $p2Path=Join-Path $logs ("upl_p2_wave_"+$Configuration+"_r3.check.json");$p2=Get-Content -LiteralPath $p2Path -Raw|ConvertFrom-Json
  if(!$p2.passed){throw 'Retained same-config P2 controls not admitted'}
  Verify @($p2.build,$p2.seeds);Verify $p2.receipts;Verify $p2.files
  $final=Join-Path $logs ($name+'.check.json');if(Test-Path -LiteralPath $final){throw 'Retained final check protected.'}
  $program=Entry $exe;$receipts=@();$outputFolders=@();$completed=@{}
  function InvokeWave([string]$job,[string[]]$arguments){
    $log=Join-Path $logs ($job+'.log');$receipt=Join-Path $logs ($job+'.run.json')
    if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt)){throw 'Retained job protected.'}
    [IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o')
    $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
    & $exe @arguments 2>&1|Tee-Object -FilePath $log|Out-Host
    $exit=$LASTEXITCODE;$ErrorActionPreference=$oldAction
    NewJson $receipt ([ordered]@{exit_code=$exit;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');program=$program;build=(Entry $buildReceipt);arguments=$arguments;log=(Entry $log);owned_call_exited=$true;physical_acceptance=$false})
    if($exit -ne 0){throw "Wave job rejected: $job. Preserve evidence; no numerical retry."}
    Entry $receipt
  }
  function CompareWave([string]$job,[string]$left,[string]$right,[string]$kind){
    $target=Join-Path $logs ($job+'.check.json')
    if(Test-Path -LiteralPath $target){throw 'Retained comparison protected.'}
    InvokeWave $job @('--compare',(Join-Path $left 'physical.bin'),(Join-Path $right 'physical.bin'),$kind,$target)
    if(!(Get-Content -LiteralPath $target -Raw|ConvertFrom-Json).passed){throw 'Comparison did not pass.'}
    Entry $target
  }
  foreach($physics in @('k0','k1')){
    foreach($tag in @('c','h')){
      $steps=if($tag -eq 'c'){256}else{512}
      $seedName=if($physics -eq 'k0'){'upl_p2_wave_seed_r2_'}else{'upl_p3_wave_seed_r1_'}
      $prefix=Join-Path $tests ("outputs\"+$seedName+$tag+"\CaseUplWave_"+$tag)
      $engines=if($physics -eq 'k0'){@('audit','actual')}else{@('audit','actual','rho')}
      foreach($engine in $engines){
        $job=$name+"_"+$physics+"_"+$tag+"_"+$engine;$out=Join-Path $tests ("outputs\"+$job)
        if(Test-Path -LiteralPath $out){throw 'Retained wave output protected.'}
        $actualEngine=if($engine -eq 'audit'){'audit'}else{'actual'};$poison=if($engine -eq 'rho'){'1'}else{'0'}
        $arguments=@('--job',$actualEngine,$poison,"$steps",'-cpu','-ompthreads:1','-stable',$prefix,$out,'-dirdataout','data')
        $receipts+=InvokeWave $job $arguments
        $done=Get-Content -LiteralPath (Join-Path $out 'complete.json') -Raw|ConvertFrom-Json
        if(!$done.passed -or $done.native_ids -ne 128 -or $done.samples -ne 257 -or $done.steps -ne $steps -or $done.actual_end_s -ne (1./32768.) -or $done.physical_acceptance){throw 'Incomplete wave completion'}
        if($engine -eq 'audit' -and $done.force_stage_audits -ne 2*$steps){throw 'Missing force audits'}
        if(($physics -eq 'k0' -and $done.hydraulic_conductivity -ne 0) -or ($physics -eq 'k1' -and [math]::Abs($done.hydraulic_conductivity-1e-4) -gt 1e-11)){throw 'Wrong admitted conductivity'}
        # Modes carry actual Nstep at each paired endpoint; no rewritten metadata.
        $rows=@(Import-Csv -LiteralPath (Join-Path $out 'modes.csv'))
        if($rows.Count -ne 257){throw 'Incomplete actual-step modes'}
        for($i=0;$i -lt 257;$i++){if([int]$rows[$i].step -ne ($i*$steps/256) -or [double]$rows[$i].time_s -ne ($i/8388608.0)){throw 'Saved actual time/step mismatch'}}
        # New-build results never adopt old fields: compare each completed unique old trajectory as a control.
        $controlName=if($physics -eq 'k1' -and $tag -eq 'h' -and $engine -eq 'audit'){'upl_p3_wave_DebugCPU_r2_k1_h_audit'}else{'upl_p3_wave_DebugCPU_r1_'+$physics+'_'+$tag+'_'+$engine}
        $control=@($oldWave.jobs|Where-Object {$_.name -eq $controlName})
        if($control.Count -gt 1){throw 'Ambiguous old-build regression control'}
        if($control.Count -eq 1){
          $receipts+=CompareWave ($job+'_oldbuild_compare') $out $control[0].directory 'exact'
        }elseif(!($physics -eq 'k1' -and $tag -eq 'h' -and $engine -in @('actual','rho'))){throw 'Missing expected sealed old trajectory'}
        $completed[$physics+'_'+$tag+'_'+$engine]=$out;$outputFolders+=$out
      }
      $a=$completed[$physics+'_'+$tag+'_actual'];$b=$completed[$physics+'_'+$tag+'_audit']
      $receipts+=CompareWave ($name+"_"+$physics+"_"+$tag+"_exact_compare") $a $b 'exact'
      if($physics -eq 'k0'){
        $old=Join-Path $tests ("outputs\upl_p2_wave_"+$Configuration+"_r3_"+$tag+"_actual")
        $oldDone=Get-Content -LiteralPath (Join-Path $old 'complete.json') -Raw|ConvertFrom-Json
        if($oldDone.steps -ne $steps -or $oldDone.samples -ne 257){throw 'Retained P2 step identity differs'}
        $receipts+=CompareWave ($name+"_"+$physics+"_"+$tag+"_p2_compare") $a $old 'p2'
      }else{
        $receipts+=CompareWave ($name+"_"+$physics+"_"+$tag+"_rho_compare") $a $completed[$physics+'_'+$tag+'_rho'] 'rho'
      }
    }
    $receipts+=CompareWave ($name+"_"+$physics+"_half") $completed[$physics+'_c_actual'] $completed[$physics+'_h_actual'] 'half'
  }
  Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program)
  foreach($item in $build.runtime){Verify @($item.copy)}
  Verify $prep.inputs;Verify $prep.jobs;Verify $prep.files;Verify $oldPrep.inputs;Verify $oldPrep.jobs;Verify $oldPrep.files
  foreach($old in $oldWave.jobs){Verify $old.files;if($old.receipt){Verify @($old.receipt)}}
  Verify @($p2.build,$p2.seeds);Verify $p2.receipts;Verify $p2.files;Verify $receipts
  $files=@($outputFolders|ForEach-Object {Get-ChildItem -LiteralPath $_ -Recurse -File}|Sort-Object FullName|ForEach-Object {Entry $_.FullName})
  NewJson $final ([ordered]@{passed=$true;new_build_only=$true;old_build_regression=(Entry $oldWavePath);stage='private2DnonzeroKcoupledComputeStep';build=(Entry $buildReceipt);seeds=(Entry $prepPath);adopted_k0_seeds=(Entry $oldPrepPath);retained_P2=(Entry $p2Path);receipts=$receipts;files=$files;actual_time_pairs=257;native_ids=128;physical_columns=25;legacy_rho_also_exact_for_audit=$true;rho_causal_exception_only=$true;dynamic_Darcy=$true;whole_Run_output_scheduling=$false;physical_acceptance=$false})
  Write-Output "PASSED bounded private P3 wave; pending review: $final";exit 0
}
