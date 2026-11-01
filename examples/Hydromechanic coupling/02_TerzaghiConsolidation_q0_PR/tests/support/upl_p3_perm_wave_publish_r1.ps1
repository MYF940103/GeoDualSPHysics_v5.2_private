param([ValidateSet('List','Seal','Stage')][string]$Mode='List',[switch]$StageAuthorized,[string]$ReviewedManifestSha256='')
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$target=Join-Path $tests 'logs\upl_p3_perm_wave_publish_r1.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[pscustomobject]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Candidates {
  $p=@()
  foreach($part in @('support','notes','logs')){$p+=Get-ChildItem -LiteralPath (Join-Path $tests $part) -File|Where-Object {$_.Name -like 'upl_p3_perm_wave_*' -and $_.Name -ne 'upl_p3_perm_wave_publish_r1.json' -and $_.Extension -in '.cpp','.ps1','.py','.json','.log'}|ForEach-Object {$_.FullName}}
  $p+=Join-Path $tests 'notes\upl_p3_perm_publish_r1_stage_audit.json'
  $p+=Join-Path $tests 'logs\upl_p3_perm_stage_r1.driver.log'
  $p+=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
  foreach($leaf in @('upl_p3_perm_wave_r1.png','upl_p3_perm_wave_r1_history.csv')){$p+=Join-Path $tests ('figures\'+$leaf)}
  foreach($dir in (Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Directory)){
    if($dir.Name -match '^upl_p3_perm_wave_(DebugCPU_r[12]|ReleaseCPU_r2)$'){$p+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Extension -in '.cpp','.ps1','.json','.xml'}|ForEach-Object {$_.FullName}}
    elseif($dir.Name -match '^upl_p3_perm_wave_(DebugCPU_r[12]_smoke|ReleaseCPU_r2_(on_c|on_h|off_c|k0_off|k0_on))$'){$p+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'modes.csv','initial_source.csv','native_ids.csv','endpoint_policy.csv','complete.json','Run.out'}|ForEach-Object {$_.FullName}}
  }
  @($p|Sort-Object -Unique)
}
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Exact reviewed identity and explicit stage authorization required'}
  $m=Get-Content -LiteralPath $target -Raw|ConvertFrom-Json
  if(!$m.ready_for_root_review -or (& git -C $repo rev-parse HEAD) -ne $m.base){throw 'Changed Git base or unready manifest'}
  foreach($r in $m.files){$a=Entry (Join-Path $repo $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Changed candidate: $($r.path)"}}
  $paths=@($m.files.path)+@($target.Substring($repo.Length+1).Replace('\','/'))
  foreach($p in @(& git -C $repo -c core.quotepath=false diff --cached --name-only)){if($p -and $p -notin $paths){throw 'Unrelated staged changes preserved'}}
  for($i=0;$i -lt $paths.Count;$i+=20){$end=[Math]::Min($i+19,$paths.Count-1);$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$message=& git -C $repo --literal-pathspecs add -f -- @($paths[$i..$end]) 2>&1;$code=$LASTEXITCODE;$ErrorActionPreference=$old;$message|Out-Host;if($code){throw 'Exact stage failed; preserve partial index'}}
  Write-Output "STAGED $($paths.Count) explicit reviewed paths only";exit 0
}
$files=@(foreach($p in (Candidates)){if(!$p.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Escaped repository'};$e=Entry $p;if($e.bytes -gt 2097152 -or [IO.Path]::GetExtension($p) -notin '.cpp','.ps1','.py','.json','.csv','.log','.out','.xml','.png'){throw "Unexpected large/nontext file: $p"};$e})
$required=@('logs\upl_p3_perm_wave_DebugCPU_r2.smoke.check.json','logs\upl_p3_perm_wave_ReleaseCPU_r2.check.json','logs\upl_p3_perm_wave_review_r1.check.json','notes\upl_p3_perm_wave_independent_r1.json')
$missing=@($required|Where-Object {!(Test-Path -LiteralPath (Join-Path $tests $_))})
if($Mode -eq 'List'){[pscustomobject]@{count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;missing=$missing;files=$files;Git_mutated=$false};return}
if((Test-Path -LiteralPath $target) -or $missing.Count){throw 'Manifest retained or prerequisite missing'}
foreach($p in $required){if(!(Get-Content -LiteralPath (Join-Path $tests $p) -Raw|ConvertFrom-Json).passed){throw "Review not passed: $p"}}
$manifest=[ordered]@{base=(& git -C $repo rev-parse HEAD);branch=(& git -C $repo branch --show-current);ready_for_root_review=$true;scope='Private CPU smooth-k actual bounded periodic integration and offline review; no new production edit, public/GPU/formal or physical-theory release';files=$files;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;required_checks=$required;raw_trajectory_ledger_program_cloud_backup_claimed=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($target,($manifest|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) paths, $($manifest.bytes) bytes"
