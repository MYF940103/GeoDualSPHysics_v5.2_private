param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Actual helper/time-policy components only; no GenCase, trajectory or formal-case run.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$name="upl_p3_perm_time_${Configuration}_r1";$folder=Join-Path $tests ("outputs\"+$name)
$harness=Join-Path $PSScriptRoot 'upl_p3_perm_time_r1.cpp'
$retainedHarness=Join-Path $PSScriptRoot 'upl_p3_perm_actual_r1.cpp'
$base=Join-Path $PSScriptRoot 'upl_p2_feedback_harness_r1.cpp'
$note=Join-Path $tests 'notes\upl_p3_perm_time_component_r1.json'
$freezePath=Join-Path $logs 'upl_p3_perm_time_build_r1.json'
$defaultOffPath=Join-Path $logs 'upl_p3_perm_time_off_r1.check.json'
$buildPath=Join-Path $logs ($name+'.build.json')
$exe=Join-Path $folder 'upl_p3_perm_time_r1.exe'
$oldCheck=Join-Path $logs ("upl_p3_actual_"+$Configuration+"_r3_run.check.json")
$oldOut=Join-Path $tests ("outputs\upl_p3_actual_"+$Configuration+"_r3_run")
$oldPermCheck=Join-Path $logs ("upl_p3_perm_actual_"+$Configuration+"_r2.check.json")
$oldPermOut=Join-Path $tests ("outputs\upl_p3_perm_actual_"+$Configuration+"_r2_on")
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root source freeze and explicit execution authorization required'}
$freeze=Get-Content -Raw -LiteralPath $freezePath|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Authoritative clean time-policy builds unavailable'}
foreach($s in $freeze.source){Verify @($s.original,$s.snapshot)};Verify $freeze.logs;Verify $freeze.programs
$defaultOff=Get-Content -Raw -LiteralPath $defaultOffPath|ConvertFrom-Json
if(!$defaultOff.passed){throw 'Original full default-OFF native regression must pass first'}
$defaultOffBindings=@(Entry $defaultOffPath)
foreach($g in $defaultOff.groups){Verify @($g.check);$defaultOffBindings+=Entry $g.check.path}
$old=Get-Content -Raw -LiteralPath $oldCheck|ConvertFrom-Json
$oldPerm=Get-Content -Raw -LiteralPath $oldPermCheck|ConvertFrom-Json
if(!$old.passed -or !$oldPerm.passed){throw 'Retained constant and smooth-k components must both pass'}
$controlsOff=@(foreach($leaf in @('rates.csv','summary.csv','ct_suppression.csv','ct_values.csv','periodic_c.csv','complete.json')){
  $p=Join-Path $oldOut $leaf;$saved=@($old.files|Where-Object {$_.path -eq $p})
  if($saved.Count -ne 1){throw 'Retained constant control file missing'};Verify $saved;$saved[0]
})
$controlsPerm=@(foreach($leaf in @('rates.csv','permeability.csv','summary.csv','guards.csv','periodic.csv','scales.csv','complete.json')){
  $p=Join-Path $oldPermOut $leaf;$saved=@($oldPerm.files|Where-Object {$_.path -eq $p})
  if($saved.Count -ne 1){throw 'Retained smooth-k control file missing'};Verify $saved;$saved[0]
})
$controls=@($controlsOff)+@($controlsPerm);$defaultOffBindings+=Entry $oldPermCheck
if($Configuration -eq 'ReleaseCPU'){
  $debugPath=Join-Path $logs 'upl_p3_perm_time_DebugCPU_r1.check.json'
  $d=Get-Content -Raw -LiteralPath $debugPath|ConvertFrom-Json
  if(!$d.passed -or $d.configuration -ne 'DebugCPU'){throw 'Debug constant/smooth controls and new time-policy gates must pass before Release'}
  Verify @($d.build,$d.off_run,$d.perm_run,$d.time_run);Verify $d.files
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
  $inputs=@(@($project,$harness,$retainedHarness,$base,$PSCommandPath,$note,$freezePath,$oldCheck)+$objects+$sources+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})+$controls+$defaultOffBindings
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $folder|Out-Null;$snapshots=@()
  foreach($p in @($harness,$retainedHarness,$base,$PSCommandPath,$note)){$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$copy=Entry $dest;if($copy.sha256 -ne (Entry $p).sha256){throw 'Recipe snapshot differs'};$snapshots+=$copy}
  $obj=Join-Path $folder 'perm_time.obj';$log=Join-Path $logs ($name+'.build.log')
  if(Test-Path -LiteralPath $log){throw 'Retained build log protected'};[IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$folder\compile.pdb",'/sourceDependencies',(Join-Path $folder 'compile.dependencies.json'))+$flags+@($harness)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs;if($debug){$link+=@('/DEBUG',"/PDB:$folder\link.pdb")}
  $start=[DateTime]::UtcNow.ToString('o');$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$ce=$LASTEXITCODE;$le=$null
  if($ce -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$le=$LASTEXITCODE};$ErrorActionPreference=$oldAction
  Verify $inputs;Verify $libraries;Verify $snapshots;$runtime=@()
  if($ce -eq 0 -and $le -eq 0){foreach($p in (@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml'))){$a=Entry $p;$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;$copy=Entry $dest;if($copy.sha256 -ne $a.sha256 -or (Entry $p).sha256 -ne $a.sha256){throw 'Runtime changed'};$runtime+=@{original=$a;copy=$copy}}}
  NewJson $buildPath ([ordered]@{status=if($ce -eq 0 -and $le -eq 0){'built_not_run'}else{'build_failed_retained'};configuration=$Configuration;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');source_freeze=(Entry $freezePath);compile_exit=$ce;link_exit=$le;inputs=$inputs;libraries=$libraries;snapshots=$snapshots;controls=$controls;compile=$compile;link=$link;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};runtime=$runtime;log=(Entry $log);physical_trajectory=$false;physical_acceptance=$false})
  if($ce -ne 0 -or $le -ne 0){throw 'Component build failed; preserve label'};Write-Output "BUILT $exe";exit 0
}

$b=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if($b.status -ne 'built_not_run'){throw 'Component build unavailable'}
function VerifyBuild{Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.original,$r.copy)}}
function InvokeComponent([string]$kind,[string]$cli){
  VerifyBuild;$job=$name+'_'+$kind;$out=Join-Path $tests ('outputs\'+$job);$receipt=Join-Path $logs ($job+'.run.json');$log=Join-Path $logs ($job+'.log')
  foreach($p in @($out,$receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Fresh component output required'}}
  $start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe $cli $out 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=(Entry $exe);arguments=@($cli,$out);build=(Entry $buildPath);log=(Entry $log);physical_trajectory=$false;physical_acceptance=$false})
  if($code -ne 0){throw "Component $kind failed; preserve evidence and stop dependencies"};VerifyBuild
  @{output=$out;receipt=(Entry $receipt)}
}
function Exact($control,[string]$out){
  @(foreach($old in $control){$current=Entry (Join-Path $out ([IO.Path]::GetFileName($old.path)));if($current.bytes -ne $old.bytes -or $current.sha256 -ne $old.sha256){throw "Retained component control differs: $($old.path)"};@{retained=$old;current=$current;byte_identical=$true}})
}
$final=Join-Path $logs ($name+'.check.json');if(Test-Path -LiteralPath $final){throw 'Retained final check protected'}
$off=InvokeComponent 'off' '--off-control';$rawEqual=Exact $controlsOff $off.output
$perm=InvokeComponent 'perm' '--perm-control';$permEqual=Exact $controlsPerm $perm.output
$time=InvokeComponent 'time' '--out'
$done=Get-Content -Raw -LiteralPath (Join-Path $time.output 'complete.json')|ConvertFrom-Json
if(!$done.passed -or $done.active_fixtures -ne 8 -or $done.cache_cases -ne 40 -or $done.actual_rate_helper_calls -ne 40 -or $done.actual_DtVariable_cases -ne 64 -or $done.thread_pairs_exact -ne 4 -or $done.node_ledger_rows -ne 720 -or !$done.actual_cached_max_from_native_helper -or !$done.zero_driving_rates_with_positive_gradient_speed -or !$done.independent_all_particle_reference -or !$done.old_pure_wave_pore_signature_unchanged -or !$done.force_statistics_manually_initialized_for_component -or !$done.stale_cache_assigned_only_for_reset_negative_checks -or !$done.covered_arrays_and_clock_unchanged -or $done.physical_trajectory -or $done.general_variable_coefficient_stability_proven -or $done.physical_acceptance){throw 'Actual gradient-cache/time-policy coverage or scope differs from peer declaration'}
foreach($pair in @(@('cache.csv',40),@('node_ledger.csv',720),@('requests.csv',64))){
  $rows=@(Import-Csv -LiteralPath (Join-Path $time.output $pair[0]));if($rows.Count -ne $pair[1]){throw 'Actual diagnostic table rows differ from declared coverage'}
}
$files=@(@($off.output,$perm.output,$time.output)|ForEach-Object {Get-ChildItem -LiteralPath $_ -Recurse -File}|Sort-Object FullName|ForEach-Object {Entry $_.FullName})
VerifyBuild;Verify $files
NewJson $final ([ordered]@{passed=$true;configuration=$Configuration;scope='Actual private CPU necessary smooth-k time-policy component; no trajectory or general sufficient-stability proof';build=(Entry $buildPath);off_run=$off.receipt;perm_run=$perm.receipt;time_run=$time.receipt;completion=$done;root_default_OFF_admission=(Entry $defaultOffPath);constant_control_six_files_exact=$rawEqual;smooth_k_control_seven_files_exact=$permEqual;files=$files;physical_trajectory=$false;general_variable_coefficient_stability_proven=$false;physical_acceptance=$false})
Write-Output "PASSED $final"
