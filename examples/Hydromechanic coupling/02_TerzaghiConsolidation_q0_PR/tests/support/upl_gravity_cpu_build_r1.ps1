param(
  [Parameter(Mandatory=$true)][ValidateSet('Rebuild','BuildHelper','RunHelper')][string]$Mode,
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^r[1-9][0-9]*$')][string]$Label='r1',
  [ValidateSet('norm','standard')][string]$GammaPolicy='norm',
  [switch]$ExecutionAuthorized
)
# One explicit action/configuration/label only. No GPU build, canonical solver,
# GenCase, accepted-control rerun, restart, help, Git command or automatic next action.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src';$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs'
$name="upl_gravity_cpu_${Configuration}_${Label}";$main=Join-Path $out ($name+'_main');$snapshot=Join-Path $out ($name+'_source');$helper=Join-Path $out ($name+'_helper');$runout=Join-Path $out ($name+'_run')
$int=[IO.Path]::GetFullPath((Join-Path $src "VS\Intermediate\$name"));$buildPath=Join-Path $logs ($name+'.build.json');$helperPath=Join-Path $logs ($name+'.helper.json');$runPath=Join-Path $logs ($name+'.run.json');$checkPath=Join-Path $logs ($name+'.check.json')
$cpp=Join-Path $t 'support\upl_gravity_cpu_r1.cpp';$fixtureNote=Join-Path $t 'notes\upl_gravity_cpu_r1.json';$note=Join-Path $t 'notes\upl_gravity_cpu_build_r1.json'
$sln=Join-Path $src 'VS\DualSPHysics5ReCpu_vs2022.sln';$project=Join-Path $src 'VS\DualSPHysics5ReCpu.vcxproj';$msbuild='D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe';$vc='D:\Program Files\VS2022\VC\Tools\MSVC\14.36.32532';$cl=Join-Path $vc 'bin\Hostx64\x64\cl.exe';$linker=Join-Path $vc 'bin\Hostx64\x64\link.exe';$vsdev='D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat'
$base='ff1bd714b561f0d9f692387d5443ec03b096de13'
function Entry([string]$p){$f=Get-Item -Force -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Frozen input changed: $($r.path)"}}}
function ReadJson([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained label protected: $p"}}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 24)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function AuthorFiles {
  Verify @(@{path=$cpp;bytes=16606;sha256='c5235f9b2c7d7dcd85bb4d2d5c8a2d308c06fa32fa16eb7fc2f95d3abde95e6e'},@{path=$fixtureNote;bytes=9102;sha256='7c01536b76d7467c5ab99247fcd9cc257b32cddfd404a735c397227b38c41bf6'})
  @($PSCommandPath,$note,$cpp,$fixtureNote,(Join-Path $t 'support\upl_p2_feedback_harness_r1.cpp'),(Join-Path $t 'notes\upl_p2_feedback_r1.json'))|ForEach-Object {Entry $_}
}
function GitIdentity {
  # Read existing worktree metadata only; no Git program or write is permitted.
  $dot=Join-Path $repo '.git';$meta=@(Entry $dot);$text=[IO.File]::ReadAllText($dot).Trim();if(!$text.StartsWith('gitdir: ')){throw 'Expected existing worktree gitdir file'}
  $gd=[IO.Path]::GetFullPath($text.Substring(8));$headPath=Join-Path $gd 'HEAD';$meta+=Entry $headPath;$head=[IO.File]::ReadAllText($headPath).Trim()
  if($head.StartsWith('ref: ')){$commonPath=Join-Path $gd 'commondir';$meta+=Entry $commonPath;$common=[IO.Path]::GetFullPath((Join-Path $gd ([IO.File]::ReadAllText($commonPath).Trim())));$ref=Join-Path $common $head.Substring(5);$meta+=Entry $ref;$head=[IO.File]::ReadAllText($ref).Trim()}
  if($head -cne $base){throw 'Declared current checkpoint differs; review a new stage before building'};@{head=$head;metadata=$meta;git_command_executed=$false}
}
function ProjectRows {
  [xml]$x=[IO.File]::ReadAllText($project);$rows=@()
  foreach($n in $x.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false;foreach($e in $n.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -ceq "'`$(Configuration)|`$(Platform)'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -ceq 'true'}}
    if(!$excluded){$file=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $n.GetAttribute('Include')));$rows+=@{source=(Entry $file);stem=[IO.Path]::GetFileNameWithoutExtension($file)}}
  }
  if($rows.Count -ne 86 -or @($rows|Where-Object {$_.stem -ceq 'main'}).Count -ne 1 -or @($rows.stem|Sort-Object -Unique).Count -ne 86){throw 'Authoritative CPU86/85 object inventory changed'};return $rows
}
function ProtectedFiles {
  $baseline=ReadJson (Join-Path $logs 'upl_gpu_public_r1.baseline.json');if(@($baseline.canonical_GPU).Count -ne 6){throw 'Protected GPU six inventory missing'};Verify $baseline.canonical_GPU
  @($baseline.canonical_GPU)+@(Entry (Join-Path $repo 'bin\windows\DualSPHysics5.2CPU_win64.exe');Entry (Join-Path $repo 'bin\windows\DualSPHysics5.2CPU_win64_debug.exe'))
}
function OwnedCall($tool,[string[]]$argv,[string]$label){
  Verify @($tool);$log=Join-Path $logs ($label+'.log');$receipt=Join-Path $logs ($label+'.call.json');Fresh @($log,$receipt);[IO.File]::WriteAllBytes($log,[byte[]]@())
  $start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null
  Push-Location $src;try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$old}
  $typed=($code -is [int]);Save $receipt ([ordered]@{program=$tool;arguments=$argv;working_directory=$src;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=$typed;owned_call_exited=$typed;exit_code=$code;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);physical_acceptance=$false});Verify @($tool);return (Entry $receipt)
}
function EnvironmentForHelper {
  # Same VS2022 x64 environment mechanism as the retained successful CPU recipe.
  # Full environment is consumed in memory only, never dumped to a log/receipt.
  $cmd=Entry $env:ComSpec;$dev=Entry $vsdev;$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null
  $lines=& $cmd.path /d /c ('call "'+$vsdev+'" -arch=x64 -host_arch=x64 >nul && set');$code=$LASTEXITCODE;$ErrorActionPreference=$old
  if($code -isnot [int] -or $code -ne 0){throw 'VS environment setup did not return typed exit0'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  @{tools=@($cmd,$dev);exit_code=$code;selected=@{VCToolsInstallDir=$env:VCToolsInstallDir;WindowsSdkDir=$env:WindowsSdkDir;WindowsSDKVersion=$env:WindowsSDKVersion;INCLUDE=$env:INCLUDE;LIB=$env:LIB};full_environment_persisted=$false}
}
if(!$ExecutionAuthorized){throw 'Root full source/recipe read and explicit single-action authorization required'}
if($Mode -eq 'Rebuild'){
  Fresh @($main,$snapshot,$int,$buildPath,$helper,$helperPath,$runout,$runPath,$checkPath);if($int -match '\s' -or !$int.StartsWith((Join-Path $src 'VS\Intermediate\'),[StringComparison]::OrdinalIgnoreCase)){throw 'New no-space project IntDir required'}
  $identity=GitIdentity;$authors=@(AuthorFiles);$rows=@(ProjectRows);$protected=@(ProtectedFiles);$sources=@(Get-ChildItem -LiteralPath (Join-Path $src 'source') -File|Sort-Object Name|ForEach-Object {Entry $_.FullName})
  $props=@('Microsoft.Cpp.Default.props','Microsoft.Cpp.props','Microsoft.Cpp.targets','Microsoft.CPP.UpgradeFromVC71.props')|ForEach-Object {Entry (Join-Path 'D:\Program Files\VS2022\MSBuild\Microsoft\VC\v170' $_)}
  $userProps=Join-Path $env:LOCALAPPDATA 'Microsoft\MSBuild\v4.0\Microsoft.Cpp.x64.user.props';if(Test-Path -LiteralPath $userProps){$props+=Entry $userProps}
  $inputs=@($authors)+@(Entry $sln;Entry $project;Entry $msbuild;Entry $cl;Entry $linker;Entry $vsdev;Entry 'D:\Program Files\VS2022\VC\Auxiliary\Build\Microsoft.VCToolsVersion.default.txt')+$props+$identity.metadata
  [void](New-Item -ItemType Directory -Path $snapshot);$copies=@();foreach($r in $sources){$dest=Join-Path $snapshot ([IO.Path]::GetFileName($r.path));Copy-Item -LiteralPath $r.path -Destination $dest;$copy=Entry $dest;if($copy.bytes -ne $r.bytes -or $copy.sha256 -ine $r.sha256){throw 'Full current source snapshot copy mismatch'};$copies+=@{original=$r;snapshot=$copy}}
  [void](New-Item -ItemType Directory -Path $main);$buildArguments=@($sln,'/m','/t:Rebuild',"/p:Configuration=$Configuration",'/p:Platform=x64','/v:minimal',('/p:OutDir='+$main.Replace('\','/')+'/'),('/p:IntDir='+$int.Replace('\','/')+'/'))
  $call=OwnedCall (Entry $msbuild) $buildArguments ($name+'_Rebuild');$owned=ReadJson $call.path;Verify $inputs;Verify $sources;Verify $protected;Verify $authors
  $objects=@();foreach($r in $rows){$obj=Join-Path $int ($r.stem+'.obj');if(Test-Path -LiteralPath $obj){$objects+=@{source=$r.source;object=(Entry $obj);stem=$r.stem}}}
  $filename=if($Configuration -eq 'DebugCPU'){'DualSPHysics5.2CPU_win64_debug.exe'}else{'DualSPHysics5.2CPU_win64.exe'};$program=Join-Path $main $filename
  $passed=$owned.typed_LASTEXITCODE_captured_immediately -and $owned.exit_code -eq 0 -and $objects.Count -eq 86 -and (Test-Path -LiteralPath $program)
  $runtime=@();if($passed){foreach($r in @($protected|Where-Object {[IO.Path]::GetExtension($_.path) -ieq '.dll' -or [IO.Path]::GetFileName($_.path) -ieq 'DsphConfig.xml'})){$dest=Join-Path $main ([IO.Path]::GetFileName($r.path));Copy-Item -LiteralPath $r.path -Destination $dest;$copy=Entry $dest;if($copy.bytes -ne $r.bytes -or $copy.sha256 -ine $r.sha256){throw 'Isolated main runtime copy differs'};$runtime+=@{original=$r;copy=$copy}}}
  Save $buildPath ([ordered]@{passed=$passed;status=$(if($passed){'authoritative_CPU_Rebuild_passed_no_program_run'}else{'authoritative_CPU_Rebuild_failed_retained'});configuration=$Configuration;label=$Label;git_base=$identity.head;git_identity_metadata=$identity.metadata;current_source_snapshot=$copies;possible_dirty_source_captured_as_full_bytes=$true;git_diff_or_clean_claimed=$false;inputs=$inputs;author_files=$authors;source=$sources;project=(Entry $project);active_CPU_translation_units=86;non_main_CPU_objects=85;objects=$objects;main_object_excluded_from_helper=$true;no_space_IntDir=$int;isolated_OutDir=$main;program=$(if(Test-Path -LiteralPath $program){Entry $program}else{$null});runtime=$runtime;protected_canonical_GPU_six_and_CPU_two=$protected;project_call=$call;no_GPU_build=$true;program_run=$false;physical_acceptance=$false})
  if(!$passed){throw 'Full isolated CPU Rebuild failed; preserve all outputs and label'};return
}
$build=ReadJson $buildPath;if(!$build.passed -or $build.status -ne 'authoritative_CPU_Rebuild_passed_no_program_run' -or $build.configuration -ne $Configuration -or $build.label -ne $Label){throw 'Matching successful current-source CPU Rebuild required'}
function VerifyBuild {Verify $build.inputs;Verify $build.source;Verify $build.author_files;Verify $build.protected_canonical_GPU_six_and_CPU_two;Verify @($build.program,$build.project_call);foreach($r in $build.current_source_snapshot){Verify @($r.original,$r.snapshot)};foreach($r in $build.objects){Verify @($r.source,$r.object)};foreach($r in $build.runtime){Verify @($r.original,$r.copy)}}
VerifyBuild
if($Mode -eq 'BuildHelper'){
  Fresh @($helper,$helperPath);$envProof=EnvironmentForHelper;$recipePath=Join-Path $logs "upl_p3_actual_${Configuration}_r3.build.json";$recipe=ReadJson $recipePath
  if($recipe.status -ne 'built_not_run' -or $recipe.compile_exit -ne 0 -or $recipe.link_exit -ne 0 -or $recipe.configuration -ne $Configuration){throw 'Successful CPU Actual r3 recipe required'};Verify $recipe.libraries
  $rows=@(ProjectRows);$objects=@($build.objects|Where-Object {$_.stem -cne 'main'});if($objects.Count -ne 85){throw 'Exactly85 non-main CPU objects required'}
  $oldCpp=Join-Path $t 'support\upl_p3_actual_r3.cpp';$oldDir=Split-Path -Parent $recipe.program.path;$oldObj=Join-Path $oldDir 'upl_p3_actual_r3.obj';$obj=Join-Path $helper 'helper.obj';$exe=Join-Path $helper 'upl_gravity_cpu_r1.exe'
  $compile=@();$fo=0;$fd=0;$deps=0;$sourceRemap=0;foreach($a in $recipe.compile){if($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fd'+(Join-Path $helper 'compile.pdb');$fd++}elseif($a -ieq (Join-Path $oldDir 'compile.dependencies.json')){$compile+=Join-Path $helper 'compile.dependencies.json';$deps++}elseif($a -ieq $oldCpp){$compile+=$cpp;$sourceRemap++}else{$compile+=$a}}
  if($fo -ne 1 -or $fd -ne 1 -or $deps -ne 1 -or $sourceRemap -ne 1 -or $compile -notcontains '/std:c++17' -or $compile -notcontains '/fp:precise'){throw 'CPU compiler remaps or frozen flags differ'}
  $byStem=@{};foreach($r in $objects){$byStem[$r.stem]=$r.object};$link=@();$seen=@{};$helperRemap=0;$outRemap=0;$pdbRemap=0
  foreach($a in $recipe.link){if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$link+='/OUT:'+$exe;$outRemap++}elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$link+='/PDB:'+(Join-Path $helper 'link.pdb');$pdbRemap++}elseif($a -ieq $oldObj){$link+=$obj;$helperRemap++}elseif($a.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)){$stem=[IO.Path]::GetFileNameWithoutExtension($a);if(!$byStem.ContainsKey($stem)-or$seen.ContainsKey($stem)){throw 'Unexpected/duplicate old CPU object'};$link+=$byStem[$stem].path;$seen[$stem]=$true}else{$link+=$a}}
  if($seen.Count -ne 85 -or $helperRemap -ne 1 -or $outRemap -ne 1 -or $pdbRemap -ne $(if($Configuration -eq 'DebugCPU'){1}else{0})){throw 'Exact85+1 CPU linker closure differs'}
  $libraries=@();foreach($a in @($link|Where-Object {$_.EndsWith('.lib',[StringComparison]::OrdinalIgnoreCase)})){$found=@();foreach($dir in @((Join-Path $src 'lib\vs2022'))+@($env:LIB.Split(';')|Where-Object {$_})){if(Test-Path -LiteralPath (Join-Path $dir $a)){$found+=Join-Path $dir $a;break}};if($found.Count -ne 1){throw "CPU library unresolved: $a"};$libraries+=Entry $found[0]}
  $authors=@(AuthorFiles);[void](New-Item -ItemType Directory -Path $helper);$cc=OwnedCall (Entry $cl) $compile ($name+'_Compile');$ce=ReadJson $cc.path;$lc=$null
  if($ce.typed_LASTEXITCODE_captured_immediately -and $ce.exit_code -eq 0){$lc=OwnedCall (Entry $linker) $link ($name+'_Link')}
  $le=if($lc){ReadJson $lc.path}else{$null};$passed=$ce.typed_LASTEXITCODE_captured_immediately -and $ce.exit_code -eq 0 -and $null -ne $le -and $le.typed_LASTEXITCODE_captured_immediately -and $le.exit_code -eq 0
  $runtime=@();if($passed){foreach($r in $build.runtime){$dest=Join-Path $helper ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $dest;$copy=Entry $dest;if($copy.bytes -ne $r.copy.bytes -or $copy.sha256 -ine $r.copy.sha256){throw 'Helper runtime copy differs'};$runtime+=@{original=$r.copy;copy=$copy}}}
  VerifyBuild;Verify $authors;Verify $libraries;Save $helperPath ([ordered]@{passed=$passed;status=$(if($passed){'actual_authoritative_CPU_objects_helper_linked_not_run'}else{'CPU_helper_build_failed_retained'});configuration=$Configuration;label=$Label;source_build=(Entry $buildPath);inputs=@(Entry $recipePath)+$authors;author_files=$authors;environment=$envProof;tools=@(Entry $cl;Entry $linker);libraries=$libraries;objects=@($objects|ForEach-Object {$_.object});CPU_non_main_objects=85;helper_object=$(if(Test-Path -LiteralPath $obj){Entry $obj}else{$null});link_object_count=86;exact_link_closure_verified=$true;compile_call=$cc;link_call=$lc;runtime=$runtime;program=$(if(Test-Path -LiteralPath $exe){Entry $exe}else{$null});program_run=$false;physical_acceptance=$false})
  if(!$passed){throw 'CPU helper compile/link failed; preserve label, no run'};return
}
Fresh @($runout,$runPath,$checkPath);$h=ReadJson $helperPath;if(!$h.passed -or $h.status -ne 'actual_authoritative_CPU_objects_helper_linked_not_run' -or $h.source_build.sha256 -ine (Entry $buildPath).sha256 -or $h.link_object_count -ne 86){throw 'Matching85+1 helper build required'}
Verify $h.inputs;Verify $h.author_files;Verify $h.tools;Verify $h.libraries;Verify $h.objects;Verify @($h.program,$h.helper_object,$h.compile_call,$h.link_call);foreach($r in $h.runtime){Verify @($r.original,$r.copy)}
if($Configuration -eq 'ReleaseCPU'){$debug=ReadJson (Join-Path $logs "upl_gravity_cpu_DebugCPU_${Label}.check.json");if(!$debug.passed){throw 'Same-label Debug component must pass before Release component'}}
$call=OwnedCall $h.program @('--out',$runout,'--gamma-policy',$GammaPolicy) ($name+'_Component');$c=ReadJson $call.path;$files=@();if(Test-Path -LiteralPath $runout){$files=@(Get-ChildItem -LiteralPath $runout -File -Recurse|Sort-Object FullName|ForEach-Object {Entry $_.FullName})}
Save $runPath ([ordered]@{source_build=(Entry $buildPath);helper=(Entry $helperPath);gamma_policy=$GammaPolicy;call=$call;files=$files;owned_completed=$c.owned_call_exited;exit_code=$c.exit_code;completed_physical_steps=0;physical_acceptance=$false})
if(!$c.typed_LASTEXITCODE_captured_immediately -or $c.exit_code -ne 0){throw 'Actual CPU gravity component failed; preserve outputs, no automatic rerun'}
$donePath=Join-Path $runout 'completion.json';$done=ReadJson $donePath
if(!$done.passed -or $done.stage -cne 'upl_gravity_cpu_r1' -or $done.gamma_policy -cne $GammaPolicy -or !$done.gamma_policy_changes_oracle_only -or $done.field_cases -ne 48 -or $done.rate_flux_rows -ne 864 -or $done.actual_complete_rate_calls -ne 52 -or $done.actual_force_ct_calls -ne 4 -or $done.force_freefall_rows -ne 72 -or !$done.nonzero_Gravity_and_CSP_gravity -or !$done.prior_propagated_bounds -or !$done.independent_all_particle_reference -or $done.public_guard_changed -or $done.wall_tested -or $done.actual_Run_or_ComputeStep_called -or $done.completed_physical_steps -ne 0 -or $done.default_OFF_regression_executed -or $done.final_material_mobility_policy_accepted -or $done.mechanical_hydrostatic_well_balance_accepted -or $done.physical_acceptance){throw 'Gravity component completion/coverage/policy scope failed'}
$rateRows=@(Import-Csv -LiteralPath (Join-Path $runout 'rates_flux.csv'));$summaryRows=@(Import-Csv -LiteralPath (Join-Path $runout 'summary.csv'));$forceRows=@(Import-Csv -LiteralPath (Join-Path $runout 'force_freefall.csv'))
if($rateRows.Count -ne 864 -or $summaryRows.Count -ne 48 -or $forceRows.Count -ne 72){throw 'Complete declared CSV coverage required'}
VerifyBuild;Verify $h.inputs;Verify $h.author_files;Verify $h.objects;Verify $h.tools;Verify $h.libraries;Verify $files
Save $checkPath ([ordered]@{passed=$true;scope='Current-source actual CPU gravity helper manufactured component only; not an integrated physical run or public gravity unlock';configuration=$Configuration;label=$Label;gamma_policy=$GammaPolicy;source_build=(Entry $buildPath);helper=(Entry $helperPath);call=$call;source_run=(Entry $runPath);completion=(Entry $donePath);files=$files;own_CPP_gates_passed=$true;completed_physical_steps=0;no_old_control_rerun=$true;physical_acceptance=$false})
