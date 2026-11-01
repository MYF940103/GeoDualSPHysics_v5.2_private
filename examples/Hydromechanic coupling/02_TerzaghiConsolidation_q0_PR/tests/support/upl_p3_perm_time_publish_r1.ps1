param([ValidateSet('List','Seal','Stage')][string]$Mode='List',[switch]$StageAuthorized,[string]$ReviewedManifestSha256='')
# Exact time-cache stage only. Default List is read-only; no commit/push in any mode.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$expectedBase='834f39caa1ab8ac226d20407b1dda9a4c500a797'
$target=Join-Path $tests 'logs\upl_p3_perm_time_publish_r1.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[pscustomobject]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Candidates {
  $paths=@(Join-Path $repo 'src\source\JSphCpu.h')+@(Join-Path $repo 'src\source\JSphCpu.cpp')
  foreach($part in @('support','notes','logs')){
    $paths+=Get-ChildItem -LiteralPath (Join-Path $tests $part) -File|Where-Object {$_.Name -like 'upl_p3_perm_time_*' -and $_.Name -ne 'upl_p3_perm_time_publish_r1.json' -and $_.Extension -in '.cpp','.ps1','.py','.json','.log'}|ForEach-Object {$_.FullName}
  }
  # Exactly the current default-OFF label, including owned call/check/build records.
  $paths+=Get-ChildItem -LiteralPath (Join-Path $tests 'logs') -File|Where-Object {$_.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_p3_perm_time_r1[._]' -and $_.Extension -in '.json','.log'}|ForEach-Object {$_.FullName}
  $paths+=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
  foreach($leaf in @('JSphCpu.h','JSphCpu.cpp','JSphCpuSingle.cpp')){$paths+=Join-Path $tests ('outputs\upl_p3_perm_time_source_r1\'+$leaf)}
  foreach($leaf in @('upl_p3_perm_time_trajectory_r2.ps1','upl_p3_perm_time_trajectory_r2.json')){$paths+=Join-Path $tests ('outputs\upl_p3_perm_time_wrapper_precheck_r1\'+$leaf)}
  foreach($dir in (Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Directory)){
    if($dir.Name -match '^upl_p3_perm_time_(DebugCPU_r1|ReleaseCPU_r1|periodic_ReleaseCPU_r1|wall_ReleaseCPU_r2)$'){
      # Only new recipes and dependency tables; unchanged prior fixture snapshots are already backed up.
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'upl_p3_perm_time_r1.cpp','upl_p3_perm_time_run_r1.ps1','upl_p3_perm_time_component_r1.json','upl_p3_perm_time_trajectory_r1.ps1','upl_p3_perm_time_trajectory_r1.json','upl_p3_perm_time_trajectory_r2.ps1','upl_p3_perm_time_trajectory_r2.json','compile.dependencies.json'}|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_p3_perm_time_(DebugCPU|ReleaseCPU)_r1_(off|perm|time)$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.csv','.json' -or $_.Name -eq 'Run.out'}|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_p3_perm_time_(periodic_ReleaseCPU_r1|wall_ReleaseCPU_r2)_on_(c|h)$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'modes.csv','initial_source.csv','source_summary.csv','native_ids.csv','fixed_ids.csv','wall_audit.csv','endpoint_policy.csv','component.check.json','component.csv','offgrid_component.check.json','offgrid_component.csv','complete.json','Run.out'}|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_p3_perm_time_r1(_(state|pair|(open_)?s(8|128)_o[01]))?$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'compile.dependencies.json','observer_complete.json','observer_final.csv','state_complete.json','theta_pairs.csv','Run.csv','Run.out'}|ForEach-Object {$_.FullName}
    }
  }
  @($paths|Sort-Object -Unique)
}
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Explicit StageAuthorized and exact root-reviewed manifest SHA required'}
  $manifest=Get-Content -Raw -LiteralPath $target|ConvertFrom-Json
  $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$base=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  if($code -or !$manifest.ready_for_root_review -or $manifest.base -ne $expectedBase -or $base -ne $expectedBase){throw 'Changed Git base or unready manifest'}
  foreach($row in $manifest.files){$now=Entry (Join-Path $repo $row.path);if($now.bytes -ne $row.bytes -or $now.sha256 -ne $row.sha256){throw "Changed candidate: $($row.path)"}}
  $paths=@($manifest.files.path)+@($target.Substring($repo.Length+1).Replace('\','/'))
  $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$index=@(& git -C $repo -c core.quotepath=false diff --cached --name-only);$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  if($code){throw 'Cannot inspect index; no stage attempted'}
  foreach($p in $index){if($p -and $p -notin $paths){throw 'Unrelated staged changes preserved; root must resolve scope'}}
  for($i=0;$i -lt $paths.Count;$i+=20){
    $end=[Math]::Min($i+19,$paths.Count-1);$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
    $message=& git -C $repo --literal-pathspecs add -f -- @($paths[$i..$end]) 2>&1;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
    $message|Out-Host;if($code){throw 'Exact stage failed; preserve and inspect partial index without resetting'}
  }
  Write-Output "STAGED $($paths.Count) reviewed paths only; no commit or push";exit 0
}
$paths=Candidates
$missingCandidates=@($paths|Where-Object {!(Test-Path -LiteralPath $_)})
$files=@(foreach($p in $paths){
  if(!(Test-Path -LiteralPath $p)){continue}
  if(!$p.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Escaped repository'}
  $e=Entry $p
  if($e.bytes -gt 2097152 -or [IO.Path]::GetExtension($p) -notin '.h','.cpp','.ps1','.py','.json','.csv','.log','.out'){throw "Unexpected large/unapproved artifact: $p"};$e
})
$required=@('logs\upl_p3_perm_time_build_r1.json','logs\upl_p3_perm_time_off_r1.check.json','logs\upl_p3_perm_time_DebugCPU_r1.check.json','logs\upl_p3_perm_time_ReleaseCPU_r1.check.json','notes\upl_p3_perm_time_independent_r1.json','logs\upl_p3_perm_time_periodic_r1_repair.check.json','logs\upl_p3_perm_time_wall_ReleaseCPU_r2.check.json','logs\upl_p3_perm_time_stage_r1.check.json')
$missing=@($required|Where-Object {!(Test-Path -LiteralPath (Join-Path $tests $_))})+@($missingCandidates|ForEach-Object {$_.Substring($repo.Length+1)})
if($Mode -eq 'List'){[pscustomobject]@{base=$expectedBase;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;missing=$missing;files=$files;Git_mutated=$false};return}
if((Test-Path -LiteralPath $target) -or $missing.Count){throw 'Manifest retained or required stage checks/snapshots missing'}
foreach($p in $required){
  $check=Get-Content -Raw -LiteralPath (Join-Path $tests $p)|ConvertFrom-Json
  if($p -eq 'logs\upl_p3_perm_time_build_r1.json'){
    if($check.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $check.msbuild_exit_codes.DebugCPU -ne 0 -or $check.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Authoritative full Rebuild not passed'}
    foreach($s in $check.source){foreach($r in @($s.original,$s.snapshot)){$f=Get-Item -LiteralPath $r.path;if($f.Length -ne $r.bytes -or (Get-FileHash -LiteralPath $r.path -Algorithm SHA256).Hash -ine $r.sha256){throw 'Current source/frozen snapshot changed'}}}
  }elseif(!$check.passed){throw "Required review/check not passed: $p"}
}
$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$base=& git -C $repo rev-parse HEAD;$baseCode=$LASTEXITCODE;$branch=& git -C $repo branch --show-current;$branchCode=$LASTEXITCODE;$ErrorActionPreference=$oldAction
if($baseCode -or $branchCode -or $base -ne $expectedBase){throw 'Cannot bind required exact Git base834f39c'}
$manifest=[ordered]@{base=$base;branch=$branch;ready_for_root_review=$true;scope='Private CPU gradient-k necessary time-cache patch, manufactured component and same-physics trajectory regressions only';files=$files;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;required_checks=$required;new_CPP_trajectory_fixture_or_PDE=$false;all_force_stage_gradient_nondominance_claimed=$false;general_sufficient_stability_proven=$false;raw_binary_large_ledger_program_cloud_backup_claimed=$false;excluded='physical.bin/ledger.csv/conductivity_ledger.csv/BI4/VTK/exe/obj/pdb/ilk/runtime DLL/lib/DsphConfig.xml/prebuild old canonical programs/crash artifacts/unrelated dirty files';public_formal_or_physical_acceptance=$false}
[IO.File]::WriteAllText($target,($manifest|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) paths, $($manifest.bytes) bytes; inspect before explicit Stage."

