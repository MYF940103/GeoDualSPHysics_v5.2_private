# Posthoc read-only binding of accepted P2 raw outputs. Never runs a program.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$repoPrefix=$repo.TrimEnd('\')+'\'
$logs=Join-Path $tests 'logs'
$manifest=Join-Path $logs 'upl_p2_outputs_r1.manifest.json'
if(Test-Path -LiteralPath $manifest){throw 'Output manifest already exists; never overwrite sealed evidence.'}
function Bind([string]$path){
  $file=Get-Item -LiteralPath $path
  if(!$file.FullName.StartsWith($repoPrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Manifest target outside repository'}
  $size=$file.Length;$stamp=$file.LastWriteTimeUtc.Ticks
  $hash=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  $after=Get-Item -LiteralPath $file.FullName
  if($after.Length -ne $size -or $after.LastWriteTimeUtc.Ticks -ne $stamp){throw 'Target changed while hashing'}
  [ordered]@{path=$file.FullName.Substring($repoPrefix.Length).Replace('\','/');bytes=$size;sha256=$hash}
}
$aggregatePath=Join-Path $logs 'upl_p2_fixture_r1.check.json'
$aggregateBinding=Bind $aggregatePath
$aggregate=Get-Content -LiteralPath $aggregatePath -Raw -Encoding UTF8|ConvertFrom-Json
if(!$aggregate.fixture_checks_passed -or $aggregate.receipts.Count -ne 18){throw 'Unexpected accepted aggregate'}
$receiptBindings=@()
foreach($entry in $aggregate.receipts){
  $actual=Bind $entry.path
  if($actual.sha256 -ne $entry.sha256){throw "Aggregate receipt changed: $($entry.path)"}
  $receiptBindings+=$actual
}
$folders=@()
foreach($configuration in @('DebugCPU','ReleaseCPU')){
  foreach($suffix in @('pair','state','s8_o0','s8_o1','s128_o0','s128_o1','open_s128_o0','open_s128_o1')){
    $folders+=Join-Path $tests "outputs\upl_p2_${configuration}_r3_$suffix"
  }
  $folders+=Join-Path $tests "outputs\upl_p2_before_$configuration"
  $folders+=Join-Path $tests "outputs\upl_p2_before_open_$configuration"
}
$inputFolders=@('upl_p2_seed_r1','upl_p2_state_seed_r1','upl_p2_open_seed_r1')|ForEach-Object {Join-Path $tests "outputs\$_"}
$configs=@('upl_p2_r1.xml','upl_p2_state_r1.xml','upl_p2_open_r1.xml')|ForEach-Object {Join-Path $tests "configs\$_"}
$files=@($folders+$inputFolders|ForEach-Object {Get-ChildItem -LiteralPath $_ -File -Recurse|ForEach-Object {$_.FullName}})+$configs
$files=@($files|Sort-Object -Unique)
$bindings=@($files|ForEach-Object {Bind $_}|Sort-Object path)
foreach($entry in $bindings){
  $again=Bind (Join-Path $repo ($entry.path.Replace('/','\')))
  if($again.sha256 -ne $entry.sha256 -or $again.bytes -ne $entry.bytes){throw "Raw evidence changed: $($entry.path)"}
}
foreach($entry in $receiptBindings){
  if((Bind (Join-Path $repo ($entry.path.Replace('/','\')))).sha256 -ne $entry.sha256){throw 'Aggregate receipt changed during seal'}
}
if((Bind $aggregatePath).sha256 -ne $aggregateBinding.sha256){throw 'Aggregate changed during seal'}
$afterFiles=@(@($folders+$inputFolders|ForEach-Object {Get-ChildItem -LiteralPath $_ -File -Recurse|ForEach-Object {$_.FullName}})+$configs|Sort-Object -Unique)
if(($files -join "`n") -cne ($afterFiles -join "`n")){throw 'Files added or removed while sealing'}
$total=[long]0;foreach($entry in $bindings){$total+=$entry.bytes}
$value=[ordered]@{
  status='posthoc_raw_outputs_and_inputs_sealed'
  utc=[DateTime]::UtcNow.ToString('o')
  git_head=(& git -C $repo rev-parse HEAD)
  relative_to='repository root'
  sha256_encoding='lowercase hexadecimal; exact on-disk bytes'
  posthoc=$true
  pre_run_attestation=$false
  solver_started=$false
  physical_acceptance=$false
  cloud_raw_data_backup_claimed=$false
  scope='Accepted r3 main/open pair/state/solver outputs, four frozen pre-edit controls, three copied input prefixes and three configs only. Failed r1/r2/build binaries excluded.'
  accepted_output_folders=@($folders|ForEach-Object {$_.Substring($repoPrefix.Length).Replace('\','/')}|Sort-Object)
  aggregate=$aggregateBinding
  aggregate_receipts_reverified=18
  aggregate_receipts=@($receiptBindings|Sort-Object path)
  script=(Bind $PSCommandPath)
  file_count=$bindings.Count
  total_bytes=$total
  files=$bindings
}
$text=($value|ConvertTo-Json -Depth 8)+[Environment]::NewLine
$stream=[IO.File]::Open($manifest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$data=(New-Object Text.UTF8Encoding($false)).GetBytes($text);$stream.Write($data,0,$data.Length)}finally{$stream.Dispose()}
Write-Output "POSTHOC SEALED: $($bindings.Count) files, $total bytes; aggregate18 hashes reverified. No solver run."
Write-Output $manifest
