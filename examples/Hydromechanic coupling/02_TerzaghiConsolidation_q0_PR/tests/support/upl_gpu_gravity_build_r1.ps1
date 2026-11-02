param([Parameter(Mandatory=$true)][ValidateSet('Debug','Release')][string]$Configuration,[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# One authoritative isolated GPU Rebuild only; no baseline action, helper or executable invocation.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t -Force).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$base='c476f81e07fda919fe3270fa9085a665ee604496'
$note=Join-Path $t 'notes\upl_gpu_gravity_build_r1.json';$verifiedPath=Join-Path $logs 'upl_porosity_operator_publish_r1.verified.json'
$cpuPath=Join-Path $logs 'upl_gpu_gravity_default_DebugCPU_r1.build.json';$wallPath=Join-Path $logs 'upl_gravity_wall_cpu_DebugCPU_r1.build.json'
$targetNames=@('JSphGpu.cpp','JSphGpu_ker.cu');$types=@('.h','.hpp','.inl','.cpp','.cu')
$expected=@(@{path=(Join-Path $repo 'src\source\JSphGpu.cpp');bytes=120270;sha256='36b9d10c5e6fdcd48b0a30b84d4041d1b3e1471c89d6a94e914a3ade1355320b'},@{path=(Join-Path $repo 'src\source\JSphGpu_ker.cu');bytes=301290;sha256='c0ac4a12eb789004db1869c7c533a788d9eef6fedf626b7c3506388b44758e0a'})
function E([string]$p){$f=Get-Item -LiteralPath $p -Force;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes-ne[long]$r.bytes-or$a.sha256-cne$r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function GitValue([string[]]$argv){
 $saved=$ErrorActionPreference;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;$lines=@(& git -C $repo @argv 2>&1);$code=$LASTEXITCODE;$ErrorActionPreference=$saved
 $value=@($lines|ForEach-Object {[string]$_}|Where-Object {$_-match'^[0-9a-f]{40}$'});if($code-isnot[int]-or$code-ne0-or$value.Count-ne1){throw 'Read-only Git identity failed'};$value[0]
}
function Call($tool,[string[]]$argv,[string]$name){
 $p=Join-Path $logs ($name+'.call.json');$log=Join-Path $logs ($name+'.log');foreach($f in @($p,$log)){if(Test-Path -LiteralPath $f){throw 'Owned build already retained'}}
 V @($tool);[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
 Push-Location (Join-Path $repo 'src');try{$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;if($code-isnot[int]){throw 'MSBuild did not return a native exit code'}}finally{Pop-Location;$ErrorActionPreference=$saved}
 V @($tool);Save $p ([ordered]@{program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=$true;owned_call_exited=$true;exit_code=$code;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);build_tool_only=$true;program_or_component_run=$false;physical_acceptance=$false});E $p
}
if(!$ProductionBuildConfirmed-or!$ExecutionAuthorized){throw 'Root full review and explicit single-configuration build authorization required'}
$verified=J $verifiedPath;if(!$verified.passed-or!$verified.local_remote_equal-or$verified.commit-cne$base-or$verified.production_changed-or$verified.physical_acceptance){throw 'Verified operator checkpoint required'}
if((GitValue @('rev-parse','HEAD'))-cne$base){throw 'Current reviewed c476f81 checkpoint required; no historical Git metadata file is revalidated as current'}
$cpu=J $cpuPath
if($cpu.exit_code-ne0-or!$cpu.owned_call_exited-or!$cpu.typed_LASTEXITCODE_captured_immediately-or!$cpu.source_hashes_unchanged-or$cpu.canonical_CPU_Debug_before.sha256-cne$cpu.canonical_CPU_Debug_after.sha256){throw 'Root-owned default CPU Debug gate required'}
V (@($cpu.program,$cpu.log,$cpu.canonical_CPU_Debug_before,$cpu.canonical_CPU_Debug_after)+@($cpu.targets));V $expected
$wall=J $wallPath;if(!$wall.passed-or@($wall.source).Count-ne271-or@($wall.current_source_snapshot).Count-ne271){throw 'Sealed wall source-directory snapshot required'}
$oldCode=@($wall.source|Where-Object {[IO.Path]::GetExtension($_.path)-in$types});$other=@($oldCode|Where-Object {[IO.Path]::GetFileName($_.path)-notin$targetNames})
$oldPairs=@($wall.current_source_snapshot|Where-Object {[IO.Path]::GetFileName($_.original.path)-in$targetNames})
if($oldCode.Count-ne265-or$other.Count-ne263-or$oldPairs.Count-ne2){throw 'Two-target/263-other code split differs'};V $other
$ancestry=@()
foreach($pair in $oldPairs){
 V @($pair.snapshot);$rel=$pair.original.path.Substring($repo.Length+1).Replace('\','/');$tree=GitValue @('rev-parse',($base+':'+$rel));$filtered=GitValue @('hash-object',("--path=$rel"),$pair.snapshot.path)
 if($tree-cne$filtered){throw 'Historical raw snapshot does not filter to the reviewed c476f81 target blob'};$ancestry+=@{source_path=$pair.original.path;retained_raw_snapshot=$pair.snapshot;committed_blob=$tree;snapshot_filtered_blob=$filtered}
}
$canonical=@($wall.protected_canonical_GPU_six_and_CPU_two)
if($canonical.Count-ne8-or@($canonical.path|Sort-Object -Unique).Count-ne8){throw 'Eight canonical GPU/CPU artifacts required'};V $canonical
$oldPath=Join-Path $logs ('upl_gpu_public_'+$Configuration+'_r1.build.json');$old=J $oldPath
if($old.status-ne'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run'-or$old.configuration-ne$Configuration-or@($old.objects).Count-ne110-or!$old.objects_exclude_main){throw 'Latest authoritative public-GPU build required'}
V @($old.baseline,$old.source_freeze,$old.project_call,$old.isolated_GPU_program);V $old.tools
foreach($r in $old.runtime){V @($r.original,$r.copy)}
$oldBase=J $old.baseline.path;$projects=@($oldBase.inputs|Where-Object {$_.path-match'\.(sln|vcxproj)$'})
if($projects.Count-ne2){throw 'Authoritative solution/project identities missing'};V $projects
$libPath=Join-Path $logs ('upl_gpu_public_reader_'+$Configuration+'_r1.helper.json');$libProof=J $libPath
if($libProof.source_build.sha256-cne(E $oldPath).sha256-or@($libProof.libraries).Count-ne6){throw 'Retained resolved library manifest differs'};V $libProof.libraries
$oldCall=J $old.project_call.path
if($oldCall.exit_code-ne0-or!$oldCall.owned_call_exited-or$oldCall.arguments-notcontains'/t:Rebuild'-or$oldCall.arguments-notcontains'/p:PostBuildEventUseInBuild=false'){throw 'Successful isolated full Rebuild vector required'}
if($Configuration-eq'Release'){
 $dp=Join-Path $logs 'upl_gpu_gravity_Debug_r1.build.json';$d=J $dp
 if($d.status-ne'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run'-or@($d.objects).Count-ne110){throw 'Fresh gravity-stage Debug build required before Release'}
 V @((E $dp),$d.source_freeze,$d.project_call,$d.isolated_GPU_program);V $d.objects;$ds=J $d.source_freeze.path;V $ds.source
}
$source=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\source') -Recurse -File|Where-Object {$_.Extension-in$types}|Sort-Object FullName|ForEach-Object {E $_.FullName})
if($source.Count-ne265-or@($source|ForEach-Object {[IO.Path]::GetFileName($_.path)}|Sort-Object -Unique).Count-ne265){throw 'Current265 code files with unique snapshot names required'}
$name='upl_gpu_gravity_'+$Configuration+'_r1';$folder=Join-Path $out $name;$copiesDir=Join-Path $out ($name+'_source');$freeze=Join-Path $logs ($name+'.source.json');$record=Join-Path $logs ($name+'.build.json')
$int=Join-Path ([IO.Path]::GetTempPath()) ('upl_gpu_gravity_r1\'+$Configuration+'\int\');if($int-match'\s'){throw 'CUDA IntDir must contain no whitespace'};$gpuout=Join-Path $folder 'gpu\'
foreach($p in @($folder,$copiesDir,$int,$freeze,$record,(Join-Path $logs ($name+'_project.call.json')),(Join-Path $logs ($name+'_project.log')),(Join-Path $logs ($name+'.binlog')))){if(Test-Path -LiteralPath $p){throw "Fresh label required; retained path exists: $p"}}
[void](New-Item -ItemType Directory -Path $folder);[void](New-Item -ItemType Directory -Path $gpuout);[void](New-Item -ItemType Directory -Path $copiesDir);[void](New-Item -ItemType Directory -Path $int)
$copies=@();foreach($r in $source){$destination=Join-Path $copiesDir ([IO.Path]::GetFileName($r.path));Copy-Item -LiteralPath $r.path -Destination $destination;$copy=E $destination;if($copy.bytes-ne$r.bytes-or$copy.sha256-cne$r.sha256){throw 'Current source snapshot copy differs'};$copies+=@{original=$r;snapshot=$copy}}
$inputs=@(E $PSCommandPath;E $note;E $verifiedPath;E $cpuPath;E $wallPath;E $oldPath;E $libPath)+$projects+$source+@($oldPairs|ForEach-Object {$_.snapshot})
Save $freeze ([ordered]@{status='private_GPU_gravity_candidate_current_source_frozen_before_build';source_base=$base;configuration=$Configuration;inputs=$inputs;source=$source;current_source_snapshot=$copies;source_code_files=265;source_directory_reference_files=271;excluded_noncode_text_files=6;target_names=$targetNames;targets=$expected;other_source_count=263;ancestral_target_git_checks=$ancestry;historical_raw_target_copies_newly_made_before_edits=$false;current265_copies_created_after_guard_edits=$true;historical_Git_metadata_revalidated_as_current=$false;authoritative_projects=$projects;tools=$old.tools;libraries=$libProof.libraries;canonical_GPU_six_and_CPU_two=$canonical;default_CPU_Debug_build=(E $cpuPath);helper_or_program_run=$false;physical_acceptance=$false})
$argv=@();$remaps=0
foreach($a in $oldCall.arguments){if($a.StartsWith('/p:OutDir=',[StringComparison]::OrdinalIgnoreCase)){$argv+='/p:OutDir='+$gpuout.Replace('\','/');$remaps++}elseif($a.StartsWith('/p:IntDir=',[StringComparison]::OrdinalIgnoreCase)){$argv+='/p:IntDir='+$int.Replace('\','/');$remaps++}elseif($a.StartsWith('/bl:',[StringComparison]::OrdinalIgnoreCase)){$argv+='/bl:'+(Join-Path $logs ($name+'.binlog'));$remaps++}else{$argv+=$a}}
if($remaps-ne3){throw 'Only exact OutDir/IntDir/binlog remaps are allowed'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$global:LASTEXITCODE=$null;$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';$envCode=$LASTEXITCODE
if($envCode-isnot[int]-or$envCode-ne0){throw 'VS environment acquisition failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i-gt0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$call=Call $oldCall.program $argv ($name+'_project');$actual=J $call.path
if($actual.exit_code-ne0){Save $record ([ordered]@{status='authoritative_GPU_Rebuild_failed_retained';configuration=$Configuration;source_freeze=(E $freeze);project_call=$call;program_or_component_run=$false;physical_acceptance=$false});throw 'Native build failed; preserve this label without retry'}
$objects=@($old.objects|ForEach-Object {E (Join-Path $int ([IO.Path]::GetFileName($_.path)))});$main=E (Join-Path $int 'main.obj')
if($objects.Count-ne110-or@($objects.path|Sort-Object -Unique).Count-ne110-or@($objects|Where-Object {[IO.Path]::GetFileName($_.path)-eq'main.obj'}).Count){throw 'Fresh110 authoritative non-main object closure differs'}
$cu=@($objects|Where-Object {$_.path-match'\.cu\.obj$'}).Count;$ch=@($objects|Where-Object {$_.path-match'\.h\.obj$'}).Count
if($cu-ne12-or$ch-ne2){throw 'Actual CUDA source/header object counts differ'}
$runtime=@();foreach($r in $old.runtime){V @($r.original,$r.copy);$destination=Join-Path $gpuout ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $destination;$copy=E $destination;if($copy.bytes-ne$r.copy.bytes-or$copy.sha256-cne$r.copy.sha256){throw 'Runtime copy differs'};$runtime+=@{original=$r.copy;copy=$copy}}
V $inputs;V $canonical;V $old.tools;V $libProof.libraries;foreach($r in $copies){V @($r.snapshot)};foreach($r in $old.runtime){V @($r.original,$r.copy)};V @($old.isolated_GPU_program)
$exe=Join-Path $gpuout ([IO.Path]::GetFileName($old.isolated_GPU_program.path))
Save $record ([ordered]@{status='full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run';configuration=$Configuration;source_base=$base;source_freeze=(E $freeze);inputs=$inputs;tools=$old.tools;libraries=$libProof.libraries;objects=$objects;objects_exclude_main=$true;project_main_object=$main;project_call=$call;isolated_GPU_program=(E $exe);runtime=$runtime;no_space_IntDir=$int;isolated_GPU_OutDir=$gpuout;replayed_build=(E $oldPath);exact_build_argument_remaps=3;source_code_files=265;target_count=2;other_source_count=263;current_source_snapshot_count=265;non_main_CPU_host_objects=96;CUDA_cu_objects=$cu;CUDA_header_objects=$ch;authoritative_non_main_objects=110;full_project_includes_own_main=$true;canonical_GPU_six_and_CPU_two_unchanged=$true;retained_public_GPU_program_unchanged=$true;default_CPU_Debug_build=(E $cpuPath);source_backup_created_before_guard_edits=$false;current_source_copies_created_before_project_call=$true;helper_built=$false;program_or_component_run=$false;private_GPU_gravity_numerical_acceptance=$false;public_nonzero_gravity_accepted=$false;physical_acceptance=$false})
