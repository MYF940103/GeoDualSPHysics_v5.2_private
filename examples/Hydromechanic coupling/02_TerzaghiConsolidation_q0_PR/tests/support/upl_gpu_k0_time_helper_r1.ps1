param([ValidateSet('BuildHelper')][string]$Mode='BuildHelper',[ValidateSet('Debug','Release')][string]$Configuration='Debug',[ValidateSet('Time','Native')][string]$Fixture='Time',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Link only. The three --time component modes are separate explicitly owned calls, never launched here.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$base='bf5ef956d4ffaf91b0b52e57a740be03fc64cee4'
$cpp=Join-Path $t $(if($Fixture -eq 'Time'){'support\upl_gpu_k0_time_r1.cpp'}else{'support\upl_gpu_observer_native_r1.cpp'})
$note=Join-Path $t $(if($Fixture -eq 'Time'){'notes\upl_gpu_k0_time_component_r1.json'}else{'notes\upl_gpu_observer_native_r1.json'})
$baselinePath=Join-Path $logs 'upl_gpu_k0_time_r1.baseline.json';$gpuPath=Join-Path $logs ('upl_gpu_k0_time_'+$Configuration+'_r1.build.json')
$oldHelperPath=Join-Path $logs ('upl_gpu_feedback_Native_'+$Configuration+'_r2.helper.json')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){Get-Content -Raw -LiteralPath (ResolveArtifactPath $p)|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,[string]$label){
  V @($tool);$p=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');if((Test-Path -LiteralPath $p) -or (Test-Path -LiteralPath $log)){throw 'Owned compile/link retained'}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$old}
  V @($tool);Save $p ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);program_or_component_run=$false;physical_acceptance=$false})
  if($code){throw 'Compile/link failed; preserve evidence'};E $p
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root source/fixture review and explicit single-build authorization required'}
$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$old;if($code -or $head -ne $base){throw 'Exact verified bf5ef95 checkpoint required'}
$b=J $baselinePath;if($b.git_base -ne $base){throw 'Current k0-time baseline required'};V $b.inputs;V $b.other_source;V $b.canonical_GPU
$g=J $gpuPath;if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne $Configuration -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main){throw 'Fresh authoritative110-object GPU closure required'}
V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program);foreach($r in $g.runtime){V @($r.original,$r.copy)}
$h=J $oldHelperPath;if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'Native' -or $h.configuration -ne $Configuration){throw 'Immutable Native helper argument recipe required'}
V @($h.source_build,$h.compile_call,$h.link_call,$h.program);V $h.tools;V $h.libraries
$oldGpu=J $h.source_build.path;$cc=J $h.compile_call.path;$lc=J $h.link_call.path
V @($cc.program,$cc.log,$lc.program,$lc.log);if($cc.exit_code -ne 0 -or $lc.exit_code -ne 0){throw 'Retained compiler/linker call did not pass'}
$oldCpp=Join-Path $t 'support\upl_gpu_observer_native_r1.cpp';$oldCppRows=@($h.inputs|Where-Object {$_.path -ieq $oldCpp});if($oldCppRows.Count -ne 1){throw 'Old compiler source identity missing'};V $oldCppRows
$name='upl_gpu_k0_time_'+$(if($Fixture -eq 'Time'){'component'}else{'native'})+'_'+$Configuration+'_r1';$folder=Join-Path $out $name;$record=Join-Path $logs ($name+'.helper.json')
foreach($p in @($folder,$record)){if(Test-Path -LiteralPath $p){throw 'Retained helper protected; use a new reviewed label'}}
$author=@(E $PSCommandPath;E $cpp;E $note);$inputs=$author+@(E $gpuPath;E $baselinePath;E $oldHelperPath)
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder $(if($Fixture -eq 'Time'){'upl_gpu_k0_time_r1.exe'}else{'upl_gpu_observer_native_r1.exe'});$oldFolder=Split-Path -Parent $h.program.path
$ca=@();$fo=0;$fd=0;$src=0;foreach($a in $cc.arguments){if($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq $oldCpp){$ca+=$cpp;$src++}else{$ca+=$a}}
if($fo -ne 1 -or $fd -ne 1 -or $src -ne 1){throw 'Only exact source/Fo/Fd compiler remaps permitted'}
$la=@();$on=0;$pdb=0;$hn=0;$gn=0;foreach($a in $lc.arguments){if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$on++}elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $folder 'link.pdb');$pdb++}elseif($a -ieq (Join-Path $oldFolder 'helper.obj')){$la+=$obj;$hn++}elseif($a.StartsWith($oldGpu.no_space_IntDir,[StringComparison]::OrdinalIgnoreCase)){$la+=Join-Path $g.no_space_IntDir ([IO.Path]::GetFileName($a));$gn++}else{$la+=$a}}
if($on -ne 1 -or $hn -ne 1 -or $gn -ne 110 -or $pdb -ne $(if($Configuration -eq 'Debug'){1}else{0})){throw 'Unexpected linker remap set'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder);$compile=Call $cc.program $ca ($name+'_compile');$link=Call $lc.program $la ($name+'_link')
$runtime=@();foreach($r in $g.runtime){$p=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $p;$v=E $p;if($v.sha256 -ne $r.copy.sha256){throw 'Helper runtime copy differs'};$runtime+=@{original=$r.copy;copy=$v}}
V $inputs;V $g.inputs;V $g.tools;V $g.objects;V $h.tools;V $h.libraries;V $b.canonical_GPU;foreach($r in $g.runtime){V @($r.original,$r.copy)}
Save $record ([ordered]@{status='actual_authoritative_GPU_objects_helper_linked_not_run';fixture=$Fixture;configuration=$Configuration;git_base=$base;source_build=(E $gpuPath);baseline=(E $baselinePath);inputs=$inputs;author_files=$author;author_files_frozen_by_hash_only=$true;additional_author_source_copies_made=0;runtime=$runtime;program=(E $exe);tools=$h.tools;libraries=$h.libraries;compile_call=$compile;link_call=$link;replayed_helper=(E $oldHelperPath);compiler_source_remaps=1;compiler_output_remaps=2;GPU_object_remaps=110;only_chosen_helper_author_files_frozen=$true;other_helper_inputs_bound=$false;canonical_GPU_unchanged=$true;program_or_component_run=$false;physical_acceptance=$false})
