$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$target=Join-Path $tests 'logs\upl_p3_spatial_publish_r1.json'
if(Test-Path -LiteralPath $target){throw 'Retained publication manifest protected'}
function Entry([string]$path){
  $f=Get-Item -LiteralPath $path
  [ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$rootCheck=Join-Path $tests 'logs\upl_p3_spatial_r1.check.json'
$independentCheck=Join-Path $tests 'notes\upl_p3_spatial_actual_review_r1.json'
foreach($path in @($rootCheck,$independentCheck)){
  if(!(Get-Content -LiteralPath $path -Raw|ConvertFrom-Json).passed){throw 'Both independent and root spatial reviews must pass'}
}
# Only this named stage is selected. Never enumerate unrelated large case outputs.
$paths=@()
foreach($part in @('support','notes','logs','configs','figures')){
  $paths+=Get-ChildItem -LiteralPath (Join-Path $tests $part) -Filter 'upl_p3_spatial*' -File|ForEach-Object {$_.FullName}
}
$dirs=@(Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Filter 'upl_p3_spatial*' -Directory)
foreach($dir in $dirs){$paths+=Get-ChildItem -LiteralPath $dir.FullName -Recurse -File|ForEach-Object {$_.FullName}}
$paths+=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
$extensions=@('.ps1','.py','.cpp','.h','.xml','.json','.csv','.log','.txt','.md','.png','.out')
$files=@()
foreach($path in $paths|Sort-Object -Unique){
  if([IO.Path]::GetExtension($path).ToLowerInvariant() -notin $extensions){continue}
  $f=Entry $path
  if(!$f.path.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Whitelist escaped repository'}
  $files+=@{path=$f.path.Substring($repo.Length+1).Replace('\','/');bytes=$f.bytes;sha256=$f.sha256}
}
$result=[ordered]@{
  stage='Private CPU actual three-grid weak-wave spatial refinement'
  base=(& git -C $repo rev-parse HEAD);created_utc=[DateTime]::UtcNow.ToString('o')
  root_review=(Entry $rootCheck);independent_review=(Entry $independentCheck)
  files=$files;count=$files.Count;total_bytes=($files|ForEach-Object {$_.bytes}|Measure-Object -Sum).Sum
  manifest_self_not_in_own_hash_list=$true
  failed_setup_attempts_preserved=$true
  raw_programs_trajectories_BI4_cloud_backed=$false
  source_changed_since_base=$false;physical_acceptance=$false;Git_mutated_by_this_recipe=$false
}
[IO.File]::WriteAllText($target,($result|ConvertTo-Json -Depth 8)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) scoped artifacts / $($result.total_bytes) bytes; stage manifest separately."
