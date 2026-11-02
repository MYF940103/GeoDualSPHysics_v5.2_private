param([Parameter(Mandatory=$true)][ValidateSet('Debug','Release')][string]$Configuration,[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# One C++ helper compile/link only; no project rebuild, input preparation or executable invocation.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t -Force).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$note=Join-Path $t 'notes\upl_gpu_gravity_helper_build_r1.json'
$cpp=Join-Path $t 'support\upl_gravity_periodic_gpu_r1.cpp';$cppNote=Join-Path $t 'notes\upl_gravity_periodic_gpu_r1.json';$inc=Join-Path $t 'support\upl_gpu_observer_native_r1.cpp';$incNote=Join-Path $t 'notes\upl_gpu_observer_native_r1.json'
$expected=@(@{path=$cpp;bytes=19450;sha256='431e3226083013e09b93865fca720e9bd7529c57e331dd7b2506b10a1df7fc16'},@{path=$cppNote;bytes=8810;sha256='eb7ad84a5cefc25d06062d3c799afe83d3916e3ac9fc28c0f51a7bf0ae410deb'},@{path=$inc;bytes=12180;sha256='b112f7e78651dde136c2438a02f326522ef4cb35b5603fa1eb17ee24d3437857'},@{path=$incNote;bytes=5803;sha256='26dafa6246e7ba38798cc7e3542bb10d9b3926c8303ae17c54dcd35bd499344d'})
function E([string]$p){$f=Get-Item -LiteralPath $p -Force;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes-ne[long]$r.bytes-or$a.sha256-cne$r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained receipt protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,[string]$label){
 $p=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');foreach($f in @($p,$log)){if(Test-Path -LiteralPath $f){throw 'Owned compiler/linker call retained'}}
 V @($tool);[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
 Push-Location (Join-Path $repo 'src');try{$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$failure=[string]$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
 V @($tool);Save $p ([ordered]@{program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code-is[int]);owned_call_exited=($code-is[int]);exit_code=$code;invocation_failure=$failure;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);build_tool_only=$true;program_or_component_run=$false;physical_acceptance=$false});E $p
}
if(!$ProductionBuildConfirmed-or!$ExecutionAuthorized){throw 'Root full source/recipe review and explicit one-configuration helper-build authorization required'}
$gpuPath=Join-Path $logs ('upl_gpu_gravity_'+$Configuration+'_r1.build.json');$g=J $gpuPath
if($g.status-ne'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run'-or$g.configuration-ne$Configuration-or@($g.objects).Count-ne110-or!$g.objects_exclude_main-or$g.target_count-ne2-or$g.other_source_count-ne263){throw 'Current gravity GPU Rebuild110/2/263 required'}
$s=J $g.source_freeze.path;$canonical=@($s.canonical_GPU_six_and_CPU_two)
if(@($s.source).Count-ne265-or@($s.current_source_snapshot).Count-ne265-or@($s.targets).Count-ne2-or$s.other_source_count-ne263-or$canonical.Count-ne8-or@($g.runtime).Count-ne4){throw 'Current265-source/snapshot and protected-eight closure differs'}
$project=J $g.project_call.path;if($project.exit_code-isnot[int]-or$project.exit_code-ne0-or!$project.typed_LASTEXITCODE_captured_immediately-or!$project.owned_call_exited){throw 'Owned authoritative GPU build exit0 required'}
$oldPath=Join-Path $logs ('upl_gpu_public_reader_'+$Configuration+'_r1.helper.json');$h=J $oldPath
if($h.status-ne'actual_authoritative_GPU_objects_helper_linked_not_run'-or$h.configuration-ne$Configuration-or@($h.objects).Count-ne110-or$h.link_object_count-ne111-or!$h.exact_link_closure_verified){throw 'Retained successful public-reader argument recipe required'}
$cc=J $h.compile_call.path;$lc=J $h.link_call.path
if($cc.exit_code-ne0-or$lc.exit_code-ne0-or!$cc.owned_call_exited-or!$lc.owned_call_exited-or@($lc.arguments|Where-Object {[IO.Path]::GetFileName($_)-ieq'bcrypt.lib'}).Count){throw 'Successful non-CNG compile/link vector required'}
$oldCpp=Join-Path $t 'support\upl_gpu_public_native_r1.cpp';$oldObj=$h.helper_object.path
$name='upl_gpu_gravity_helper_'+$Configuration+'_r1';$folder=Join-Path $out $name;$record=Join-Path $logs ($name+'.helper.json');$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder 'upl_gravity_periodic_gpu_r1.exe'
foreach($p in @($folder,$record,(Join-Path $logs ($name+'_compile.call.json')),(Join-Path $logs ($name+'_compile.log')),(Join-Path $logs ($name+'_link.call.json')),(Join-Path $logs ($name+'_link.log')))){if(Test-Path -LiteralPath $p){throw "Fresh reviewed helper label required: $p"}}
$author=@(E $PSCommandPath;E $note;E $cpp;E $cppNote;E $inc;E $incNote);$inputs=$author+@(E $gpuPath;E $oldPath)+@($g.source_freeze,$h.source_build,$h.compile_call,$h.link_call)
function VerifyCurrent{
 V $inputs;V $expected;V $g.inputs;V $g.objects;V $g.tools;V $g.libraries;V $s.source;V $canonical;V @($g.project_call,$g.isolated_GPU_program,$g.default_CPU_Debug_build,$h.program);V $h.tools;V $h.libraries
 foreach($r in $s.current_source_snapshot){V @($r.snapshot)};foreach($r in @($g.runtime)+@($h.runtime)){V @($r.original,$r.copy)}
}
VerifyCurrent
if($Configuration-eq'Release'){$dp=Join-Path $logs 'upl_gpu_gravity_helper_Debug_r1.helper.json';$d=J $dp;if($d.status-ne'actual_authoritative_GPU_objects_helper_linked_not_run'-or$d.fixture-ne'GravityPeriodic'-or!$d.exact_link_closure_verified){throw 'Fresh Debug helper link required first'};V @($d.program,$d.compile_call,$d.link_call,$d.source_build)}
$newByName=@{};foreach($r in $g.objects){$n=[IO.Path]::GetFileName($r.path);if($newByName.ContainsKey($n)-or$n-ieq'main.obj'-or[IO.Path]::GetDirectoryName($r.path).TrimEnd('\')-ine([IO.Path]::GetFullPath($g.no_space_IntDir).TrimEnd('\'))){throw 'Non-main current GPU object inventory differs'};$newByName[$n]=$r}
$map=@{};foreach($r in $h.objects){$n=[IO.Path]::GetFileName($r.path);if(!$newByName.ContainsKey($n)-or$map.ContainsKey($r.path)){throw 'Old/current GPU object basename closure differs'};$map[$r.path]=$newByName[$n].path}
if($map.Count-ne110-or@($g.objects|Where-Object {$_.path-match'\.cu\.obj$'}).Count-ne12-or@($g.objects|Where-Object {$_.path-match'\.h\.obj$'}).Count-ne2){throw '110 current objects including12 CUDA+2 header units required'}
$ca=@();$src=0;$fo=0;$fd=0;foreach($a in $cc.arguments){if($a-ieq$oldCpp){$ca+=$cpp;$src++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}else{$ca+=$a}}
if($src-ne1-or$fo-ne1-or$fd-ne1-or$ca-notcontains'/D_WITHGPU'-or$ca-notcontains'/std:c++17'){throw 'Only one source and two compiler output remaps permitted'}
$la=@();$on=0;$pn=0;$hn=0;$gn=0;$seen=@{}
foreach($a in $lc.arguments){
 if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$on++}
 elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $folder 'link.pdb');$pn++}
 elseif($a-ieq$oldObj){$la+=$obj;$hn++}
 elseif($map.ContainsKey($a)){if($seen.ContainsKey($a)){throw 'Duplicate GPU link object'};$la+=$map[$a];$seen[$a]=$true;$gn++}
 else{$la+=$a}
}
if($on-ne1-or$hn-ne1-or$gn-ne110-or$pn-ne$(if($Configuration-eq'Debug'){1}else{0})){throw 'Only exact helper/110-object/OUT/PDB remaps permitted'}
$actual=@($la|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)}|ForEach-Object {[IO.Path]::GetFullPath($_).ToLowerInvariant()});$wanted=@($obj.ToLowerInvariant())+@($g.objects|ForEach-Object {[IO.Path]::GetFullPath($_.path).ToLowerInvariant()})
if($actual.Count-ne111-or@($actual|Sort-Object -Unique).Count-ne111-or@(Compare-Object @($actual|Sort-Object) @($wanted|Sort-Object)).Count){throw 'Exact111 link closure failed; no main or old object may remain'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$global:LASTEXITCODE=$null;$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';$envCode=$LASTEXITCODE
if($envCode-isnot[int]-or$envCode-ne0){throw 'VS process environment acquisition failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i-gt0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder);$compile=Call $cc.program $ca ($name+'_compile');$c=J $compile.path
if($c.exit_code-isnot[int]-or$c.exit_code-ne0-or$c.invocation_failure){Save $record ([ordered]@{status='helper_compile_failed_retained';configuration=$Configuration;source_build=(E $gpuPath);compile_call=$compile;program_or_component_run=$false;physical_acceptance=$false});throw 'Compiler failed; preserve label without retry'}
$link=Call $lc.program $la ($name+'_link');$l=J $link.path
if($l.exit_code-isnot[int]-or$l.exit_code-ne0-or$l.invocation_failure){Save $record ([ordered]@{status='helper_link_failed_retained';configuration=$Configuration;source_build=(E $gpuPath);compile_call=$compile;link_call=$link;program_or_component_run=$false;physical_acceptance=$false});throw 'Linker failed; preserve label without retry'}
$runtime=@();foreach($r in $g.runtime){$destination=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $destination;$copy=E $destination;if($copy.bytes-ne$r.copy.bytes-or$copy.sha256-cne$r.copy.sha256){throw 'Helper runtime copy differs'};$runtime+=@{original=$r.copy;copy=$copy}}
VerifyCurrent
Save $record ([ordered]@{status='actual_authoritative_GPU_objects_helper_linked_not_run';fixture='GravityPeriodic';configuration=$Configuration;source_build=(E $gpuPath);source_freeze=$g.source_freeze;inputs=$inputs;author_files=$author;transitive_author_include_files=@(E $inc;E $incNote);project_include_source_freeze=$g.source_freeze;source_code_files=265;target_count=2;other_source_count=263;objects=$g.objects;helper_object=(E $obj);link_object_count=111;exact_link_closure_verified=$true;tools=$g.tools;libraries=$g.libraries;runtime=$runtime;program=(E $exe);compile_call=$compile;link_call=$link;replayed_helper=(E $oldPath);historical_object_source_build=$h.source_build;compiler_source_remaps=1;compiler_output_remaps=2;GPU_object_substitutions=110;link_helper_object_substitutions=1;link_OUT_remaps=1;link_PDB_remaps=$pn;protected_canonical_GPU_and_CPU_count=8;canonical_GPU_and_CPU_unchanged=$true;historical_original_source_paths_revalidated_as_current=$false;baseline_or_environment_selected_read=$false;new_source_or_program_backup_copies_made=0;Rebuild_executed=$false;program_or_component_run=$false;private_GPU_gravity_numerical_acceptance=$false;public_nonzero_gravity_accepted=$false;physical_acceptance=$false})
