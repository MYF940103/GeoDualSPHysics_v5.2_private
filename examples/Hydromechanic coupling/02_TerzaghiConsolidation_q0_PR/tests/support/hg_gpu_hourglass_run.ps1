param(
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [string]$DebugBuild='', [string]$ReleaseBuild='',
  [switch]$Run
)
# Default is read-only. -Run executes the two already-built operator fixtures
# once, serially. No compilation, physical solver, retry, notifier or cleanup.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$logs=Join-Path $tests 'logs'
$tag="hg_gpu_hourglass_$Label"
$startPath=Join-Path $logs "$tag.start.json"
$checkPath=Join-Path $logs "$tag.check.json"
if(!$DebugBuild){$DebugBuild=Join-Path $logs 'hg_gpu_hourglass_Debug_r1.build.json'}
if(!$ReleaseBuild){$ReleaseBuild=Join-Path $logs 'hg_gpu_hourglass_Release_r1.build.json'}
function Hashes([string[]]$Paths){@($Paths|Sort-Object -Unique|ForEach-Object{[ordered]@{path=(Resolve-Path -LiteralPath $_).Path;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})}
function Verify($Entries){foreach($e in $Entries){if((Get-FileHash -LiteralPath $e.path -Algorithm SHA256).Hash -ne $e.sha256){throw "Changed bound input/output: $($e.path)"}}}
function Record([string]$Path,$Value){
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 14)+"`n")
  $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
