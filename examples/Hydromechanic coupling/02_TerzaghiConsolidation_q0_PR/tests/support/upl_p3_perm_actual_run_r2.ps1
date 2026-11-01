param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Actual private helper components only; no GenCase, ComputeStep trajectory or formal case.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$name="upl_p3_perm_actual_${Configuration}_r2"
$folder=Join-Path $tests ("outputs\"+$name)
$harness=Join-Path $PSScriptRoot 'upl_p3_perm_actual_r1.cpp'
$retainedHarness=Join-Path $PSScriptRoot 'upl_p3_actual_r3.cpp'
$base=Join-Path $PSScriptRoot 'upl_p2_feedback_harness_r1.cpp'
$note=Join-Path $tests 'notes\upl_p3_perm_actual_r2.json'
$freezePath=Join-Path $logs 'upl_p3_perm_build_r2.json'
$defaultOffPath=Join-Path $logs 'upl_p3_perm_off_r2.check.json'
$buildPath=Join-Path $logs ($name+'.build.json')
$exe=Join-Path $folder 'upl_p3_perm_actual_r1.exe'
$oldCheck=Join-Path $logs ("upl_p3_actual_"+$Configuration+"_r3_run.check.json")
$oldOut=Join-Path $tests ("outputs\upl_p3_actual_"+$Configuration+"_r3_run")
$controlLeaves=@('rates.csv','summary.csv','ct_suppression.csv','ct_values.csv','periodic_c.csv','complete.json')
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root source freeze and explicit execution authorization required; authoring is not permission'}
$freeze=Get-Content -Raw -LiteralPath $freezePath|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Authoritative perm builds unavailable'}
foreach($s in $freeze.source){Verify @($s.original,$s.snapshot)};Verify $freeze.logs;Verify $freeze.programs
$defaultOff=Get-Content -Raw -LiteralPath $defaultOffPath|ConvertFrom-Json
if(!$defaultOff.passed){throw 'Root original full default-OFF regressions must pass before any new component build/run'}
$defaultOffBindings=@(Entry $defaultOffPath)
foreach($g in $defaultOff.groups){Verify @($g.check);$defaultOffBindings+=Entry $g.check.path}
$old=Get-Content -Raw -LiteralPath $oldCheck|ConvertFrom-Json
if(!$old.passed){throw 'Retained constant-k actual component not passed'}
$controls=@(foreach($leaf in $controlLeaves){
  $p=Join-Path $oldOut $leaf;$saved=@($old.files|Where-Object {$_.path -eq $p})
  if($saved.Count -ne 1){throw "Retained component field missing: $leaf"};Verify $saved;$saved[0]
})
if($Configuration -eq 'ReleaseCPU'){
  $debugPath=Join-Path $logs 'upl_p3_perm_actual_DebugCPU_r2.check.json'
  $d=Get-Content -Raw -LiteralPath $debugPath|ConvertFrom-Json
  if(!$d.passed -or $d.configuration -ne 'DebugCPU'){throw 'Debug OFF and ON component gates must pass before Release'}
  Verify @($d.build,$d.off_run,$d.on_run);Verify $d.files
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
  $obj=Join-Path $folder 'perm_actual.obj';$log=Join-Path $logs ($name+'.build.log')
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
if($b.status -ne 'built_not_run'){throw 'Component build not admitted'}
function VerifyBuild{Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.original,$r.copy)}}
function InvokeComponent([string]$kind,[string]$cli){
  VerifyBuild;$job=$name+'_'+$kind;$out=Join-Path $tests ("outputs\"+$job);$receipt=Join-Path $logs ($job+'.run.json');$log=Join-Path $logs ($job+'.log')
  foreach($p in @($out,$receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Fresh component output required'}}
  $start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe $cli $out 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=(Entry $exe);arguments=@($cli,$out);build=(Entry $buildPath);log=(Entry $log);physical_trajectory=$false;physical_acceptance=$false})
  if($code -ne 0){throw "Component $kind failed; preserve evidence and stop dependencies"};VerifyBuild
  @{output=$out;receipt=(Entry $receipt)}
}
$final=Join-Path $logs ($name+'.check.json');if(Test-Path -LiteralPath $final){throw 'Retained final check protected'}
$off=InvokeComponent 'off' '--off-control';$equal=@()
foreach($a in $controls){$current=Entry (Join-Path $off.output ([IO.Path]::GetFileName($a.path)));if($current.sha256 -ne $a.sha256 -or $current.bytes -ne $a.bytes){throw "Constant-law OFF control differs: $($a.path)"};$equal+=@{retained=$a;current=$current;byte_identical=$true}}
$on=InvokeComponent 'on' '--out'
$done=Get-Content -Raw -LiteralPath (Join-Path $on.output 'complete.json')|ConvertFrom-Json
if(!$done.passed -or !$done.actual_private_helper -or $done.field_cases -ne 28 -or $done.helper_evaluations -ne 40 -or $done.rate_checks -ne 728 -or $done.guard_checks -ne 10 -or $done.scale_checks -ne 2 -or $done.total_actual_rate_helper_calls -ne 70 -or !$done.force_statistics_manually_initialized_for_component -or $done.physical_trajectory -or $done.physical_acceptance){throw 'Variable-k component coverage or scope differs from declared protocol'}
foreach($leaf in @('rates.csv','summary.csv','permeability.csv','guards.csv','periodic.csv','scales.csv','complete.json')){[void](Entry (Join-Path $on.output $leaf))}
$files=@(@($off.output,$on.output)|ForEach-Object {Get-ChildItem -LiteralPath $_ -File -Recurse}|Sort-Object FullName|ForEach-Object {Entry $_.FullName})
VerifyBuild;Verify $files
NewJson $final ([ordered]@{passed=$true;configuration=$Configuration;scope='actual private CPU smooth-k helper manufactured components only, no integration';build=(Entry $buildPath);off_run=$off.receipt;on_run=$on.receipt;completion=$done;root_default_OFF_admission=(Entry $defaultOffPath);constant_law_OFF_complete_text_byte_comparisons=$equal;files=$files;physical_trajectory=$false;new_half_test=$false;general_sufficient_time_stability_proven=$false;physical_acceptance=$false})
Write-Output "PASSED $final"
