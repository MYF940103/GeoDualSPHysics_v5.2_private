param(
  [ValidateSet('Build','Prepare','Run','Review')][string]$Mode='Build',
  [ValidateSet('ON_from_OFF','OFF_from_ON','OFF_from_FALSE')][string]$Case='ON_from_OFF',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Root-selected actions only. This driver never chains or restarts physical runs.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$logs=Join-Path $tests 'logs'
$helperSource=Join-Path $PSScriptRoot 'upl_cpu_public_part_tag_r1.cpp'
$notePath=Join-Path $tests 'notes\upl_cpu_public_part_r1.json'
$basePath=Join-Path $logs 'upl_cpu_public_reader_ReleaseCPU_r2.build.json'
$freezePath=Join-Path $logs 'upl_cpu_public_build_r3.json'
$offPath=Join-Path $logs 'upl_cpu_public_off_r2.check.json'
$planPath=Join-Path $logs 'upl_cpu_public_r1.inputs.json'
$folder=Join-Path $tests 'outputs\upl_cpu_public_part_program_r1'
$helper=Join-Path $folder 'upl_cpu_public_part_tag_r1.exe'
$buildPath=Join-Path $logs 'upl_cpu_public_part_r1.build.json'
$preparePath=Join-Path $logs 'upl_cpu_public_part_r1.prepare.check.json'
$writerCheck=Join-Path $logs 'upl_cpu_public_part_r1.writer.check.json'
$scratch=Join-Path $tests 'outputs\upl_cpu_public_part_false_r1'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){if($null -eq $r){throw 'Null frozen binding'};$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function NeedPass([string]$p){$r=Get-Content -LiteralPath $p -Raw|ConvertFrom-Json;if(!$r.passed){throw "Required gate failed: $p"};Verify $r.files;if($r.completion){Verify @($r.completion)};Entry $p}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root source/build review and explicit action authorization required'}
$base=Get-Content -LiteralPath $basePath -Raw|ConvertFrom-Json
$freeze=Get-Content -LiteralPath $freezePath -Raw|ConvertFrom-Json
$off=Get-Content -LiteralPath $offPath -Raw|ConvertFrom-Json
$plan=Get-Content -LiteralPath $planPath -Raw|ConvertFrom-Json
if($base.status -ne 'built_not_run' -or $base.compile_exit -ne 0 -or $base.link_exit -ne 0 -or $base.configuration -ne 'ReleaseCPU'){throw 'Sealed canonical Release reader build required'}
if($freeze.source.Count -ne 7 -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Full CPU public Rebuild r3 required'}
if(!$off.passed -or $off.actual_native_frame_pairs -ne 140 -or !$off.all_bits_0ULP){throw 'Default-OFF140 gate required'}
if($plan.status -ne 'runtime_inputs_prepared_not_solved' -or $plan.jobs.Count -ne 9 -or !$plan.all_copied_BI4_byte_identical){throw 'Sealed canonical inputs required'}
$bindings=@(Entry $PSCommandPath;Entry $helperSource;Entry $notePath;Entry $basePath;Entry $freezePath;Entry $offPath;Entry $planPath)
$dependencies=@()
foreach($label in @('OFF_default','periodic_constant_c')){
  $dependencies+=NeedPass (Join-Path $logs ('upl_cpu_public_'+$label+'_r1.review.check.json'))
}
foreach($label in @('periodic_constant','wall_constant','wall_evolving')){
  $dependencies+=NeedPass (Join-Path $logs ('upl_cpu_public_'+$label+'_r1.half.check.json'))
}
$offJob=@($plan.jobs|Where-Object {$_.label -ceq 'OFF_default'})[0]
$onJob=@($plan.jobs|Where-Object {$_.label -ceq 'periodic_constant_c'})[0]
if(!$offJob -or !$onJob -or $offJob.dynamic -or !$onJob.dynamic -or $offJob.native -ne 512 -or $onJob.native -ne 512){throw 'Exact retained periodic ON/OFF512 jobs required'}
$offData=Join-Path $offJob.planned_output 'data'
$onData=Join-Path $onJob.planned_output 'data'
$partInputs=@(Entry (Join-Path $offData 'Part_0001.bi4');Entry (Join-Path $onData 'Part_0001.bi4'))
function VerifyStage {
  Verify $bindings;Verify $dependencies;Verify $partInputs
  foreach($s in $freeze.source){Verify @($s.original,$s.snapshot)}
  Verify $freeze.inputs;Verify $freeze.logs;Verify $freeze.programs
  Verify $base.inputs;Verify $base.libraries;Verify $base.snapshots
  Verify @($base.source_freeze,$base.canonical_original,$base.canonical_program,$base.reader,$base.log)
  foreach($r in $base.runtime){Verify @($r.original,$r.copy)}
  Verify $plan.inputs
  foreach($j in @($offJob,$onJob)){Verify $j.source;Verify @($j.copied_geometry,$j.runtime)}
}
VerifyStage
if($Mode -eq 'Build'){
  $log=Join-Path $logs 'upl_cpu_public_part_r1.build.log'
  foreach($p in @($folder,$buildPath,$log)){if(Test-Path -LiteralPath $p){throw 'Native helper build label retained'}}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  New-Item -ItemType Directory -Path $folder|Out-Null
  $snapshots=@()
  foreach($p in @($helperSource,$notePath,$PSCommandPath)){
    $dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest
    $a=Entry $p;$c=Entry $dest;if($a.sha256 -ne $c.sha256){throw 'New helper recipe snapshot differs'};$snapshots+=$c
  }
  $runtime=@()
  foreach($r in $base.runtime){
    $dest=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $dest
    $a=Entry $dest;if($a.bytes -ne $r.copy.bytes -or $a.sha256 -ne $r.copy.sha256){throw 'Helper isolated runtime copy differs'}
    $runtime+=@{original=$r.copy;copy=$a}
  }
  # Reuse the authoritative object/library closure; replace only this tool's source/object/output paths.
  $baseObject=@($base.compile|Where-Object {$_ -like '/Fo*'})
  if($baseObject.Count -ne 1){throw 'Ambiguous sealed reader compile object'}
  $baseObjectPath=$baseObject[0].Substring(3);$obj=Join-Path $folder 'part_tag.obj'
  $compile=@($base.compile|ForEach-Object {
    if($_ -eq $baseObject[0]){"/Fo$obj"}
    elseif($_ -like '/Fd*'){"/Fd$folder\compile.pdb"}
    elseif($_ -eq (Join-Path ([IO.Path]::GetDirectoryName($base.reader.path)) 'compile.dependencies.json')){Join-Path $folder 'compile.dependencies.json'}
    elseif($_ -eq (Join-Path $PSScriptRoot 'upl_cpu_public_native_r1.cpp')){$helperSource}
    else{$_}
  })
  if(@($compile|Where-Object {$_ -eq $helperSource}).Count -ne 1){throw 'Native helper source substitution failed'}
  $link=@($base.link|ForEach-Object {if($_ -eq $baseObjectPath){$obj}elseif($_ -like '/OUT:*'){"/OUT:$helper"}else{$_}})
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o')
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$ce=$LASTEXITCODE;$le=$null
  if($ce -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$le=$LASTEXITCODE}
  $ErrorActionPreference=$old
  VerifyStage;Verify $snapshots;foreach($r in $runtime){Verify @($r.original,$r.copy)}
  NewJson $buildPath ([ordered]@{status=if($ce -eq 0 -and $le -eq 0){'built_not_run'}else{'build_failed_retained'};configuration='ReleaseCPU';started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');compile_exit=$ce;link_exit=$le;source_freeze=(Entry $freezePath);base_build=(Entry $basePath);inputs=$bindings;snapshots=$snapshots;runtime=$runtime;compile=$compile;link=$link;helper=if(Test-Path $helper){Entry $helper}else{$null};log=(Entry $log);production_build_called=$false;solver_started=$false;physical_acceptance=$false})
  if($ce -ne 0 -or $le -ne 0){throw 'Native helper compile/link failed; preserve immutable label'}
  Write-Output "BUILT metadata helper only: $buildPath";exit 0
}
$build=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json
if($build.status -ne 'built_not_run' -or $build.compile_exit -ne 0 -or $build.link_exit -ne 0){throw 'Metadata helper build required'}
function VerifyBuild {
  VerifyStage;Verify $build.inputs;Verify $build.snapshots;Verify @($build.helper,$build.log,$build.source_freeze,$build.base_build)
  foreach($r in $build.runtime){Verify @($r.original,$r.copy)}
}
function Call([string]$exe,[string[]]$argv,[string]$label){
  VerifyBuild;$receipt=Join-Path $logs ($label+'.run.json');$log=Join-Path $logs ($label+'.log')
  foreach($p in @($receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Owned call retained; no restart/retry'}}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$program=Entry $exe
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  Verify @($program)
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=$program;arguments=$argv;source_freeze=(Entry $freezePath);build=(Entry $buildPath);log=(Entry $log);physical_acceptance=$false})
  VerifyBuild
  return [pscustomobject]@{code=$code;receipt=(Entry $receipt);log=(Entry $log)}
}
if($Mode -eq 'Prepare'){
  foreach($p in @($scratch,$writerCheck,$preparePath)){if(Test-Path -LiteralPath $p){throw 'False-metadata scratch or receipt retained'}}
  $prefix=[string]$offJob.input_prefix
  if(($prefix+'.xml') -cne [string]$offJob.runtime.path){throw 'Sealed OFF case prefix/runtime disagree'}
  $call=Call $helper @('--write-false',$offData,(Split-Path -Parent $prefix),([IO.Path]::GetFileName($prefix)),$scratch,$writerCheck) 'upl_cpu_public_part_r1_writer'
  if($call.code -ne 0){throw 'Native writer/loader-only positive control failed; preserve scratch and logs'}
  $w=Get-Content -LiteralPath $writerCheck -Raw|ConvertFrom-Json
  if(!$w.passed -or !$w.real_OFF_loader_positive_control_passed -or $w.loaded_positive_native_ids -ne 512 -or $w.arrays_preserved -ne 15 -or !$w.all_array_bits_preserved -or !$w.all_existing_scalar_typed_bits_preserved -or !$w.item_topology_and_hide_flags_preserved -or !$w.original_source_unchanged -or $w.added_scalar_value -ne $false -or $w.new_scalar_count -ne 1 -or $w.dynamic_arrays_added -ne 0 -or $w.solver_or_integration_called -or $w.coupled_restart_acceptance){throw 'Native false-only metadata contract failed'}
  NewJson $preparePath ([ordered]@{passed=$true;scope='Native loader-only OFF positive control and real OFF PART1 copy plus sole false scalar';writer=(Entry $writerCheck);call=$call.receipt;files=@((Entry (Join-Path $scratch 'Part_0001.bi4')),(Entry $writerCheck));original_parts=$partInputs;dependencies=$dependencies;build=(Entry $buildPath);solver_started=$false;coupled_restart_acceptance=$false;physical_acceptance=$false})
  Write-Output "PREPARED false-only native PART: $preparePath";exit 0
}
$prep=Get-Content -LiteralPath $preparePath -Raw|ConvertFrom-Json
if(!$prep.passed -or $prep.coupled_restart_acceptance){throw 'Native writer prepare gate required'}
Verify $prep.files;Verify $prep.original_parts;Verify @($prep.writer,$prep.call,$prep.build)
$caseNames=@('ON_from_OFF','OFF_from_ON','OFF_from_FALSE')
function NegativePath([string]$name){Join-Path $logs ('upl_cpu_public_part_'+$name+'_r1.check.json')}
if($Mode -eq 'Run'){
  $output=Join-Path $tests ('outputs\upl_cpu_public_part_'+$Case+'_r1')
  $check=NegativePath $Case
  foreach($p in @($output,$check)){if(Test-Path -LiteralPath $p){throw 'Actual PART rejection label retained'}}
  $jobData=if($Case -eq 'ON_from_OFF'){$onJob}else{$offJob}
  $data=if($Case -eq 'OFF_from_ON'){$onData}elseif($Case -eq 'OFF_from_FALSE'){$scratch}else{$offData}
  $prefix=[string]$jobData.input_prefix
  if(($prefix+'.xml') -cne [string]$jobData.runtime.path){throw 'Sealed selected case prefix/runtime disagree'}
  $expected=if($Case -eq 'ON_from_OFF'){'HydroMechDynamicSeepage is experimental: fresh CPU 2-D, zero gravity, InitMode=None and positive constant DtFixed only.'}else{'Dynamic/J-state PART restart is not supported; refusing to discard the porosity state even when the dynamic switch is OFF.'}
  $stage=if($Case -eq 'ON_from_OFF'){'JSph::LoadConfig early fresh-only guard'}else{'JPartsLoad4::LoadParticles dynamic/J-state presence guard'}
  $argv=@('-cpu','-ompthreads:1','-stable',$prefix,$output,'-dirdataout','data','-svres','-partbegin:1',$data)
  $call=Call $base.canonical_program.path $argv ('upl_cpu_public_part_'+$Case+'_r1')
  $text=Get-Content -LiteralPath $call.log.path -Raw
  $files=@();if(Test-Path -LiteralPath $output){$files=@(Get-ChildItem -LiteralPath $output -Recurse -File|ForEach-Object {Entry $_.FullName})}
  $runout=Join-Path $output 'Run.out';if(Test-Path -LiteralPath $runout){$text+=[Environment]::NewLine+(Get-Content -LiteralPath $runout -Raw)}
  $numbered=@($files|Where-Object {[IO.Path]::GetFileName($_.path) -match '^Part_[0-9]{4}(?:_.*)?\.bi4$'})
  $heads=@($files|Where-Object {[IO.Path]::GetFileName($_.path) -match '^Part_Head.*\.bi4$'})
  $exact=$text.Contains($expected)
  $noLoop=$text -notmatch '\[Initialising simulation|Part_[0-9]{4}\s+.*successfully stored|PART\s+PartTime\s+TotalSteps'
  $passed=$call.code -ne 0 -and $exact -and $numbered.Count -eq 0 -and $noLoop
  NewJson $check ([ordered]@{passed=$passed;case=$Case;expected_stage=$stage;expected_exception=$expected;expected_exception_observed=$exact;exit_code=$call.code;owned_call_exited=$true;numbered_native_PART_frames=$numbered.Count;part_head_files=$heads.Count;loop_initialization_or_native_save_absent=$noLoop;no_simulation_step_evidence='Early source guard plus absent loop/native-save markers; no fabricated runtime stage counter';call=$call.receipt;program=$base.canonical_program;runtime_XML=$jobData.runtime;source_PART=(Entry (Join-Path $data 'Part_0001.bi4'));prepared_false=(Entry $preparePath);source_freeze=(Entry $freezePath);files=$files;dependencies=$dependencies;coupled_restart_acceptance=$false;physical_acceptance=$false})
  if(!$passed){throw 'Actual PART guard did not reject at the declared stage before native saves; retain all evidence'}
  Write-Output "PASSED actual canonical PART rejection $Case";exit 0
}
if($Mode -eq 'Review'){
  $final=Join-Path $logs 'upl_cpu_public_part_r1.check.json'
  if(Test-Path -LiteralPath $final){throw 'Final PART aggregate retained'}
  $checks=@();foreach($name in $caseNames){
    $path=NegativePath $name;$r=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
    if(!$r.passed -or $r.case -cne $name -or $r.exit_code -eq 0 -or !$r.owned_call_exited -or !$r.expected_exception_observed -or $r.numbered_native_PART_frames -ne 0 -or !$r.loop_initialization_or_native_save_absent -or $r.coupled_restart_acceptance){throw "Actual declared rejection failed: $name"}
    Verify $r.files;Verify @($r.call,$r.program,$r.runtime_XML,$r.source_PART,$r.prepared_false,$r.source_freeze);$checks+=Entry $path
  }
  VerifyBuild;Verify $prep.files;Verify $partInputs
  NewJson $final ([ordered]@{passed=$true;scope='Exactly three actual canonical CPU PART rejection paths plus native OFF loader-only positive control and sole-false metadata writer';canonical_rejections=3;actual_rejections=3;all_three_nonzero_expected_guard=$true;all_three_numbered_PART_frames_zero=$true;real_OFF_loader_positive_control_passed=$true;false_scalar_copy_verified=$true;false_scalar_only_preservation_verified=$true;writer=(Entry $writerCheck);prepare=(Entry $preparePath);checks=$checks;files=@($checks)+$prep.files;input_parts=$partInputs;source_freeze=(Entry $freezePath);base_build=(Entry $basePath);helper_build=(Entry $buildPath);recipe=$bindings;coupled_restart_acceptance=$false;physical_acceptance=$false})
  Write-Output "PASSED genuine PART scope aggregate $final";exit 0
}
throw 'Unknown action'