$plans=@();$inputs=@();$reserved=@($startPath,$checkPath)
foreach($configuration in @('Debug','Release')){
  $buildPath=(Resolve-Path -LiteralPath $(if($configuration -eq 'Debug'){$DebugBuild}else{$ReleaseBuild})).Path
  $b=Get-Content -LiteralPath $buildPath -Raw -Encoding UTF8|ConvertFrom-Json
  if($b.status -ne 'built_not_run' -or $b.configuration -ne $configuration -or !$b.inputs.Count -or !$b.runtime_dlls.Count){throw "Incomplete/wrong fixture build: $buildPath"}
  $fixture=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'hg_gpu_hourglass_test.cpp')).Path
  if(!@($b.inputs|Where-Object {$_.path -eq $fixture}).Count -or [IO.Path]::GetFileName($b.executable) -ne 'hg_gpu_hourglass_test.exe'){throw 'Build manifest does not bind this HG fixture'}
  $entries=@($b.inputs)+@($b.runtime_dlls)+@([ordered]@{path=$b.executable;sha256=$b.executable_sha256})
  Verify $entries
  $inputs+=@($entries)+@(Hashes @($buildPath))
  $prefix=Join-Path $logs "hg_gpu_hourglass_${configuration}_$Label"
  $p=[ordered]@{configuration=$configuration;build=$buildPath;executable=$b.executable;prefix=$prefix;check="$prefix.check.json";record="$prefix.run.json";process="$prefix.process.json";stdout="$prefix.stdout.log";stderr="$prefix.stderr.log"}
  $plans+=,$p;$reserved+=@($p.check,$p.record,$p.process,$p.stdout,$p.stderr)
}
$inputs+=@(Hashes @($PSCommandPath))
foreach($path in $reserved){if(Test-Path -LiteralPath $path){throw "Refusing existing artifact: $path"}}
if(!$Run){[ordered]@{status='dry_run_no_writes_no_execution';plans=$plans;verified_hash_references=$inputs.Count;physical_acceptance=$false}|ConvertTo-Json -Depth 5;return}
if(Get-CimInstance Win32_Process|Where-Object {$_.Name -match '^(DualSPHysics.*|hg_gpu_.*)\.exe$'}){throw 'A solver/GPU fixture is active; no process was started or stopped'}
$started=[DateTime]::UtcNow
Record $startPath ([ordered]@{status='operator_sequence_started';utc_started=$started.ToString('o');plans=$plans;inputs=$inputs;physical_acceptance=$false;full_cycle_admitted=$false})
$passed=$false;$reason='';$runs=@();$unchanged=$false
try{
  foreach($p in $plans){
    Verify $inputs
    $timer=[Diagnostics.Stopwatch]::StartNew();$proc=$null;$metrics=$null;$okay=$false;$errorText=''
    $child=[ordered]@{pid=$null;exit_code=$null;owned_process_absent=$false;stopped_by_runner=$false}
    $arguments=@('--json',$p.check)
    try{
      $textArgs=($arguments|ForEach-Object {'"'+$_+'"'}) -join ' '
      $proc=Start-Process -FilePath $p.executable -ArgumentList $textArgs -WorkingDirectory (Split-Path -Parent $p.executable) -WindowStyle Hidden -RedirectStandardOutput $p.stdout -RedirectStandardError $p.stderr -PassThru
      $null=$proc.Handle
      $child.pid=$proc.Id
      Record $p.process ([ordered]@{pid=$proc.Id;executable=$p.executable;arguments=$arguments;utc_started=[DateTime]::UtcNow.ToString('o')})
      $proc.WaitForExit();$child.exit_code=$proc.ExitCode
      $child.owned_process_absent=$null -eq (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)")
      if($null -eq $child.exit_code -or $child.exit_code -ne 0 -or !$child.owned_process_absent){throw "Fixture did not complete: $($child|ConvertTo-Json -Compress)"}
      $metrics=Get-Content -LiteralPath $p.check -Raw -Encoding UTF8|ConvertFrom-Json
      if(!$metrics.passed -or $metrics.status -ne 'device_hg_operator_verified_not_physical_acceptance' -or $metrics.physical_acceptance -or $metrics.double_relative_plus_absolute_tolerance -ne 1e-8 -or $metrics.float_acceleration_epsilon_multiplier -ne 64 -or $metrics.gpu_cache_required_max_ulp -ne 0){throw 'HG operator receipt failed, altered its declared limits, or claims physical acceptance'}
      Verify $inputs;$okay=$true
    }catch{$errorText=$_.Exception.Message}finally{
      if($proc -and !$proc.HasExited){$proc.Kill();$proc.WaitForExit();$child.stopped_by_runner=$true}
      if($proc){$child.exit_code=$proc.ExitCode;$child.owned_process_absent=$null -eq (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)")}
      $timer.Stop()
    }
    # Even a rejected fixture retains its raw failed check and both streams.
    if(!$metrics -and (Test-Path -LiteralPath $p.check)){try{$metrics=Get-Content -LiteralPath $p.check -Raw -Encoding UTF8|ConvertFrom-Json}catch{}}
    try{Verify $inputs}catch{$okay=$false;$errorText+='; '+$_.Exception.Message}
    $outputs=Hashes @(@($p.check,$p.stdout,$p.stderr,$p.process)|Where-Object {Test-Path -LiteralPath $_})
    Record $p.record ([ordered]@{passed=$okay;configuration=$p.configuration;reason=$errorText;executable=$p.executable;arguments=$arguments;child=$child;wall_seconds=$timer.Elapsed.TotalSeconds;utc_finished=[DateTime]::UtcNow.ToString('o');metrics=$metrics;outputs=$outputs;stage_start=$startPath;stage_start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash;scope='Standalone four-stage device HG operator; no physical solver or coupled acceptance';physical_acceptance=$false;full_cycle_admitted=$false})
    $runs+=,$p.record
    if(!$okay){throw "Stage $($p.configuration) rejected: $errorText"}
  }
  Verify $inputs
  foreach($path in $runs){$r=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json;Verify $r.outputs}
  $unchanged=$true;$passed=$true
}catch{$reason=$_.Exception.Message}
if(!$unchanged){try{Verify $inputs;$unchanged=$true}catch{$reason+='; '+$_.Exception.Message}}
Record $checkPath ([ordered]@{passed=$passed;status=$(if($passed){'two_hg_operator_fixtures_passed_pending_review'}else{'failed_retained_no_retry'});reason=$reason;utc_started=$started.ToString('o');utc_finished=[DateTime]::UtcNow.ToString('o');runs=$runs;evidence=(Hashes $runs);inputs_unchanged=$unchanged;stage_start=$startPath;stage_start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash;physical_acceptance=$false;full_cycle_admitted=$false;limitations=@('No coupled GPU trajectory, boundary, pore pressure, restart or whole-run speedup claim.','Source/object/runtime/executable hashes bind artifacts; fresh authoritative production builds require separate review.','Any failure stops the sequence, preserves evidence, and is never retried.')})
if(!$passed){throw "HG operator sequence failed: $checkPath : $reason"}
Write-Output "PASS standalone operator fixtures only: $checkPath"
