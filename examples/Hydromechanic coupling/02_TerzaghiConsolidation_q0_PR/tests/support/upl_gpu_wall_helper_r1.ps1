param([ValidateSet('BuildFixture')][string]$Mode='BuildFixture',[Parameter(Mandatory=$true)][ValidateSet('Component','Native','Feedback','DarcyActual','SmoothActual','WallActual')][string]$Fixture,[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Compile/link exactly one chosen fixture. Never execute it or an old solver/control here.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$stagePath=Join-Path $logs 'upl_gpu_perm_stage_r1.check.json';$buildNote=Join-Path $t 'notes\upl_gpu_wall_helper_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((ResolveArtifactPath $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,[string]$label){
  V @($tool);$p=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($f in @($p,$log)){if(Test-Path -LiteralPath $f){throw 'Owned compile/link retained'}}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$old}
  V @($tool);Save $p ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);program_or_component_run=$false;physical_acceptance=$false})
  if($code){throw 'Compile/link failed; preserve evidence'};E $p
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root full source/fixture review and explicit single-build authorization required'}
$stage=J $stagePath;if(!$stage.passed -or !$stage.new_periodic_smooth_k_implementation_verified -or !$stage.all_original_absolute_and_normalized_gates_preserved -or $stage.physical_acceptance -or $stage.public_GPU_dynamic_accepted -or $stage.wall_or_general_boundary_accepted){throw 'Accepted bounded periodic smooth-k stage required'}
$gpuPath=Join-Path $logs ('upl_gpu_wall_'+$Configuration+'_r1.build.json');$g=J $gpuPath
if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $Configuration -or $g.git_base -cne '038f569d1d9b4ed6e124e99cf84a3268a30b5bfb' -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main -or !$g.private_static_wall_GPU_candidate_build_only){throw 'Current authoritative private-wall GPU objects required'}
$source=J $g.source_freeze.path;$baseline=J $g.baseline.path;$five=@('JSphGpu.h','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')
if(@($source.source).Count -ne 265 -or @($source.five_targets).Count -ne 5 -or $source.unchanged_source_count -ne 260 -or @($baseline.other_source).Count -ne 260 -or @($baseline.canonical_GPU).Count -ne 6 -or @(Compare-Object $five @($source.five_targets|ForEach-Object {[IO.Path]::GetFileName($_.path)})).Count -or $source.baseline.sha256 -ine $g.baseline.sha256 -or $source.accepted_periodic_smooth_k_stage.sha256 -ine (E $stagePath).sha256){throw 'Five/260/265 source/baseline closure differs'}
function VerifyCurrent {
  V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program);V $source.source;V $source.five_targets;V $baseline.inputs;V $baseline.source_control_receipts;V $baseline.other_source;V $baseline.canonical_GPU;foreach($r in $g.runtime){V @($r.original,$r.copy)}
}
VerifyCurrent;$project=J $g.project_call.path;V @($project.program,$project.log);if(!$project.owned_call_exited -or $project.exit_code -ne 0 -or $project.arguments -notcontains '/t:Rebuild'){throw 'Owned full authoritative Rebuild required'}
# Only immutable old compile/link recipes and their author inputs are reused, never old current-source inventories.
$native=Join-Path $t 'support\upl_gpu_observer_native_r1.cpp';$nativeNote=Join-Path $t 'notes\upl_gpu_observer_native_r1.json'
$extra=@();$expectedInclude=$null;$includeCpp=$null
switch($Fixture){
  'Component' {$token='component';$oldPath=Join-Path $logs ('upl_gpu_perm_component_'+$Configuration+'_r1.helper.json');$oldFixture='Component';$oldCpp=Join-Path $t 'support\upl_gpu_perm_component_r1.cpp';$cpp=Join-Path $t 'support\upl_gpu_wall_component_r1.cpp';$note=Join-Path $t 'notes\upl_gpu_wall_component_r1.json';$exeLeaf='upl_gpu_wall_component_r1.exe';$includeCpp=Join-Path $t 'support\upl_gpu_k0_time_r1.cpp';$expectedInclude='e886b659688ea369a3a30b8384ffa4c8f6ede4efd1342a288aebf24cdc712f95';$extra=@(E $includeCpp;E (Join-Path $t 'notes\upl_gpu_k0_time_component_r1.json'))}
  'Native' {$token='native';$oldPath=Join-Path $logs ('upl_gpu_perm_native_'+$Configuration+'_r1.helper.json');$oldFixture='Native';$cpp=Join-Path $t 'support\upl_gpu_darcy_legacy_batch_r1.cpp';$oldCpp=$cpp;$note=Join-Path $t 'notes\upl_gpu_darcy_legacy_batch_r1.json';$exeLeaf='upl_gpu_observer_native_r1.exe';$extra=@(E $native;E $nativeNote)}
  'Feedback' {$token='feedback';$oldPath=Join-Path $logs ('upl_gpu_perm_feedback_'+$Configuration+'_r1.helper.json');$oldFixture='Feedback';$cpp=Join-Path $t 'support\upl_gpu_k0_actual_r2.cpp';$oldCpp=$cpp;$note=Join-Path $t 'notes\upl_gpu_k0_actual_r2.json';$exeLeaf='upl_gpu_k0_actual_r1.exe';$extra=@(E $native;E $nativeNote)}
  'DarcyActual' {$token='actual';$oldPath=Join-Path $logs ('upl_gpu_perm_actual_'+$Configuration+'_r1.helper.json');$oldFixture='DarcyActual';$cpp=Join-Path $t 'support\upl_gpu_darcy_actual_r1.cpp';$oldCpp=$cpp;$note=Join-Path $t 'notes\upl_gpu_darcy_actual_r1.json';$exeLeaf='upl_gpu_darcy_actual_r1.exe';$extra=@(E $native;E $nativeNote)}
  'SmoothActual' {$token='variable_actual';$oldPath=Join-Path $logs ('upl_gpu_perm_variable_actual_'+$Configuration+'_r1.helper.json');$oldFixture='SmoothActual';$cpp=Join-Path $t 'support\upl_gpu_perm_actual_r1.cpp';$oldCpp=$cpp;$note=Join-Path $t 'notes\upl_gpu_perm_actual_r1.json';$exeLeaf='upl_gpu_perm_actual_r1.exe';$extra=@(E $native;E $nativeNote)}
  'WallActual' {$token='wall_actual';$oldPath=Join-Path $logs ('upl_gpu_perm_variable_actual_'+$Configuration+'_r1.helper.json');$oldFixture='SmoothActual';$oldCpp=Join-Path $t 'support\upl_gpu_perm_actual_r1.cpp';$cpp=Join-Path $t 'support\upl_gpu_wall_actual_r1.cpp';$note=Join-Path $t 'notes\upl_gpu_wall_actual_r1.json';$exeLeaf='upl_gpu_wall_actual_r1.exe';$extra=@(E $native;E $nativeNote)}
}
$h=J $oldPath;if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne $oldFixture -or $h.configuration -ne $Configuration){throw 'Immutable chosen helper recipe differs'}
V $h.inputs;V $h.author_files;V $h.tools;V $h.libraries;V @($h.source_build,$h.program,$h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}
$oldGpu=J $h.source_build.path;$cc=J $h.compile_call.path;$lc=J $h.link_call.path;V @($cc.program,$cc.log,$lc.program,$lc.log)
if(!$cc.owned_call_exited -or !$lc.owned_call_exited -or $cc.exit_code -ne 0 -or $lc.exit_code -ne 0 -or @($oldGpu.objects).Count -ne 110 -or !$oldGpu.objects_exclude_main){throw 'Old successful argument/object inventory required'}
if($expectedInclude){if((E $includeCpp).sha256 -cne $expectedInclude){throw 'Immutable transitive Time source changed'}}elseif((E $native).sha256 -cne 'b112f7e78651dde136c2438a02f326522ef4cb35b5603fa1eb17ee24d3437857'){throw 'Immutable typed Native include changed'}
$oldSourceRows=@($h.author_files|Where-Object {$_.path -ieq $oldCpp});if($oldSourceRows.Count -ne 1){throw 'Old compiler source binding not unique'};V $oldSourceRows
$name='upl_gpu_wall_'+$token+'_'+$Configuration+'_r1';$folder=Join-Path $out $name;$record=Join-Path $logs ($name+'.helper.json');foreach($p in @($folder,$record)){if(Test-Path -LiteralPath $p){throw 'Retained helper protected'}}
$author=@(E $PSCommandPath;E $buildNote;E $cpp;E $note)+$extra;$inputs=$author+@(E $stagePath;E $gpuPath;E $oldPath)
$oldInt=[IO.Path]::GetFullPath($oldGpu.no_space_IntDir).TrimEnd('\')+'\';$newInt=[IO.Path]::GetFullPath($g.no_space_IntDir).TrimEnd('\')+'\';if($oldInt -ieq $newInt -or $newInt -match '\s'){throw 'Fresh isolated no-space object directory required'}
$oldObjects=@{};$newObjects=@{};foreach($r in $oldGpu.objects){$n=[IO.Path]::GetFileName($r.path);if($oldObjects.ContainsKey($n) -or [IO.Path]::GetFullPath($r.path) -ine (Join-Path $oldInt $n)){throw 'Old non-flat/duplicate object inventory'};$oldObjects[$n]=$r}
foreach($r in $g.objects){$n=[IO.Path]::GetFileName($r.path);if($newObjects.ContainsKey($n) -or !$oldObjects.ContainsKey($n) -or [IO.Path]::GetFullPath($r.path) -ine (Join-Path $newInt $n)){throw 'New object basename closure differs'};$newObjects[$n]=$r}
$obj=Join-Path $folder 'helper.obj';$oldObj=Join-Path (Split-Path -Parent $h.program.path) 'helper.obj';$exe=Join-Path $folder $exeLeaf
$ca=@();$fo=0;$fd=0;$src=0;foreach($a in $cc.arguments){if($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq $oldCpp){$ca+=$cpp;$src++}else{$ca+=$a}}
if($fo -ne 1 -or $fd -ne 1 -or $src -ne 1){throw 'Only exact source/Fo/Fd compiler substitutions permitted'}
$la=@();$on=0;$pn=0;$hn=0;$gn=0;$mapped=@{};foreach($a in $lc.arguments){
  if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$on++}
  elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $folder 'link.pdb');$pn++}
  elseif($a -ieq $oldObj){$la+=$obj;$hn++}
  elseif($a.StartsWith($oldInt,[StringComparison]::OrdinalIgnoreCase)){$n=[IO.Path]::GetFileName($a);if(!$oldObjects.ContainsKey($n) -or $mapped.ContainsKey($n) -or $a -ine $oldObjects[$n].path){throw 'Unexpected/duplicate old GPU link object'};$la+=$newObjects[$n].path;$mapped[$n]=$true;$gn++}
  else{$la+=$a}
}
if($on -ne 1 -or $hn -ne 1 -or $gn -ne 110 -or $pn -ne $(if($Configuration -eq 'Debug'){1}else{0})){throw 'Unexpected linker substitution set'}
$actual=@($la|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)}|ForEach-Object {[IO.Path]::GetFullPath($_).ToLowerInvariant()});$expected=@($obj.ToLowerInvariant())+@($g.objects|ForEach-Object {[IO.Path]::GetFullPath($_.path).ToLowerInvariant()})
if($actual.Count -ne 111 -or @($actual|Sort-Object -Unique).Count -ne 111 -or @(Compare-Object @($actual|Sort-Object) @($expected|Sort-Object)).Count){throw 'Exact110 current authoritative objects plus one fixture required'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder);$compile=Call $cc.program $ca ($name+'_compile');$link=Call $lc.program $la ($name+'_link')
$runtime=@();foreach($r in $g.runtime){$p=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $p;$v=E $p;if($v.sha256 -ne $r.copy.sha256){throw 'New helper runtime differs'};$runtime+=@{original=$r.copy;copy=$v}}
VerifyCurrent;V $inputs;V $h.tools;V $h.libraries
Save $record ([ordered]@{status='actual_authoritative_GPU_objects_helper_linked_not_run';fixture=$Fixture;configuration=$Configuration;source_build=(E $gpuPath);prerequisite_stage=(E $stagePath);baseline=$g.baseline;inputs=$inputs;author_files=$author;author_files_frozen_by_hash_only=$true;transitive_project_include_files=$source.source;transitive_author_include_files=$extra;additional_author_source_copies_made=0;runtime=$runtime;program=(E $exe);tools=$h.tools;libraries=$h.libraries;objects=$g.objects;helper_object=(E $obj);link_object_count=111;exact_link_closure_verified=$true;compile_call=$compile;link_call=$link;replayed_helper=(E $oldPath);old_object_source_build=$h.source_build;compiler_source_remaps=$(if($Fixture -in 'Component','WallActual'){1}else{0});compiler_output_remaps=2;GPU_object_substitutions=110;only_chosen_helper_author_files_frozen=$true;other_helper_inputs_bound=$false;canonical_GPU_unchanged=$true;historical_source_paths_revalidated_as_current=$false;HEAD_equality_required=$false;mutable_validation_status_bound=$false;program_or_component_run=$false;physical_acceptance=$false})


