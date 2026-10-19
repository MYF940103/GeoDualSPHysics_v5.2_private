# Preserve installed GPU binaries/objects before G1. Source and CPU objects are
# preserved separately by mdbc_snapshot.ps1 -Label mdbc_vector_base.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$target=Join-Path $tests 'outputs\gpu_g1_base'
$record=Join-Path $tests 'logs\gpu_g1_base.snapshot.json'
if((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $record)){throw 'GPU snapshot already exists'}
$entries=@()
foreach($configuration in @('Debug','Release')){
  $folder=Join-Path $repo "src\VS\Intermediate\DualSPHysics_${configuration}_x64"
  foreach($file in Get-ChildItem -LiteralPath $folder -Filter '*.obj' -File){
    $entries+= [ordered]@{path=$file.FullName;relative="objects\$configuration\$($file.Name)";sha256=(Get-FileHash -LiteralPath $file.FullName).Hash}
  }
}
$bin=Join-Path $repo 'bin\windows'
$files=@('DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2_win64_debug.exe')|ForEach-Object {Get-Item -LiteralPath (Join-Path $bin $_)}
$files+=Get-ChildItem -LiteralPath $bin -Filter '*.dll' -File
foreach($file in $files){
  $entries+=[ordered]@{path=$file.FullName;relative="bin\$($file.Name)";sha256=(Get-FileHash -LiteralPath $file.FullName).Hash}
}
foreach($entry in $entries){
  $destination=Join-Path $target $entry.relative
  $null=New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force
  Copy-Item -LiteralPath $entry.path -Destination $destination
  if((Get-FileHash -LiteralPath $destination).Hash -ne $entry.sha256 -or
    (Get-FileHash -LiteralPath $entry.path).Hash -ne $entry.sha256){throw "Snapshot mismatch: $($entry.path)"}
}
[ordered]@{
  status='preserved_before_G1';created_utc=[DateTime]::UtcNow.ToString('o');entries=$entries
  source_snapshot='mdbc_vector_base.snapshot.json'
  limitation='Installed GPU binaries/objects are preserved, not asserted to match the current source or constitute a tested baseline.'
}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $record -Encoding UTF8
Write-Output "FROZEN $($entries.Count) GPU files: $target"
