param([Parameter(Mandatory=$true)][ValidateSet('Native','Feedback')][string]$Fixture,[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Relink retained functions, with a Native entry-only batch wrapper, against current Darcy objects. Never run here.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$note=Join-Path $t 'notes\upl_gpu_darcy_legacy_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function P([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){if(!$r -or !$r.path){throw 'Missing binding'};$a=E (P $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((P $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained evidence protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,[string]$label){
  V @($tool);$p=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($f in @($p,$log)){if(Test-Path -LiteralPath $f){throw 'Retained compile/link call protected'}}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$old}
  V @($tool);Save $p ([ordered]@{owned_call_exited=$true;exit_code=$code;program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);program_or_component_run=$false;physical_acceptance=$false});if($code){throw 'Compile/link failed; preserve evidence'};E $p
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root complete recipe/source review and explicit one-build authorization required'}
if($Configuration -eq 'Release'){foreach($job in 'OFF_smoke','Observer_smoke','Feedback_smoke'){$p=Join-Path $logs ('upl_gpu_darcy_legacy_'+$job+'_r1.check.json');$q=J $p;if(!$q.passed -or !$q.all_original15_exact -or !$q.memcheck_zero_errors_and_leaks -or $q.DynamicPorePressure_enabled){throw 'All three fresh Debug exact/memcheck reviews required before Release helper build'};V $q.files;V @($q.source_run,$q.completion)}}
$gpuPath=Join-Path $logs ('upl_gpu_darcy_'+$Configuration+'_r2.build.json');$g=J $gpuPath
if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $Configuration -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main -or !$g.canonical_GPU_unchanged){throw 'Current authoritative Darcy r2 objects required'}
$source=J $g.source_freeze.path;$baseline=J $g.baseline.path
function VerifyGpu {V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program);V $source.source;V $source.five_targets;V $baseline.other_source;V $baseline.canonical_GPU;foreach($r in $g.runtime){V @($r.original,$r.copy)}}
VerifyGpu;$project=J $g.project_call.path;if(!$project.owned_call_exited -or $project.exit_code -ne 0 -or $project.arguments -notcontains '/t:Rebuild'){throw 'Owned successful authoritative Rebuild required'};V @($project.program,$project.log)
$oldName=if($Fixture -eq 'Native'){'upl_gpu_k0_time_native_'+$Configuration+'_r1.helper.json'}else{'upl_gpu_k0_actual_'+$Configuration+'_r2.helper.json'}
$oldPath=Join-Path $logs $oldName;$h=J $oldPath;$oldFixture=if($Fixture -eq 'Native'){'Native'}else{'Actual'}
if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne $oldFixture -or $h.configuration -ne $Configuration){throw 'Immutable old helper recipe differs'}
# Validate historical recipes/programs, never recursively assert their old production source originals are current.
V $h.inputs;V $h.author_files;V $h.tools;V $h.libraries;V @($h.source_build,$h.program,$h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}
$oldg=J $h.source_build.path;$cc=J $h.compile_call.path;$lc=J $h.link_call.path;V @($cc.program,$cc.log,$lc.program,$lc.log)
if(!$cc.owned_call_exited -or !$lc.owned_call_exited -or $cc.exit_code -ne 0 -or $lc.exit_code -ne 0 -or @($oldg.objects).Count -ne 110 -or !$oldg.objects_exclude_main){throw 'Immutable compile/link/object inventory rejected'}
$cpp=Join-Path $t $(if($Fixture -eq 'Native'){'support\upl_gpu_observer_native_r1.cpp'}else{'support\upl_gpu_k0_actual_r2.cpp'})
$expected=if($Fixture -eq 'Native'){'b112f7e78651dde136c2438a02f326522ef4cb35b5603fa1eb17ee24d3437857'}else{'7bdf0ffbf04b8cf964682ae3e8636691998231b7e6472f64e9c1a3adc2e15625'}
if((E $cpp).sha256 -ne $expected -or (E (Join-Path $t 'support\upl_gpu_observer_native_r1.cpp')).sha256 -ne 'b112f7e78651dde136c2438a02f326522ef4cb35b5603fa1eb17ee24d3437857'){throw 'Unchanged historical fixture/include required'}
$buildCpp=$cpp;$batchAuthor=@();if($Fixture -eq 'Native'){$buildCpp=Join-Path $t 'support\upl_gpu_darcy_legacy_batch_r1.cpp';$batchAuthor=@(E $buildCpp;E (Join-Path $t 'notes\upl_gpu_darcy_legacy_batch_r1.json'))}
$name='upl_gpu_darcy_legacy_'+$Fixture+'_'+$Configuration+'_r1';$folder=Join-Path $outputs $name;$record=Join-Path $logs ($name+'.helper.json');foreach($p in @($folder,$record)){if(Test-Path -LiteralPath $p){throw 'Retained helper protected'}}
$oldInt=[IO.Path]::GetFullPath($oldg.no_space_IntDir).TrimEnd('\')+'\';$newInt=[IO.Path]::GetFullPath($g.no_space_IntDir).TrimEnd('\')+'\'
if($oldInt -ieq $newInt -or $newInt -match '\s'){throw 'New isolated no-space object directory required'}
$obj=Join-Path $folder 'helper.obj';$oldObj=Join-Path (Split-Path -Parent $h.program.path) 'helper.obj';$exe=Join-Path $folder ([IO.Path]::GetFileName($h.program.path))
$newObjects=@{};foreach($r in $g.objects){$n=[IO.Path]::GetFileName($r.path);if($newObjects.ContainsKey($n) -or [IO.Path]::GetFullPath($r.path) -ine (Join-Path $newInt $n)){throw 'Non-flat/duplicate new object inventory'};$newObjects[$n]=$r}
$oldObjects=@{};foreach($r in $oldg.objects){$n=[IO.Path]::GetFileName($r.path);if($oldObjects.ContainsKey($n) -or !$newObjects.ContainsKey($n) -or [IO.Path]::GetFullPath($r.path) -ine (Join-Path $oldInt $n)){throw 'Old/new object basename set differs'};$oldObjects[$n]=$r}
$ca=@();$fo=0;$fd=0;$src=0;foreach($a in $cc.arguments){if($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq $cpp){$ca+=$buildCpp;$src++}else{$ca+=$a}}
if($fo -ne 1 -or $fd -ne 1 -or $src -ne 1){throw 'Only compiler outputs and the explicit entry-only Native wrapper substitution permitted'}
$la=@();$on=0;$pn=0;$hn=0;$gn=0;$mapped=@{};foreach($a in $lc.arguments){
  if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$on++}
  elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $folder 'link.pdb');$pn++}
  elseif($a -ieq $oldObj){$la+=$obj;$hn++}
  elseif($a.StartsWith($oldInt,[StringComparison]::OrdinalIgnoreCase)){$n=[IO.Path]::GetFileName($a);if(!$oldObjects.ContainsKey($n) -or $mapped.ContainsKey($n) -or $a -ine $oldObjects[$n].path){throw 'Unexpected old GPU object'};$la+=$newObjects[$n].path;$mapped[$n]=$true;$gn++}
  else{$la+=$a}
}
if($on -ne 1 -or $hn -ne 1 -or $gn -ne 110 -or $pn -ne $(if($Configuration -eq 'Debug'){1}else{0})){throw 'Link substitutions differ from one helper plus 110 current objects'}
$linked=@($la|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)});if($linked.Count -ne 111 -or @($linked|Sort-Object -Unique).Count -ne 111){throw 'Object closure not exact'}
$author=@(E $PSCommandPath;E $note)+@($h.author_files)+$batchAuthor;$inputs=$author+@(E $gpuPath;E $oldPath)
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder);$compile=Call $cc.program $ca ($name+'_compile');$link=Call $lc.program $la ($name+'_link')
$runtime=@();foreach($r in $g.runtime){$p=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $p;$v=E $p;if($v.sha256 -ne $r.copy.sha256){throw 'Runtime copy differs'};$runtime+=@{original=$r.copy;copy=$v}}
VerifyGpu;V $inputs;V $h.tools;V $h.libraries
Save $record ([ordered]@{status='actual_authoritative_GPU_objects_helper_linked_not_run';fixture=$Fixture;configuration=$Configuration;source_build=(E $gpuPath);inputs=$inputs;author_files=$author;program=(E $exe);runtime=$runtime;tools=$h.tools;libraries=$h.libraries;objects=$g.objects;helper_object=(E $obj);link_object_count=111;compile_call=$compile;link_call=$link;replayed_helper=(E $oldPath);unchanged_fixture_source=($Fixture -eq 'Feedback');retained_native_functions_unchanged=$true;Native_batch_entry=($Fixture -eq 'Native');compiler_source_remaps=$(if($Fixture -eq 'Native'){1}else{0});GPU_object_substitutions=110;canonical_GPU_unchanged=$true;historical_source_paths_revalidated_as_current=$false;DynamicPorePressure_enabled=$false;program_or_component_run=$false;physical_acceptance=$false})
