param(
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$BinaryLabel,
  [Parameter(Mandatory=$true)][ValidateSet('hg_release_sequence_r1_spr015_c','hg_release_hgoff_r1')][string]$InputRun,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label
)
# Fresh manufactured-field execution only: reuse geometry/input, not old source.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$logs=Join-Path $tests 'logs'
$output=Join-Path $tests "outputs\$Label"
$receipt=Join-Path $logs "$Label.run.json"
$stdout=Join-Path $logs "$Label.stdout.log"
$stderr=Join-Path $logs "$Label.stderr.log"
foreach($path in @($output,$receipt,$stdout,$stderr)){
  if(Test-Path -LiteralPath $path){throw "Refusing overwrite: $path"}
}
function HashFile([string]$path){
  $file=Get-Item -LiteralPath $path
  [ordered]@{path=$file.FullName;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
}
function VerifyFiles($entries){
  foreach($entry in $entries){
    if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw "Hash mismatch: $($entry.path)"}
  }
}
$buildPath=Join-Path $logs "mdbc_scalar_$BinaryLabel.build.json"
$preparePath=Join-Path $logs "$InputRun.prepare.json"
$sourceRunPath=Join-Path $logs "$InputRun.run.json"
$build=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json
$prepare=Get-Content -LiteralPath $preparePath -Raw|ConvertFrom-Json
$sourceRun=Get-Content -LiteralPath $sourceRunPath -Raw|ConvertFrom-Json
if($build.status -ne 'built_not_run' -or !$build.production_build_confirmed){throw 'Fixture build is not confirmed.'}
$buildEntries=@($build.inputs)+@($build.resolved_compile_link_inputs)+@($build.runtime)
VerifyFiles $buildEntries
$buildLog=Join-Path $logs "mdbc_scalar_$BinaryLabel.build.log"
VerifyFiles @([pscustomobject]@{path=$buildLog;sha256=$build.build_log_sha256})
$exe=Join-Path $tests "outputs\mdbc_scalar_$BinaryLabel\mdbc_scalar.exe"
VerifyFiles @([pscustomobject]@{path=$exe;sha256=$build.exe_sha256})
$expectedPrefix=Join-Path $tests "outputs\${InputRun}_input\CaseTCq0_$InputRun"
if($prepare.prefix -ne $expectedPrefix){throw 'Prepared input prefix does not match the selected fixture input.'}
$inputPaths=@($prepare.definition,"$expectedPrefix.xml","$expectedPrefix.bi4","${expectedPrefix}_Normals.nbi4")
$inputs=@()
foreach($path in $inputPaths){
  $fromPrepare=@($prepare.inputs|Where-Object{$_.path -eq $path})
  $fromRun=@($sourceRun.inputs|Where-Object{$_.path -eq $path})
  if($fromPrepare.Count -ne 1 -or $fromRun.Count -ne 1 -or $fromPrepare[0].sha256 -ne $fromRun[0].sha256){throw "Run/prepare input evidence disagrees: $path"}
  VerifyFiles $fromPrepare
  $inputs+=HashFile $path
}
$arguments=@('-cpu','-stable','-ompthreads:1','-mdbc',$expectedPrefix,$output,'-dirdataout','data','-svres','-sv:none')
$record=[ordered]@{
  status='validated_not_started';purpose='production_scalar_manufactured_fields';label=$Label
  started_utc=[DateTime]::UtcNow.ToString('o');binary_label=$BinaryLabel;input_run=$InputRun
  configuration=$build.configuration;executable=HashFile $exe;arguments=$arguments
  build_manifest=HashFile $buildPath;build_log=HashFile $buildLog
  prepare_manifest=HashFile $preparePath;source_run_manifest=HashFile $sourceRunPath
  runner=HashFile $PSCommandPath;inputs=$inputs;verified_build_entry_count=$buildEntries.Count
  old_production_source_revalidated=$false;input_reuse_scope='prepared XML and native GenCase particles/normals only'
  output=$output;pid=$null;exit_code=$null;owned_process_absent=$null
  inputs_unchanged=$false;completion=$null;outputs=@();failure=$null;physical_accuracy_accepted=$false
}
# Exclusively reserve this run label before starting its one owned child.
$reservation=[IO.File]::Open($receipt,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
$reservation.Dispose()
function SaveRecord{$record|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $receipt -Encoding UTF8}
SaveRecord
$child=$null
try{
  $quoted=@($arguments|ForEach-Object{'"'+$_+'"'}) -join ' '
  # -Wait preserves the completed short process handle/exit code. Do not call
  # Refresh afterwards: an already exited process may lose that cached code.
  $child=Start-Process -FilePath $exe -ArgumentList $quoted -WorkingDirectory (Split-Path -Parent $exe) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $record.pid=$child.Id;$record.exit_code=$child.ExitCode;$record.owned_process_absent=$child.HasExited
  VerifyFiles $buildEntries;VerifyFiles $inputs
  VerifyFiles @($record.build_manifest,$record.prepare_manifest,$record.source_run_manifest,$record.runner)
  $record.inputs_unchanged=$true
  $completePath=Join-Path $output 'scalar_complete.json'
  if(Test-Path -LiteralPath $completePath){$record.completion=Get-Content -LiteralPath $completePath -Raw|ConvertFrom-Json}
  if($null -eq $record.exit_code -or $record.exit_code -ne 0){throw "Fixture exit code '$($record.exit_code)'; inspect stdout/stderr and Run.out."}
  if(!$record.completion -or !$record.completion.passed -or $record.completion.time_integrated -or $record.completion.physical_acceptance){throw 'Missing or invalid scalar completion.'}
  if([int]$record.completion.spr_enabled -ne [int]$prepare.settings.spr){throw 'Completion SPR mode disagrees with prepared input.'}
  $expectedTrials=if($prepare.settings.spr){4}else{1}
  if($record.completion.trials -ne $expectedTrials -or $record.completion.native_walls -ne 40){throw 'Incomplete manufactured-field coverage.'}
  $record.status='passed_scalar_only'
}
catch{
  $record.status='failed';$record.failure=$_.Exception.Message
}
finally{
  $record.finished_utc=[DateTime]::UtcNow.ToString('o')
  $paths=@($stdout,$stderr)|Where-Object{Test-Path -LiteralPath $_}
  if(Test-Path -LiteralPath $output){$paths+=@(Get-ChildItem -LiteralPath $output -Recurse -File|ForEach-Object{$_.FullName})}
  $record.outputs=@($paths|ForEach-Object{HashFile $_});SaveRecord
}
Write-Output "$($record.status): $receipt"
if($record.status -ne 'passed_scalar_only'){throw $record.failure}
