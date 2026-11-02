param(
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [switch]$ExecutionAuthorized
)
# One helper compile/link only: no Rebuild, audit, solver, old main or installation.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src';$logs=Join-Path $t 'logs'
$name="upl_gravity_endpoint_cpu_${Configuration}_r1";$folder=Join-Path $t "outputs\${name}_helper";$result=Join-Path $logs ($name+'.helper.json')
$oldPath=Join-Path $logs "upl_gravity_periodic_cpu_${Configuration}_r1.helper.json";$stagePath=Join-Path $logs 'upl_gravity_periodic_stage_r1.check.json';$publishedPath=Join-Path $logs 'upl_gravity_periodic_publish_r1.verified.json'
$defaultBuildPath=Join-Path $logs 'upl_gravity_endpoint_default_DebugCPU_r1.build.json';$defaultBuildLog=Join-Path $logs 'upl_gravity_endpoint_default_DebugCPU_r1.build.log'
$cpp=Join-Path $t 'support\upl_gravity_endpoint_cpu_r1.cpp';$fixtureNote=Join-Path $t 'notes\upl_gravity_endpoint_cpu_r1.json';$note=Join-Path $t 'notes\upl_gravity_endpoint_build_r1.json'
function Entry([string]$p){$f=Get-Item -Force -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function ReadJson([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"}}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 24)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function ReadGit([string[]]$argv){$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;try{$lines=@(& $git.path -C $repo @argv);$code=$LASTEXITCODE}finally{$ErrorActionPreference=$oldAction};if($code -isnot [int] -or $code -ne 0){throw 'Read-only Git identity command failed'};return ($lines -join "`n").Trim()}
function CurrentGit{
  Verify @($git,$publishedIdentity);$head=ReadGit @('rev-parse','HEAD');$branch=ReadGit @('branch','--show-current');if($head -cne $parent -or $branch -cne 'upl-dev'){throw 'Verified published endpoint parent/branch required'}
  $relative=@($b.source|ForEach-Object {$_.path.Substring($repo.Length+1).Replace('\','/')});$tree=@{};foreach($line in ((ReadGit @('ls-tree','-r',$parent,'--','src/source')) -split "`n")){if($line -cnotmatch '^[0-7]{6} blob ([0-9a-f]{40})\t(.+)$'){throw 'Unexpected parent source tree entry'};$tree[$Matches[2]]=$Matches[1]}
  if($tree.Count -ne 271 -or @(Compare-Object ($relative|Sort-Object) @($tree.Keys|Sort-Object)).Count){throw 'Parent/current271-file source tree membership differs'}
  # Filename arguments apply each file's own Git path filters; no -w or object write.
  $filtered=@((ReadGit (@('hash-object','--')+$relative)) -split "`n");if($filtered.Count -ne 271){throw 'Filtered source blob inventory differs'}
  $blobs=@();for($i=0;$i -lt $relative.Count;$i++){if($filtered[$i] -cne $tree[$relative[$i]]){throw "Current filtered source differs from published parent: $($relative[$i])"};$blobs+=@{path=$relative[$i];parent_blob=$tree[$relative[$i]];filtered_current_blob=$filtered[$i]}}
  @{parent=$head;branch=$branch;source_blobs=$blobs;git_tool=$git;read_only_no_write_object_flag=$true}
}
function PassedCall($e){Verify @($e);$c=ReadJson $e.path;if(!$c.typed_LASTEXITCODE_captured_immediately -or !$c.owned_call_exited -or $c.exit_code -ne 0){throw 'Owned typed exit0 compile/link call required'};Verify @($c.program,$c.log);return $c}
function Owned($tool,[string[]]$argv,[string]$suffix){
  $log=Join-Path $logs ($name+'_'+$suffix+'.log');$receipt=Join-Path $logs ($name+'_'+$suffix+'.call.json');Fresh @($log,$receipt);Verify @($tool);[IO.File]::WriteAllBytes($log,[byte[]]@())
  $start=[DateTime]::UtcNow.ToString('o');$code=$null;$invocationFailure=$null;$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null
  Push-Location $src;try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$invocationFailure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldAction}
  $typed=$code -is [int];Save $receipt ([ordered]@{program=$tool;arguments=$argv;working_directory=$src;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=$typed;owned_call_exited=$typed;exit_code=$code;invocation_failure=$invocationFailure;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);program_is_build_tool_only=$true;physical_acceptance=$false});Verify @($tool);return (Entry $receipt)
}
if(!$ExecutionAuthorized){throw 'Root full author/recipe review and explicit one-configuration build authorization required'}
Fresh @($folder,$result);$publishedIdentity=Entry $publishedPath;$published=ReadJson $publishedPath;$parent=[string]$published.commit
if($parent -cnotmatch '^[0-9a-f]{40}$' -or $published.branch -cne 'upl-dev' -or $published.local_remote_equal -ne $true){throw 'Actual verified local/remote periodic checkpoint required'}
$defaultBuildArtifacts=@((Entry $defaultBuildPath),(Entry $defaultBuildLog));$defaultBuild=ReadJson $defaultBuildPath
if($defaultBuild.passed -ne $true -or $defaultBuild.typed_LASTEXITCODE_captured_immediately -ne $true -or $defaultBuild.owned_call_exited -ne $true -or $defaultBuild.exit_code -ne 0 -or $defaultBuild.production_source_changed -ne $false -or $defaultBuild.physical_solver_called -ne $false -or $defaultBuild.canonical_cpu_debug_unchanged -ne $true -or $defaultBuild.canonical_cpu_debug_before_sha256 -cne $defaultBuild.canonical_cpu_debug_after_sha256){throw 'Observed default CPU Debug build exit0 with unchanged protected canonical required'}
$stageIdentity=Entry $stagePath;$stage=ReadJson $stagePath
if($stage.passed -ne $true -or $stage.stage -cne 'upl_gravity_periodic_stage_r1' -or $stage.public_gravity_accepted -ne $false -or $stage.wall_gravity_accepted -ne $false -or $stage.physical_acceptance -ne $false){throw 'Passed bounded periodic stage with public/wall/physical admission held required'}
Verify $stage.proof;Verify @($stage.production_source)
$requiredProof=@('upl_gravity_periodic_cpu_DebugCPU_smoke_r1.check.json','upl_gravity_periodic_cpu_ReleaseCPU_c_r1.check.json','upl_gravity_periodic_cpu_ReleaseCPU_h_r1.check.json','upl_gravity_periodic_half_r2.check.json','upl_gravity_periodic_frame_c_r2.check.json','upl_gravity_periodic_frame_h_r2.check.json','upl_gravity_periodic_r2_adoption.json')
$scientificProof=@();foreach($leaf in $requiredProof){$rows=@($stage.proof|Where-Object {[IO.Path]::GetFileName($_.path) -ceq $leaf});if($rows.Count -ne 1){throw "Required sealed periodic proof missing: $leaf"};$p=ReadJson $rows[0].path;if($p.passed -ne $true -or $p.physical_acceptance -ne $false){throw "Bounded periodic proof not passed: $leaf"};$scientificProof+=$rows[0]}
$oldIdentity=Entry $oldPath;$h=ReadJson $oldPath
if(!$h.passed -or $h.status -cne 'actual_authoritative_CPU_objects_periodic_helper_linked_not_run' -or $h.configuration -cne $Configuration -or $h.CPU_non_main_objects -ne 85 -or $h.link_object_count -ne 86 -or !$h.exact_link_closure_verified){throw 'Sealed periodic85+1 helper recipe required'}
Verify @($h.parent_helper,$h.source_build);$g=ReadJson $h.parent_helper.path;$b=ReadJson $h.source_build.path
if(!$g.passed -or $g.label -cne 'r2' -or $g.configuration -cne $Configuration -or $g.source_build.sha256 -ine $h.source_build.sha256 -or !$b.passed -or $b.label -cne 'r2' -or $b.configuration -cne $Configuration -or @($b.source).Count -ne 271 -or @($b.current_source_snapshot).Count -ne 271 -or @($b.objects).Count -ne 86){throw 'Original authoritative Gamma r2 source/object/environment closure required'}
# Only the four explicitly sealed Git metadata records are historical, not current inputs.
$historicalGit=@($b.git_identity_metadata);if($historicalGit.Count -ne 4){throw 'Historical Git metadata inventory differs'}
$nonGitInputs=@($b.inputs|Where-Object {$_.path -notin $historicalGit.path});if($nonGitInputs.Count+$historicalGit.Count -ne @($b.inputs).Count){throw 'Only explicit four historical Git entries may be separated'}
function VerifyBase{
  Verify @($oldIdentity,$publishedIdentity,$stageIdentity,$h.parent_helper,$h.source_build);Verify $defaultBuildArtifacts;Verify $stage.proof;Verify @($stage.production_source)
  Verify $h.author_files;Verify $h.tools;Verify $h.libraries;Verify $h.objects;Verify @($h.program,$h.helper_object,$h.compile_call,$h.link_call);foreach($r in $h.runtime){Verify @($r.original,$r.copy)}
  Verify $g.inputs;Verify $g.author_files;Verify $g.tools;Verify $g.environment.tools;Verify $g.libraries;Verify $g.objects;Verify @($g.program,$g.helper_object,$g.compile_call,$g.link_call);foreach($r in $g.runtime){Verify @($r.original,$r.copy)}
  Verify $nonGitInputs;Verify $b.author_files;Verify $b.source;Verify $b.protected_canonical_GPU_six_and_CPU_two;Verify @($b.program,$b.project_call);foreach($r in $b.current_source_snapshot){Verify @($r.original,$r.snapshot)};foreach($r in $b.objects){Verify @($r.source,$r.object)};foreach($r in $b.runtime){Verify @($r.original,$r.copy)}
  $current=@(Get-ChildItem -LiteralPath (Join-Path $src 'source') -File|ForEach-Object {$_.FullName});if($current.Count -ne 271 -or @(Compare-Object ($current|Sort-Object) ($b.source.path|Sort-Object)).Count){throw 'Current source directory membership changed'}
}
VerifyBase;$git=Entry (Get-Command git.exe -CommandType Application).Source;$identity=CurrentGit;$cc=PassedCall $h.compile_call;$lc=PassedCall $h.link_call
if($Configuration -eq 'ReleaseCPU'){$debugPath=Join-Path $logs 'upl_gravity_endpoint_cpu_DebugCPU_r1.helper.json';$debug=ReadJson $debugPath;if(!$debug.passed -or $debug.configuration -cne 'DebugCPU' -or $debug.parent_checkpoint -cne $parent -or $debug.link_object_count -ne 86){throw 'New endpoint Debug helper build must pass before Release build'};Verify @($debug.program,$debug.compile_call,$debug.link_call);Verify $debug.author_files;$debugGate=Entry $debugPath}else{$debugGate=$null}
$readerCpp=Join-Path $t 'support\upl_cpu_public_native_r1.cpp';$readerNote=Join-Path $t 'notes\upl_cpu_public_native_r1.json';$declaration=ReadJson $fixtureNote
$fixtureIdentity=Entry $cpp;$declarationIdentity=Entry $fixtureNote;$reader=Entry $readerCpp
if($fixtureIdentity.sha256 -ine 'c4ff2b06a44a3c11ab8af9bef9840bbdfbd5f13784fa93b688f7603793184085' -or $declarationIdentity.sha256 -ine '1e211e36cd7a77ef2509117559a943a7bb7b723299ed7d27d5276b22efb93833' -or $reader.bytes -ne $declaration.immutable_include.bytes -or $reader.sha256 -ine $declaration.immutable_include.sha256){throw 'Reviewed endpoint/immutable reader author identity differs'}
$authors=@($PSCommandPath,$note,$cpp,$fixtureNote,$readerCpp,$readerNote)|ForEach-Object {Entry $_}
foreach($key in @('INCLUDE','LIB','VCToolsInstallDir','WindowsSdkDir','WindowsSDKVersion')){[Environment]::SetEnvironmentVariable($key,[string]$g.environment.selected.$key,'Process')};$env:PATH=([IO.Path]::GetDirectoryName($cc.program.path))+';'+$env:PATH
$oldCpp=Join-Path $t 'support\upl_gravity_periodic_cpu_r1.cpp';$oldDir=Split-Path -Parent $h.program.path;$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder 'upl_gravity_endpoint_cpu_r1.exe'
$compile=@();$sourceRemap=0;$fo=0;$fd=0;$deps=0
foreach($a in $cc.arguments){if($a -ieq $oldCpp){$compile+=$cpp;$sourceRemap++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq (Join-Path $oldDir 'compile.dependencies.json')){$compile+=Join-Path $folder 'compile.dependencies.json';$deps++}else{$compile+=$a}}
if($sourceRemap -ne 1 -or $fo -ne 1 -or $fd -ne 1 -or $deps -ne 1){throw 'Exact source/Fo/Fd/dependency remaps required'}
$link=@();$objectRemap=0;$exeRemap=0;$pdbRemap=0
foreach($a in $lc.arguments){if($a -ieq $h.helper_object.path){$link+=$obj;$objectRemap++}elseif($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$link+='/OUT:'+$exe;$exeRemap++}elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$link+='/PDB:'+(Join-Path $folder 'link.pdb');$pdbRemap++}else{$link+=$a}}
if($objectRemap -ne 1 -or $exeRemap -ne 1 -or $pdbRemap -ne $(if($Configuration -eq 'DebugCPU'){1}else{0})){throw 'Exact helper/OUT/PDB remaps required'}
$allObjects=@($link|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)});$unchanged=@($allObjects|Where-Object {$_ -ine $obj});if($allObjects.Count -ne 86 -or $unchanged.Count -ne 85 -or @(Compare-Object ($unchanged|Sort-Object) ($h.objects.path|Sort-Object)).Count -or @(Compare-Object ($unchanged|Sort-Object) ($g.objects.path|Sort-Object)).Count){throw 'Unchanged85+newhelper1 linker closure required'}
[void](New-Item -ItemType Directory -Path $folder);$compileCall=Owned $cc.program $compile 'Compile';$compileDone=ReadJson $compileCall.path;$linkCall=$null
if($compileDone.typed_LASTEXITCODE_captured_immediately -and $compileDone.exit_code -eq 0){$linkCall=Owned $lc.program $link 'Link'}
$linkDone=if($linkCall){ReadJson $linkCall.path}else{$null};$passed=$compileDone.typed_LASTEXITCODE_captured_immediately -and $compileDone.exit_code -eq 0 -and $null -ne $linkDone -and $linkDone.typed_LASTEXITCODE_captured_immediately -and $linkDone.exit_code -eq 0
$runtime=@();if($passed){foreach($r in $h.runtime){$dest=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $dest;$copy=Entry $dest;if($copy.sha256 -ine $r.copy.sha256 -or $copy.bytes -ne $r.copy.bytes){throw 'Runtime copy differs'};$runtime+=@{original=$r.copy;copy=$copy}}}
VerifyBase;Verify $authors;[void](CurrentGit)
Save $result ([ordered]@{passed=$passed;status=$(if($passed){'actual_authoritative_CPU_objects_endpoint_helper_linked_not_run'}else{'endpoint_helper_build_failed_retained'});fixture='GravityEndpoint';configuration=$Configuration;parent_checkpoint=$parent;published_checkpoint=$publishedIdentity;current_git_identity=$identity;historical_git_identity_not_revalidated_as_current=$historicalGit;only_historical_git_metadata_separated=$true;parent_helper=$oldIdentity;periodic_stage=$stageIdentity;scientific_prerequisites=$scientificProof;default_CPU_Debug_build=$defaultBuildArtifacts;source_build=$h.source_build;source_directory_files=271;code_source_files=265;additional_text_files=6;current_source_and_snapshot_hashes_unchanged=$true;author_files=$authors;debug_build_gate=$debugGate;environment=$g.environment;tools=$h.tools;libraries=$h.libraries;objects=$h.objects;CPU_non_main_objects=85;helper_object=$(if(Test-Path -LiteralPath $obj){Entry $obj}else{$null});link_object_count=86;exact_link_closure_verified=$true;compile_call=$compileCall;link_call=$linkCall;runtime=$runtime;program=$(if(Test-Path -LiteralPath $exe){Entry $exe}else{$null});Rebuild_executed=$false;program_run=$false;endpoint_audit_executed=$false;input_PART_or_runtime_probe_is_later_owned_runner_duty=$true;public_gravity_accepted=$false;physical_acceptance=$false})
if(!$passed){throw 'Endpoint helper compile/link failed; preserve label and do not run'}
