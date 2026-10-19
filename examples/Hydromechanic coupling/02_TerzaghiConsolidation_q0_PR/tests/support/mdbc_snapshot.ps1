param([ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='mdbc_base',[switch]$IncludeGpu)
# Preserve source/build evidence before each boundary/GPU integration stage.
# Copies only: no compilation, solver, overwrite, or Git mutation.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src'
$target=Join-Path $tests "outputs\$Label"
$record=Join-Path $tests "logs\$Label.snapshot.json"
if((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $record)){throw 'Snapshot already exists'}
$entries=New-Object System.Collections.Generic.List[object]
function Add-Files($files,[string]$base,[string]$folder){
  foreach($file in $files){
    $relative=$file.FullName.Substring($base.Length).TrimStart('\')
    $entries.Add([ordered]@{path=$file.FullName;relative=(Join-Path $folder $relative);bytes=$file.Length;
      sha256=(Get-FileHash -LiteralPath $file.FullName).Hash})
  }
}
$source=Join-Path $src 'source';$vs=Join-Path $src 'VS';$bin=Join-Path $repo 'bin\windows'
Add-Files @(Get-ChildItem -LiteralPath $source -File -Recurse) $source 'source'
Add-Files @(Get-ChildItem -LiteralPath $vs -File -Recurse | Where-Object{
  $_.Name -match '\.(sln|vcxproj|vcxproj\.filters|props|targets)$' -and $_.FullName -notmatch '\\\.vs\\'
}) $vs 'VS'
foreach($config in @('DebugCPU','ReleaseCPU')){
  $obj=Join-Path $vs "Intermediate\DualSPHysics_${config}_x64"
  Add-Files @(Get-ChildItem -LiteralPath $obj -File | Where-Object{$_.Extension -eq '.obj'}) $obj "objects\$config"
}
Add-Files @((Get-Item -LiteralPath (Join-Path $bin 'DualSPHysics5.2CPU_win64.exe')),
  (Get-Item -LiteralPath (Join-Path $bin 'DualSPHysics5.2CPU_win64_debug.exe'))) $bin 'bin'
if($IncludeGpu){
  foreach($config in @('Debug','Release')){
    $obj=Join-Path $vs "Intermediate\DualSPHysics_${config}_x64"
    Add-Files @(Get-ChildItem -LiteralPath $obj -Filter '*.obj' -File) $obj "objects\$config"
    $cudaobj=Join-Path $vs "x64\$config"
    Add-Files @(Get-ChildItem -LiteralPath $cudaobj -Filter '*.obj' -File) $cudaobj "cudaobjects\$config"
  }
  Add-Files @((Get-Item -LiteralPath (Join-Path $bin 'DualSPHysics5.2_GEO_win64.exe')),
    (Get-Item -LiteralPath (Join-Path $bin 'DualSPHysics5.2_win64_debug.exe'))) $bin 'bin'
  Add-Files @(Get-ChildItem -LiteralPath $bin -Filter '*.dll' -File) $bin 'bin'
  Add-Files @(Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object{
    $_.Name -match '^(hg_gpu_|gpu_)'
  }) $PSScriptRoot 'support'
}
Add-Files @(Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object{
  $_.Name -match '^(hg_release|mdbc_)' -and $_.Extension -in @('.cpp','.h','.py','.ps1')
}) $PSScriptRoot 'support'
$doc=Join-Path $repo 'doc\xml_format\_FmtXML_ElastoplasticSoil.xml'
Add-Files @((Get-Item -LiteralPath $doc)) (Split-Path -Parent $doc) 'doc'
if(@($entries.relative|Sort-Object -Unique).Count -ne $entries.Count){throw 'Duplicate snapshot destination'}
$head=(& git -C $src rev-parse HEAD).Trim()
$null=New-Item -ItemType Directory -Path $target
foreach($entry in $entries){
  $destination=Join-Path $target $entry.relative
  $parent=Split-Path -Parent $destination
  if(!(Test-Path -LiteralPath $parent)){$null=New-Item -ItemType Directory -Path $parent}
  Copy-Item -LiteralPath $entry.path -Destination $destination
  if((Get-FileHash -LiteralPath $destination).Hash -ne $entry.sha256){throw "Copy hash mismatch: $destination"}
}
foreach($entry in $entries){
  if((Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256){throw "Source changed during snapshot: $($entry.path)"}
}
[ordered]@{
  status='frozen_stage_baseline';created_utc=[DateTime]::UtcNow.ToString('o');git_head=$head;includes_gpu=$IncludeGpu.IsPresent
  snapshot=$target;files=$entries.Count;total_bytes=($entries|ForEach-Object{$_.bytes}|Measure-Object -Sum).Sum
  source_and_copy_hashes_verified=$true;entries=@($entries.ToArray())
  limitations=@('This is a copy/hash receipt, not a build or physical acceptance.',
    'Original run/build manifests and raw physical outputs remain at their retained paths.')
}|ConvertTo-Json -Depth 7|Set-Content -LiteralPath $record -Encoding UTF8
Write-Output "FROZEN $($entries.Count) files: $target"
Write-Output "MANIFEST $record"
