param([switch]$Execute)
$ErrorActionPreference='Stop'
if(!$Execute){throw 'Review notes/root_retire_r1.md, then select -Execute.'}
$taskTests=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskCase=[IO.Path]::GetFullPath((Join-Path $taskTests '..'))
$taskZipPath=Join-Path $taskTests 'outputs\root_legacy_r1.zip'
$taskRecordPath=Join-Path $taskTests 'logs\root_retire_r1.archive.json'
$taskStatusPath=Join-Path $taskTests 'logs\root_retire_r1.status.json'
$taskNames=@(
  'CaseTerzaghiConsolidation_q0_PR_full_k1em2_out',
  'CaseTerzaghiConsolidation_q0_PR_full_k1em3_out',
  'CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0005_dt2em6_out',
  'CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_out',
  'CaseTerzaghiConsolidation_q0_PR_full_k1em4_double_out'
)
if((Test-Path -LiteralPath $taskZipPath) -or (Test-Path -LiteralPath $taskRecordPath) -or (Test-Path -LiteralPath $taskStatusPath)){throw 'Fresh archive only; do not overwrite or restart.'}
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$taskEntries=@();$taskFolders=@()
foreach($taskName in $taskNames){
  $taskDir=Get-Item -LiteralPath (Join-Path $taskCase $taskName)
  if(!$taskDir.PSIsContainer -or $taskDir.Parent.FullName -cne $taskCase -or $taskDir.Name -cne $taskName -or ($taskDir.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Invalid direct-child target'}
  $taskChildren=@(Get-ChildItem -LiteralPath $taskDir.FullName -Recurse -Force)
  if(@($taskChildren|Where-Object{$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count){throw 'Reparse point in source'}
  $taskFolders+=@($taskDir.FullName)+@($taskChildren|Where-Object{$_.PSIsContainer}|ForEach-Object{$_.FullName})
  foreach($taskFile in @($taskChildren|Where-Object{!$_.PSIsContainer})){
    $taskEntries+=[pscustomobject]@{source=$taskFile.FullName;member=$taskFile.FullName.Substring($taskCase.Length+1).Replace('\','/');bytes=$taskFile.Length;modified_ticks=$taskFile.LastWriteTimeUtc.Ticks.ToString();sha256=(Get-FileHash -LiteralPath $taskFile.FullName -Algorithm SHA256).Hash}
  }
}
$taskDataCount=$taskEntries.Count;$taskDataBytes=($taskEntries|Measure-Object bytes -Sum).Sum
$taskSnapshots=@(
  @('CaseTerzaghiConsolidation_q0_PR_full_k1em2_Def.xml','retired_inputs/CaseTerzaghiConsolidation_q0_PR_full_k1em2_Def.xml'),
  @('CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_Def.xml','retired_inputs/CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_Def.xml'),
  @('CaseTerzaghiConsolidation_q0_PR_full_k1em4_double_Def.xml','retired_inputs/CaseTerzaghiConsolidation_q0_PR_full_k1em4_double_Def.xml'),
  @('README.md','retired_inputs/README_before_root_retire.md')
)
foreach($taskStem in @('k1em2','k1em4_precision','k1em4_double')){
  $taskBat='xCaseTerzaghiConsolidation_q0_PR_full_'+$taskStem+'_win64_CPU.bat'
  $taskSnapshots+=,@(('tests\outputs\retired_root_inputs_r1\'+$taskBat),('retired_inputs/'+$taskBat))
}
foreach($taskPair in $taskSnapshots){
  $taskFile=Get-Item -LiteralPath (Join-Path $taskCase $taskPair[0])
  $taskEntries+=[pscustomobject]@{source=$taskFile.FullName;member=$taskPair[1];bytes=$taskFile.Length;modified_ticks=$taskFile.LastWriteTimeUtc.Ticks.ToString();sha256=(Get-FileHash -LiteralPath $taskFile.FullName -Algorithm SHA256).Hash}
}
$taskProtected=@(Get-ChildItem -LiteralPath $taskCase -File|Where-Object{$_.Extension -in @('.xml','.bat')})
$taskProtected+=@(Get-ChildItem -LiteralPath (Join-Path $taskCase 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_out') -File -Recurse)
$taskProtection=@($taskProtected|ForEach-Object{[pscustomobject]@{path=$_.FullName;bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}})
$taskZip=[IO.Compression.ZipFile]::Open($taskZipPath,[IO.Compression.ZipArchiveMode]::Create)
try{
  foreach($taskFolder in $taskFolders){[void]$taskZip.CreateEntry($taskFolder.Substring($taskCase.Length+1).Replace('\','/')+'/')}
  foreach($taskItem in $taskEntries){[void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($taskZip,$taskItem.source,$taskItem.member,[IO.Compression.CompressionLevel]::Fastest)}
}finally{$taskZip.Dispose()}
$taskZip=[IO.Compression.ZipFile]::OpenRead($taskZipPath)
try{
  if(@($taskZip.Entries|Where-Object{!$_.FullName.EndsWith('/')}).Count -ne $taskEntries.Count){throw 'Archive member count mismatch'}
  foreach($taskItem in $taskEntries){
    $taskEntry=$taskZip.GetEntry($taskItem.member)
    if(!$taskEntry -or $taskEntry.Length -ne $taskItem.bytes){throw 'Archive member missing or length changed'}
    $taskStream=$taskEntry.Open();$taskSha=[Security.Cryptography.SHA256]::Create()
    try{$taskHash=([BitConverter]::ToString($taskSha.ComputeHash($taskStream))).Replace('-','')}finally{$taskStream.Dispose();$taskSha.Dispose()}
    if($taskHash -cne $taskItem.sha256){throw ('Archive plaintext hash differs: '+$taskItem.member)}
  }
}finally{$taskZip.Dispose()}
$taskRecord=[pscustomobject]@{verified=$true;case_root=$taskCase;archive=$taskZipPath;archive_bytes=(Get-Item -LiteralPath $taskZipPath).Length;archive_sha256=(Get-FileHash -LiteralPath $taskZipPath -Algorithm SHA256).Hash;output_names=$taskNames;data_files=$taskDataCount;data_bytes=$taskDataBytes;member_files=$taskEntries.Count;members=$taskEntries;protected_files=$taskProtection;script_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash;raw_archive_cloud_backup=$false}
$taskRecord|ConvertTo-Json -Depth 7|Set-Content -LiteralPath $taskRecordPath -Encoding UTF8
$taskStatus=[pscustomobject]@{status='archive_verified';removed=@();remaining=@($taskNames);archive=$taskZipPath}
$taskStatus|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $taskStatusPath -Encoding UTF8
foreach($taskName in $taskNames){
  $taskTarget=(Resolve-Path -LiteralPath (Join-Path $taskCase $taskName)).Path
  if([IO.Path]::GetDirectoryName($taskTarget) -cne $taskCase -or [IO.Path]::GetFileName($taskTarget) -cne $taskName){throw 'Resolved target escaped exact whitelist'}
  $taskMembers=@($taskEntries|Where-Object{$_.member.StartsWith($taskName+'/',[StringComparison]::Ordinal)})
  if(@(Get-ChildItem -LiteralPath $taskTarget -Recurse -File -Force).Count -ne $taskMembers.Count){throw 'Source file count changed'}
  foreach($taskItem in $taskMembers){if((Get-FileHash -LiteralPath $taskItem.source -Algorithm SHA256).Hash -cne $taskItem.sha256){throw 'Source changed after archive verification'}}
  Remove-Item -LiteralPath $taskTarget -Recurse
  $taskStatus.removed+=@($taskTarget);$taskStatus.remaining=@($taskNames|Where-Object{$taskStatus.removed -notcontains (Join-Path $taskCase $_)})
  $taskStatus.status='removing';$taskStatus|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $taskStatusPath -Encoding UTF8
  Write-Host ('Archived, fully verified and removed from root: '+$taskName)
}
foreach($taskItem in $taskProtection){if((Get-FileHash -LiteralPath $taskItem.path -Algorithm SHA256).Hash -cne $taskItem.sha256){throw 'Protected baseline or formal input changed'}}
$taskStatus.status='completed';$taskStatus|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $taskStatusPath -Encoding UTF8
Write-Host ('Complete: '+$taskDataCount+' original output files; archive '+[math]::Round($taskRecord.archive_bytes/1MB,2)+' MiB; original information recoverable.')
