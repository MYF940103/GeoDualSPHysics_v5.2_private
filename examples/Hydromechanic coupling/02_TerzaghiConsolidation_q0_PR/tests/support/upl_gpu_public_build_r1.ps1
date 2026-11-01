param([Parameter(Mandatory=$true)][ValidateSet('Baseline','Build')][string]$Mode,[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# One explicit baseline/build action only. No helper, help, solver, GenCase, install or Git mutation.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$base='b499bc1fc5d5fb37d590563f8aba189494c0df3c'
$note=Join-Path $t 'notes\upl_gpu_public_build_r1.json';$plan=Join-Path $t 'notes\upl_gpu_public_plan_r1.md'
$baselinePath=Join-Path $logs 'upl_gpu_public_r1.baseline.json';$backup=Join-Path $out 'upl_gpu_public_source_base_r1'
$acceptedPath=Join-Path $logs 'upl_gpu_wall_stage_r1.check.json';$targets=@('JSph.h','JSph.cpp','JSphGpu.cpp','JSphGpuSingle.cpp')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText((ResolveArtifactPath $p))|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,[string]$label){
 V @($tool);$p=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($f in @($p,$log)){if(Test-Path -LiteralPath $f){throw 'Owned build retained'}}
 [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference;$ErrorActionPreference='Continue'
 Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
 V @($tool);Save $p ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);program_or_component_run=$false;physical_acceptance=$false})
 if($code){throw 'Build failed; retain evidence'};E $p
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root full review and explicit one baseline/build action authorization required'}
$oldPreference=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$oldPreference
if($code -or $head -cne $base){throw 'Exact verified b499bc1 wall checkpoint required'}
$accepted=J $acceptedPath
if($accepted.passed -ne $true -or $accepted.wall_implementation_verified_within_private_scope -ne $true -or $accepted.public_GPU_dynamic_accepted -ne $false -or $accepted.physical_acceptance -ne $false){throw 'Verified private wall stage with public/physical admission held required'}
# Read immutable old receipts, not their historically mutable source paths as new current identities.
$oldBuildPaths=@{};$oldBuilds=@{};$oldSources=@{};$controls=@()
foreach($cfg in 'Debug','Release'){
 $p=Join-Path $logs ('upl_gpu_wall_'+$cfg+'_r1.build.json');$g=J $p
 if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $cfg -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main){throw 'Retained authoritative wall build required'}
 V @($g.source_freeze,$g.project_call,$g.isolated_GPU_program);V $g.tools;$s=J $g.source_freeze.path;if(@($s.source).Count -ne 265){throw 'Retained265-source closure differs'}
 $oldBuildPaths[$cfg]=$p;$oldBuilds[$cfg]=$g;$oldSources[$cfg]=$s
 foreach($r in $g.runtime){V @($r.original,$r.copy)}
 $controls+=@{role='private_wall_isolated_main';configuration=$cfg;receipt=(E $p);source_build=(E $p);program=$g.isolated_GPU_program;runtime=$g.runtime}
 $hp=Join-Path $logs ('upl_gpu_wall_wall_actual_'+$cfg+'_r2.helper.json');$h=J $hp
 if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'WallActual' -or $h.configuration -ne $cfg -or $h.link_object_count -ne 111 -or !$h.exact_link_closure_verified){throw 'Retained real-wall control helper required'}
 V @($h.source_build,$h.program,$h.compile_call,$h.link_call);if($h.source_build.sha256 -ine (E $p).sha256){throw 'Wall helper and main source builds differ'}
 foreach($r in $h.runtime){V @($r.original,$r.copy)}
 $controls+=@{role='private_wall_actual_helper';configuration=$cfg;receipt=(E $hp);source_build=$h.source_build;program=$h.program;runtime=$h.runtime}
}
$oldSource=@($oldSources.Debug.source)
foreach($r in $oldSources.Release.source){$same=@($oldSource|Where-Object {$_.path -ceq $r.path -and $_.bytes -eq $r.bytes -and $_.sha256 -ceq $r.sha256});if($same.Count -ne 1){throw 'Historical Debug/Release source inventories differ'}}
$other=@($oldSource|Where-Object {[IO.Path]::GetFileName($_.path) -notin $targets});$oldTargets=@($oldSource|Where-Object {[IO.Path]::GetFileName($_.path) -in $targets})
if($other.Count -ne 261 -or $oldTargets.Count -ne 4){throw 'Four-target/261-unchanged split differs'};V $other
$inheritedBaseline=J $oldBuilds.Debug.baseline.path;V $inheritedBaseline.canonical_GPU
$canonical=@($inheritedBaseline.canonical_GPU);$canonicalNames=@('DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2_GEO_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll')
if($canonical.Count -ne 6){throw 'Six protected canonical GPU artifacts required'}
foreach($name in $canonicalNames){if(@($canonical|Where-Object {[IO.Path]::GetFileName($_.path) -ceq $name}).Count -ne 1){throw 'Canonical GPU explicit name whitelist differs'}}
$projects=@($inheritedBaseline.inputs|Where-Object {$_.path -match '\.(sln|vcxproj)$'});if($projects.Count -ne 2){throw 'Authoritative solution/project identities missing'};V $projects
if($Mode -eq 'Baseline'){
 foreach($p in @($baselinePath,$backup)){if(Test-Path -LiteralPath $p){throw 'Retained baseline/source copies protected'}}
 # This action MUST precede all four source edits. Compare actual raw source to sealed wall raw source, not filtered Git blobs.
 V $oldSource;$current=@();foreach($r in $oldTargets){$current+=E $r.path}
 [void](New-Item -ItemType Directory -Path $backup);$copies=@()
 foreach($r in $current){$destination=Join-Path $backup ([IO.Path]::GetFileName($r.path));Copy-Item -LiteralPath $r.path -Destination $destination;$copy=E $destination;if($copy.bytes -ne $r.bytes -or $copy.sha256 -cne $r.sha256){throw 'Raw baseline source copy differs'};$copies+=@{original=$r;copy=$copy}}
 V $oldSource;V $canonical
 Save $baselinePath ([ordered]@{status='raw_four_targets_copied_before_public_wiring_edits';git_base=$base;accepted_private_wall_stage=(E $acceptedPath);inputs=@(E $PSCommandPath;E $note;E $plan;E $acceptedPath;E $oldBuildPaths.Debug;E $oldBuildPaths.Release)+@($controls|ForEach-Object {$_.receipt})+$projects;source_control_receipts=@($oldBuilds.Debug.source_freeze,$oldBuilds.Release.source_freeze);base_source=$oldSource;four_raw_base_targets=$current;target_copies=$copies;other_source=$other;canonical_GPU=$canonical;compiled_private_wall_controls=$controls;historical_target_original_paths_not_revalidated_after_edit=$true;raw_hash_not_compared_to_filtered_Git_blob=$true;source_backup_copies_made=4;program_backup_copies_made=0;mutable_validation_status_or_doc_bound=$false;program_or_component_run=$false;public_GPU_dynamic_accepted=$false;physical_acceptance=$false})
 exit 0
}
if(!(Test-Path -LiteralPath $baselinePath)){throw 'Explicit raw-source Baseline action required before Build'}
$b=J $baselinePath;if($b.git_base -cne $base -or $b.status -ne 'raw_four_targets_copied_before_public_wiring_edits' -or @($b.target_copies).Count -ne 4){throw 'Public raw baseline differs'}
V $b.inputs;V $b.source_control_receipts;V $b.other_source;V $b.canonical_GPU
foreach($r in $b.target_copies){V @($r.copy)}
foreach($control in $b.compiled_private_wall_controls){V @($control.receipt,$control.source_build,$control.program);foreach($r in $control.runtime){V @($r.original,$r.copy)}}
$oldBuildPath=$oldBuildPaths[$Configuration];$oldGpu=$oldBuilds[$Configuration];$oldCall=J $oldGpu.project_call.path;V @($oldCall.program,$oldCall.log)
if(!$oldCall.owned_call_exited -or $oldCall.exit_code -ne 0 -or $oldCall.arguments -notcontains '/t:Rebuild'){throw 'Successful authoritative full Rebuild vector required'}
if($Configuration -eq 'Release'){$d=J (Join-Path $logs 'upl_gpu_public_Debug_r1.build.json');if($d.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run'){throw 'Fresh Debug build required before Release'};V $d.inputs;V @($d.project_call,$d.isolated_GPU_program,$d.source_freeze)}
$source=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl','.cpp','.cu'}|Sort-Object FullName|ForEach-Object {E $_.FullName});if($source.Count -ne 265){throw 'Current265-source closure differs'}
$newTargets=@($source|Where-Object {[IO.Path]::GetFileName($_.path) -in $targets});if($newTargets.Count -ne 4){throw 'Current four-target inventory differs'}
$name='upl_gpu_public_'+$Configuration+'_r1';$folder=Join-Path $out $name;$freeze=Join-Path $logs ($name+'.source.json');$record=Join-Path $logs ($name+'.build.json')
$int=Join-Path ([IO.Path]::GetTempPath()) ('upl_gpu_public_r1\'+$Configuration+'\int\');if($int -match '\s'){throw 'CUDA IntDir must have no spaces'}
foreach($p in @($folder,$int,$freeze,$record)){if(Test-Path -LiteralPath $p){throw 'Retained build protected; use a new reviewed label'}}
$inputs=@(E $PSCommandPath;E $note;E $plan;E $baselinePath;E $acceptedPath;E $oldBuildPath)+$source+$projects
Save $freeze ([ordered]@{status='bounded_public_GPU_wiring_source_frozen_before_authoritative_build';git_base=$base;baseline=(E $baselinePath);source=$source;four_targets=$newTargets;unchanged_source_count=261;accepted_private_wall_stage=(E $acceptedPath);inputs=$inputs;mutable_validation_status_or_doc_bound=$false;raw_base_target_copies_bound=$true;new_source_or_program_backup_copies_made=0;public_GPU_dynamic_accepted=$false;physical_acceptance=$false})
[void](New-Item -ItemType Directory -Path $folder);[void](New-Item -ItemType Directory -Path $int);$gpuout=Join-Path $folder 'gpu\';[void](New-Item -ItemType Directory -Path $gpuout)
$arguments2=@();$replaced=0
foreach($a in $oldCall.arguments){if($a.StartsWith('/p:OutDir=',[StringComparison]::OrdinalIgnoreCase)){$arguments2+='/p:OutDir='+$gpuout.Replace('\','/');$replaced++}elseif($a.StartsWith('/p:IntDir=',[StringComparison]::OrdinalIgnoreCase)){$arguments2+='/p:IntDir='+$int.Replace('\','/');$replaced++}elseif($a.StartsWith('/bl:',[StringComparison]::OrdinalIgnoreCase)){$arguments2+='/bl:'+(Join-Path $logs ($name+'.binlog'));$replaced++}else{$arguments2+=$a}}
if($replaced -ne 3){throw 'Exactly OutDir/IntDir/binlog build path remaps permitted'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$call=Call $oldCall.program $arguments2 ($name+'_project');$objects=@($oldGpu.objects|ForEach-Object {E (Join-Path $int ([IO.Path]::GetFileName($_.path)))});if($objects.Count -ne 110){throw '110 authoritative objects excluding main required'}
$runtime=@();foreach($r in $oldGpu.runtime){V @($r.original,$r.copy);$p=Join-Path $gpuout ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $p;$v=E $p;if($v.sha256 -ne $r.copy.sha256){throw 'New runtime copy differs'};$runtime+=@{original=$r.copy;copy=$v}}
V $inputs;V $b.other_source;V $b.canonical_GPU;V $oldGpu.tools
foreach($control in $b.compiled_private_wall_controls){V @($control.receipt,$control.source_build,$control.program);foreach($r in $control.runtime){V @($r.original,$r.copy)}}
$exe=Join-Path $gpuout ([IO.Path]::GetFileName($oldGpu.isolated_GPU_program.path))
Save $record ([ordered]@{status='full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run';configuration=$Configuration;git_base=$base;baseline=(E $baselinePath);source_freeze=(E $freeze);inputs=$inputs;tools=$oldGpu.tools;objects=$objects;objects_exclude_main=$true;project_call=$call;isolated_GPU_program=(E $exe);runtime=$runtime;no_space_IntDir=$int;isolated_GPU_OutDir=$gpuout;replayed_build=(E $oldBuildPath);remapped_GPU_arguments=3;canonical_GPU_unchanged=$true;compiled_private_wall_controls_unchanged=$true;source_or_program_backup_copies_made=0;bounded_public_GPU_wiring_candidate_build_only=$true;default_CPU_Debug_build_is_root_separate_requirement=$true;public_GPU_dynamic_accepted=$false;program_or_component_run=$false;physical_acceptance=$false})
