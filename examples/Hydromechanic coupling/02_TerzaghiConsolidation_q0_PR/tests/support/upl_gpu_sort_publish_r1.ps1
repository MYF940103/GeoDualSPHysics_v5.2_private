param([ValidateSet('List','Seal','Stage')][string]$Mode='List',[switch]$CpuDebugExitObserved0,[switch]$StageAuthorized,[string]$ReviewedManifestSha256='')
# GPU double-copy/sort utility checkpoint only; no build, program, solver, commit or push.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$base='25f40dc13b8bfacf698aab3e7668ec2afb252788'
$target=Join-Path $tests 'logs\upl_gpu_sort_publish_r1.json'
$four=@('JCellDivGpu.h','JCellDivGpu.cpp','JCellDivGpu_ker.h','JCellDivGpu_ker.cu')
function Entry([string]$p){$f=Get-Item -LiteralPath $p;if(!$f.FullName.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Escaped repository'};[pscustomobject]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$p=if([IO.Path]::IsPathRooted($r.path)){$r.path}else{Join-Path $repo $r.path};$a=Entry $p;if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function Candidates {
  $paths=@($four|ForEach-Object {Join-Path $repo ('src\source\'+$_)})
  foreach($p in @('support\upl_gpu_sort_r1.cpp','support\upl_gpu_sort_r1.ps1','notes\upl_gpu_sort_r1.json','support\upl_gpu_sort_publish_r1.ps1','notes\upl_gpu_sort_review_r1.md','notes\upl_gpu_state_plan_r1.md')){$paths+=Join-Path $tests $p}
  $paths+=Get-ChildItem -LiteralPath (Join-Path $tests 'logs') -File|Where-Object {($_.Name -eq 'upl_gpu_sort_r1.baseline.json' -or $_.Name -eq 'upl_gpu_sort_CPU_Debug_default_r1.build.log' -or $_.Name -match '^upl_gpu_sort_(Debug|Release)_r1[._]') -and $_.Extension -in '.json','.log'}|ForEach-Object {$_.FullName}
  foreach($name in $four){$paths+=Join-Path $tests ('outputs\upl_gpu_sort_prebuild_r1\'+$name)}
  foreach($cfg in @('Debug','Release')){
    foreach($name in $four){$paths+=Join-Path $tests ('outputs\upl_gpu_sort_'+$cfg+'_r1\'+$name)}
    foreach($leaf in @('cases.csv','complete.json')){$paths+=Join-Path $tests ('outputs\upl_gpu_sort_'+$cfg+'_r1_data\'+$leaf)}
  }
  @($paths|Sort-Object -Unique)
}
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Explicit StageAuthorized and exact reviewed manifest SHA required'}
  $m=Get-Content -Raw -LiteralPath $target|ConvertFrom-Json
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  if($code -or !$m.ready_for_root_review -or $m.base -ne $base -or $head -ne $base){throw 'Changed Git base or unready manifest'}
  Verify $m.files;$paths=@($m.files.path)+@($target.Substring($repo.Length+1).Replace('\','/'))
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';$index=@(& git -C $repo -c core.quotepath=false diff --cached --name-only);$code=$LASTEXITCODE;$ErrorActionPreference=$old
  if($code){throw 'Cannot inspect index; no stage attempted'}
  foreach($p in $index){if($p -and $p -notin $paths){throw 'Unrelated staged changes preserved'}}
  for($i=0;$i -lt $paths.Count;$i+=20){$last=[Math]::Min($i+19,$paths.Count-1);$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$msg=& git -C $repo --literal-pathspecs add -f -- @($paths[$i..$last]) 2>&1;$code=$LASTEXITCODE;$ErrorActionPreference=$old;$msg|Out-Host;if($code){throw 'Stage failed; preserve partial index and inspect'}}
  Write-Output "STAGED $($paths.Count) explicit paths only; no commit/push";exit 0
}
$required=@('logs\upl_gpu_sort_r1.baseline.json','logs\upl_gpu_sort_Debug_r1.check.json','logs\upl_gpu_sort_Release_r1.check.json','logs\upl_gpu_sort_CPU_Debug_default_r1.build.log')
$paths=Candidates
$missing=@($paths|Where-Object {!(Test-Path -LiteralPath $_)})+@($required|ForEach-Object {Join-Path $tests $_}|Where-Object {!(Test-Path -LiteralPath $_)})
$files=@(foreach($p in $paths){if(Test-Path -LiteralPath $p){$e=Entry $p;if($e.bytes -gt 2097152 -or [IO.Path]::GetExtension($p) -notin '.h','.cpp','.cu','.ps1','.json','.md','.csv','.log'){throw "Unapproved/large candidate: $p"};$e}})
if($Mode -eq 'List'){[pscustomobject]@{base=$base;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;missing=@($missing|Sort-Object -Unique);CPU_exit_requires_root_observation_at_Seal=$true;files=$files;Git_mutated=$false};return}
if((Test-Path -LiteralPath $target) -or $missing.Count -or !$CpuDebugExitObserved0){throw 'Fresh complete evidence and explicit root CPU Debug exit0 observation required'}
$b=Get-Content -Raw -LiteralPath (Join-Path $tests 'logs\upl_gpu_sort_r1.baseline.json')|ConvertFrom-Json
if($b.status -ne 'pre_four_edit_source_and_old_GPU_binaries_frozen' -or $b.root_verified_CPU_checkpoint -ne $base -or $b.old_four_sources.Count -ne 4){throw 'Wrong pre-edit baseline'}
Verify $b.inputs
Verify @($b.source|Where-Object {[IO.Path]::GetFileName($_.path) -notin $four})
foreach($r in $b.old_GPU_runtime){Verify @($r.original,$r.snapshot)}
$deltas=@();$insertions=0
foreach($oldsource in $b.old_four_sources){
  Verify @($oldsource.snapshot)
  $current=Entry $oldsource.original.path
  $oldlines=[IO.File]::ReadAllLines($oldsource.snapshot.path);$newlines=[IO.File]::ReadAllLines($oldsource.original.path)
  $j=0
  foreach($line in $newlines){if($j -lt $oldlines.Count -and $line -ceq $oldlines[$j]){$j++}}
  if($j -ne $oldlines.Count){throw 'Original source lines removed/changed; not insertion-only'}
  $added=$newlines.Count-$oldlines.Count;$insertions+=$added
  $deltas+=@{current=$current;baseline=$oldsource.snapshot;added_lines=$added;old_lines_preserved_in_order=$true}
}
if($insertions -ne 31){throw 'Expected exactly31 inserted source lines'}
$checks=@()
foreach($cfg in @('Debug','Release')){
  $path=Join-Path $tests ('logs\upl_gpu_sort_'+$cfg+'_r1.check.json');$c=Get-Content -Raw -LiteralPath $path|ConvertFrom-Json
  if(!$c.passed -or $c.configuration -ne $cfg -or $c.cases -ne 576 -or $c.direct_cases -ne 288 -or $c.wrapper_cases -ne 288 -or !$c.canonical_GPU_unchanged -or $c.actual_cell_division_tested -or $c.J_state_or_physics_tested -or $c.default_OFF_native_solver_regression_passed){throw 'Wrong actual component scope/count'}
  Verify @($c.build,$c.completion,$c.call);Verify $c.files
  $done=Get-Content -Raw -LiteralPath $c.completion.path|ConvertFrom-Json
  if(!$done.passed -or $done.cases -ne 576 -or $done.zero_size_cases -ne 96 -or !$done.byte_exact -or !$done.source_unchanged -or !$done.map_unchanged -or !$done.tail_unchanged -or !$done.actual_class_wrapper -or $done.actual_cell_division_tested -or $done.physics_or_J_state_tested){throw 'Component completion contract differs'}
  $rows=@(Import-Csv -LiteralPath (Join-Path $tests ('outputs\upl_gpu_sort_'+$cfg+'_r1_data\cases.csv')))
  if($rows.Count -ne 576 -or @($rows|Where-Object {$_.output_exact -ne 'true' -or $_.source_unchanged -ne 'true' -or $_.map_unchanged -ne 'true' -or $_.tail_unchanged -ne 'true'}).Count){throw 'Not all576 native copy rows passed'}
  $call=Get-Content -Raw -LiteralPath $c.call.path|ConvertFrom-Json
  if($call.exit_code -ne 0){throw 'Actual component owned-call exit nonzero'};Verify @($call.log)
  $build=Get-Content -Raw -LiteralPath $c.build.path|ConvertFrom-Json
  if($build.status -ne 'full_GPU_Rebuild_and_actual_object_fixture_link_passed_not_run'){throw 'Authoritative full GPU build unavailable'}
  Verify @($build.source_freeze,$build.project_call,$build.compile_call,$build.link_call)
  $s=Get-Content -Raw -LiteralPath $build.source_freeze.path|ConvertFrom-Json
  if($s.source.Count -ne 4){throw 'Four new source snapshots required'}
  foreach($r in $s.source){Verify @($r.original,$r.snapshot)}
  if($cfg -eq 'Debug'){
    $log=[IO.File]::ReadAllText($call.log.path)
    if(!$c.memcheck_executed -or !$c.memcheck_zero_errors -or $log -notmatch 'ERROR SUMMARY:\s*0 errors' -or $log -notmatch 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'){throw 'Actual Debug zero-error/zero-leak memcheck missing'}
  }
  $checks+=Entry $path
}
$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$headCode=$LASTEXITCODE;$branch=& git -C $repo branch --show-current;$branchCode=$LASTEXITCODE;$ErrorActionPreference=$old
if($headCode -or $branchCode -or $head -ne $base){throw 'Exact checkpoint Git base changed'}
$m=[ordered]@{base=$head;branch=$branch;ready_for_root_review=$true;scope='GPU single-double sorting overload utility only';files=$files;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;checks=$checks;inserted_source_lines=$insertions;source_delta=$deltas;canonical_GPU_current_and_baseline_archives_hash_verified=$true;CPU_default_Debug_build=@{log=(Entry (Join-Path $tests 'logs\upl_gpu_sort_CPU_Debug_default_r1.build.log'));exit_code=0;provenance='Root direct tool observation: session6934 terminal exit0, explicitly confirmed at Seal';exit_inferred_from_log_text=$false;native_solver_regression_tested=$false};GPU_Debug_memcheck_zero_errors_and_leaks=$true;component_cases_per_configuration=576;actual_cell_division_tested=$false;GPU_J_state_or_physics_tested=$false;default_OFF_native_solver_regression_passed=$false;GPU_public_entry_admitted=$false;source_snapshot_policy='old4 plus Debug/Release new4 text snapshots only; not all-source copy';next_plan=(Entry (Join-Path $tests 'notes\upl_gpu_state_plan_r1.md'));excluded='exe,obj,lib,pdb,ilk,binlog,runtime DLL/config,all-source text copies,raw solver outputs and unrelated dirty files';raw_program_cloud_backup_claimed=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($target,($m|ConvertTo-Json -Depth 14)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) paths, $($m.bytes) bytes; inspect before explicit Stage"

