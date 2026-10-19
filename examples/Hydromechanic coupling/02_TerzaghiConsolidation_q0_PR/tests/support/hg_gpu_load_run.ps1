param(
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$BuildLabel='r1',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [switch]$Origin
)
# Execute only the built, zero-step G2 fixture; never launches the physical solver.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$case=Split-Path -Parent $tests
$prefix=if($Origin){'hg_gpu_load_origin'}else{'hg_gpu_load'}
$name="${prefix}_${Configuration}_$Label"
$buildPath=Join-Path $tests "logs\${prefix}_${Configuration}_$BuildLabel.build.json"
$build=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json
$out=Join-Path $tests "outputs\${name}_run"
$start=Join-Path $tests "logs\$name.start.json"
$receipt=Join-Path $tests "logs\$name.check.json"
$stdout=Join-Path $tests "logs\$name.stdout.log"
$stderr=Join-Path $tests "logs\$name.stderr.log"
foreach($p in @($out,$start,$receipt,$stdout,$stderr)){if(Test-Path -LiteralPath $p){throw "Refusing existing artifact: $p"}}
if(Get-CimInstance Win32_Process|Where-Object {$_.Name -match '^(DualSPHysics.*|hg_gpu_load_test)\.exe$'}){throw 'A solver/fixture is already running'}
$stem=Join-Path $case 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_out\CaseTerzaghiConsolidation_q0_PR_full_k1em4'
$inputs=@($build.inputs)+@($build.runtime_dlls)+@([pscustomobject]@{path=$build.executable;sha256=$build.executable_sha256})
foreach($p in @($buildPath,$PSCommandPath,"$stem.xml","$stem.bi4","${stem}_Normals.nbi4")){
  $inputs+=([pscustomobject]@{path=$p;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash})
}
function VerifyInputs {foreach($entry in $inputs){if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw "Changed input: $($entry.path)"}}}
VerifyInputs
$argsText='"'+$stem+'" "'+$out+'"'
$record=[ordered]@{status='started';started_utc=[DateTime]::UtcNow.ToString('o');configuration=$Configuration;executable=$build.executable;arguments=$argsText;inputs=$inputs;physical_acceptance=$false}
$record|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $start -Encoding UTF8
$timer=[Diagnostics.Stopwatch]::StartNew()
$process=Start-Process -FilePath $build.executable -ArgumentList $argsText -WorkingDirectory (Split-Path -Parent $build.executable) -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -Wait
$record['pid']=$process.Id
$record|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $start -Encoding UTF8
$timer.Stop()
$record['exit_code']=$process.ExitCode
$record['wall_seconds']=$timer.Elapsed.TotalSeconds
$record['ended_utc']=[DateTime]::UtcNow.ToString('o')
$record['status']='failed'
try{
  if($null -eq $process.ExitCode -or $process.ExitCode -ne 0){throw "Fixture exit: $($process.ExitCode); inspect $stderr"}
  VerifyInputs
  $complete=Get-Content -LiteralPath (Join-Path $out 'complete.json') -Raw|ConvertFrom-Json
  if($Origin){
    if($complete.integrated_steps -ne 0 -or !$complete.same_backend_origin_exact -or !$complete.spatial_force_passed -or $complete.g2_accepted){throw 'Origin diagnostic did not pass or incorrectly claims acceptance'}
  }else{
    if(!$complete.passed -or $complete.integrated_steps -ne 0 -or !$complete.synthetic_passed -or !$complete.same_backend_off_path_exact){throw 'Fixture receipt did not pass'}
  }
  $record['metrics']=$complete
  $record['status']=if($Origin){'origin_and_spatial_force_passed_not_physical_acceptance'}else{'passed_zero_step_operators_only'}
}catch{$record['error']=$_.Exception.Message}
$files=@($stdout,$stderr)+@(Get-ChildItem -LiteralPath $out -File -Recurse -ErrorAction SilentlyContinue|ForEach-Object {$_.FullName})
$record['outputs']=@($files|Where-Object {Test-Path -LiteralPath $_}|ForEach-Object {[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})
$record|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $receipt -Encoding UTF8
Write-Output "$($record.status): $receipt"
if($record.status -eq 'failed'){throw $record.error}
