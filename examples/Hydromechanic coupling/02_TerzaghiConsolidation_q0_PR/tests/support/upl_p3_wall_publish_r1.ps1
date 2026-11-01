param(
  [ValidateSet('List','Seal','Stage')][string]$Mode='List',
  [switch]$StageAuthorized,
  [string]$ReviewedManifestSha256=''
)
# Fixed wall-stage text plus one reviewed PNG whitelist. List is read-only; Seal writes one new manifest.
# Stage is opt-in after root review, never commits/pushes or changes unrelated index entries.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$target=Join-Path $tests 'logs\upl_p3_wall_publish_r1.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[pscustomobject][ordered]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Candidates {
  $paths=@()
  foreach($p in @('JSphCpu.h','JSphCpu.cpp','JSphCpuSingle.cpp')){$paths+=Join-Path $repo ('src\source\'+$p)}
  foreach($part in @('support','configs','notes')){
    $paths+=Get-ChildItem -LiteralPath (Join-Path $tests $part) -File|Where-Object {
      $_.Name -like 'upl_p3_wall_*' -and $_.Name -notlike 'upl_p3_wall_mirror*' -and $_.Extension -in '.cpp','.ps1','.py','.xml','.json'
    }|ForEach-Object {$_.FullName}
  }
  $paths+=Join-Path $tests 'notes\upl_permeability_priority_r1.json'
  $paths+=Get-ChildItem -LiteralPath (Join-Path $tests 'logs') -File|Where-Object {
    ($_.Name -like 'upl_p3_wall_*' -and $_.Name -notlike 'upl_p3_wall_mirror*' -and $_.Name -ne 'upl_p3_wall_publish_r1.json' -and $_.Extension -in '.json','.log') -or
    ($_.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_p3_wall_r2' -and ($_.Extension -eq '.json' -or $_.Name -like '*.build.log')) -or
    ($_.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_p3_wall_r1\.(build\.json|build\.log)$')
  }|ForEach-Object {$_.FullName}
  $paths+=Join-Path $tests 'figures\upl_p3_wall_flux_audit_r1.csv'
  $paths+=Join-Path $tests 'figures\upl_p3_wall_r1.png'
  $paths+=Join-Path $tests 'figures\upl_p3_wall_r1_history.csv'
  $paths+=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
  foreach($dir in (Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Directory)){
    $leaves=@()
    if($dir.Name -match '^upl_p3_wall_source_r[123]$'){$leaves=@(Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.h','.cpp'})}
    elseif($dir.Name -match '^upl_p3_wall_wave_seed_r[123]_[ch]$'){$leaves=@(Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.xml','.out'})}
    elseif($dir.Name -match '^upl_p3_wall_(wave_(DebugCPU_r[234]|ReleaseCPU_r[34])|periodic_ReleaseCPU_r[12])$'){$leaves=@(Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.cpp','.ps1','.json','.xml'})}
    elseif($dir.Name -match '^upl_p3_wall_(wave_(DebugCPU_r[234]_smoke|ReleaseCPU_r[34]_k[01]_[ch])|periodic_ReleaseCPU_r[12]_n32_[ch])$'){$leaves=@(Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.csv','.json','.out'})}
    elseif($dir.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_p3_wall_r2_'){$leaves=@(Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -eq '.json' -or $_.Name -in 'theta_pairs.csv','Run.out'})}
    $paths+=$leaves|ForEach-Object {$_.FullName}
  }
  @($paths|Sort-Object -Unique)
}
$required=@(
  'support\upl_p3_wall_review_r1.py',
  'notes\upl_p3_wall_review_r1.json',
  'logs\upl_p3_wall_build_r3.json',
  'logs\upl_p3_wall_wave_DebugCPU_r4.smoke.check.json',
  'logs\upl_p3_wall_wave_ReleaseCPU_r4.check.json',
  'logs\upl_p3_wall_off_r2.check.json',
  'logs\upl_p3_wall_periodic_ReleaseCPU_r2.check.json',
  'logs\upl_p3_wall_flux_audit_r1.check.json'
  'logs\upl_p3_wall_r1.check.json'
)
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$'){throw 'Root review and an explicit StageAuthorized plus exact reviewed manifest SHA256 are required'}
  if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Reviewed manifest identity differs'}
  $m=Get-Content -LiteralPath $target -Raw|ConvertFrom-Json
  if(!$m.ready_for_root_review -or (& git -C $repo rev-parse HEAD) -ne $m.base){throw 'Unready manifest or changed Git base'}
  foreach($row in $m.files){$now=Entry (Join-Path $repo $row.path);if($now.bytes -ne $row.bytes -or $now.sha256 -ne $row.sha256){throw "Reviewed candidate changed: $($row.path)"}}
  $stagePaths=@($m.files|ForEach-Object {$_.path})+@($target.Substring($repo.Length+1).Replace('\','/'))
  $index=@(& git -C $repo -c core.quotepath=false diff --cached --name-only)
  foreach($p in $index){if($p -and $p -notin $stagePaths){throw "Unrelated staged change preserved; root must resolve scope before this recipe stages: $p"}}
  for($i=0;$i -lt $stagePaths.Count;$i+=20){$end=[Math]::Min($i+19,$stagePaths.Count-1);& git -C $repo --literal-pathspecs add -f -- @($stagePaths[$i..$end]);if($LASTEXITCODE){throw 'Explicit whitelist stage failed; inspect partial index without resetting it'}}
  Write-Output "STAGED explicit wall whitelist only; no commit or push: $($stagePaths.Count) paths";exit 0
}
$missing=@($required|Where-Object {!(Test-Path -LiteralPath (Join-Path $tests $_))})
$paths=Candidates
$files=@(foreach($p in $paths){
  if(!$p.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Candidate escaped repository'}
  if([IO.Path]::GetExtension($p) -notin '.h','.cpp','.ps1','.py','.xml','.json','.csv','.log','.out','.png'){throw "Unapproved binary/non-text candidate rejected: $p"}
  $row=Entry $p;if($row.bytes -gt 2097152){throw "Unexpected large text candidate requires explicit review: $p"};$row
})
if($Mode -eq 'List'){
  [pscustomobject]@{count=$files.Count;total_bytes=($files|ForEach-Object {[long]$_.bytes}|Measure-Object -Sum).Sum;missing=$missing;files=$files;Git_mutated=$false};return
}
if($missing.Count){throw ('Required independent review/evidence not ready: '+($missing -join ', '))}
foreach($p in @('notes\upl_p3_wall_review_r1.json','logs\upl_p3_wall_wave_DebugCPU_r4.smoke.check.json','logs\upl_p3_wall_wave_ReleaseCPU_r4.check.json','logs\upl_p3_wall_off_r2.check.json','logs\upl_p3_wall_periodic_ReleaseCPU_r2.check.json','logs\upl_p3_wall_flux_audit_r1.check.json','logs\upl_p3_wall_r1.check.json')){
  if(!(Get-Content -Raw -LiteralPath (Join-Path $tests $p)|ConvertFrom-Json).passed){throw "Required gate not passed: $p"}
}
$freeze=Get-Content -Raw -LiteralPath (Join-Path $tests 'logs\upl_p3_wall_build_r3.json')|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'){throw 'Latest source builds unavailable'}
foreach($pair in $freeze.source){foreach($row in @($pair.original,$pair.snapshot)){$f=Get-Item -LiteralPath $row.path;if($f.Length -ne $row.bytes -or (Get-FileHash -LiteralPath $row.path -Algorithm SHA256).Hash -ine $row.sha256){throw 'Frozen production/source snapshot changed'}}}
if(Test-Path -LiteralPath $target){throw 'Retained publication manifest protected; never overwrite'}
$result=[ordered]@{stage='Bounded private CPU static parallel FreeSlip walls, constant-k and g=0 only';base=(& git -C $repo rev-parse HEAD);ready_for_root_review=$true;count=$files.Count;total_bytes=($files|ForEach-Object {[long]$_.bytes}|Measure-Object -Sum).Sum;files=$files;excluded='BI4/IBI4/OBI4/VTK/physical.bin/exe/obj/pdb/DLL/lib and unrelated dirty files; raw outputs remain local and are bound by original receipts, not cloud backed';historical_failures_retained=$true;source_changed=$true;physical_acceptance=$false;public_XML_enabled=$false;manifest_self_not_in_own_hash_list=$true;Git_mutated_by_Seal=$false;staging_requires_separate_root_authorization=$true}
[IO.File]::WriteAllText($target,($result|ConvertTo-Json -Depth 9)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) text files / $($result.total_bytes) bytes; review manifest before any explicit Stage call."
