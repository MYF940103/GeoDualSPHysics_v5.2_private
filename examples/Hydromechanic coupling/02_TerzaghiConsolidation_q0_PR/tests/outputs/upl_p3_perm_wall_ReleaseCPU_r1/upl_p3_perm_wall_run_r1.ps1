param(
  [ValidateSet('Build','Smoke','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Bounded private smooth-k fixed-wall actual steps only; no new geometry or formal run.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$name="upl_p3_perm_wall_${Configuration}_r1";$folder=Join-Path $tests ("outputs\"+$name)
$harness=Join-Path $PSScriptRoot 'upl_p3_perm_wall_r1.cpp'
$retainedHarness=Join-Path $PSScriptRoot 'upl_p3_wall_wave_harness_r2.cpp'
$note=Join-Path $tests 'notes\upl_p3_perm_wall_r1.json'
$freezePath=Join-Path $logs 'upl_p3_perm_build_r2.json'
$seedReceiptPath=Join-Path $logs 'upl_p3_wall_wave_seed_r3.inputs.json'
$oldFinalPath=Join-Path $logs 'upl_p3_wall_wave_ReleaseCPU_r4.check.json'
$oldControl=Join-Path $tests 'outputs\upl_p3_wall_wave_ReleaseCPU_r4_k1_c'
$buildPath=Join-Path $logs ($name+'.build.json')
$exe=Join-Path $folder 'upl_p3_perm_wall_r1.exe'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Roundtrip([double]$v){$v.ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
$declaration=Get-Content -Raw -LiteralPath $note|ConvertFrom-Json
$declaredHarness=Entry $harness
if($declaredHarness.bytes -ne $declaration.harness_identity.bytes -or $declaredHarness.sha256 -ne $declaration.harness_identity.sha256){throw 'Reviewed variable-k wall fixture identity changed'}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root review and explicit execution authorization are required'}
$freeze=Get-Content -Raw -LiteralPath $freezePath|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Authoritative clean source builds unavailable'}
foreach($s in $freeze.source){Verify @($s.original,$s.snapshot)};Verify $freeze.logs;Verify $freeze.programs
$gateBindings=@()
foreach($p in @('logs\upl_p3_perm_off_r2.check.json','logs\upl_p3_perm_actual_DebugCPU_r2.check.json','logs\upl_p3_perm_actual_ReleaseCPU_r2.check.json','logs\upl_p3_perm_review_r1.check.json','logs\upl_p3_perm_wave_review_r1.check.json','notes\upl_p3_perm_wave_independent_r1.json','logs\upl_p3_perm_periodic_ReleaseCPU_r1.check.json')){
  $path=Join-Path $tests $p;$gate=Get-Content -Raw -LiteralPath $path|ConvertFrom-Json
  if(!$gate.passed){throw "Required prior gate failed: $p"};$gateBindings+=Entry $path;Verify $gate.files
}
$seedReceipt=Get-Content -Raw -LiteralPath $seedReceiptPath|ConvertFrom-Json
if($seedReceipt.status -ne 'seeds_prepared_not_solved'){throw 'Retained wall geometry unavailable'}
Verify $seedReceipt.inputs;Verify $seedReceipt.jobs;Verify $seedReceipt.files
$seedFiles=@($seedReceipt.inputs)+@($seedReceipt.jobs)+@($seedReceipt.files)
$oldFinal=Get-Content -Raw -LiteralPath $oldFinalPath|ConvertFrom-Json
if(!$oldFinal.passed){throw 'Accepted constant-k wall control unavailable'}
$controlFiles=@(foreach($leaf in @('physical.bin','native_ids.csv','fixed_ids.csv')){
  $p=Join-Path $oldControl $leaf;$rows=@($oldFinal.files|Where-Object {$_.path -eq $p})
  if($rows.Count -ne 1){throw 'Retained whole trajectory/identity proof missing'};Verify $rows;$rows[0]
})
$gateBindings+=Entry $oldFinalPath;$gateBindings+=$controlFiles
if($Configuration -eq 'ReleaseCPU'){
  $smokePath=Join-Path $logs 'upl_p3_perm_wall_DebugCPU_r1.smoke.check.json'
  $d=Get-Content -Raw -LiteralPath $smokePath|ConvertFrom-Json
  if(!$d.passed -or !$d.smoke_only -or $d.solver_jobs -ne 1){throw 'Actual Debug two-step wall smoke must pass before Release'}
  Verify @($d.build);Verify $d.receipts;Verify $d.files;$gateBindings+=Entry $smokePath
}
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $buildPath)){throw 'Fresh immutable build required'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj';[xml]$projectXml=Get-Content -Raw -LiteralPath $project
  $objects=@();$sources=@()
  foreach($node in $projectXml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false
    $expectedCondition="'"+'$(Configuration)|$(Platform)'+"'=='"+$Configuration+"|x64'"
    foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq $expectedCondition){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){$objects+=Join-Path $source "VS\Intermediate\DualSPHysics_${Configuration}_x64\$stem.obj";$sources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))}
  }
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($project,$harness,$retainedHarness,$PSCommandPath,$note,$freezePath,$seedReceiptPath)+$objects+$sources+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})+$seedFiles+$gateBindings
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $folder|Out-Null;$snapshots=@()
  foreach($p in @($harness,$retainedHarness,$PSCommandPath,$note)){$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$copy=Entry $dest;if($copy.sha256 -ne (Entry $p).sha256){throw 'Recipe snapshot differs'};$snapshots+=$copy}
  $obj=Join-Path $folder 'perm_wall.obj';$log=Join-Path $logs ($name+'.build.log')
  if(Test-Path -LiteralPath $log){throw 'Retained build log protected'};[IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$folder\compile.pdb",'/sourceDependencies',(Join-Path $folder 'compile.dependencies.json'))+$flags+@($harness)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs;if($debug){$link+=@('/DEBUG',"/PDB:$folder\link.pdb")}
  $start=[DateTime]::UtcNow.ToString('o');$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$ce=$LASTEXITCODE;$le=$null
  if($ce -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$le=$LASTEXITCODE};$ErrorActionPreference=$oldAction
  Verify $inputs;Verify $libraries;Verify $snapshots;$runtime=@()
  if($ce -eq 0 -and $le -eq 0){foreach($p in (@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml'))){$a=Entry $p;$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$copy=Entry $dest;if($copy.sha256 -ne $a.sha256 -or (Entry $p).sha256 -ne $a.sha256){throw 'Runtime changed'};$runtime+=@{original=$a;copy=$copy}}}
  NewJson $buildPath ([ordered]@{status=if($ce -eq 0 -and $le -eq 0){'built_not_run'}else{'build_failed_retained'};configuration=$Configuration;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');source_freeze=(Entry $freezePath);compile_exit=$ce;link_exit=$le;inputs=$inputs;libraries=$libraries;snapshots=$snapshots;controls=$seedFiles;compile=$compile;link=$link;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};runtime=$runtime;log=(Entry $log);planned_actual_ComputeStep_Sym=$true;physical_acceptance=$false})
  if($ce -ne 0 -or $le -ne 0){throw 'Component build failed; preserve label'};Write-Output "BUILT $exe";exit 0
}

if(($Mode -eq 'Smoke' -and $Configuration -ne 'DebugCPU') -or ($Mode -eq 'Run' -and $Configuration -ne 'ReleaseCPU')){throw 'Only Debug smoke and Release bounded wall windows are admitted'}
$b=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if($b.status -ne 'built_not_run'){throw 'Fixture build unavailable'}
function VerifyBuild{Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.original,$r.copy)};Verify $seedFiles;Verify $gateBindings}
function InvokeProgram([string]$job,[string[]]$argv){
  VerifyBuild;$receipt=Join-Path $logs ($job+'.run.json');$log=Join-Path $logs ($job+'.log')
  foreach($p in @($receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Retained owned call protected'}}
  $start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=(Entry $exe);arguments=$argv;build=(Entry $buildPath);log=(Entry $log);physical_acceptance=$false})
  if($code -ne 0){throw "Actual wall call failed: $job; preserve output and stop dependencies"};VerifyBuild;Entry $receipt
}
$Cu=[Math]::Sqrt((89478488.+4.*134217728./3.+67108864./.25)/2048.)
$Pstar=(67108864./.25)*(1./512.)/$Cu;$Ustar=(1./512.)/($Cu*2*[Math]::PI/.125)
$receipts=@();$files=@();$solverJobs=0
function RunJob([string]$suffix,[string]$tag,[int]$steps,[bool]$smoke,[bool]$variable){
  $job=$name+'_'+$suffix;$output=Join-Path $tests ('outputs\'+$job)
  if(Test-Path -LiteralPath $output){throw 'Retained actual output protected'}
  $seed=Join-Path $tests ("outputs\upl_p3_wall_wave_seed_r3_"+$tag+"\CaseUplWall_"+$tag)
  $receipt=InvokeProgram $job @('--job',"$steps",$(if($smoke){'1'}else{'0'}),$(if($variable){'1'}else{'0'}),'-cpu','-ompthreads:1','-stable',$seed,$output,'-dirdataout','data')
  $d=Get-Content -Raw -LiteralPath (Join-Path $output 'complete.json')|ConvertFrom-Json
  $dt=if($tag -eq 'c'){1./33554432.}else{1./67108864.};$samples=if($smoke){3}else{257}
  if(!$d.passed -or !$d.actual_ComputeStep_Sym -or $d.Nx -ne 32 -or $d.Nz -ne 32 -or $d.native_ids -ne 1024 -or $d.fixed_ids -ne 256 -or $d.band_native -ne 256 -or $d.steps -ne $steps -or $d.samples -ne $samples -or [double]$d.dt_actual -ne $dt -or [double]$d.actual_end_s -ne [double]($steps*$dt) -or [bool]$d.smoke -ne $smoke -or $d.k0 -or [bool]$d.conductivity_switch -ne $variable -or [double]$d.Ck -ne 1./8192. -or [double]$d.cu -ne $Cu -or [double]$d.Pstar -ne $Pstar -or [double]$d.Ustar -ne $Ustar -or $d.physical_acceptance){throw 'Actual wall identity, clock or nominal scale differs'}
  if($d.native_conductivity_ledger_rows -ne $samples*1024 -or $d.additional_option_rate_calls -ne $(if($variable){$samples}else{2*$samples}) -or [bool]$d.constant_coefficient_reference_used_as_truth -ne (!$variable) -or $d.rollback26_exact_frames -ne $samples -or $d.additional_saved_point_force_audits -ne $samples -or !$d.first_audit_initialized_force_statistics -or $d.automatic_integrator_wall_helper_calls_directly_observed){throw 'Actual wall ledger, rollback or audit scope differs'}
  if(!$smoke -and $variable){
    foreach($key in @('max_source_RMS_over_roundoff','max_chain_RMS_over_roundoff','max_pressure_chain_RMS_over_roundoff','max_acceleration_chain_RMS_over_roundoff')){if([double]$d.$key -le 10){throw 'Resolved variable-k source/chain requirement failed'}}
    if([double]$d.max_k_span_over_initial_k0 -lt .005 -or [double]$d.max_k_change_over_initial_k0 -lt .005 -or [double]$d.max_physical_qn_over_original_bound -gt 1 -or $d.physical_wrong_zero_detected -le 0 -or $d.physical_wrong_copy_detected -le 0){throw 'Variable-k evolution or physical face/negative-control gate failed'}
  }
  $history=@(Import-Csv -LiteralPath (Join-Path $output 'modes.csv'));if($history.Count -ne $samples){throw 'Incomplete actual saved history'}
  for($i=0;$i -lt $samples;$i++){$stride=$steps/($samples-1);if([int]$history[$i].step -ne $i*$stride -or [double]$history[$i].time_s -ne $i*$stride*$dt){throw 'Actual saved step/time differs; no interpolation'}}
  foreach($leaf in @('physical.bin','native_ids.csv','fixed_ids.csv','modes.csv','wall_audit.csv','conductivity_ledger.csv','source_summary.csv','complete.json')){[void](Entry (Join-Path $output $leaf))}
  @{directory=$output;completion=$d;receipt=$receipt;files=@(Get-ChildItem -LiteralPath $output -Recurse -File|ForEach-Object {Entry $_.FullName})}
}
$smoke=$Mode -eq 'Smoke';$final=Join-Path $logs ($name+$(if($smoke){'.smoke.check.json'}else{'.check.json'}))
if(Test-Path -LiteralPath $final){throw 'Retained final receipt protected'}
if($smoke){
  $r=RunJob 'smoke' 'c' 2 $true $true;$receipts+=$r.receipt;$files+=$r.files;$solverJobs++
}else{
  $c=RunJob 'on_c' 'c' 1024 $false $true;$receipts+=$c.receipt;$files+=$c.files;$solverJobs++
  $h=RunJob 'on_h' 'h' 2048 $false $true;$receipts+=$h.receipt;$files+=$h.files;$solverJobs++
  $halfPath=Join-Path $logs ($name+'_half.check.json')
  $receipts+=InvokeProgram ($name+'_half_compare') @('--half',(Join-Path $c.directory 'physical.bin'),(Join-Path $h.directory 'physical.bin'),$halfPath)
  $half=Get-Content -Raw -LiteralPath $halfPath|ConvertFrom-Json
  if(!$half.passed -or $half.samples -ne 257 -or $half.native_ids -ne 1024 -or $half.columns -ne 26){throw 'Independent original wall half gate failed'};$files+=Entry $halfPath
  $off=RunJob 'off_c' 'c' 1024 $false $false;$receipts+=$off.receipt;$files+=$off.files;$solverJobs++
  $equal=@()
  foreach($old in $controlFiles){$current=Entry (Join-Path $off.directory ([IO.Path]::GetFileName($old.path)));if($current.bytes -ne $old.bytes -or $current.sha256 -ne $old.sha256){throw 'Constant-law whole26-field trajectory/time/ID ledger differs from retained r4'};$equal+=@{retained=$old;current=$current;byte_identical=$true}}
  $exactPath=Join-Path $logs ($name+'_constant_exact.check.json')
  NewJson $exactPath ([ordered]@{passed=$true;samples=257;native_ids=1024;fixed_ids=256;columns=26;all_native_physical_fields_and_saved_clocks_0ULP=$true;identity_ledgers_byte_exact=$true;equal_files=$equal;scope='same-dt constant-law implementation, not half or new theory';physical_acceptance=$false});$files+=Entry $exactPath
  $effectPath=Join-Path $logs ($name+'_effect.check.json')
  $receipts+=InvokeProgram ($name+'_effect_compare') @('--effect',(Join-Path $c.directory 'physical.bin'),(Join-Path $off.directory 'physical.bin'),(Roundtrip ([double]$half.max_pressure_RMS_Pa)),$effectPath)
  $effect=Get-Content -Raw -LiteralPath $effectPath|ConvertFrom-Json;$required=[Math]::Max(.001,10*[double]$half.max_pressure_RMS_Pa)
  if(!$effect.passed -or $effect.samples -ne 257 -or $effect.native_ids -ne 1024 -or $effect.columns -ne 26 -or [double]$effect.measured_half_pressure_RMS_Pa -ne [double]$half.max_pressure_RMS_Pa -or [double]$effect.required_pressure_effect_Pa -ne $required -or [double]$effect.max_pressure_RMS_Pa -le $required -or $effect.comparison_kind -ne 'same_initial_ON_vs_constant_OFF_not_half_or_theory' -or $effect.physical_acceptance){throw 'Variable-k wall effect unresolved or comparison identity differs'};$files+=Entry $effectPath
}
VerifyBuild;Verify $receipts;Verify $files
NewJson $final ([ordered]@{passed=$true;smoke_only=$smoke;actual_ComputeStep_Sym=$true;source_freeze=(Entry $freezePath);build=(Entry $buildPath);seeds=(Entry $seedReceiptPath);retained_constant_control=(Entry $oldFinalPath);prerequisites=$gateBindings;solver_jobs=$solverJobs;receipts=$receipts;files=$files;general_sufficient_time_stability_proven=$false;new_physical_or_public_admission=$false;physical_acceptance=$false})
Write-Output "PASSED bounded private variable-k wall $Mode; pending independent review: $final"
