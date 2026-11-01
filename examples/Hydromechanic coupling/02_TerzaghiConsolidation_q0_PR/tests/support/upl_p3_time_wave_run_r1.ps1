param(
  [ValidateSet('PrepareM4','Build','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [ValidateSet('fundamental','m4')][string]$Window='fundamental',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Two fixed admitted windows only; no arbitrary-mode/parameter runner.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$logs=Join-Path $tests 'logs'
$prefix=if($Window -eq 'fundamental'){'upl_p3_time_wave'}else{'upl_p3_time_m4'}
$name="${prefix}_${Configuration}_$Label"
$buildOut=Join-Path $tests "outputs\$name"
$harness=Join-Path $PSScriptRoot ($prefix+'_harness_r1.cpp')
$notes=Join-Path $tests 'notes\upl_p3_time_wave_r1.json'
$coarse=Join-Path $tests $(if($Window -eq 'fundamental'){'configs\upl_p3_wave_c_r1_Def.xml'}else{'configs\upl_p3_time_m4_c_r1_Def.xml'})
$addendum=Join-Path $tests $(if($Window -eq 'fundamental'){'configs\upl_p3_wave_h_r1_Def.xml'}else{'configs\upl_p3_time_m4_h_r1_Def.xml'})
$exe=Join-Path $buildOut ($prefix+'_harness_r1.exe')
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


$freezePath=Join-Path $logs 'upl_p3_time_build_r1.json'
$freeze=Get-Content -LiteralPath $freezePath -Raw|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'){throw 'Authoritative source is not frozen'}
foreach($entry in $freeze.source){Verify @($entry.original,$entry.snapshot)}


if($Mode -eq 'PrepareM4'){
  if($Window -ne 'm4' -or !$ExecutionAuthorized){throw 'Explicit root authorization is required for fixed M4 seed copies.'}
  $prepPath=Join-Path $logs 'upl_p3_time_m4_seed_r1.inputs.json'
  if(Test-Path -LiteralPath $prepPath){throw 'Prepared seeds are immutable; do not repeat preparation'}
  $oldPath=Join-Path $logs 'upl_p3_wave_seed_r1.inputs.json';$old=Get-Content -LiteralPath $oldPath -Raw|ConvertFrom-Json
  Verify $old.inputs;Verify $old.jobs;Verify $old.files
  $inputs=@((Entry $PSCommandPath),(Entry $notes),(Entry $oldPath));$files=@();$copies=@()
  foreach($tag in @('c','h')){
    $stem='CaseUplWave_'+$tag
    $parent=Join-Path $tests ('outputs\upl_p3_wave_seed_r1_'+$tag)
    $output=Join-Path $tests ('outputs\upl_p3_time_m4_seed_r1_'+$tag)
    if(Test-Path -LiteralPath $output){throw 'Prepared seed output already exists'}
    $xmlPath=Join-Path $tests ('configs\upl_p3_time_m4_'+$tag+'_r1.xml')
    [xml]$xml=Get-Content -LiteralPath $xmlPath -Raw;[xml]$control=Get-Content -LiteralPath (Join-Path $parent ($stem+'.xml')) -Raw
    if($xml.case.execution.particles.np -ne 128 -or $xml.case.execution.particles.nb -ne 0 -or $xml.case.casedef.OuterXml -ne $control.case.casedef.OuterXml -or $xml.case.execution.constants.OuterXml -ne $control.case.execution.constants.OuterXml -or $xml.case.execution.special.OuterXml -ne $control.case.execution.special.OuterXml -or $xml.case.execution.particles.OuterXml -ne $control.case.execution.particles.OuterXml){throw 'M4 copy changed particle geometry/constants/material'}
    $ps=$xml.case.execution.parameters.parameter;$oldps=$control.case.execution.parameters.parameter
    foreach($p in $ps){
      $original=@($oldps|Where-Object {$_.key -eq $p.key})
      if($original.Count -ne 1){throw 'Ambiguous original XML parameter'}
      if($p.key -in 'TimeMax','TimeOut'){
        if([double]$p.value -ne 1./131072.){throw 'Wrong fixed M4 end/cadence'}
      }elseif($p.OuterXml -ne $original[0].OuterXml){throw ('M4 runtime changed parameter '+$p.key)}
    }
    $bi4=Join-Path $parent ($stem+'.bi4');$inputs+=@((Entry $xmlPath),(Entry $bi4))
    New-Item -ItemType Directory -Path $output|Out-Null
    foreach($pair in @(@($xmlPath,(Join-Path $output ($stem+'.xml'))),@($bi4,(Join-Path $output ($stem+'.bi4'))))){
      Copy-Item -LiteralPath $pair[0] -Destination $pair[1]
      $a=Entry $pair[0];$b=Entry $pair[1];if($a.sha256 -ne $b.sha256){throw 'Seed copy changed bytes'}
      $copies+=@{original=$a;copy=$b};$files+=$b
    }
  }
  Verify $inputs;Verify $files
  NewJson $prepPath ([ordered]@{status='prepared_not_run';geometry_reused_byte_identically=$true;gencase_or_solver_started=$false;inputs=$inputs;copies=$copies;files=$files;physical_acceptance=$false})
  Write-Output "PREPARED fixed M4 seed copies: $prepPath";exit 0
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
  $inputs=@(@($project,$harness,$PSCommandPath,$notes,$coarse,$addendum,(Join-Path $logs 'upl_p3_time_build_r1.json'))+$objects+$sourceFiles+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
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
  $obj=Join-Path $buildOut 'time_wave.obj'
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
  if(!$ExecutionAuthorized -or !$ProductionBuildConfirmed){throw 'Explicit root execution authorization and authoritative freeze required'}
  $build=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
  if($build.status -ne 'built_not_run'){throw 'No successful frozen build'}
  Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program)
  foreach($item in $build.runtime){Verify @($item.copy)}
  $fundamental=$Window -eq 'fundamental'
  $samples=if($fundamental){257}else{65};$end=if($fundamental){1./32768.}else{1./131072.}
  $prepPath=Join-Path $logs $(if($fundamental){'upl_p3_wave_seed_r1.inputs.json'}else{'upl_p3_time_m4_seed_r1.inputs.json'})
  $prep=Get-Content -LiteralPath $prepPath -Raw|ConvertFrom-Json
  Verify $prep.inputs;Verify $prep.files;if($prep.jobs){Verify $prep.jobs}
  if($fundamental){
    $k0Path=Join-Path $logs 'upl_p2_wave_seed_r2.inputs.json';$k0=Get-Content -LiteralPath $k0Path -Raw|ConvertFrom-Json
    Verify $k0.inputs;Verify $k0.jobs;Verify $k0.files
    $oldPath=Join-Path $logs ("upl_p3_wave_"+$Configuration+"_r3.check.json");$old=Get-Content -LiteralPath $oldPath -Raw|ConvertFrom-Json
    if(!$old.passed){throw 'Retained same-config r3 was not admitted'}
    Verify @($old.build,$old.seeds);Verify $old.receipts;Verify $old.files
  }else{
    foreach($config in @('DebugCPU','ReleaseCPU')){
      $path=Join-Path $logs ("upl_p3_time_wave_"+$config+"_r1.check.json")
      $gate=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
      if(!$gate.passed -or $gate.solver_jobs -ne 10 -or $gate.comparison_jobs -ne 18){throw 'Full fundamental new-time regression prerequisite missing'}
      Verify $gate.receipts;Verify $gate.files
    }
  }
  $final=Join-Path $logs ($name+'.check.json');if(Test-Path -LiteralPath $final){throw 'Retained final check protected'}
  $program=Entry $exe;$receipts=@();$folders=@();$completed=@{};$script:CompareCount=0
  function InvokeWave([string]$job,[string[]]$arguments){
    $log=Join-Path $logs ($job+'.log');$outcome=Join-Path $logs ($job+'.run.json')
    if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $outcome)){throw 'Retained job protected'}
    [IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o')
    $before=$ErrorActionPreference;$ErrorActionPreference='Continue'
    & $exe @arguments 2>&1|Tee-Object -FilePath $log|Out-Host
    $code=$LASTEXITCODE;$ErrorActionPreference=$before
    NewJson $outcome ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');program=$program;build=(Entry $buildReceipt);arguments=$arguments;log=(Entry $log);physical_acceptance=$false})
    if($code -ne 0){throw "Wave failed: $job; preserve physical output and stop later dependent jobs"}
    Entry $outcome
  }
  function CompareWave([string]$job,[string]$left,[string]$right,[string]$kind){
    $target=Join-Path $logs ($job+'.check.json')
    if(Test-Path -LiteralPath $target){throw 'Retained comparison protected'}
    InvokeWave $job @('--compare',(Join-Path $left 'physical.bin'),(Join-Path $right 'physical.bin'),$kind,$target)
    if(!(Get-Content -LiteralPath $target -Raw|ConvertFrom-Json).passed){throw 'Comparison rejected'}
    $script:CompareCount++;Entry $target
  }
  $physicsList=if($fundamental){@('k0','k1')}else{@('k1')}
  foreach($physics in $physicsList){
    foreach($tag in @('c','h')){
      $steps=if($fundamental){if($tag -eq 'c'){256}else{512}}else{if($tag -eq 'c'){64}else{128}}
      $seed=if(!$fundamental){'upl_p3_time_m4_seed_r1_'}elseif($physics -eq 'k0'){'upl_p2_wave_seed_r2_'}else{'upl_p3_wave_seed_r1_'}
      $input=Join-Path $tests ("outputs\"+$seed+$tag+"\CaseUplWave_"+$tag)
      $engines=if($fundamental -and $physics -eq 'k1'){@('audit','actual','rho')}else{@('audit','actual')}
      foreach($engine in $engines){
        $job=$name+"_"+$physics+"_"+$tag+"_"+$engine;$output=Join-Path $tests ("outputs\"+$job)
        if(Test-Path -LiteralPath $output){throw 'Retained physical output protected'}
        $engineArg=if($engine -eq 'audit'){'audit'}else{'actual'};$poison=if($engine -eq 'rho'){'1'}else{'0'}
        $receipts+=InvokeWave $job @('--job',$engineArg,$poison,"$steps",'-cpu','-ompthreads:1','-stable',$input,$output,'-dirdataout','data')
        $done=Get-Content -LiteralPath (Join-Path $output 'complete.json') -Raw|ConvertFrom-Json
        if(!$done.passed -or $done.native_ids -ne 128 -or $done.samples -ne $samples -or $done.steps -ne $steps -or $done.actual_end_s -ne $end -or $done.physical_acceptance -or $done.max_fixed_dt_error_s -gt 1e-14){throw 'Native trajectory/time-policy completion invalid'}
        $expected=if($engine -eq 'audit'){2*$steps}else{0}
        if($done.force_stage_audits -ne $expected -or $done.time_policy_calls -ne $expected){throw 'Missing force/policy stage audit'}
        if(($physics -eq 'k0' -and $done.hydraulic_conductivity -ne 0) -or ($physics -eq 'k1' -and [math]::Abs($done.hydraulic_conductivity-1e-4) -gt 1e-11)){throw 'Wrong conductivity'}
        $rows=@(Import-Csv -LiteralPath (Join-Path $output 'modes.csv'))
        if($rows.Count -ne $samples){throw 'Incomplete mode history'}
        for($i=0;$i -lt $samples;$i++){if([int]$rows[$i].step -ne $i*$steps/($samples-1) -or [double]$rows[$i].time_s -ne $i/8388608.0){throw 'Actual dyadic time/step identity changed'}}
        $policy=@(Import-Csv -LiteralPath (Join-Path $output 'time_policy.csv'));if($policy.Count -ne $expected){throw 'Incomplete policy history'}
        if($fundamental){
          $control=Join-Path $tests ("outputs\upl_p3_wave_"+$Configuration+"_r3_"+$physics+"_"+$tag+"_"+$engine)
          $receipts+=CompareWave ($job+'_r3_compare') $output $control 'exact'
        }
        $completed[$physics+'_'+$tag+'_'+$engine]=$output;$folders+=$output
      }
      $actual=$completed[$physics+'_'+$tag+'_actual']
      $receipts+=CompareWave ($name+"_"+$physics+"_"+$tag+"_audit_compare") $actual $completed[$physics+'_'+$tag+'_audit'] 'exact'
      if($fundamental -and $physics -eq 'k1'){$receipts+=CompareWave ($name+"_"+$physics+"_"+$tag+"_rho_compare") $actual $completed[$physics+'_'+$tag+'_rho'] 'rho'}
    }
    $receipts+=CompareWave ($name+"_"+$physics+"_half_compare") $completed[$physics+'_c_actual'] $completed[$physics+'_h_actual'] 'half'
  }
  Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program)
  foreach($item in $build.runtime){Verify @($item.copy)}
  Verify $prep.inputs;Verify $prep.files;if($prep.jobs){Verify $prep.jobs}
  if($fundamental){Verify $k0.inputs;Verify $k0.jobs;Verify $k0.files;Verify @($old.build,$old.seeds);Verify $old.receipts;Verify $old.files}
  Verify $receipts
  $files=@($folders|ForEach-Object {Get-ChildItem -LiteralPath $_ -Recurse -File}|Sort-Object FullName|ForEach-Object {Entry $_.FullName})
  $expectedJobs=if($fundamental){10}else{4};$expectedCompare=if($fundamental){18}else{3}
  if($completed.Count -ne $expectedJobs -or $script:CompareCount -ne $expectedCompare){throw 'Unexpected fixed job/comparison set'}
  NewJson $final ([ordered]@{passed=$true;window=$Window;source_freeze=(Entry $freezePath);build=(Entry $buildReceipt);seeds=(Entry $prepPath);old_r3=if($fundamental){Entry $oldPath}else{$null};solver_jobs=$completed.Count;comparison_jobs=$script:CompareCount;receipts=$receipts;files=$files;actual_time_pairs=$samples;native_ids=128;serialized_columns=26;dynamic_Darcy=$true;new_dterror_is_nonserialized_model_telemetry=$true;default_OFF_checked_separately=$true;whole_Run_output_scheduling=$false;physical_acceptance=$false})
  Write-Output "PASSED fixed $Window time-policy wave; pending review: $final";exit 0
}

