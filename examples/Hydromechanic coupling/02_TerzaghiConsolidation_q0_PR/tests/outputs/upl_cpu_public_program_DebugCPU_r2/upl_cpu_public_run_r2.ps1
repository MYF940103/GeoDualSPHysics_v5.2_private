param(
  [ValidateSet('BuildReader','Run','Review','Half','CompareOff')][string]$Mode='BuildReader',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [string]$Job='',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# One root-selected action only. Never chains physical jobs or selects a GPU executable.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$freezePath=Join-Path $logs 'upl_cpu_public_build_r3.json'
$offPath=Join-Path $logs 'upl_cpu_public_off_r2.check.json'
$planPath=Join-Path $logs 'upl_cpu_public_r1.inputs.json'
$readerSource=Join-Path $PSScriptRoot 'upl_cpu_public_native_r1.cpp'
$readerNote=Join-Path $tests 'notes\upl_cpu_public_native_r1.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Roundtrip([double]$v){$v.ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
function ReviewPath([string]$label){Join-Path $logs ('upl_cpu_public_'+$label+'_r1.review.check.json')}
function NeedPass([string]$p){$r=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json;if(!$r.passed){throw "Required prior gate failed: $p"};Verify $r.files;Verify @($r.completion);Entry $p}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root build/source review and explicit action authorization required'}
$freeze=Get-Content -Raw -LiteralPath $freezePath|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.source.Count -ne 7 -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Seven-file authoritative public Rebuild r3 unavailable'}
$off=Get-Content -Raw -LiteralPath $offPath|ConvertFrom-Json
if(!$off.passed -or $off.actual_native_frame_pairs -ne 140 -or !$off.all_bits_0ULP -or !$off.clock_step_dterror_exact -or $off.exclusions -ne 0){throw 'Current default-OFF140-pair gate unavailable'}
$plan=Get-Content -Raw -LiteralPath $planPath|ConvertFrom-Json
if($plan.status -ne 'runtime_inputs_prepared_not_solved' -or $plan.jobs.Count -ne 9 -or !$plan.all_copied_BI4_byte_identical){throw 'Exactly nine sealed canonical inputs required'}
$bindings=@(Entry $PSCommandPath;Entry $freezePath;Entry $offPath;Entry $planPath)
function VerifyStage {
  Verify $bindings
  foreach($s in $freeze.source){Verify @($s.original,$s.snapshot)}
  Verify $freeze.inputs;Verify $freeze.logs;Verify $freeze.programs
  foreach($g in $off.groups){Verify @($g.check)}
  Verify $plan.inputs
  foreach($j in $plan.jobs){Verify $j.source;Verify @($j.copied_geometry,$j.runtime)}
}
VerifyStage
$jobData=$null;$dependencies=@()
if($Mode -in 'Half','CompareOff'){$Configuration='ReleaseCPU'}
if($Mode -in 'Run','Review'){
  $selected=@($plan.jobs|Where-Object {$_.label -ceq $Job})
  if($selected.Count -ne 1){throw 'Select exactly one prepared job label; no automatic batch'}
  $jobData=$selected[0];$Configuration=$jobData.configuration
  $before=@{
    periodic_constant_c='debug_wall_evolving_smoke'
    periodic_constant_h='periodic_constant_c'
    wall_constant_h='wall_constant_c'
    wall_evolving_h='wall_evolving_c'
  }
  if($before.ContainsKey($Job)){$dependencies+=NeedPass (ReviewPath $before[$Job])}
  if($Job -eq 'wall_constant_c'){$dependencies+=NeedPass (Join-Path $logs 'upl_cpu_public_periodic_constant_r1.half.check.json')}
  if($Job -eq 'wall_evolving_c'){$dependencies+=NeedPass (Join-Path $logs 'upl_cpu_public_wall_constant_r1.half.check.json')}
}
if($Configuration -eq 'ReleaseCPU'){$dependencies+=NeedPass (ReviewPath 'debug_wall_evolving_smoke')}
$folder=Join-Path $tests ('outputs\upl_cpu_public_program_'+$Configuration+'_r2')
$buildPath=Join-Path $logs ('upl_cpu_public_reader_'+$Configuration+'_r2.build.json')
$cpuLeaf=if($Configuration -eq 'DebugCPU'){'DualSPHysics5.2CPU_win64_debug.exe'}else{'DualSPHysics5.2CPU_win64.exe'}
$canonical=Join-Path $repo ('bin\windows\'+$cpuLeaf)
$program=Join-Path $folder $cpuLeaf
$reader=Join-Path $folder 'upl_cpu_public_native_r2.exe'
if($Mode -eq 'BuildReader'){
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $buildPath)){throw 'Isolated program/reader build already exists; retain it'}
  [void](Entry $readerSource);[void](Entry $readerNote)
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj';[xml]$xml=Get-Content -Raw -LiteralPath $project
  $objects=@();$sources=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false;$condition="'"+'$(Configuration)|$(Platform)'+"'=='"+$Configuration+"|x64'"
    foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq $condition){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){$objects+=Join-Path $source "VS\Intermediate\DualSPHysics_$($Configuration)_x64\$stem.obj";$sources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))}
  }
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($project,$readerSource,$readerNote)+$objects+$sources+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})+$bindings+$dependencies
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $folder|Out-Null;$snapshots=@()
  foreach($p in @($readerSource,$readerNote,$PSCommandPath)){$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$a=Entry $p;$c=Entry $dest;if($a.sha256 -ne $c.sha256){throw 'Recipe snapshot differs'};$snapshots+=$c}
  $runtime=@()
  foreach($p in (@($canonical)+@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml'))){
    $a=Entry $p;$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$c=Entry $dest;if($a.bytes -ne $c.bytes -or $a.sha256 -ne $c.sha256){throw 'Isolated canonical program/runtime differs'};$runtime+=@{original=$a;copy=$c}
  }
  $obj=Join-Path $folder 'native_reader.obj';$log=Join-Path $logs ('upl_cpu_public_reader_'+$Configuration+'_r2.build.log')
  if(Test-Path -LiteralPath $log){throw 'Build log retained'};[IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$folder\compile.pdb",'/sourceDependencies',(Join-Path $folder 'compile.dependencies.json'))+$flags+@($readerSource)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$reader","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs;if($debug){$link+=@('/DEBUG',"/PDB:$folder\link.pdb")}
  $start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$ce=$LASTEXITCODE;$le=$null
  if($ce -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$le=$LASTEXITCODE};$ErrorActionPreference=$old
  VerifyStage;Verify $inputs;Verify $libraries;Verify $snapshots;foreach($r in $runtime){Verify @($r.original,$r.copy)}
  NewJson $buildPath ([ordered]@{status=if($ce -eq 0 -and $le -eq 0){'built_not_run'}else{'build_failed_retained'};configuration=$Configuration;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');source_freeze=(Entry $freezePath);compile_exit=$ce;link_exit=$le;inputs=$inputs;libraries=$libraries;snapshots=$snapshots;runtime=$runtime;compile=$compile;link=$link;canonical_original=(Entry $canonical);canonical_program=(Entry $program);reader=if(Test-Path $reader){Entry $reader}else{$null};log=(Entry $log);solver_started=$false;physical_acceptance=$false})
  if($ce -ne 0 -or $le -ne 0){throw 'Reader build failed; preserve label'}
  Write-Output "BUILT isolated CPU program and offline reader: $buildPath";exit 0
}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if($build.status -ne 'built_not_run' -or $build.configuration -ne $Configuration){throw 'Isolated canonical program/reader unavailable'}
function VerifyBuild {
  VerifyStage;Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots
  Verify @($build.canonical_original,$build.canonical_program,$build.reader)
  foreach($r in $build.runtime){Verify @($r.original,$r.copy)}
}
function InvokeOwned([string]$exe,[string[]]$argv,[string]$label){
  VerifyBuild;$receipt=Join-Path $logs ($label+'.run.json');$log=Join-Path $logs ($label+'.log')
  foreach($p in @($receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Owned call retained; no retry'}}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o');$before=Entry $exe
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  Verify @($before)
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');program=$before;arguments=$argv;build=(Entry $buildPath);log=(Entry $log);physical_acceptance=$false})
  if($code -ne 0){throw "Owned call failed: $label; preserve completion/partial output"}
  VerifyBuild;Entry $receipt
}
if($Mode -eq 'Run'){
  $output=$jobData.planned_output;$checkPath=Join-Path $logs ('upl_cpu_public_'+$Job+'_r1.solver.check.json')
  if((Test-Path -LiteralPath $output) -or (Test-Path -LiteralPath $checkPath)){throw 'Canonical output/check retained'}
  $argv=@($jobData.planned_canonical_argv)
  if($argv.Count -lt 2 -or [IO.Path]::GetFileName($argv[0]) -ne $cpuLeaf -or $argv[1] -ne '-cpu' -or @($argv|Where-Object {$_ -like '-gpu*'}).Count){throw 'Only sealed explicit CPU command admitted'}
  $call=InvokeOwned $program @($argv[1..($argv.Count-1)]) ('upl_cpu_public_'+$Job+'_r1_solver')
  [void](Entry (Join-Path $output 'Run.out'))
  $files=@(Get-ChildItem -LiteralPath $output -Recurse -File|ForEach-Object {Entry $_.FullName})
  $parts=@(Get-ChildItem -LiteralPath (Join-Path $output 'data') -Filter 'Part_????.bi4' -File)
  if($parts.Count -ne $jobData.samples){throw 'Canonical normal exit has incomplete native save count'}
  NewJson $checkPath ([ordered]@{passed=$true;job=$Job;scope='Owned canonical CPU exit/output sealing only; native physical review still required';build=(Entry $buildPath);source_freeze=(Entry $freezePath);prepared_inputs=(Entry $planPath);call=$call;dependencies=$dependencies;files=$files;native_frames=$parts.Count;actual_native_review_passed=$false;physical_acceptance=$false})
  Write-Output "SEALED canonical solve only; now explicitly Review $Job";exit 0
}
if($Mode -eq 'Review'){
  $runPath=Join-Path $logs ('upl_cpu_public_'+$Job+'_r1.solver.check.json');$run=Get-Content -Raw -LiteralPath $runPath|ConvertFrom-Json
  if(!$run.passed -or $run.job -ne $Job){throw 'Completed canonical job receipt missing'};Verify $run.files;Verify @($run.call,$run.build,$run.source_freeze,$run.prepared_inputs)
  $output=Join-Path $tests ('outputs\upl_cpu_public_review_r1_'+$Job);$final=ReviewPath $Job
  if((Test-Path -LiteralPath $output) -or (Test-Path -LiteralPath $final)){throw 'Offline review retained; never rerun solver for analysis'}
  $model=if($jobData.dynamic){[int]$jobData.model}else{-1}
  $call=InvokeOwned $reader @('--read',(Join-Path $jobData.planned_output 'data'),"$($jobData.native)","$($jobData.fixed)","$($jobData.samples)",(Roundtrip ([double]$jobData.dt)),(Roundtrip ([double]$jobData.cadence)),"$model",$output) ('upl_cpu_public_'+$Job+'_r1_reader')
  $completionPath=Join-Path $output 'complete.json';$done=Get-Content -Raw -LiteralPath $completionPath|ConvertFrom-Json
  if(!$done.passed -or $done.native_count -ne $jobData.native -or $done.fixed_count -ne $jobData.fixed -or $done.samples -ne $jobData.samples -or $done.model -ne $model -or $done.original_arrays -ne 15 -or !$done.no_exclusions -or !$done.native_ID_aligned -or !$done.saved_clock_step_exact -or !$done.double_sigma_state -or !$done.initial_sine_verified -or [double]$done.actual_end_s -ne [double]$jobData.end -or [double]$done.dt_actual -ne [double]$jobData.dt -or [double]$done.cadence_s -ne [double]$jobData.cadence -or $done.physical_acceptance){throw 'Native reader identity/clock/original-field gates differ'}
  if(!$done.finite_dterror_safety_checked -or [double]$done.max_signed_dterror -gt 1e-14){throw 'Original finite signed dterror safety guard failed'}
  foreach($leaf in @('original15.bin','native_ids.csv','fixed_ids.csv','history.csv','complete.json')){[void](Entry (Join-Path $output $leaf))}
  if($jobData.dynamic){
    [void](Entry (Join-Path $output 'physical.bin'))
    if($done.derived_arrays -ne 6 -or !$done.posdiv_native_present -or !$done.model_metadata_verified -or $done.ledger_native_checks -ne $jobData.native*$jobData.samples -or $done.fixed_marker_checks -ne $jobData.fixed*$jobData.samples -or [double]$done.max_ledger_relative_error -gt 5e-13 -or [double]$done.max_energy_ratio -gt 1.1 -or [double]$done.max_coupled_CFL -gt .01 -or [double]$done.max_Ddt_h2 -gt .01){throw 'Native dynamic ledger/energy/necessary-step guard failed'}
    if($jobData.samples -eq 257 -and [double]$done.max_abs_J_minus_1 -le 1e-8){throw 'Dynamic J path is empty'}
    if($jobData.samples -eq 257 -and $model -eq 1 -and ([double]$done.max_k_span_over_initial_k0 -lt .005 -or [double]$done.max_k_change_over_initial_k0 -lt .005)){throw 'Variable-k evolution is empty'}
  }elseif($done.derived_arrays -ne 0 -or !$done.model_metadata_absent){throw 'Default-OFF unexpectedly saved ON-only metadata/derived arrays'}
  Verify $run.files;VerifyBuild
  $files=@(Get-ChildItem -LiteralPath $output -File|ForEach-Object {Entry $_.FullName})
  NewJson $final ([ordered]@{passed=$true;job=$Job;completion=(Entry $completionPath);solver=(Entry $runPath);reader_call=$call;build=(Entry $buildPath);files=$files;full_formal_or_physical_acceptance=$false;physical_acceptance=$false})
  Write-Output "PASSED actual native review $Job";exit 0
}
if($Mode -eq 'Half'){
  if($Configuration -ne 'ReleaseCPU' -or $Job -notin 'periodic_constant','wall_constant','wall_evolving'){throw 'Choose exactly one declared Release pair'}
  $left=Get-Content -Raw -LiteralPath (ReviewPath ($Job+'_c'))|ConvertFrom-Json
  $right=Get-Content -Raw -LiteralPath (ReviewPath ($Job+'_h'))|ConvertFrom-Json
  [void](NeedPass (ReviewPath ($Job+'_c')));[void](NeedPass (ReviewPath ($Job+'_h')))
  $a=@($left.files|Where-Object {[IO.Path]::GetFileName($_.path) -eq 'physical.bin'})
  $b=@($right.files|Where-Object {[IO.Path]::GetFileName($_.path) -eq 'physical.bin'})
  if($a.Count -ne 1 -or $b.Count -ne 1){throw 'No full native26 half inputs'}
  $json=Join-Path $logs ('upl_cpu_public_'+$Job+'_r1.half.native.json')
  $final=Join-Path $logs ('upl_cpu_public_'+$Job+'_r1.half.check.json')
  if((Test-Path $json) -or (Test-Path $final)){throw 'Half result retained'}
  $call=InvokeOwned $reader @('--half',$a[0].path,$b[0].path,$json) ('upl_cpu_public_'+$Job+'_r1_half')
  $half=Get-Content -Raw -LiteralPath $json|ConvertFrom-Json
  if(!$half.passed -or $half.samples -ne 257 -or $half.columns -ne 26){throw 'Original full-history half gate failed'}
  NewJson $final ([ordered]@{passed=$true;comparison='independent_same-physics_coarse_half_original5Pa_.005mm_and_normalized1e-4';completion=(Entry $json);files=@($a[0],$b[0],(Entry $json));call=$call;physical_acceptance=$false})
  Write-Output "PASSED original independent half $Job";exit 0
}
if($Mode -eq 'CompareOff'){
  if($Configuration -ne 'ReleaseCPU'){throw 'OFF comparison uses prepared Release jobs'}
  [void](NeedPass (ReviewPath 'OFF_default'));[void](NeedPass (ReviewPath 'OFF_explicit'))
  $a=Get-Content -Raw -LiteralPath (ReviewPath 'OFF_default')|ConvertFrom-Json
  $b=Get-Content -Raw -LiteralPath (ReviewPath 'OFF_explicit')|ConvertFrom-Json
  $equal=@()
  foreach($leaf in @('original15.bin','native_ids.csv','fixed_ids.csv','history.csv')){
    $l=@($a.files|Where-Object {[IO.Path]::GetFileName($_.path) -eq $leaf});$r=@($b.files|Where-Object {[IO.Path]::GetFileName($_.path) -eq $leaf})
    if($l.Count -ne 1 -or $r.Count -ne 1 -or $l[0].bytes -ne $r[0].bytes -or $l[0].sha256 -ne $r[0].sha256){throw 'Absent/explicitfalse public switch changes original physical/metadata bytes'}
    $equal+=@{left=$l[0];right=$r[0];byte_identical=$true}
  }
  NewJson (Join-Path $logs 'upl_cpu_public_OFF_r1.exact.check.json') ([ordered]@{passed=$true;samples=9;native_count=512;original_arrays=15;equal_files=$equal;physical_acceptance=$false})
  Write-Output 'PASSED absent versus explicitfalse original native arrays and clock history';exit 0
}



