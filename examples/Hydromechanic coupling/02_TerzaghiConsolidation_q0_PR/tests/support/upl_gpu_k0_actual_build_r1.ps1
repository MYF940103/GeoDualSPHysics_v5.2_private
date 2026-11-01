param([ValidateSet('BuildActual')][string]$Mode='BuildActual',[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Build one actual-Run helper only. No help, solver, smoke, old worker, or Git mutation.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$stagePath=Join-Path $logs 'upl_gpu_k0_time_stage_r1.check.json'
$cpp=Join-Path $t 'support\upl_gpu_k0_actual_r1.cpp';$note=Join-Path $t 'notes\upl_gpu_k0_actual_r1.json'
$included=Join-Path $t 'support\upl_gpu_observer_native_r1.cpp';$includedNote=Join-Path $t 'notes\upl_gpu_observer_native_r1.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){Get-Content -Raw -LiteralPath (ResolveArtifactPath $p)|ConvertFrom-Json}
function VerifyTree($x){if($null -eq $x){return};if($x -is [array]){foreach($v in $x){VerifyTree $v};return};if($x -is [pscustomobject]){if($x.PSObject.Properties['path'] -and $x.PSObject.Properties['bytes'] -and $x.PSObject.Properties['sha256']){V @($x);return};foreach($v in $x.PSObject.Properties){VerifyTree $v.Value}}}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,[string]$label){
  V @($tool);$p=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');if((Test-Path -LiteralPath $p) -or (Test-Path -LiteralPath $log)){throw 'Owned compile/link retained'}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$old}
  V @($tool);Save $p ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);program_or_component_run=$false;physical_acceptance=$false});if($code){throw 'Compile/link failed; preserve evidence'};E $p
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root full fixture/source review and explicit single-build authorization required'}
$stage=J $stagePath;VerifyTree $stage
if(!$stage.passed -or $stage.physical_acceptance -or $stage.public_GPU_dynamic_accepted -or @($stage.native).Count -ne 2 -or @($stage.components).Count -ne 6){throw 'Completed two-native/six-Time stage required'}
$gpuPath=Join-Path $logs ('upl_gpu_k0_time_'+$Configuration+'_r1.build.json');$g=J $gpuPath;$listed=@($stage.builds|Where-Object {$_.sha256 -ieq (E $gpuPath).sha256})
if($listed.Count -ne 1 -or $g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $Configuration -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main){throw 'Accepted frozen authoritative GPU objects required'}
V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program);foreach($r in $g.runtime){V @($r.original,$r.copy)}
$source=J $g.source_freeze.path;V $source.source;V $source.four_targets;if(@($source.source).Count -ne 265 -or @($source.four_targets).Count -ne 4){throw 'Frozen four-target and265-source identity differs'}
$baseline=J $g.baseline.path;V $baseline.inputs;V $baseline.other_source;V $baseline.canonical_GPU
# A later selective checkpoint is allowed. Actual current source hashes, not HEAD equality, govern reuse of these objects.
$oldPath=Join-Path $logs ('upl_gpu_k0_time_component_'+$Configuration+'_r1.helper.json');$h=J $oldPath
if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'Time' -or $h.configuration -ne $Configuration -or $h.source_build.sha256 -ine (E $gpuPath).sha256){throw 'Immutable current Time helper argument recipe required'}
V $h.inputs;V $h.author_files;V $h.tools;V $h.libraries;V @($h.source_build,$h.program,$h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}
$cc=J $h.compile_call.path;$lc=J $h.link_call.path;V @($cc.program,$cc.log,$lc.program,$lc.log);if($cc.exit_code -ne 0 -or $lc.exit_code -ne 0){throw 'Retained compile/link call did not pass'}
$name='upl_gpu_k0_actual_'+$Configuration+'_r1';$folder=Join-Path $out $name;$record=Join-Path $logs ($name+'.helper.json');foreach($p in @($folder,$record)){if(Test-Path -LiteralPath $p){throw 'Retained actual helper protected'}}
$author=@(E $PSCommandPath;E $cpp;E $note;E $included;E $includedNote);$inputs=$author+@(E $stagePath;E $gpuPath;E $oldPath)
if((E $included).sha256 -ne 'b112f7e78651dde136c2438a02f326522ef4cb35b5603fa1eb17ee24d3437857'){throw 'Immutable included Native reader/solver changed'}
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder 'upl_gpu_k0_actual_r1.exe';$oldFolder=Split-Path -Parent $h.program.path;$oldCpp=Join-Path $t 'support\upl_gpu_k0_time_r1.cpp'
$ca=@();$fo=0;$fd=0;$src=0;foreach($a in $cc.arguments){if($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq $oldCpp){$ca+=$cpp;$src++}else{$ca+=$a}}
if($fo -ne 1 -or $fd -ne 1 -or $src -ne 1){throw 'Only source/Fo/Fd compiler substitutions permitted'}
$la=@();$on=0;$pdb=0;$hn=0;$gn=0;foreach($a in $lc.arguments){if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$on++}elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $folder 'link.pdb');$pdb++}elseif($a -ieq (Join-Path $oldFolder 'helper.obj')){$la+=$obj;$hn++}elseif($a.StartsWith($g.no_space_IntDir,[StringComparison]::OrdinalIgnoreCase)){$la+=Join-Path $g.no_space_IntDir ([IO.Path]::GetFileName($a));$gn++}else{$la+=$a}}
if($on -ne 1 -or $hn -ne 1 -or $gn -ne 110 -or $pdb -ne $(if($Configuration -eq 'Debug'){1}else{0})){throw 'Unexpected linker substitution set'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder);$compile=Call $cc.program $ca ($name+'_compile');$link=Call $lc.program $la ($name+'_link')
$runtime=@();foreach($r in $g.runtime){$p=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $p;$v=E $p;if($v.sha256 -ne $r.copy.sha256){throw 'Actual helper runtime differs'};$runtime+=@{original=$r.copy;copy=$v}}
V $inputs;V $g.inputs;V $g.objects;V $g.tools;V $h.tools;V $h.libraries;V $baseline.canonical_GPU;foreach($r in $g.runtime){V @($r.original,$r.copy)}
Save $record ([ordered]@{status='actual_authoritative_GPU_objects_helper_linked_not_run';fixture='Actual';configuration=$Configuration;source_build=(E $gpuPath);prerequisite_stage=(E $stagePath);inputs=$inputs;author_files=$author;author_files_frozen_by_hash_only=$true;additional_author_source_copies_made=0;runtime=$runtime;program=(E $exe);tools=$h.tools;libraries=$h.libraries;compile_call=$compile;link_call=$link;replayed_helper=(E $oldPath);compiler_source_remaps=1;compiler_output_remaps=2;GPU_object_substitutions=110;GPU_object_directory_changed=$false;only_chosen_helper_author_files_frozen=$true;other_helper_inputs_bound=$false;canonical_GPU_unchanged=$true;HEAD_equality_required=$false;program_or_component_run=$false;physical_acceptance=$false})
