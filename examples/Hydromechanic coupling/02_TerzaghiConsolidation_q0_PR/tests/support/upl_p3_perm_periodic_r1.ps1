param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Fixed no-wall implementation regression only. Reuse the unchanged actual spatial harness.
# This wrapper does not prepare seeds, run GenCase, change production, or recompute a half gate.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$name='upl_p3_perm_periodic_ReleaseCPU_r1'
$out=Join-Path $tests ("outputs\"+$name)
$exe=Join-Path $out 'upl_p3_spatial_wave_harness_r2.exe'
$harness=Join-Path $PSScriptRoot 'upl_p3_spatial_wave_harness_r2.cpp'
$note=Join-Path $tests 'notes\upl_p3_perm_periodic_r1.json'
$freezePath=Join-Path $logs 'upl_p3_perm_build_r2.json'
$oldFinalPath=Join-Path $logs 'upl_p3_spatial_wave_ReleaseCPU_r5.check.json'
$oldBuildPath=Join-Path $logs 'upl_p3_spatial_wave_ReleaseCPU_r5.build.json'
$seedReceiptPath=Join-Path $logs 'upl_p3_spatial_seed_r1.inputs.json'
$buildPath=Join-Path $logs ($name+'.build.json')
function Entry([string]$path){$i=Get-Item -LiteralPath $path;[ordered]@{path=$i.FullName;bytes=$i.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$path,$v){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Authoring is not permission to execute; both root-authorized flags are required'}
$declaration=Get-Content -Raw -Encoding UTF8 -LiteralPath $note|ConvertFrom-Json
if($declaration.scope -ne 'no_wall_constant_conductivity_flag_OFF_implementation_regression' -or $declaration.harness_sha256 -ne (Entry $harness).sha256){throw 'Frozen declaration/harness mismatch'}
$freeze=Get-Content -Raw -Encoding UTF8 -LiteralPath $freezePath|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Authoritative full-Rebuild source builds not admitted'}
foreach($pair in $freeze.source){Verify @($pair.original,$pair.snapshot)}
Verify $freeze.logs;Verify $freeze.programs

# Both public-default-OFF configurations and both manufactured new-law components
# must be sealed before linking or running this distinct private-dynamic OFF control.
$prerequisiteBindings=@()
$offPath=Join-Path $logs 'upl_p3_perm_off_r2.check.json'
$off=Get-Content -Raw -LiteralPath $offPath|ConvertFrom-Json
if(!$off.passed -or $off.label -ne 'p3_perm_r2' -or $off.actual_native_frame_pairs -ne 140 -or $off.native_ids_per_pair -ne 1040 -or $off.existing_arrays_per_pair -ne 15 -or !$off.all_bits_0ULP -or !$off.clock_step_dterror_exact -or $off.exclusions -ne 0){throw 'Both default-OFF configurations are not admitted'}
$prerequisiteBindings+=Entry $offPath
if(@($off.groups).Count -ne 10 -or @($off.groups|Where-Object {$_.configuration -eq 'DebugCPU'}).Count -ne 5 -or @($off.groups|Where-Object {$_.configuration -eq 'ReleaseCPU'}).Count -ne 5){throw 'Default-OFF group coverage differs'}
foreach($g in $off.groups){
  Verify @($g.check);$p=Get-Content -Raw -LiteralPath $g.check.path|ConvertFrom-Json
  if(!$p.passed -or !$p.all15_original_arrays_ID_aligned_0ULP -or !$p.saved_clock_step_dterror_exact -or $p.actual_native_samples -ne $g.frames){throw 'Default-OFF group failed'}
  Verify $p.receipts;$prerequisiteBindings+=@($g.check)+@($p.receipts)
}
foreach($cfg in @('DebugCPU','ReleaseCPU')){
  $componentPath=Join-Path $logs ('upl_p3_perm_actual_'+$cfg+'_r2.check.json')
  $c=Get-Content -Raw -LiteralPath $componentPath|ConvertFrom-Json;$d=$c.completion
  if(!$c.passed -or $c.configuration -ne $cfg -or !$d.passed -or !$d.actual_private_helper -or $d.field_cases -ne 28 -or $d.helper_evaluations -ne 40 -or $d.rate_checks -ne 728 -or $d.guard_checks -ne 10 -or $d.scale_checks -ne 2 -or $d.total_actual_rate_helper_calls -ne 70 -or $d.physical_trajectory -or $d.physical_acceptance -or $c.physical_acceptance){throw "Manufactured component not admitted: $cfg"}
  Verify @($c.build,$c.off_run,$c.on_run,$c.root_default_OFF_admission);Verify $c.files
  if($c.root_default_OFF_admission.sha256 -ne (Entry $offPath).sha256){throw 'Component default-OFF prerequisite differs'}
  $cb=Get-Content -Raw -LiteralPath $c.build.path|ConvertFrom-Json
  if($cb.configuration -ne $cfg -or $cb.compile_exit -ne 0 -or $cb.link_exit -ne 0 -or $cb.source_freeze.path -ne $freezePath -or $cb.source_freeze.sha256 -ne (Entry $freezePath).sha256){throw 'Component source/build differs'}
  Verify @($cb.source_freeze)
  foreach($rr in @($c.off_run,$c.on_run)){
    $owned=Get-Content -Raw -LiteralPath $rr.path|ConvertFrom-Json
    if($owned.exit_code -ne 0 -or !$owned.owned_call_exited -or $owned.build.sha256 -ne $c.build.sha256){throw 'Component owned run failed or build differs'}
    Verify @($owned.program,$owned.build,$owned.log);$prerequisiteBindings+=@($owned.program,$owned.build,$owned.log)
  }
  if(@($c.constant_law_OFF_complete_text_byte_comparisons).Count -ne 6){throw 'Component constant-law OFF controls incomplete'}
  foreach($q in $c.constant_law_OFF_complete_text_byte_comparisons){
    Verify @($q.current,$q.retained)
    if(!$q.byte_identical -or $q.current.bytes -ne $q.retained.bytes -or $q.current.sha256 -ne $q.retained.sha256){throw 'Component constant-law OFF changed'}
    $prerequisiteBindings+=@($q.current,$q.retained)
  }
  $prerequisiteBindings+=@(Entry $componentPath)+@($c.build,$c.off_run,$c.on_run,$c.root_default_OFF_admission)+@($c.files)
}
$oldFinal=Get-Content -Raw -Encoding UTF8 -LiteralPath $oldFinalPath|ConvertFrom-Json
$oldBuild=Get-Content -Raw -Encoding UTF8 -LiteralPath $oldBuildPath|ConvertFrom-Json
if(!$oldFinal.passed -or $oldBuild.compile_exit -ne 0 -or $oldBuild.link_exit -ne 0){throw 'Retained actual spatial control not admitted'}
# Old production files legitimately changed. Recheck archived harness and selected immutable
# raw controls/receipts, not the historical build's now-current source paths.
$oldHarness=@($oldBuild.snapshots|Where-Object {[IO.Path]::GetFileName($_.path) -eq 'upl_p3_spatial_wave_harness_r2.cpp'})
if($oldHarness.Count -ne 1 -or $oldHarness[0].sha256 -ne (Entry $harness).sha256){throw 'Actual harness differs from retained controls'}
Verify $oldHarness
$seedReceipt=Get-Content -Raw -Encoding UTF8 -LiteralPath $seedReceiptPath|ConvertFrom-Json
$controls=@();$seeds=@();$controlReceipts=@()
foreach($tag in @('c','h')){
  $control=Join-Path $tests ("outputs\upl_p3_spatial_wave_ReleaseCPU_r5_n32_"+$tag)
  $seedDir=Join-Path $tests ("outputs\upl_p3_spatial_seed_r1_n32_"+$tag)
  $selected=@($oldFinal.files|Where-Object {$_.path.StartsWith($control+'\',[StringComparison]::OrdinalIgnoreCase)})
  if($selected.Count -ne @(Get-ChildItem -LiteralPath $control -Recurse -File).Count){throw 'Retained raw control manifest incomplete'}
  Verify $selected;$controls+=$selected
  $seedFiles=@($seedReceipt.files|Where-Object {$_.path.StartsWith($seedDir+'\',[StringComparison]::OrdinalIgnoreCase)})
  if(@($seedFiles|Where-Object {[IO.Path]::GetExtension($_.path) -in '.bi4','.xml'}).Count -ne 2){throw 'Exact-dp runtime/BI4 seed missing'}
  Verify $seedFiles;$seeds+=$seedFiles
  $rp=Join-Path $logs ("upl_p3_spatial_wave_ReleaseCPU_r5_n32_"+$tag+'.run.json')
  $saved=@($oldFinal.receipts|Where-Object {$_.path -eq $rp});if($saved.Count -ne 1){throw 'Retained owned-call receipt missing'};Verify $saved
  $prior=Get-Content -Raw -LiteralPath $rp|ConvertFrom-Json
  if($prior.exit_code -ne 0 -or !$prior.owned_call_exited){throw 'Retained control did not exit successfully'}
  $controlReceipts+=Entry $rp
}
$bindings=@(@($harness,$PSCommandPath,$note,$freezePath,$oldFinalPath,$oldBuildPath,$seedReceiptPath)|ForEach-Object {Entry $_})+$oldHarness+$controls+$seeds+$controlReceipts+$prerequisiteBindings
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $buildPath)){throw 'Retained build protected; no replacement admitted'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $environment=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment setup failed'}
  foreach($line in $environment){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj';[xml]$xml=Get-Content -Raw -LiteralPath $project
  $objects=@();$sources=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false
    foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq "'`$(Configuration)|`$(Platform)'=='ReleaseCPU|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){$objects+=Join-Path $source "VS\Intermediate\DualSPHysics_ReleaseCPU_x64\$stem.obj";$sources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))}
  }
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=$bindings+@(@($project)+$objects+$sources+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  $libs=@('dsphchrono.lib','LibJVtkLib_x64_v143_Release.lib','LibJNumexLib_x64_v143_Release.lib','LibJWaveGen_x64_v143_Release.lib','LibDSphMoorDyn_x64_v143_Release.lib','kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $out|Out-Null
  $copies=@();foreach($p in @($harness,$PSCommandPath,$note)){$target=Join-Path $out ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $target;$copy=Entry $target;if($copy.sha256 -ne (Entry $p).sha256){throw 'Recipe copy mismatch'};$copies+=$copy}
  $obj=Join-Path $out 'perm_periodic.obj';$log=Join-Path $logs ($name+'.build.log')
  if(Test-Path -LiteralPath $log){throw 'Retained build log protected'};[IO.File]::WriteAllBytes($log,[byte[]]@())
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$out\compile.pdb",'/sourceDependencies',(Join-Path $out 'compile.dependencies.json'),'/O2','/MT',$harness)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs
  $start=[DateTime]::UtcNow.ToString('o');$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$ce=$LASTEXITCODE;$le=$null
  if($ce -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$le=$LASTEXITCODE};$ErrorActionPreference=$oldAction
  Verify $inputs;Verify $libraries;Verify $copies
  $runtime=@();if($ce -eq 0 -and $le -eq 0){
    $runtimeSources=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml')
    foreach($p in $runtimeSources){$original=Entry $p;$target=Join-Path $out ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $target;$copy=Entry $target;if($copy.sha256 -ne $original.sha256 -or (Entry $p).sha256 -ne $original.sha256){throw 'Runtime copy mismatch'};$runtime+=@{original=$original;copy=$copy}}
  }
  NewJson $buildPath ([ordered]@{status=if($ce -eq 0 -and $le -eq 0){'built_not_run'}else{'build_failed_retained'};configuration='ReleaseCPU';started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');source_freeze=Entry $freezePath;compile_exit=$ce;link_exit=$le;inputs=$inputs;libraries=$libraries;snapshots=$copies;compile=$compile;link=$link;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};runtime=$runtime;log=Entry $log;physical_acceptance=$false})
  if($ce -ne 0 -or $le -ne 0){throw 'Companion build failed; preserve evidence and stop'};Write-Output "BUILT $exe";exit 0
}
$b=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if($b.status -ne 'built_not_run'){throw 'Companion build not admitted'}
Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.original,$r.copy)}
$final=Join-Path $logs ($name+'.check.json');if(Test-Path -LiteralPath $final){throw 'Retained final check protected'}
$receipts=@();$files=@();$comparisons=@()
foreach($tag in @('c','h')){
  $steps=if($tag -eq 'c'){512}else{1024};$dt=if($tag -eq 'c'){1./16777216.}else{1./33554432.}
  $job=$name+'_n32_'+$tag;$output=Join-Path $tests ('outputs\'+$job)
  $seed=Join-Path $tests ("outputs\upl_p3_spatial_seed_r1_n32_"+$tag+"\CaseUplSpatial_n32_"+$tag)
  $priorDir=Join-Path $tests ("outputs\upl_p3_spatial_wave_ReleaseCPU_r5_n32_"+$tag)
  $run=Join-Path $logs ($job+'.run.json');$log=Join-Path $logs ($job+'.log')
  if((Test-Path -LiteralPath $output) -or (Test-Path -LiteralPath $run) -or (Test-Path -LiteralPath $log)){throw 'Retained actual job protected'}
  Verify $b.inputs;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.copy)}
  $argv=@('--job','32',"$steps",'0','-cpu','-ompthreads:1','-stable',$seed,$output,'-dirdataout','data')
  $start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  NewJson $run ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=Entry $exe;arguments=$argv;log=Entry $log;physical_acceptance=$false});$receipts+=Entry $run
  if($code -ne 0){throw "Actual regression failed: $tag; preserve output and stop later job"}
  $d=Get-Content -Raw -LiteralPath (Join-Path $output 'complete.json')|ConvertFrom-Json
  if(!$d.passed -or !$d.actual_ComputeStep_Sym -or $d.Nx -ne 32 -or $d.native_ids -ne 512 -or $d.steps -ne $steps -or $d.samples -ne 257 -or [double]$d.actual_end_s -ne [double]($steps*$dt) -or $d.smoke -or $d.physical_acceptance){throw 'Wrong actual completion geometry/time/count'}
  $modeHistory=@(Import-Csv -LiteralPath (Join-Path $output 'modes.csv'));if($modeHistory.Count -ne 257){throw 'Incomplete saved times'}
  for($i=0;$i -lt 257;$i++){if([int]$modeHistory[$i].step -ne $i*$steps/256 -or [double]$modeHistory[$i].time_s -ne [double]($i/8388608.)){throw 'Actual saved time/step differs'}}
  $equal=@();foreach($leaf in @('physical.bin','modes.csv','endpoint_policy.csv','complete.json')){$new=Entry (Join-Path $output $leaf);$old=Entry (Join-Path $priorDir $leaf);if($new.bytes -ne $old.bytes -or $new.sha256 -ne $old.sha256){throw "No-wall implementation changed $tag/$leaf"};$equal+=@{current=$new;retained=$old;byte_identical=$true}}
  $physical=Join-Path $output 'physical.bin';$stream=[IO.File]::OpenRead($physical);$reader=New-Object IO.BinaryReader($stream)
  try{if($reader.ReadUInt32() -ne 512 -or $reader.ReadUInt32() -ne 26 -or $reader.ReadUInt32() -ne 257){throw 'Wrong native binary schema'};for($i=0;$i -lt 257;$i++){if($reader.ReadDouble() -ne [double]($i/8388608.)){throw 'Binary actual clock differs'};[void]$stream.Seek(512*26*8,[IO.SeekOrigin]::Current)};if($stream.Position -ne $stream.Length){throw 'Unreviewed raw physical bytes'}}finally{$reader.Dispose();$stream.Dispose()}
  $comparison=Join-Path $logs ($job+'.exact.check.json')
  NewJson $comparison ([ordered]@{passed=$true;native_ids=512;native_id_order='Implicit real IDs 0..511, checked by unchanged actual harness Indices() and tensor-coordinate test';samples=257;columns=26;actual_end_s=[double]$d.actual_end_s;steps=$steps;dt_actual=$dt;all_native_physical_fields_0ULP=$true;all_actual_saved_clocks_exact=$true;equal_files=$equal;new_half_test=$false;physical_acceptance=$false})
  $comparisons+=Entry $comparison;$files+=Get-ChildItem -LiteralPath $output -Recurse -File|ForEach-Object {Entry $_.FullName}
}
Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.original,$r.copy)};Verify $receipts;Verify $files;Verify $comparisons
NewJson $final ([ordered]@{passed=$true;scope='no_wall_constant_conductivity_flag_OFF_implementation_regression';source_freeze=Entry $freezePath;build=Entry $buildPath;retained_controls=Entry $oldFinalPath;prerequisites=$prerequisiteBindings;conductivity_flag=$false;wall_flag=$false;solver_jobs=2;native_ids_per_job=512;samples_per_job=257;columns=26;native_field_pairs=6842368;all_native_physical_fields_0ULP=$true;new_half_test=$false;new_physical_acceptance=$false;physical_acceptance=$false;receipts=$receipts;comparisons=$comparisons;files=$files})
Write-Output "PASSED no-wall implementation invariance only: $final"
