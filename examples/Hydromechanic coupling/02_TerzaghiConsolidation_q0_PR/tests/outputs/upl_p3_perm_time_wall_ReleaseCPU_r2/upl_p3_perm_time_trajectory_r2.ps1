param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('Wall')][string]$Geometry='Wall',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# New source identity, unchanged accepted fixtures. Exactly two actual Release jobs per geometry.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs';$Configuration='ReleaseCPU'
$name='upl_p3_perm_time_'+$Geometry.ToLowerInvariant()+'_ReleaseCPU_r2'
$folder=Join-Path $tests ('outputs\'+$name);$buildPath=Join-Path $logs ($name+'.build.json')
$note=Join-Path $tests 'notes\upl_p3_perm_time_trajectory_r2.json'
$freezePath=Join-Path $logs 'upl_p3_perm_time_build_r1.json'
$periodic=$Geometry -eq 'Periodic'
if($periodic){
  $harness=Join-Path $PSScriptRoot 'upl_p3_perm_wave_r2.cpp'
  $retainedHarness=Join-Path $PSScriptRoot 'upl_p3_spatial_wave_harness_r2.cpp'
  $seedReceiptPath=Join-Path $logs 'upl_p3_spatial_seed_r1.inputs.json'
  $oldFinalPath=Join-Path $logs 'upl_p3_perm_wave_ReleaseCPU_r2.check.json'
  $oldName='upl_p3_perm_wave_ReleaseCPU_r2';$native=512;$fixed=0;$stepsC=512;$stepsH=1024
  $leaves=@('physical.bin','native_ids.csv','ledger.csv','modes.csv','endpoint_policy.csv','initial_source.csv','complete.json')
}else{
  $harness=Join-Path $PSScriptRoot 'upl_p3_perm_wall_r1.cpp'
  $retainedHarness=Join-Path $PSScriptRoot 'upl_p3_wall_wave_harness_r2.cpp'
  $seedReceiptPath=Join-Path $logs 'upl_p3_wall_wave_seed_r3.inputs.json'
  $oldFinalPath=Join-Path $logs 'upl_p3_perm_wall_ReleaseCPU_r1.check.json'
  $oldName='upl_p3_perm_wall_ReleaseCPU_r1';$native=1024;$fixed=256;$stepsC=1024;$stepsH=2048
  $leaves=@('physical.bin','native_ids.csv','fixed_ids.csv','conductivity_ledger.csv','modes.csv','endpoint_policy.csv','source_summary.csv','wall_audit.csv','component.check.json','component.csv','offgrid_component.check.json','offgrid_component.csv','complete.json')
}
$exe=Join-Path $folder 'upl_p3_perm_time_trajectory_r2.exe'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Roundtrip([double]$v){$v.ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root review and explicit execution authorization are required'}
$d=Get-Content -Raw -LiteralPath $note|ConvertFrom-Json
$declared=if($periodic){$d.unchanged_harnesses.periodic}else{$d.unchanged_harnesses.wall}
$a=Entry $harness;if($a.bytes -ne $declared.bytes -or $a.sha256 -ne $declared.sha256){throw 'Unchanged accepted fixture identity differs'}
$freeze=Get-Content -Raw -LiteralPath $freezePath|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Authoritative source rebuilds unavailable'}
foreach($s in $freeze.source){Verify @($s.original,$s.snapshot)};Verify $freeze.logs;Verify $freeze.programs
$gateBindings=@()
foreach($leaf in @('upl_p3_perm_time_off_r1.check.json','upl_p3_perm_time_DebugCPU_r1.check.json','upl_p3_perm_time_ReleaseCPU_r1.check.json')){
  $p=Join-Path $logs $leaf;$g=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
  if(!$g.passed){throw "Required time-policy prerequisite failed: $leaf"};$gateBindings+=Entry $p;Verify $g.files
  if($leaf -eq 'upl_p3_perm_time_off_r1.check.json'){
    if($g.actual_native_frame_pairs -ne 140 -or !$g.all_bits_0ULP){throw 'Default-OFF full regression missing'}
    foreach($group in $g.groups){Verify @($group.check)}
  }else{Verify @($g.build,$g.off_run,$g.perm_run,$g.time_run)}
}
$oldFinal=Get-Content -Raw -LiteralPath $oldFinalPath|ConvertFrom-Json
if(!$oldFinal.passed -or $oldFinal.smoke_only -or !$oldFinal.actual_ComputeStep_Sym){throw 'Accepted retained native trajectories missing'}
$oldFiles=@()
foreach($tag in @('c','h')){foreach($leaf in $leaves){
  $p=Join-Path $tests ('outputs\'+$oldName+'_on_'+$tag+'\'+$leaf)
  $selected=@($oldFinal.files|Where-Object {$_.path -eq $p})
  if($selected.Count -ne 1){throw "Retained exact diagnostic binding missing: $p"};Verify $selected;$oldFiles+=$selected
}}
$gateBindings+=Entry $oldFinalPath
$seedReceipt=Get-Content -Raw -LiteralPath $seedReceiptPath|ConvertFrom-Json
$seedFiles=@()
foreach($tag in @('c','h')){
  $seedDir=if($periodic){Join-Path $tests ('outputs\upl_p3_spatial_seed_r1_n32_'+$tag)}else{Join-Path $tests ('outputs\upl_p3_wall_wave_seed_r3_'+$tag)}
  $selected=@($seedReceipt.files|Where-Object {$_.path.StartsWith($seedDir+'\',[StringComparison]::OrdinalIgnoreCase) -and [IO.Path]::GetExtension($_.path) -in '.xml','.bi4' -and ($periodic -or [IO.Path]::GetFileNameWithoutExtension($_.path) -eq ('CaseUplWall_'+$tag))})
  if($selected.Count -ne 2){throw 'Exact retained seed XML/BI4 pair missing'};Verify $selected;$seedFiles+=$selected
}
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $buildPath)){throw 'Fresh immutable companion build required'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj';[xml]$projectXml=Get-Content -Raw -LiteralPath $project
  $objects=@();$sources=@()
  foreach($node in $projectXml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false;$expectedCondition="'"+'$(Configuration)|$(Platform)'+"'=='ReleaseCPU|x64'"
    foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq $expectedCondition){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){$objects+=Join-Path $source "VS\Intermediate\DualSPHysics_ReleaseCPU_x64\$stem.obj";$sources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))}
  }
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($project,$harness,$retainedHarness,$PSCommandPath,$note,$freezePath,$seedReceiptPath)+$objects+$sources+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})+$seedFiles+$oldFiles+$gateBindings
  $libs=@('dsphchrono.lib','LibJVtkLib_x64_v143_Release.lib','LibJNumexLib_x64_v143_Release.lib','LibJWaveGen_x64_v143_Release.lib','LibDSphMoorDyn_x64_v143_Release.lib','kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $folder|Out-Null;$snapshots=@()
  foreach($p in @($harness,$retainedHarness,$PSCommandPath,$note)){$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$copy=Entry $dest;if($copy.sha256 -ne (Entry $p).sha256){throw 'Recipe snapshot differs'};$snapshots+=$copy}
  $obj=Join-Path $folder 'trajectory.obj';$log=Join-Path $logs ($name+'.build.log')
  if(Test-Path -LiteralPath $log){throw 'Retained build log protected'};[IO.File]::WriteAllBytes($log,[byte[]]@())
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj",'/O2','/MT','/sourceDependencies',(Join-Path $folder 'compile.dependencies.json'),$harness)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs
  $start=[DateTime]::UtcNow.ToString('o');$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$ce=$LASTEXITCODE;$le=$null
  if($ce -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$le=$LASTEXITCODE};$ErrorActionPreference=$oldAction
  Verify $inputs;Verify $libraries;Verify $snapshots;$runtime=@()
  if($ce -eq 0 -and $le -eq 0){foreach($p in (@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml'))){$a=Entry $p;$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$copy=Entry $dest;if($copy.sha256 -ne $a.sha256 -or (Entry $p).sha256 -ne $a.sha256){throw 'Runtime changed'};$runtime+=@{original=$a;copy=$copy}}}
  NewJson $buildPath ([ordered]@{status=if($ce -eq 0 -and $le -eq 0){'built_not_run'}else{'build_failed_retained'};configuration='ReleaseCPU';geometry=$Geometry;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');source_freeze=(Entry $freezePath);compile_exit=$ce;link_exit=$le;inputs=$inputs;libraries=$libraries;snapshots=$snapshots;compile=$compile;link=$link;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};runtime=$runtime;log=(Entry $log);physical_acceptance=$false})
  if($ce -ne 0 -or $le -ne 0){throw 'Companion build failed; preserve label'};Write-Output "BUILT $exe";exit 0
}
$b=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if($b.status -ne 'built_not_run' -or $b.geometry -ne $Geometry){throw 'Reviewed companion build unavailable'}
function VerifyBuild{Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.original,$r.copy)}}
function InvokeProgram([string]$job,[string[]]$argv){
  VerifyBuild;$receipt=Join-Path $logs ($job+'.run.json');$log=Join-Path $logs ($job+'.log')
  foreach($p in @($receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Retained owned call protected'}}
  [IO.File]::WriteAllBytes($log,[byte[]]@()) # Empty-stdout comparator still has an immutable owned log.
  $start=[DateTime]::UtcNow.ToString('o');$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=(Entry $exe);arguments=$argv;build=(Entry $buildPath);log=(Entry $log);physical_acceptance=$false})
  if($code -ne 0){throw "Actual trajectory/check failed: $job; retain output and stop dependencies"};VerifyBuild;Entry $receipt
}
$final=Join-Path $logs ($name+'.check.json');if(Test-Path -LiteralPath $final){throw 'Retained final check protected'}
$receipts=@();$files=@();$exact=@();$outputs=@{}
foreach($tag in @('c','h')){
  $job=$name+'_on_'+$tag;$output=Join-Path $tests ('outputs\'+$job);if(Test-Path -LiteralPath $output){throw 'Retained native output protected'}
  $steps=if($tag -eq 'c'){$stepsC}else{$stepsH}
  $seed=if($periodic){Join-Path $tests ('outputs\upl_p3_spatial_seed_r1_n32_'+$tag+'\CaseUplSpatial_n32_'+$tag)}else{Join-Path $tests ('outputs\upl_p3_wall_wave_seed_r3_'+$tag+'\CaseUplWall_'+$tag)}
  $argv=if($periodic){@('--job',"$steps",'0','0','1')}else{@('--job',"$steps",'0','1')}
  $receipts+=InvokeProgram $job ($argv+@('-cpu','-ompthreads:1','-stable',$seed,$output,'-dirdataout','data'))
  $donePath=Join-Path $output 'complete.json';$done=Get-Content -Raw -LiteralPath $donePath|ConvertFrom-Json
  $dt=if($periodic){if($tag -eq 'c'){1./16777216.}else{1./33554432.}}else{if($tag -eq 'c'){1./33554432.}else{1./67108864.}}
  if(!$done.passed -or !$done.actual_ComputeStep_Sym -or $done.native_ids -ne $native -or $done.steps -ne $steps -or $done.samples -ne 257 -or [double]$done.dt_actual -ne $dt -or [double]$done.actual_end_s -ne 1./32768. -or !$done.conductivity_switch -or $done.smoke -or $done.k0 -or $done.physical_acceptance){throw 'Actual identity, saved clock or scope differs'}
  $stream=[IO.File]::OpenRead((Join-Path $output 'physical.bin'));$reader=New-Object IO.BinaryReader($stream)
  try{
    if($reader.ReadUInt32() -ne $native -or $reader.ReadUInt32() -ne 26 -or $reader.ReadUInt32() -ne 257 -or $stream.Length -ne 12+257*(8+$native*26*8)){throw 'Full native26 binary header/length differs'}
    for($i=0;$i -lt 257;$i++){[void]$stream.Seek(12+[long]$i*(8+$native*26*8),[IO.SeekOrigin]::Begin);if($reader.ReadDouble() -ne $i/8388608.){throw 'Native binary saved clock differs'}}
  }finally{$reader.Dispose()}
  $identities=@(Import-Csv -LiteralPath (Join-Path $output 'native_ids.csv'))
  if($identities.Count -ne $native){throw 'Native identity ledger incomplete'}
  for($i=0;$i -lt $native;$i++){if([int]$identities[$i].native_id -ne $i+$fixed){throw 'Native ID ownership/order differs'}}
  foreach($leaf in $leaves){
    $current=Entry (Join-Path $output $leaf)
    $oldPath=Join-Path $tests ('outputs\'+$oldName+'_on_'+$tag+'\'+$leaf)
    $old=@($oldFiles|Where-Object {$_.path -eq $oldPath})[0]
    if($current.bytes -ne $old.bytes -or $current.sha256 -ne $old.sha256){throw "Time-policy patch changed retained native/diagnostic bytes: $tag $leaf"}
    $exact+=@{tag=$tag;retained=$old;current=$current;byte_identical=$true}
  }
  $files+=@(Get-ChildItem -LiteralPath $output -Recurse -File|ForEach-Object {Entry $_.FullName});$outputs[$tag]=$output
}
$halfPath=Join-Path $logs ($name+'_half.check.json')
$Cu=[Math]::Sqrt((89478488.+4.*134217728./3.+67108864./.25)/2048.)
$Pstar=(67108864./.25)*(1./512.)/$Cu;$Ustar=(1./512.)/($Cu*2*[Math]::PI/.125)
$halfArgs=@('--half',(Join-Path $outputs.c 'physical.bin'),(Join-Path $outputs.h 'physical.bin'))
if($periodic){$halfArgs+=@((Roundtrip $Pstar),(Roundtrip $Ustar))};$halfArgs+=@($halfPath)
$receipts+=InvokeProgram ($name+'_half_compare') $halfArgs
$half=Get-Content -Raw -LiteralPath $halfPath|ConvertFrom-Json
if(!$half.passed -or $half.samples -ne 257 -or $half.native_ids -ne $native -or $half.columns -ne 26){throw 'Original complete-history half gate failed'}
$files+=Entry $halfPath;VerifyBuild;Verify $receipts;Verify $files
NewJson $final ([ordered]@{passed=$true;geometry=$Geometry;configuration='ReleaseCPU';actual_ComputeStep_Sym=$true;source_freeze=(Entry $freezePath);build=(Entry $buildPath);seeds=(Entry $seedReceiptPath);prerequisites=$gateBindings;retained_final=(Entry $oldFinalPath);solver_jobs=2;matched_samples_per_job=257;native_ids=$native;fixed_ids=$fixed;columns=26;all_native_fields_and_actual_saved_clocks_bitwise_exact=$true;existing_diagnostics_byte_exact=$true;exact_files=$exact;half=(Entry $halfPath);receipts=$receipts;files=$files;new_actual_DtVariable_guard_executed=$true;gradient_bound_never_dominant_inferred=$false;independent_gradient_screen_scope='retained saved-point ledger only; no independent every-force-stage cache trace';new_CPP_or_physics=$false;general_sufficient_stability_proven=$false;physical_acceptance=$false;public_or_formal_admission=$false})
Write-Output "PASSED $Geometry complete native/diagnostic regression; no gradient-nondominance inference: $final"



