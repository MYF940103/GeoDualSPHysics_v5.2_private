param([switch]$Apply,[int[]]$Index=@())
$ErrorActionPreference='Stop'
if(!$Apply){throw 'Explicit -Apply is required; review logs/cleanup_r1.plan.json first.'}
$taskTests=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskOutputs=[IO.Path]::GetFullPath((Join-Path $taskTests 'outputs'))
$taskPlanPath=Join-Path $taskTests 'logs\cleanup_r1.plan.json'
$taskPlan=Get-Content -LiteralPath $taskPlanPath -Raw -Encoding UTF8|ConvertFrom-Json
$taskPrefix=$taskOutputs.TrimEnd('\')+'\'
if([IO.Path]::GetFullPath($taskPlan.root) -cne $taskOutputs){throw 'Wrong cleanup root'}
$taskStatePath=Join-Path $taskTests 'logs\cleanup_r1.status.json'
if(Test-Path -LiteralPath $taskStatePath){$taskState=Get-Content -LiteralPath $taskStatePath -Raw -Encoding UTF8|ConvertFrom-Json}
else{$taskState=[pscustomobject]@{status='running';deleted=@();source_bytes_removed=0L;archive_bytes_retained=0L}}
if($Index.Count -eq 0){$Index=@($taskPlan.files|ForEach-Object{$_.index})}
foreach($taskIndex in $Index){
  if(@($taskState.deleted.index) -contains $taskIndex){continue}
  $taskItem=$taskPlan.files[$taskIndex]
  $taskPath=[IO.Path]::GetFullPath($taskItem.path)
  if(!$taskPath.StartsWith($taskPrefix,[StringComparison]::OrdinalIgnoreCase) -or $taskPath -cne $taskItem.path -or [IO.Path]::GetExtension($taskPath) -ne '.csv'){throw 'Target escaped exact CSV allowlist'}
  $taskAncestor=[IO.DirectoryInfo]::new([IO.Path]::GetDirectoryName($taskPath))
  while($taskAncestor.FullName.Length -ge $taskOutputs.Length){
    if($taskAncestor.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse directory is not admitted'}
    if($taskAncestor.FullName -ceq $taskOutputs){break};$taskAncestor=$taskAncestor.Parent
  }
  $taskFile=Get-Item -LiteralPath $taskPath
  if($taskFile.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse file is not admitted'}
  if($taskFile.Length -ne $taskItem.bytes -or $taskFile.LastWriteTimeUtc.Ticks -ne $taskItem.modified_ticks){throw 'Source metadata changed'}
  $taskTracked=@(git -C (Split-Path (Split-Path (Split-Path (Split-Path $taskTests)))) ls-files -- $taskPath)
  if($taskTracked.Count){throw 'Refuse removal of a tracked file'}
  $taskReceipt=Join-Path $taskTests ('logs\cleanup_r1_file_{0:D3}.json' -f $taskIndex)
  if(!(Test-Path -LiteralPath $taskReceipt)){
    $taskResult=& 'D:\Anaconda3\python.exe' -B (Join-Path $PSScriptRoot 'cleanup_archive_r1.py') --archive $taskIndex
    if($LASTEXITCODE -ne 0){throw ('Archive verification failed: '+$taskPath)}
  }
  $taskProof=Get-Content -LiteralPath $taskReceipt -Raw -Encoding UTF8|ConvertFrom-Json
  $taskFile=Get-Item -LiteralPath $taskPath
  if(!$taskProof.verified -or $taskProof.source -cne $taskPath -or $taskProof.archive -cne $taskItem.archive -or
     $taskProof.source_bytes -ne $taskFile.Length -or $taskProof.source_sha256 -cne $taskProof.decoded_sha256 -or
     $taskFile.LastWriteTimeUtc.Ticks -ne $taskItem.modified_ticks){throw 'Final source/archive guard failed'}
  if((Get-FileHash -LiteralPath $taskItem.archive -Algorithm SHA256).Hash.ToLowerInvariant() -cne $taskProof.archive_sha256){throw 'Archive hash changed'}
  Remove-Item -LiteralPath $taskPath
  $taskState.deleted+=@([pscustomobject]@{index=$taskIndex;path=$taskPath;archive=$taskItem.archive;source_bytes=$taskProof.source_bytes;archive_bytes=$taskProof.archive_bytes;deleted_utc=[DateTime]::UtcNow.ToString('o')})
  $taskState.source_bytes_removed+=$taskProof.source_bytes;$taskState.archive_bytes_retained+=$taskProof.archive_bytes
  $taskState.status='running';$taskState|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $taskStatePath -Encoding UTF8
  Write-Host ('Archived/verified/removed '+$taskIndex+': '+$taskItem.relative+'; saved '+[math]::Round(($taskProof.source_bytes-$taskProof.archive_bytes)/1MB,1)+' MiB')
}
$taskState.status=if($taskState.deleted.Count -eq $taskPlan.count){'completed'}else{'partial'}
$taskState|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $taskStatePath -Encoding UTF8
