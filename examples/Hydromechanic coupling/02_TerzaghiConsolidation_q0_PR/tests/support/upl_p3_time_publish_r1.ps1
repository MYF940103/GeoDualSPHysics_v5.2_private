$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$target=Join-Path $tests 'logs\upl_p3_time_publish_r1.json'
if(Test-Path -LiteralPath $target){throw 'Retained publication whitelist protected'}
function Entry([string]$path){
  $f=Get-Item -LiteralPath $path
  [ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$stagePath=Join-Path $tests 'logs\upl_p3_time_stage_r2.check.json'
$stage=Get-Content -LiteralPath $stagePath -Raw|ConvertFrom-Json
if(!$stage.passed){throw 'Stage review failed'}
$independentPath=Join-Path $tests 'notes\upl_p3_time_integration_review_r1.json'
$independent=Get-Content -LiteralPath $independentPath -Raw|ConvertFrom-Json
if(!$independent.passed){throw 'Independent integration review failed'}
$guardPath=Join-Path $tests 'logs\upl_p3_timeguard_review_r1.check.json'
$guard=Get-Content -LiteralPath $guardPath -Raw|ConvertFrom-Json
$wavePath=Join-Path $tests 'logs\upl_p3_time_git_seal_r1.json'
$wave=Get-Content -LiteralPath $wavePath -Raw|ConvertFrom-Json
$paths=@($stagePath,$independentPath,$guardPath,$wavePath,$PSCommandPath)
$paths+=@($guard.text_files|ForEach-Object {$_.path})
foreach($item in $wave.files){
  $paths+=if([IO.Path]::IsPathRooted($item.path)){$item.path}else{Join-Path $repo $item.path}
}
$paths+=@('src\source\JSphCpu.h','src\source\JSphCpu.cpp','examples\Hydromechanic coupling\validation\upl_current_status.json')|ForEach-Object {Join-Path $repo $_}
$paths+=@('support\upl_p3_time_build_seal_r1.ps1','support\upl_p3_time_stage_r1.ps1','notes\upl_p3_time_source_review_r1.json')|ForEach-Object {Join-Path $tests $_}
$paths+=Get-ChildItem -LiteralPath (Join-Path $tests 'outputs\upl_p3_time_source_r1') -File|ForEach-Object {$_.FullName}
$paths+=Get-ChildItem -LiteralPath (Join-Path $tests 'logs') -Filter 'upl_p2_*_p3_time_r1*.json' -File|ForEach-Object {$_.FullName}
$paths+=Join-Path $tests 'logs\upl_p3_time_off_r1.check.json'
$files=@()
foreach($path in $paths|Sort-Object -Unique){
  $entry=Entry $path
  if(!$entry.path.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Whitelist escaped repository'}
  $relative=$entry.path.Substring($repo.Length+1).Replace('\','/')
  if([IO.Path]::GetExtension($relative) -notin '.h','.cpp','.ps1','.py','.xml','.json','.csv','.log','.out'){throw "Non-text artifact selected: $relative"}
  $files+=@{path=$relative;bytes=$entry.bytes;sha256=$entry.sha256}
}
$result=[ordered]@{
  stage='Verified private CPU necessary-step/domain guard and bounded regressions'
  created_utc=[DateTime]::UtcNow.ToString('o');base=(& git -C $repo rev-parse HEAD)
  stage_review=(Entry $stagePath);independent_review=(Entry $independentPath)
  files=$files;count=$files.Count;total_bytes=($files|ForEach-Object {$_.bytes}|Measure-Object -Sum).Sum
  manifest_self_not_in_own_hash_list=$true
  raw_programs_trajectories_BI4_stage_detail_cloud_backed=$false
  physical_acceptance=$false;Git_mutated_by_this_recipe=$false
}
[IO.File]::WriteAllText($target,($result|ConvertTo-Json -Depth 8)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) text paths / $($result.total_bytes) bytes; add this manifest itself separately."
