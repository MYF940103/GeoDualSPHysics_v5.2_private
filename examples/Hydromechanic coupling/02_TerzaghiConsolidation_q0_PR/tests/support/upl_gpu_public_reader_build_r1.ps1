param([ValidateSet('BuildReader')][string]$Mode='BuildReader',[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Build exactly one offline Reader. Never execute it, a helper, help or a solver.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$base='b499bc1fc5d5fb37d590563f8aba189494c0df3c'
$buildNote=Join-Path $t 'notes\upl_gpu_public_reader_build_r1.json';$cpp=Join-Path $t 'support\upl_gpu_public_native_r1.cpp';$readerNote=Join-Path $t 'notes\upl_gpu_public_native_r1.json';$includeCpp=Join-Path $t 'support\upl_cpu_public_native_r1.cpp'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((ResolveArtifactPath $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,[string]$label){
  V @($tool);$receipt=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($p in @($receipt,$log)){if(Test-Path -LiteralPath $p){throw 'Owned compile/link retained'}}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$preference=$ErrorActionPreference;$ErrorActionPreference='Continue'
  Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$preference}
  V @($tool);Save $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);program_or_component_run=$false;physical_acceptance=$false})
  if($code){throw 'Reader compile/link failed; preserve evidence'};E $receipt
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root full reader/source review and explicit one-configuration build authorization required'}
$gpuPath=Join-Path $logs ('upl_gpu_public_'+$Configuration+'_r1.build.json');$g=J $gpuPath
if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $Configuration -or $g.git_base -cne $base -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main -or !$g.bounded_public_GPU_wiring_candidate_build_only){throw 'Current authoritative public-GPU Rebuild required'}
$source=J $g.source_freeze.path;$baseline=J $g.baseline.path;$four=@('JSph.h','JSph.cpp','JSphGpu.cpp','JSphGpuSingle.cpp')
if(@($source.source).Count -ne 265 -or @($source.four_targets).Count -ne 4 -or $source.unchanged_source_count -ne 261 -or @($baseline.other_source).Count -ne 261 -or @($baseline.canonical_GPU).Count -ne 6 -or @($baseline.target_copies).Count -ne 4 -or @(Compare-Object $four @($source.four_targets|ForEach-Object {[IO.Path]::GetFileName($_.path)})).Count -or $source.baseline.sha256 -ine $g.baseline.sha256 -or $baseline.git_base -cne $base){throw 'Four/261/265 source or protected-six closure differs'}
function VerifyCurrent {
  V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program);V $source.source;V $source.four_targets
  V $baseline.inputs;V $baseline.source_control_receipts;V $baseline.other_source;V $baseline.canonical_GPU
  foreach($r in $baseline.target_copies){V @($r.copy)} # Raw base targets' original paths changed deliberately; only their sealed copies remain current evidence.
  foreach($r in $g.runtime){V @($r.original,$r.copy)}
}
VerifyCurrent;$project=J $g.project_call.path;V @($project.program,$project.log)
if(!$project.owned_call_exited -or $project.exit_code -ne 0 -or $project.arguments -notcontains '/t:Rebuild'){throw 'Owned full authoritative Rebuild required'}
# Reuse this non-CNG SmoothActual argument recipe, NOT WallActual's bcrypt helper.
$oldPath=Join-Path $logs ('upl_gpu_wall_variable_actual_'+$Configuration+'_r1.helper.json');$h=J $oldPath;$oldCpp=Join-Path $t 'support\upl_gpu_perm_actual_r1.cpp'
if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'SmoothActual' -or $h.configuration -ne $Configuration -or $h.link_object_count -ne 111 -or !$h.exact_link_closure_verified){throw 'Retained successful non-CNG SmoothActual recipe required'}
V $h.inputs;V $h.author_files;V $h.tools;V $h.libraries;V @($h.source_build,$h.program,$h.compile_call,$h.link_call)
$oldGpu=J $h.source_build.path;$cc=J $h.compile_call.path;$lc=J $h.link_call.path;V @($cc.program,$cc.log,$lc.program,$lc.log)
if(!$cc.owned_call_exited -or !$lc.owned_call_exited -or $cc.exit_code -ne 0 -or $lc.exit_code -ne 0 -or @($oldGpu.objects).Count -ne 110 -or !$oldGpu.objects_exclude_main -or @($lc.arguments|Where-Object {[IO.Path]::GetFileName($_) -ieq 'bcrypt.lib'}).Count){throw 'Successful non-CNG compile/link/object recipe differs'}
$oldSourceRows=@($h.author_files|Where-Object {$_.path -ieq $oldCpp});if($oldSourceRows.Count -ne 1){throw 'Old compiler source binding not unique'};V $oldSourceRows
# No traversal into historical GPU source inventories: their four original target paths are not current after public edits.
$expectedAuthor=@(
  @{path=$cpp;bytes=17784;sha256='f1ffa24f3cb002285698fd85f3082617c10bbb4cb6a8eb3c81a5f0dd6f5145f0'},
  @{path=$readerNote;bytes=6960;sha256='bbb34b0b36a3f08e1a824501ff14e261ce5670f953a7b93d29e73622a1f639f1'},
  @{path=$includeCpp;bytes=22469;sha256='9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38'}
);V $expectedAuthor
$name='upl_gpu_public_reader_'+$Configuration+'_r1';$folder=Join-Path $out $name;$record=Join-Path $logs ($name+'.helper.json');foreach($p in @($folder,$record)){if(Test-Path -LiteralPath $p){throw 'Retained reader protected'}}
$author=@(E $PSCommandPath;E $buildNote;E $cpp;E $readerNote;E $includeCpp);$inputs=$author+@(E $gpuPath;E $oldPath)
$oldInt=[IO.Path]::GetFullPath($oldGpu.no_space_IntDir).TrimEnd('\')+'\';$newInt=[IO.Path]::GetFullPath($g.no_space_IntDir).TrimEnd('\')+'\';if($oldInt -ieq $newInt -or $newInt -match '\s'){throw 'Fresh current no-space GPU IntDir required'}
$oldObjects=@{};$newObjects=@{};foreach($r in $oldGpu.objects){$n=[IO.Path]::GetFileName($r.path);if($oldObjects.ContainsKey($n) -or [IO.Path]::GetFullPath($r.path) -ine (Join-Path $oldInt $n)){throw 'Old duplicate/non-flat object inventory'};$oldObjects[$n]=$r}
foreach($r in $g.objects){$n=[IO.Path]::GetFileName($r.path);if($newObjects.ContainsKey($n) -or !$oldObjects.ContainsKey($n) -or [IO.Path]::GetFullPath($r.path) -ine (Join-Path $newInt $n)){throw 'Current GPU object basename closure differs'};$newObjects[$n]=$r}
$obj=Join-Path $folder 'helper.obj';$oldObj=Join-Path (Split-Path -Parent $h.program.path) 'helper.obj';$exe=Join-Path $folder 'upl_gpu_public_native_r1.exe'
$ca=@();$fo=0;$fd=0;$src=0;foreach($a in $cc.arguments){if($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq $oldCpp){$ca+=$cpp;$src++}else{$ca+=$a}}
if($fo -ne 1 -or $fd -ne 1 -or $src -ne 1 -or $ca -notcontains '/std:c++17'){throw 'Only exact source/Fo/Fd compiler substitutions permitted'}
$la=@();$on=0;$pn=0;$hn=0;$gn=0;$mapped=@{};foreach($a in $lc.arguments){
  if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$on++}
  elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $folder 'link.pdb');$pn++}
  elseif($a -ieq $oldObj){$la+=$obj;$hn++}
  elseif($a.StartsWith($oldInt,[StringComparison]::OrdinalIgnoreCase)){$n=[IO.Path]::GetFileName($a);if(!$oldObjects.ContainsKey($n) -or $mapped.ContainsKey($n) -or $a -ine $oldObjects[$n].path){throw 'Unexpected/duplicate old GPU link object'};$la+=$newObjects[$n].path;$mapped[$n]=$true;$gn++}
  else{$la+=$a}
}
if($on -ne 1 -or $hn -ne 1 -or $gn -ne 110 -or $pn -ne $(if($Configuration -eq 'Debug'){1}else{0})){throw 'Unexpected linker substitution set'}
$actual=@($la|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)}|ForEach-Object {[IO.Path]::GetFullPath($_).ToLowerInvariant()});$expected=@($obj.ToLowerInvariant())+@($g.objects|ForEach-Object {[IO.Path]::GetFullPath($_.path).ToLowerInvariant()})
if($actual.Count -ne 111 -or @($actual|Sort-Object -Unique).Count -ne 111 -or @(Compare-Object @($actual|Sort-Object) @($expected|Sort-Object)).Count){throw 'Exact110 current GPU objects plus one reader object required'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder);$compile=Call $cc.program $ca ($name+'_compile');$link=Call $lc.program $la ($name+'_link')
$runtime=@();foreach($r in $g.runtime){$p=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $p;$v=E $p;if($v.bytes -ne $r.copy.bytes -or $v.sha256 -ine $r.copy.sha256){throw 'New reader runtime differs'};$runtime+=@{original=$r.copy;copy=$v}}
VerifyCurrent;V $inputs;V $expectedAuthor;V $h.tools;V $h.libraries
Save $record ([ordered]@{status='actual_authoritative_GPU_objects_helper_linked_not_run';fixture='Reader';configuration=$Configuration;source_build=(E $gpuPath);source_freeze=$g.source_freeze;baseline=$g.baseline;inputs=$inputs;author_files=$author;author_files_frozen_by_hash_only=$true;transitive_project_include_files=$source.source;transitive_author_include_files=@(E $includeCpp);runtime=$runtime;program=(E $exe);tools=$h.tools;libraries=$h.libraries;objects=$g.objects;helper_object=(E $obj);link_object_count=111;exact_link_closure_verified=$true;compile_call=$compile;link_call=$link;replayed_helper=(E $oldPath);old_object_source_build=$h.source_build;compiler_source_remaps=1;compiler_output_remaps=2;GPU_object_substitutions=110;GPU_object_directory_changed=$true;four_target_261_unchanged_265_source_verified=$true;protected_canonical_GPU_count=6;canonical_GPU_unchanged=$true;historical_source_paths_revalidated_as_current=$false;additional_source_or_program_copies_made=0;mutable_validation_status_bound=$false;reader_execution_backend_relabelled_as_CPU=$false;offline_reader_only=$true;program_or_component_run=$false;public_GPU_dynamic_accepted=$false;physical_acceptance=$false})
