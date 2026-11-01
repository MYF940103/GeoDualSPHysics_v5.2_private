param([ValidateSet('List','Seal','Stage')][string]$Mode='List',[switch]$StageAuthorized,[string]$ReviewedManifestSha256='')
# Fixed wall-stage whitelist; default List is read-only, Stage requires exact root-reviewed identity.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$target=Join-Path $tests 'logs\upl_p3_perm_wall_publish_r1.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[pscustomobject]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Candidates {
  $paths=@()
  foreach($part in @('support','notes','logs')){
    $paths+=Get-ChildItem -LiteralPath (Join-Path $tests $part) -File|Where-Object {$_.Name -like 'upl_p3_perm_wall_*' -and $_.Name -ne 'upl_p3_perm_wall_publish_r1.json' -and $_.Extension -in '.cpp','.ps1','.py','.json','.log'}|ForEach-Object {$_.FullName}
  }
  # Preserve the small previous-stage driver record if present; no prior raw trajectory is repeated.
  $previous=Join-Path $tests 'logs\upl_p3_perm_wave_stage_r1.driver.log';if(Test-Path -LiteralPath $previous){$paths+=$previous}
  $paths+=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
  foreach($leaf in @('upl_p3_perm_wall_r1.png','upl_p3_perm_wall_r1_history.csv')){$paths+=Join-Path $tests ('figures\'+$leaf)}
  foreach($dir in (Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Directory)){
    if($dir.Name -match '^upl_p3_perm_wall_(DebugCPU_r1|ReleaseCPU_r1)$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.cpp','.ps1','.json'}|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_p3_perm_wall_(DebugCPU_r1_smoke|ReleaseCPU_r1_(on_c|on_h|off_c))$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'modes.csv','source_summary.csv','native_ids.csv','fixed_ids.csv','wall_audit.csv','endpoint_policy.csv','component.check.json','component.csv','offgrid_component.check.json','offgrid_component.csv','complete.json','Run.out'}|ForEach-Object {$_.FullName}
    }
  }
  @($paths|Sort-Object -Unique)
}
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Exact reviewed identity and explicit StageAuthorized are required'}
  $manifest=Get-Content -Raw -LiteralPath $target|ConvertFrom-Json
  $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$base=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  if($code -or !$manifest.ready_for_root_review -or $base -ne $manifest.base){throw 'Changed Git base or unready manifest'}
  foreach($row in $manifest.files){$now=Entry (Join-Path $repo $row.path);if($now.bytes -ne $row.bytes -or $now.sha256 -ne $row.sha256){throw "Changed candidate: $($row.path)"}}
  $paths=@($manifest.files.path)+@($target.Substring($repo.Length+1).Replace('\','/'))
  $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$index=@(& git -C $repo -c core.quotepath=false diff --cached --name-only);$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  if($code){throw 'Unable to inspect index; no stage attempted'}
  foreach($p in $index){if($p -and $p -notin $paths){throw 'Unrelated staged changes preserved; root must resolve scope'}}
  for($i=0;$i -lt $paths.Count;$i+=20){
    $end=[Math]::Min($i+19,$paths.Count-1);$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
    $message=& git -C $repo --literal-pathspecs add -f -- @($paths[$i..$end]) 2>&1;$code=$LASTEXITCODE;$ErrorActionPreference=$oldAction
    $message|Out-Host;if($code){throw 'Exact stage failed; preserve and inspect the partial index without resetting it'}
  }
  Write-Output "STAGED $($paths.Count) explicit reviewed paths only; no commit or push";exit 0
}
$paths=Candidates
$missingCandidates=@($paths|Where-Object {!(Test-Path -LiteralPath $_)})
$files=@(foreach($p in $paths){
  if(!(Test-Path -LiteralPath $p)){continue}
  if(!$p.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Escaped repository'}
  $entry=Entry $p
  if($entry.bytes -gt 2097152 -or [IO.Path]::GetExtension($p) -notin '.cpp','.ps1','.py','.json','.csv','.log','.out','.xml','.png'){throw "Unexpected large/unapproved file: $p"};$entry
})
$required=@('logs\upl_p3_perm_wall_DebugCPU_r1.smoke.check.json','logs\upl_p3_perm_wall_ReleaseCPU_r1.check.json','logs\upl_p3_perm_wall_review_r1.check.json','notes\upl_p3_perm_wall_independent_r1.json')
$missing=@($required|Where-Object {!(Test-Path -LiteralPath (Join-Path $tests $_))})+@($missingCandidates|ForEach-Object {$_.Substring($repo.Length+1)})
if($Mode -eq 'List'){[pscustomobject]@{count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;missing=$missing;files=$files;Git_mutated=$false};return}
if((Test-Path -LiteralPath $target) -or $missing.Count){throw 'Manifest retained or required review/figure/status missing'}
foreach($p in $required){if(!(Get-Content -Raw -LiteralPath (Join-Path $tests $p)|ConvertFrom-Json).passed){throw "Required review/check not passed: $p"}}
$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue';$base=& git -C $repo rev-parse HEAD;$baseCode=$LASTEXITCODE;$branch=& git -C $repo branch --show-current;$branchCode=$LASTEXITCODE;$ErrorActionPreference=$oldAction
if($baseCode -or $branchCode){throw 'Cannot bind the exact Git base'}
$manifest=[ordered]@{base=$base;branch=$branch;ready_for_root_review=$true;scope='Private CPU smooth-k bounded fixed parallel FreeSlip walls g=0; no production edit, public/GPU/formal or physical-theory release';files=$files;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;required_checks=$required;raw_trajectory_conductivity_ledger_program_cloud_backup_claimed=$false;excluded='physical.bin/conductivity_ledger.csv/BI4/VTK/exe/obj/pdb/runtime DLL/lib and unrelated dirty files';physical_acceptance=$false}
[IO.File]::WriteAllText($target,($manifest|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) paths, $($manifest.bytes) bytes; inspect before an explicitly authorized Stage."
