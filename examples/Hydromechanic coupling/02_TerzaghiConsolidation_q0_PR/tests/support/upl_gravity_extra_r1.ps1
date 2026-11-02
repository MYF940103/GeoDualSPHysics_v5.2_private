param(
  [Parameter(Mandatory=$true)][ValidateSet('Build','Run')][string]$Mode,
  [Parameter(Mandatory=$true)][ValidateSet('balance','scales')][string]$Kind,
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^r[1-9][0-9]*$')][string]$BuildLabel='r1',
  [ValidatePattern('^r[1-9][0-9]*$')][string]$Label='r1',
  [ValidateSet('norm','standard')][string]$GammaPolicy='norm',
  [switch]$ExecutionAuthorized
)
# Explicit helper Build OR one component Run. No Rebuild/old-main/solver/Git action.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src';$logs=Join-Path $t 'logs'
$name="upl_gravity_${Kind}_${Configuration}_${Label}";$helper=Join-Path $t "outputs\${name}_helper";$runout=Join-Path $t "outputs\${name}_run"
$newHelper=Join-Path $logs ($name+'.helper.json');$runPath=Join-Path $logs ($name+'.run.json');$checkPath=Join-Path $logs ($name+'.check.json')
$oldHelper=Join-Path $logs "upl_gravity_cpu_${Configuration}_${BuildLabel}.helper.json";$cpp=Join-Path $t "support\upl_gravity_${Kind}_r1.cpp";$fixtureNote=Join-Path $t "notes\upl_gravity_${Kind}_r1.json";$note=Join-Path $t 'notes\upl_gravity_extra_r1.json'
function Entry([string]$p){$f=Get-Item -Force -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function ReadJson([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained label protected: $p"}}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 24)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Owned($tool,[string[]]$argv,[string]$suffix){
  $log=Join-Path $logs ($name+'_'+$suffix+'.log');$receipt=Join-Path $logs ($name+'_'+$suffix+'.call.json');Fresh @($log,$receipt);Verify @($tool);[IO.File]::WriteAllBytes($log,[byte[]]@())
  $start=[DateTime]::UtcNow.ToString('o');$code=$null;$invokeFailure=$null;$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null
  Push-Location $src;try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$invokeFailure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldAction}
  $typed=$code -is [int];Save $receipt ([ordered]@{program=$tool;arguments=$argv;working_directory=$src;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=$typed;owned_call_exited=$typed;exit_code=$code;invocation_failure=$invokeFailure;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);physical_acceptance=$false});Verify @($tool);return (Entry $receipt)
}
function PassedCall($e){Verify @($e);$c=ReadJson $e.path;if(!$c.typed_LASTEXITCODE_captured_immediately -or !$c.owned_call_exited -or $c.exit_code -ne 0){throw 'Owned typed-exit0 call required'};Verify @($c.program,$c.log);return $c}
function MainGate([string]$cfg){$p=Join-Path $logs "upl_gravity_cpu_${cfg}_${BuildLabel}.check.json";$d=ReadJson $p;if(!$d.passed -or $d.completed_physical_steps -ne 0 -or $d.physical_acceptance){throw 'Passed current-source main gravity component required'};Verify @($d.source_build,$d.helper,$d.call,$d.source_run,$d.completion);Verify $d.files;[void](PassedCall $d.call);return (Entry $p)}
if(!$ExecutionAuthorized){throw 'Root full source/recipe read and explicit single-action authorization required'}
$mainGates=@(MainGate 'DebugCPU');if($Configuration -eq 'ReleaseCPU'){$mainGates+=MainGate 'ReleaseCPU';$dp=Join-Path $logs "upl_gravity_${Kind}_DebugCPU_${Label}.check.json";$d=ReadJson $dp;if(!$d.passed -or $d.kind -cne $Kind -or $d.build_label -cne $BuildLabel -or ($Kind -eq 'scales' -and $d.gamma_policy -cne $GammaPolicy)){throw 'Same-kind/label/policy Debug extra component must pass before Release'};Verify @($d.helper,$d.call,$d.source_run,$d.completion);Verify $d.files;[void](PassedCall $d.call);$mainGates+=Entry $dp}
$h=ReadJson $oldHelper;if(!$h.passed -or $h.status -cne 'actual_authoritative_CPU_objects_helper_linked_not_run' -or $h.configuration -cne $Configuration -or $h.label -cne $BuildLabel -or $h.CPU_non_main_objects -ne 85 -or $h.link_object_count -ne 86 -or !$h.exact_link_closure_verified){throw 'Sealed85+1 main helper recipe required'}
Verify @($h.source_build);$b=ReadJson $h.source_build.path;if(!$b.passed -or $b.status -cne 'authoritative_CPU_Rebuild_passed_no_program_run' -or $b.configuration -cne $Configuration -or $b.label -cne $BuildLabel -or @($b.objects).Count -ne 86){throw 'Matching authoritative current CPU Rebuild required'}
function VerifyBase {
  Verify @($baseIdentity,$h.source_build);Verify $h.inputs;Verify $h.author_files;Verify $h.tools;Verify $h.libraries;Verify $h.objects;Verify @($h.program,$h.helper_object,$h.compile_call,$h.link_call);foreach($r in $h.runtime){Verify @($r.original,$r.copy)}
  Verify $b.inputs;Verify $b.source;Verify $b.author_files;Verify $b.protected_canonical_GPU_six_and_CPU_two;Verify @($b.program,$b.project_call);foreach($r in $b.current_source_snapshot){Verify @($r.original,$r.snapshot)};foreach($r in $b.objects){Verify @($r.source,$r.object)};foreach($r in $b.runtime){Verify @($r.original,$r.copy)}
}
$baseIdentity=Entry $oldHelper;VerifyBase;$cc=PassedCall $h.compile_call;$lc=PassedCall $h.link_call
if($Mode -eq 'Build'){
  Fresh @($helper,$newHelper,$runout,$runPath,$checkPath)
  $authors=@($PSCommandPath,$note,$cpp,$fixtureNote,(Join-Path $t 'support\upl_p2_feedback_harness_r1.cpp'),(Join-Path $t 'notes\upl_p2_feedback_r1.json'))|ForEach-Object {Entry $_}
  # Consume only the already-sealed compiler environment. No setup shell or old program.
  foreach($key in @('INCLUDE','LIB','VCToolsInstallDir','WindowsSdkDir','WindowsSDKVersion')){[Environment]::SetEnvironmentVariable($key,[string]$h.environment.selected.$key,'Process')}
  $env:PATH=([IO.Path]::GetDirectoryName($cc.program.path))+';'+$env:PATH
  $oldCpp=Join-Path $t 'support\upl_gravity_cpu_r1.cpp';$oldDir=Split-Path -Parent $h.program.path;$obj=Join-Path $helper 'helper.obj';$exe=Join-Path $helper "upl_gravity_${Kind}_r1.exe"
  $compile=@();$sourceRemap=0;$fo=0;$fd=0;$deps=0
  foreach($a in $cc.arguments){if($a -ieq $oldCpp){$compile+=$cpp;$sourceRemap++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fd'+(Join-Path $helper 'compile.pdb');$fd++}elseif($a -ieq (Join-Path $oldDir 'compile.dependencies.json')){$compile+=Join-Path $helper 'compile.dependencies.json';$deps++}else{$compile+=$a}}
  if($sourceRemap -ne 1 -or $fo -ne 1 -or $fd -ne 1 -or $deps -ne 1){throw 'Exact source/Fo/Fd/dependency remaps required'}
  $link=@();$objectRemap=0;$exeRemap=0;$pdbRemap=0
  foreach($a in $lc.arguments){if($a -ieq $h.helper_object.path){$link+=$obj;$objectRemap++}elseif($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$link+='/OUT:'+$exe;$exeRemap++}elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$link+='/PDB:'+(Join-Path $helper 'link.pdb');$pdbRemap++}else{$link+=$a}}
  if($objectRemap -ne 1 -or $exeRemap -ne 1 -or $pdbRemap -ne $(if($Configuration -eq 'DebugCPU'){1}else{0})){throw 'Exact helper/OUT/PDB remaps required'}
  $linkObjects=@($link|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)});$unchanged=@($linkObjects|Where-Object {$_ -ine $obj});$expected=@($h.objects.path|Sort-Object);if($linkObjects.Count -ne 86 -or $unchanged.Count -ne 85 -or @(Compare-Object ($unchanged|Sort-Object) $expected).Count){throw 'Unchanged85+newhelper1 linker closure required'}
  [void](New-Item -ItemType Directory -Path $helper);$compileCall=Owned $cc.program $compile 'Compile';$compileDone=ReadJson $compileCall.path;$linkCall=$null
  if($compileDone.typed_LASTEXITCODE_captured_immediately -and $compileDone.exit_code -eq 0){$linkCall=Owned $lc.program $link 'Link'}
  $linkDone=if($linkCall){ReadJson $linkCall.path}else{$null};$passed=$compileDone.typed_LASTEXITCODE_captured_immediately -and $compileDone.exit_code -eq 0 -and $null -ne $linkDone -and $linkDone.typed_LASTEXITCODE_captured_immediately -and $linkDone.exit_code -eq 0
  $runtime=@();if($passed){foreach($r in $h.runtime){$dest=Join-Path $helper ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $dest;$copy=Entry $dest;if($copy.sha256 -ine $r.copy.sha256 -or $copy.bytes -ne $r.copy.bytes){throw 'Runtime copy differs'};$runtime+=@{original=$r.copy;copy=$copy}}}
  VerifyBase;Verify @($baseIdentity);Verify $authors
  Save $newHelper ([ordered]@{passed=$passed;status=$(if($passed){'actual_authoritative_CPU_objects_extra_helper_linked_not_run'}else{'extra_helper_build_failed_retained'});kind=$Kind;configuration=$Configuration;label=$Label;build_label=$BuildLabel;parent_helper=$baseIdentity;source_build=$h.source_build;prerequisites=$mainGates;author_files=$authors;tools=$h.tools;libraries=$h.libraries;objects=$h.objects;CPU_non_main_objects=85;helper_object=$(if(Test-Path -LiteralPath $obj){Entry $obj}else{$null});link_object_count=86;exact_link_closure_verified=$true;compile_call=$compileCall;link_call=$linkCall;runtime=$runtime;program=$(if(Test-Path -LiteralPath $exe){Entry $exe}else{$null});program_run=$false;physical_acceptance=$false})
  if(!$passed){throw 'Extra helper compile/link failed; preserve label and do not run'};return
}
Fresh @($runout,$runPath,$checkPath);$n=ReadJson $newHelper;if(!$n.passed -or $n.status -cne 'actual_authoritative_CPU_objects_extra_helper_linked_not_run' -or $n.kind -cne $Kind -or $n.configuration -cne $Configuration -or $n.label -cne $Label -or $n.build_label -cne $BuildLabel -or $n.parent_helper.sha256 -ine $baseIdentity.sha256){throw 'Matching fresh extra helper required'}
function VerifyExtra{Verify @($n.parent_helper,$n.source_build);Verify $n.prerequisites;Verify $n.author_files;Verify $n.tools;Verify $n.libraries;Verify $n.objects;Verify @($n.program,$n.helper_object,$n.compile_call,$n.link_call);foreach($r in $n.runtime){Verify @($r.original,$r.copy)}}
VerifyExtra;[void](PassedCall $n.compile_call);[void](PassedCall $n.link_call);$argv=@('--out',$runout);if($Kind -eq 'scales'){$argv+=@('--gamma-policy',$GammaPolicy)}
$call=Owned $n.program $argv 'Component';$owned=ReadJson $call.path;$files=@();if(Test-Path -LiteralPath $runout){$files=@(Get-ChildItem -LiteralPath $runout -File|Sort-Object Name|ForEach-Object {Entry $_.FullName})}
Save $runPath ([ordered]@{kind=$Kind;configuration=$Configuration;label=$Label;build_label=$BuildLabel;gamma_policy=$(if($Kind -eq 'scales'){$GammaPolicy}else{$null});source_build=$h.source_build;helper=(Entry $newHelper);call=$call;files=$files;owned_completed=$owned.owned_call_exited;exit_code=$owned.exit_code;physical_acceptance=$false})
if(!$owned.typed_LASTEXITCODE_captured_immediately -or $owned.exit_code -ne 0){throw 'Extra component failed; preserve completed outputs, no automatic retry'}
$donePath=Join-Path $runout 'completion.json';$done=ReadJson $donePath
if(!$done.passed -or $done.stage -cne "upl_gravity_${Kind}_r1" -or $done.physical_acceptance){throw 'Extra component completion/scope not passed'}
if($Kind -eq 'balance'){if($done.cases -ne 4 -or $done.native_rows -ne 72 -or $done.actual_force_ct_calls -ne 4 -or $done.actual_complete_rate_calls -ne 4 -or !$done.independent_float_pair_momentum_reference -or !$done.prior_rounding_and_decomposition_bounds -or !$done.continuous_equilibrium_residual_is_descriptive -or $done.production_modified -or $done.public_guard_changed -or $done.wall_tested -or $done.actual_Run_or_ComputeStep_called -or $done.completed_physical_steps -ne 0 -or $done.mechanical_hydrostatic_well_balance_accepted){throw 'Balance counts/conditional scope differs'}}
else{if($done.cases -ne 20 -or $done.gamma_policy -cne $GammaPolicy){throw 'Scales counts/oracle policy differs'}}
VerifyBase;VerifyExtra;Verify $files
Save $checkPath ([ordered]@{passed=$true;kind=$Kind;configuration=$Configuration;label=$Label;build_label=$BuildLabel;gamma_policy=$(if($Kind -eq 'scales'){$GammaPolicy}else{$null});parent_helper=$baseIdentity;helper=(Entry $newHelper);call=$call;source_run=(Entry $runPath);completion=(Entry $donePath);files=$files;CPP_completion_gates_passed=$true;independent_full_numeric_review_performed_by_driver=$false;no_Rebuild_or_old_main=$true;no_automatic_next_action=$true;physical_acceptance=$false})
