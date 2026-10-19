param(
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$BinaryLabel,
  [ValidatePattern('^mdbc_plane_[A-Za-z0-9_-]+$')][string]$PrepareTag='mdbc_plane_r2',
  [Parameter(Mandatory=$true)][ValidateSet('2d_h','2d_v','2d_t','3d_h','3d_t','3d_o')][string]$Geometry,
  [Parameter(Mandatory=$true)][ValidateRange(1,3)][int]$Slip,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label
)
# One fresh non-integrating fixture only. Never rerun/overwrite retained outputs.
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
    if(!$entry.path -or !$entry.sha256 -or (Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw "Hash mismatch: $($entry.path)"}
  }
}
$buildPath=Join-Path $logs "mdbc_vector_$BinaryLabel.build.json"
$preparePath=Join-Path $logs "$PrepareTag.prepare.json"
$build=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json
$prepare=Get-Content -LiteralPath $preparePath -Raw|ConvertFrom-Json
if($build.status -ne 'built_not_run' -or !$build.production_build_confirmed){throw 'Fixture build is not confirmed.'}
if($prepare.tag -ne $PrepareTag -or $prepare.status -ne 'gencase_prepared_not_solver_validated' -or $prepare.solver_started){throw 'Invalid plane preparation manifest.'}
$variantLabel="${PrepareTag}_${Geometry}_s$Slip"
$variants=@($prepare.variants|Where-Object{$_.label -eq $variantLabel})
$runs=@($prepare.runs|Where-Object{$_.label -eq $variantLabel})
if($variants.Count -ne 1 -or $runs.Count -ne 1 -or $null -eq $runs[0].exit_code -or $runs[0].exit_code -ne 0){throw 'Prepared variant is missing, ambiguous or failed.'}
$variant=$variants[0];$preparedRun=$runs[0]
$expectedPrefix=Join-Path $tests "outputs\${variantLabel}_input\CaseMdbcPlane_$variantLabel"
if($variant.prefix -ne $expectedPrefix -or $variant.geometry -ne $Geometry -or $variant.slip_mode -ne $Slip){throw 'Selected preparation descriptor disagrees with its path/mode.'}
if(@($variant.rotation).Count -ne 3 -or @($variant.normal).Count -ne 3){throw 'Missing prepared rotation/normal.'}
for($i=0;$i -lt 3;$i++){
  if(@($variant.rotation[$i]).Count -ne 3 -or [math]::Abs([double]$variant.rotation[$i][2]-[double]$variant.normal[$i]) -gt 1e-12){throw 'Prepared rotation and normal disagree.'}
}
$buildEntries=@($build.inputs)+@($build.resolved_compile_link_inputs)+@($build.runtime)
VerifyFiles $buildEntries
$buildLog=Join-Path $logs "mdbc_vector_$BinaryLabel.build.log"
VerifyFiles @([pscustomobject]@{path=$buildLog;sha256=$build.build_log_sha256})
$exe=Join-Path $tests "outputs\mdbc_vector_$BinaryLabel\mdbc_vector.exe"
VerifyFiles @([pscustomobject]@{path=$exe;sha256=$build.exe_sha256})
$preparedEntries=@($prepare.template,$prepare.script,$prepare.gencase,$preparedRun.definition,$preparedRun.log)+@($preparedRun.outputs)
VerifyFiles $preparedEntries
if($preparedRun.definition.path -ne $variant.definition){throw 'Prepared definition path mismatch.'}
foreach($path in @("$expectedPrefix.xml","$expectedPrefix.bi4")){
  if(@($preparedRun.outputs|Where-Object{$_.path -eq $path}).Count -ne 1){throw "Missing ordinary GenCase input: $path"}
}
# NBI4 is intentionally not required: the production initializer constructs
# normals from boundnormal_plane in these ordinary GenCase XML/BI4 inputs.
$arguments=@([string]$variant.dimension,[string]$variant.slip_mode,[string]$variant.native_count,[string]$variant.wall_count,[string]$variant.wall_roi_count)
for($i=0;$i -lt 3;$i++){for($j=0;$j -lt 3;$j++){$arguments+=([double]$variant.rotation[$i][$j]).ToString('R',[Globalization.CultureInfo]::InvariantCulture)}}
$boundaryOption=@('-mdbc','-mdbc_noslip','-mdbc_freeslip')[$Slip-1]
$arguments+=@('-cpu','-stable','-ompthreads:1',$boundaryOption,$expectedPrefix,$output,'-dirdataout','data','-svres','-sv:none')
$record=[ordered]@{
  status='validated_not_started';purpose='production_vector_and_scalar_manufactured_fields';label=$Label
  started_utc=[DateTime]::UtcNow.ToString('o');binary_label=$BinaryLabel;prepared_variant=$variantLabel
  configuration=$build.configuration;descriptor=$variant;executable=HashFile $exe;arguments=$arguments
  build_manifest=HashFile $buildPath;build_log=HashFile $buildLog;prepare_manifest=HashFile $preparePath
  runner=HashFile $PSCommandPath;inputs=$preparedEntries;verified_build_entry_count=$buildEntries.Count
  old_production_source_revalidated=$false;input_reuse_scope='ordinary GenCase XML/BI4 and plane initializer; no old physical run adopted'
  output=$output;pid=$null;exit_code=$null;owned_process_absent=$null
  inputs_unchanged=$false;completion=$null;outputs=@();failure=$null;physical_accuracy_accepted=$false
}
$reservation=[IO.File]::Open($receipt,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
$reservation.Dispose()
function SaveRecord{$record|ConvertTo-Json -Depth 10|Set-Content -LiteralPath $receipt -Encoding UTF8}
SaveRecord
$child=$null
try{
  $quoted=@($arguments|ForEach-Object{'"'+$_+'"'}) -join ' '
  # Preserve the exit code of a short-lived fixture. No post-exit Refresh().
  $child=Start-Process -FilePath $exe -ArgumentList $quoted -WorkingDirectory (Split-Path -Parent $exe) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $record.pid=$child.Id;$record.exit_code=$child.ExitCode;$record.owned_process_absent=$child.HasExited
  VerifyFiles $buildEntries;VerifyFiles $preparedEntries
  VerifyFiles @($record.build_manifest,$record.build_log,$record.prepare_manifest,$record.runner)
  $record.inputs_unchanged=$true
  $completePath=Join-Path $output 'vector_complete.json'
  if(Test-Path -LiteralPath $completePath){$record.completion=Get-Content -LiteralPath $completePath -Raw|ConvertFrom-Json}
  if($null -eq $record.exit_code -or $record.exit_code -ne 0 -or !$record.owned_process_absent){throw "Fixture exit code '$($record.exit_code)'; inspect stdout/stderr and Run.out."}
  $done=$record.completion
  if(!$done -or !$done.passed -or $done.time_integrated -or $done.physical_acceptance){throw 'Missing or invalid manufactured-field completion.'}
  if($done.dimension -ne $variant.dimension -or $done.slip_mode -ne $Slip -or $done.native_count -ne $variant.native_count -or $done.wall_count -ne $variant.wall_count -or $done.wall_roi_count -ne $variant.wall_roi_count){throw 'Incomplete/wrong manufactured-field geometry coverage.'}
  $soilRoi=if($variant.dimension -eq 2){12}else{48}
  if($done.soil_roi_count -ne $soilRoi -or $done.r_wiring_0ulp_native_count -ne $variant.native_count -or !$done.r_reference_physical_velocity_restored -or !$done.actual_rotated_native_grid_verified){throw 'Incomplete consumer/native-grid/restore checks.'}
  $inactiveTrials=if($Slip -eq 1){0}else{1}
  if($done.forced_inactive_branch_trials -ne $inactiveTrials -or !$done.forced_inactive_is_not_physical_activation_test){throw 'Incomplete inactive-branch fixture.'}
  if($done.copied_mls_or_neighbor_formula -or !$done.raw_density_analytic_error_is_not_an_acceptance_gate -or !$done.constant_projection_is_not_bc_compatible_flow){throw 'Fixture scope changed.'}
  $record.status='passed_manufactured_fields_only'
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
if($record.status -ne 'passed_manufactured_fields_only'){throw $record.failure}
