param([ValidateSet('BuildActual')][string]$Mode='BuildActual',[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Compile/link one component only. No program/help, solver, worker, or Git call.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$stagePath=Join-Path $logs 'upl_gpu_k0_actual_stage_r2.check.json'
$cpp=Join-Path $t 'support\upl_gpu_darcy_actual_r1.cpp';$note=Join-Path $t 'notes\upl_gpu_darcy_actual_r1.json';$buildNote=Join-Path $t 'notes\upl_gpu_darcy_actual_build_r1.json'
$included=Join-Path $t 'support\upl_gpu_observer_native_r1.cpp';$includedNote=Join-Path $t 'notes\upl_gpu_observer_native_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((ResolveArtifactPath $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,[string]$label){
  V @($tool);$p=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');if((Test-Path -LiteralPath $p) -or (Test-Path -LiteralPath $log)){throw 'Owned compile/link retained'}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$old}
  V @($tool);Save $p ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);program_or_component_run=$false;physical_acceptance=$false});if($code){throw 'Compile/link failed; preserve evidence'};E $p
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root complete source/fixture review and explicit single-build authorization required'}
# Bind the accepted aggregate itself, not its recursive historical/mutable author-status graph.
$stage=J $stagePath;if(!$stage.passed -or !$stage.successful_Debug_Pre_Corr_smoke -or $stage.public_GPU_dynamic_accepted -or $stage.physical_acceptance -or $stage.nonzero_k_tested){throw 'Accepted bounded k0 actual stage required'}
$gpuPath=Join-Path $logs ('upl_gpu_darcy_'+$Configuration+'_r2.build.json');$g=J $gpuPath
if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $Configuration -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main -or !$g.private_constant_k_Darcy_candidate_build_only){throw 'Fresh authoritative Darcy r2 GPU objects required'}
V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program);foreach($r in $g.runtime){V @($r.original,$r.copy)}
$project=J $g.project_call.path;if(!$project.owned_call_exited -or $project.exit_code -ne 0 -or $project.arguments -notcontains '/t:Rebuild'){throw 'Owned successful full Rebuild required'};V @($project.program,$project.log)
$source=J $g.source_freeze.path;V $source.source;V $source.five_targets
$five=@('JSphGpu.h','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')
if(@($source.source).Count -ne 265 -or @($source.five_targets).Count -ne 5 -or @($source.five_targets|Where-Object {[IO.Path]::GetFileName($_.path) -notin $five}).Count){throw 'Frozen five-target/265-source closure differs'}
$baseline=J $g.baseline.path;V $baseline.inputs;V $baseline.other_source;V $baseline.canonical_GPU
if(@($baseline.other_source).Count -ne 260 -or $source.baseline.sha256 -ine $g.baseline.sha256 -or $source.accepted_actual_stage.sha256 -ine (E $stagePath).sha256){throw 'Immutable baseline or accepted-stage binding differs'}
# Reuse only immutable argument recipes. Do NOT revalidate their old five source paths against current files.
$oldPath=Join-Path $logs ('upl_gpu_k0_time_component_'+$Configuration+'_r1.helper.json');$h=J $oldPath
if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'Time' -or $h.configuration -ne $Configuration){throw 'Retained Time compile/link recipe required'}
V $h.inputs;V $h.author_files;V $h.tools;V $h.libraries;V @($h.source_build,$h.program,$h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}
$oldg=J $h.source_build.path;if($oldg.configuration -ne $Configuration -or @($oldg.objects).Count -ne 110 -or !$oldg.objects_exclude_main){throw 'Retained source-build object inventory differs'}
$cc=J $h.compile_call.path;$lc=J $h.link_call.path;V @($cc.program,$cc.log,$lc.program,$lc.log)
if(!$cc.owned_call_exited -or !$lc.owned_call_exited -or $cc.exit_code -ne 0 -or $lc.exit_code -ne 0){throw 'Retained compile/link calls did not pass'}
$oldInt=[IO.Path]::GetFullPath($oldg.no_space_IntDir).TrimEnd('\')+'\';$newInt=[IO.Path]::GetFullPath($g.no_space_IntDir).TrimEnd('\')+'\'
if($oldInt -ieq $newInt -or $newInt -match '\s'){throw 'New isolated no-space object directory required'}
$oldObjects=@{};$newObjects=@{};foreach($r in $oldg.objects){$n=[IO.Path]::GetFileName($r.path);if($oldObjects.ContainsKey($n) -or [IO.Path]::GetFullPath($r.path) -ine (Join-Path $oldInt $n)){throw 'Old object closure is not unique/flat'};$oldObjects[$n]=$r}
foreach($r in $g.objects){$n=[IO.Path]::GetFileName($r.path);if($newObjects.ContainsKey($n) -or !$oldObjects.ContainsKey($n) -or [IO.Path]::GetFullPath($r.path) -ine (Join-Path $newInt $n)){throw 'New object closure is not the exact old basename set'};$newObjects[$n]=$r}
$name='upl_gpu_darcy_actual_'+$Configuration+'_r1';$folder=Join-Path $out $name;$record=Join-Path $logs ($name+'.helper.json');foreach($p in @($folder,$record)){if(Test-Path -LiteralPath $p){throw 'Retained component helper protected'}}
$author=@(E $PSCommandPath;E $buildNote;E $cpp;E $note;E $included;E $includedNote);$inputs=$author+@(E $stagePath;E $gpuPath;E $oldPath)
if((E $included).sha256 -ne 'b112f7e78651dde136c2438a02f326522ef4cb35b5603fa1eb17ee24d3437857'){throw 'Immutable included typed Native reader changed'}
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder 'upl_gpu_darcy_actual_r1.exe';$oldFolder=Split-Path -Parent $h.program.path;$oldObj=Join-Path $oldFolder 'helper.obj';$oldCpp=Join-Path $t 'support\upl_gpu_k0_time_r1.cpp'
$ca=@();$fo=0;$fd=0;$src=0;foreach($a in $cc.arguments){if($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq $oldCpp){$ca+=$cpp;$src++}else{$ca+=$a}}
if($fo -ne 1 -or $fd -ne 1 -or $src -ne 1){throw 'Only source/Fo/Fd compiler substitutions permitted'}
$la=@();$on=0;$pdb=0;$hn=0;$gn=0;$mapped=@{}
foreach($a in $lc.arguments){
  if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$on++}
  elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $folder 'link.pdb');$pdb++}
  elseif($a -ieq $oldObj){$la+=$obj;$hn++}
  elseif($a.StartsWith($oldInt,[StringComparison]::OrdinalIgnoreCase)){$n=[IO.Path]::GetFileName($a);if(!$oldObjects.ContainsKey($n) -or !$newObjects.ContainsKey($n) -or $mapped.ContainsKey($n) -or $a -ine $oldObjects[$n].path){throw 'Unexpected/duplicate old GPU link object'};$la+=$newObjects[$n].path;$mapped[$n]=$true;$gn++}
  else{$la+=$a}
}
if($on -ne 1 -or $hn -ne 1 -or $gn -ne 110 -or $pdb -ne $(if($Configuration -eq 'Debug'){1}else{0})){throw 'Unexpected linker substitution set'}
$actualObj=@($la|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)}|ForEach-Object {[IO.Path]::GetFullPath($_).ToLowerInvariant()})
$expectedObj=@($obj.ToLowerInvariant())+@($g.objects|ForEach-Object {[IO.Path]::GetFullPath($_.path).ToLowerInvariant()})
if($actualObj.Count -ne 111 -or @($actualObj|Sort-Object -Unique).Count -ne 111 -or @(Compare-Object ($expectedObj|Sort-Object) ($actualObj|Sort-Object)).Count){throw 'Link must contain exactly one helper plus all 110 current authoritative objects'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder);$compile=Call $cc.program $ca ($name+'_compile');$link=Call $lc.program $la ($name+'_link')
$runtime=@();foreach($r in $g.runtime){$p=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $p;$v=E $p;if($v.sha256 -ne $r.copy.sha256){throw 'Component runtime differs'};$runtime+=@{original=$r.copy;copy=$v}}
V $inputs;V $g.inputs;V $g.objects;V $g.tools;V $h.tools;V $h.libraries;V $source.source;V $baseline.other_source;V $baseline.canonical_GPU;foreach($r in $g.runtime){V @($r.original,$r.copy)}
Save $record ([ordered]@{status='actual_authoritative_GPU_objects_helper_linked_not_run';fixture='DarcyActual';configuration=$Configuration;source_build=(E $gpuPath);prerequisite_stage=(E $stagePath);baseline=$g.baseline;inputs=$inputs;author_files=$author;author_files_frozen_by_hash_only=$true;transitive_project_include_files=$source.source;additional_author_source_copies_made=0;runtime=$runtime;program=(E $exe);tools=$h.tools;libraries=$h.libraries;objects=$g.objects;helper_object=(E $obj);link_object_count=111;exact_link_closure_verified=$true;compile_call=$compile;link_call=$link;replayed_helper=(E $oldPath);old_object_source_build=$h.source_build;compiler_source_remaps=1;compiler_output_remaps=2;GPU_object_substitutions=110;GPU_object_directory_changed=$true;only_chosen_helper_author_files_frozen=$true;other_helper_inputs_bound=$false;canonical_GPU_unchanged=$true;HEAD_equality_required=$false;historical_source_paths_revalidated_as_current=$false;mutable_validation_status_bound=$false;program_or_component_run=$false;physical_acceptance=$false})
