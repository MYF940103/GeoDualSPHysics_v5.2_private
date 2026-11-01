$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$target=Join-Path $tests 'logs\upl_p3_wall_mirror_publish_r1.json'
if(Test-Path -LiteralPath $target){throw 'Retained manifest protected'}
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
$review=Join-Path $tests 'notes\upl_p3_wall_mirror_review_r1.json'
foreach($p in @($review,(Join-Path $tests 'logs\upl_p3_wall_mirror_r2.check.json'))){
  if(!(Get-Content -LiteralPath $p -Raw|ConvertFrom-Json).passed){throw 'Independent and executed screen reviews must pass'}
}
$paths=@()
foreach($part in @('support','notes','logs')){$paths+=Get-ChildItem -LiteralPath (Join-Path $tests $part) -Filter 'upl_p3_wall_mirror*' -File|ForEach-Object {$_.FullName}}
foreach($dir in (Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Filter 'upl_p3_wall_mirror*' -Directory)){$paths+=Get-ChildItem -LiteralPath $dir.FullName -File|ForEach-Object {$_.FullName}}
$paths+=Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json'
$files=@(foreach($p in ($paths|Sort-Object -Unique)){
  if([IO.Path]::GetExtension($p) -notin '.cpp','.ps1','.py','.json','.csv','.log','.md'){continue}
  $f=Entry $p
  if(!$f.path.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Publication path escaped repository'}
  @{path=$f.path.Substring($repo.Length+1).Replace('\','/');bytes=$f.bytes;sha256=$f.sha256}
})
$result=[ordered]@{stage='Frozen planar mirror operator screen, not production wall support';base=(& git -C $repo rev-parse HEAD);independent_review=(Entry $review);files=$files;count=$files.Count;total_bytes=($files|ForEach-Object {$_.bytes}|Measure-Object -Sum).Sum;source_changed=$false;physical_acceptance=$false;program_binaries_cloud_backed=$false;manifest_self_not_in_own_hash_list=$true;Git_mutated_by_this_recipe=$false}
[IO.File]::WriteAllText($target,($result|ConvertTo-Json -Depth 8)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) scoped artifacts / $($result.total_bytes) bytes; stage manifest separately."
