param(
  [ValidateSet('List','Seal','Stage')][string]$Mode='List',
  [switch]$StageAuthorized,
  [string]$ReviewedManifestSha256=''
)
# Explicit reviewed component/OFF stage only. Future variable-k trajectories are excluded.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$target=Join-Path $tests 'logs\upl_p3_perm_publish_r1.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[pscustomobject][ordered]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Candidates {
  $paths=@('src\source\JSphCpu.h','src\source\JSphCpu.cpp','examples\Hydromechanic coupling\validation\upl_current_status.json')|ForEach-Object {Join-Path $repo $_}
  foreach($leaf in @('upl_p3_perm_actual_r1.cpp','upl_p3_perm_actual_run_r1.ps1','upl_p3_perm_actual_run_r2.ps1','upl_p3_perm_build_r1.ps1','upl_p3_perm_build_r2.ps1','upl_p3_perm_symbol_r1.ps1','upl_p3_perm_review_r1.py','upl_p3_perm_periodic_r1.ps1','upl_p3_perm_publish_r1.ps1')){$paths+=Join-Path $tests ('support\'+$leaf)}
  foreach($leaf in @('upl_p3_perm_abi_r1.json','upl_p3_perm_actual_r1.json','upl_p3_perm_actual_r2.json','upl_p3_perm_components_review_r1.json','upl_p3_perm_periodic_r1.json')){$paths+=Join-Path $tests ('notes\'+$leaf)}
  $paths+=Get-ChildItem -LiteralPath (Join-Path $tests 'logs') -File|Where-Object {
    $_.Extension -in '.json','.log' -and (
      $_.Name -match '^upl_p3_perm_build_r[12]\.json$' -or
      $_.Name -match '^upl_p3_perm_(DebugCPU|ReleaseCPU)_build_r[12]\.log$' -or
      $_.Name -match '^upl_p3_perm_abi_r[12]\.log$' -or
      $_.Name -match '^upl_p3_perm_off_.*_r[12](\.check\.json|\.driver\.log)$' -or
      $_.Name -match '^upl_p3_perm_actual_(DebugCPU|ReleaseCPU)_.*r2' -or
      $_.Name -match '^upl_p3_perm_periodic_(ReleaseCPU_r1|Build_r1|Run_r1)' -or
      $_.Name -eq 'upl_p3_perm_review_r1.check.json' -or
      $_.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_p3_perm_r[12]'
    )
  }|ForEach-Object {$_.FullName}
  # The aggregate default-OFF name is not covered by driver-log expressions above.
  $paths+=Join-Path $tests 'logs\upl_p3_perm_off_r2.check.json'
  foreach($dir in (Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Directory)){
    $leaves=@()
    if($dir.Name -match '^upl_p3_perm_source_r[12]$'){$leaves=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.h','.cpp'}}
    elseif($dir.Name -match '^upl_p3_perm_actual_(DebugCPU|ReleaseCPU)_r2$' -or $dir.Name -eq 'upl_p3_perm_periodic_ReleaseCPU_r1'){$leaves=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.cpp','.ps1','.py','.json','.xml'}}
    elseif($dir.Name -match '^upl_p3_perm_actual_(DebugCPU|ReleaseCPU)_r2_(off|on)$' -or $dir.Name -match '^upl_p3_perm_periodic_ReleaseCPU_r1_n32_[ch]$'){$leaves=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.csv','.json','.out'}}
    elseif($dir.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_p3_perm_r[12]_'){$leaves=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -eq '.json' -or $_.Name -in 'theta_pairs.csv','Run.out'}}
    $paths+=@($leaves|ForEach-Object {$_.FullName})
  }
  @($paths|Sort-Object -Unique)
}
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$'){throw 'Exact reviewed manifest identity and explicit stage authorization required'}
  if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Reviewed manifest differs'}
  $m=Get-Content -LiteralPath $target -Raw|ConvertFrom-Json
  if(!$m.ready_for_root_review -or (& git -C $repo rev-parse HEAD) -ne $m.base){throw 'Manifest unready or Git base changed'}
  foreach($r in $m.files){$a=Entry (Join-Path $repo $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Reviewed file changed: $($r.path)"}}
  $stagePaths=@($m.files|ForEach-Object {$_.path})+@($target.Substring($repo.Length+1).Replace('\','/'))
  foreach($p in @(& git -C $repo -c core.quotepath=false diff --cached --name-only)){if($p -and $p -notin $stagePaths){throw "Unrelated index entry preserved: $p"}}
  for($i=0;$i -lt $stagePaths.Count;$i+=20){$end=[Math]::Min($i+19,$stagePaths.Count-1);& git -C $repo --literal-pathspecs add -f -- @($stagePaths[$i..$end]);if($LASTEXITCODE){throw 'Explicit stage failed; inspect partial index without reset'}}
  Write-Output "STAGED reviewed component/OFF scope only: $($stagePaths.Count) paths; no commit/push";exit 0
}
$files=@(foreach($p in (Candidates)){
  if(!$p.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Escaped repository'}
  if([IO.Path]::GetExtension($p) -notin '.h','.cpp','.ps1','.py','.xml','.json','.csv','.log','.out'){throw "Unapproved file type: $p"}
  $r=Entry $p;if($r.bytes -gt 2097152){throw "Unexpected large text file: $p"};$r
})
$required=@('logs\upl_p3_perm_off_r2.check.json','logs\upl_p3_perm_actual_DebugCPU_r2.check.json','logs\upl_p3_perm_actual_ReleaseCPU_r2.check.json','logs\upl_p3_perm_review_r1.check.json','logs\upl_p3_perm_periodic_ReleaseCPU_r1.check.json')
$missing=@($required|Where-Object {!(Test-Path -LiteralPath (Join-Path $tests $_))})
if($Mode -eq 'List'){[pscustomobject]@{count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;missing=$missing;files=$files;Git_mutated=$false};return}
if(Test-Path -LiteralPath $target){throw 'Retained manifest protected'}
if($missing.Count){throw ('Missing gates: '+($missing -join ', '))}
foreach($p in $required){if(!(Get-Content -LiteralPath (Join-Path $tests $p) -Raw|ConvertFrom-Json).passed){throw "Gate failed: $p"}}
$freeze=Get-Content -LiteralPath (Join-Path $tests 'logs\upl_p3_perm_build_r2.json') -Raw|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Full authoritative builds unavailable'}
foreach($s in $freeze.source){foreach($r in @($s.original,$s.snapshot)){if((Get-FileHash -LiteralPath $r.path -Algorithm SHA256).Hash -ine $r.sha256){throw 'Frozen source differs'}}}
$manifest=[ordered]@{base=(& git -C $repo rev-parse HEAD);branch=(& git -C $repo branch --show-current);scope='Private CPU smooth-k components and exact default/constant-k trajectory compatibility; no physical/public/GPU release';ready_for_root_review=$true;files=$files;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;required_checks=$required;raw_BI4_exe_dump_cloud_backup_claimed=$false;future_variable_k_trajectory_artifacts_included=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($target,($manifest|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) explicit files, $($manifest.bytes) bytes: $target"
