# Freeze the pre-merge CPU/HG baseline. No build, solver, deletion, or overwrite.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src'
$target=Join-Path $tests 'outputs\hg_merge_base'
$record=Join-Path $tests 'logs\hg_merge_base.json'
foreach($path in @($target,$record)){
  if(Test-Path -LiteralPath $path){throw "Refusing overwrite: $path"}
}
$head=(& git -C $repo rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0){throw 'Cannot read Git HEAD'}
$status=@(& git -C $src status --porcelain=v1 --untracked-files=all -- source VS)
if($LASTEXITCODE -ne 0){throw 'Cannot read source/project Git status'}
$entries=New-Object System.Collections.Generic.List[object]
function Add-Files($files,[string]$base,[string]$folder){
  foreach($file in $files){
    $relative=$file.FullName.Substring($base.Length).TrimStart('\')
    $entries.Add([ordered]@{path=$file.FullName;relative=(Join-Path $folder $relative);bytes=$file.Length;
      last_write_utc=$file.LastWriteTimeUtc.ToString('o');sha256=(Get-FileHash -LiteralPath $file.FullName).Hash})
  }
}
$source=Join-Path $src 'source';$vs=Join-Path $src 'VS';$bin=Join-Path $repo 'bin\windows'
Add-Files @(Get-ChildItem -LiteralPath $source -File -Recurse) $source 'source'
Add-Files @(Get-ChildItem -LiteralPath $vs -File -Recurse|Where-Object{
  $_.Name -match '\.(sln|vcxproj|vcxproj\.filters|vcxproj\.user|props|targets)$' -and $_.FullName -notmatch '\\\.vs\\'
}) $vs 'VS'
Add-Files @((Get-Item -LiteralPath (Join-Path $bin 'DualSPHysics5.2CPU_win64.exe')),
  (Get-Item -LiteralPath (Join-Path $bin 'DualSPHysics5.2CPU_win64_debug.exe'))) $bin 'bin'
Add-Files @(Get-ChildItem -LiteralPath $PSScriptRoot -File|Where-Object{
  $_.Name -match '^(hourglass|traction|mechanics)' -or $_.Name -eq 'hg_merge_snapshot.ps1'
}) $PSScriptRoot 'support'
$logs=Join-Path $tests 'logs'
Add-Files @(Get-ChildItem -LiteralPath $logs -File|Where-Object{
  $_.Name -match '^hg_.*\.json$' -or $_.Name -match '^mech_bin_hg_.*\.build\.(json|log)$'
}) $logs 'logs'
foreach($label in @('hg_r2rel','hg_r2dbg')){
  $frozen=Join-Path $tests "outputs\mech_bin_$label"
  Add-Files @(Get-ChildItem -LiteralPath $frozen -File|Where-Object{
    $_.Extension -in @('.exe','.dll','.json','.snapshot')
  }) $frozen $label
}
$run=Get-Content -LiteralPath (Join-Path $logs 'hg_window_x01.run.json') -Raw -Encoding UTF8|ConvertFrom-Json
$inputs=@($run.inputs|Where-Object{[IO.Path]::GetExtension($_.path) -in @('.xml','.bi4','.nbi4')})
foreach($input in $inputs){
  if((Get-FileHash -LiteralPath $input.path).Hash -ne $input.sha256){throw "Changed retained input: $($input.path)"}
  Add-Files @((Get-Item -LiteralPath $input.path)) (Split-Path -Parent $input.path) 'inputs'
}
if(@($entries.relative|Sort-Object -Unique).Count -ne $entries.Count){throw 'Duplicate snapshot destination'}
$null=New-Item -ItemType Directory -Path $target
foreach($entry in $entries){
  $destination=Join-Path $target $entry.relative
  $parent=Split-Path -Parent $destination
  if(!(Test-Path -LiteralPath $parent)){$null=New-Item -ItemType Directory -Path $parent}
  Copy-Item -LiteralPath $entry.path -Destination $destination
  if((Get-FileHash -LiteralPath $destination).Hash -ne $entry.sha256){throw "Snapshot hash mismatch: $destination"}
}
foreach($entry in $entries){
  if((Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256){throw "Input changed during snapshot: $($entry.path)"}
}
if((& git -C $repo rev-parse HEAD).Trim() -ne $head){throw 'Git HEAD changed during snapshot'}
$statusAfter=@(& git -C $src status --porcelain=v1 --untracked-files=all -- source VS)
if(($status -join "`n") -ne ($statusAfter -join "`n")){throw 'Source/project Git status changed during snapshot'}
[ordered]@{
  status='frozen_pre_production_merge';created_utc=[DateTime]::UtcNow.ToString('o');git_head=$head
  source_status_cwd=$src;source_project_git_status=$status;source_project_status_unchanged=$true
  snapshot=$target;files=$entries.Count;total_bytes=($entries|ForEach-Object{$_.bytes}|Measure-Object -Sum).Sum
  source_and_copy_hashes_verified=$true;script_sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash;entries=@($entries.ToArray())
  limitations=@('Raw retained solver outputs remain at original protected paths; their existing run manifests are copied.',
    'Executable identity is frozen; this operation does not rebuild or prove that installed CPU executables match current source.',
    'No GPU executable or compiler intermediate is copied; source includes the current CPU and GPU code.')
}|ConvertTo-Json -Depth 7|Set-Content -LiteralPath $record -Encoding UTF8
Write-Output "FROZEN $($entries.Count) files: $target"
Write-Output "MANIFEST $record"
