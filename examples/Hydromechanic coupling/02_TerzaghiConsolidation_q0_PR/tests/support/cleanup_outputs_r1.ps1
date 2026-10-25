param([switch]$Inventory,[switch]$After)
$ErrorActionPreference='Stop'
$taskTests=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskOutputs=Join-Path $taskTests 'outputs'
$taskInventory=Join-Path $taskTests $(if($After){'logs\cleanup_r1.after_inventory.json'}else{'logs\cleanup_r1.inventory.json'})
if(!$Inventory){throw 'Select -Inventory; this script does not delete data.'}
if(Test-Path -LiteralPath $taskInventory){throw 'Inventory already exists; do not overwrite.'}
$taskRows=@()
foreach($taskDir in ([IO.DirectoryInfo]::new($taskOutputs)).EnumerateDirectories()){
  if($taskDir.Attributes -band [IO.FileAttributes]::ReparsePoint){throw ('Reparse directory: '+$taskDir.FullName)}
  $taskBytes=0L;$taskCount=0L;$taskTypes=@{};$taskReparse=@()
  foreach($taskFile in $taskDir.EnumerateFiles('*',[IO.SearchOption]::AllDirectories)){
    if($taskFile.Attributes -band [IO.FileAttributes]::ReparsePoint){$taskReparse+=$taskFile.FullName;continue}
    $taskBytes+=$taskFile.Length;$taskCount++
    $taskExt=$taskFile.Extension.ToLowerInvariant()
    if(!$taskExt){$taskExt='[none]'}
    if(!$taskTypes.ContainsKey($taskExt)){$taskTypes[$taskExt]=@{bytes=0L;files=0L}}
    $taskTypes[$taskExt].bytes+=$taskFile.Length;$taskTypes[$taskExt].files++
  }
  $taskRows+=[pscustomobject]@{name=$taskDir.Name;path=$taskDir.FullName;bytes=$taskBytes;files=$taskCount;types=$taskTypes;reparse_files=$taskReparse}
  if($taskBytes -ge 1GB){Write-Host ($taskDir.Name+' '+[math]::Round($taskBytes/1GB,2)+' GiB')}
}
$taskLoose=@($taskOutputs|Get-ChildItem -File|ForEach-Object{[pscustomobject]@{path=$_.FullName;bytes=$_.Length}})
$taskRecord=[pscustomobject]@{root=$taskOutputs;generated_utc=[DateTime]::UtcNow.ToString('o');directories=$taskRows;loose_files=$taskLoose;total_bytes=($taskRows|Measure-Object bytes -Sum).Sum}
$taskRecord|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $taskInventory -Encoding UTF8
Write-Host ('Recorded '+$taskRows.Count+' directories; '+[math]::Round($taskRecord.total_bytes/1GB,2)+' GiB')
