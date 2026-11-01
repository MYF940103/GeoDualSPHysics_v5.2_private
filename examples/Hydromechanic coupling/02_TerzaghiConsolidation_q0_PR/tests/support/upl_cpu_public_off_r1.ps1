param([switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Exactly the previously accepted P2 calls under a new label; no new harness/geometry/physics.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$logs=Join-Path $tests 'logs'
$label='cpu_public_r1';$target=Join-Path $logs 'upl_cpu_public_off_r1.check.json'
$freezePath=Join-Path $logs 'upl_cpu_public_build_r2.json'
$runner=Join-Path $PSScriptRoot 'upl_p2_run_r1.ps1'
$powershell=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 14)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root source/build review and explicit execution authorization required'}
if(Test-Path -LiteralPath $target){throw 'Final aggregate retained; no retry or overwrite'}
$existing=@(Get-ChildItem -LiteralPath $logs -File|Where-Object {$_.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_cpu_public_r1[._]' -or $_.Name -like 'upl_cpu_public_off_*_r1*'})
$existing+=@(Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Directory|Where-Object {$_.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_cpu_public_r1($|_)'})
if($existing.Count){throw 'New label already has artifacts; preserve and inspect instead of restarting'}
$freeze=Get-Content -Raw -LiteralPath $freezePath|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $freeze.source.Count -ne 7 -or $freeze.msbuild_exit_codes.DebugCPU -ne 0 -or $freeze.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Seven-file authoritative public CPU Rebuild not passed'}
$inputs=@(Entry $PSCommandPath;Entry $runner;Entry $powershell;Entry $freezePath)
function VerifyFreeze {
  Verify $inputs
  foreach($s in $freeze.source){Verify @($s.original,$s.snapshot)}
  Verify $freeze.inputs;Verify $freeze.logs;Verify $freeze.programs
}
VerifyFreeze
$driverCalls=@();$groups=@();$total=0
foreach($config in @('DebugCPU','ReleaseCPU')){
  foreach($mode in @('Build','Run','RunOpen')){
    VerifyFreeze
    $name="upl_cpu_public_off_$($config)_$($mode)_r1"
    $log=Join-Path $logs ($name+'.driver.log');$receipt=Join-Path $logs ($name+'.driver.json')
    foreach($p in @($log,$receipt)){if(Test-Path -LiteralPath $p){throw 'Owned driver call retained'}}
    [IO.File]::WriteAllBytes($log,[byte[]]@())
    $argv=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-Mode',$mode,'-Configuration',$config,'-Label',$label)
    if($mode -eq 'Build'){$argv+=@('-ProductionBuildConfirmed')}
    $start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
    & $powershell @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
    NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=(Entry $powershell);arguments=$argv;source_freeze=(Entry $freezePath);log=(Entry $log);physical_acceptance=$false})
    $driverCalls+=Entry $receipt
    if($code -ne 0){throw "Default-OFF $config $mode failed; preserve partial evidence and hold later calls"}
    VerifyFreeze
    if($mode -eq 'Build'){
      $buildPath=Join-Path $logs ("upl_p2_"+$config+"_"+$label+'.build.json')
      $build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
      if($build.status -ne 'built_not_run' -or $build.configuration -ne $config){throw 'Default-OFF companion build identity differs'}
      Verify $build.inputs;Verify @($build.program,$build.log);Verify $build.runtime
    }
  }
  foreach($spec in @(@('default_OFF',17),@('open_default_OFF',17),@('s8_observer',2),@('s128_observer',17),@('open_s128_observer',17))){
    $kind=[string]$spec[0];$expected=[int]$spec[1]
    $p=Join-Path $logs ("upl_p2_"+$config+"_"+$label+"_"+$kind+'.check.json')
    $check=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
    if(!$check.passed -or $check.actual_native_samples -ne $expected -or !$check.all15_original_arrays_ID_aligned_0ULP -or !$check.saved_clock_step_dterror_exact -or $check.receipts.Count -ne $expected){throw 'Full default-OFF native comparison incomplete'}
    Verify $check.receipts
    foreach($frame in $check.receipts){
      $f=Get-Content -Raw -LiteralPath $frame.path|ConvertFrom-Json
      if(!$f.passed -or $f.native_count -ne 1040 -or $f.arrays -ne 15 -or !$f.native_ID_aligned -or !$f.all_original_physical_array_bits_identical -or !$f.saved_time_step_dterror_exact -or !$f.no_exclusions){throw 'Native physical/clock/exclusion regression failed'}
    }
    $groups+=@{configuration=$config;frames=$expected;check=(Entry $p);comparison=$kind};$total+=$expected
  }
}
if($total -ne 140 -or $groups.Count -ne 10){throw 'Wrong complete native regression coverage'}
VerifyFreeze;Verify $driverCalls
NewJson $target ([ordered]@{passed=$true;label=$label;scope='Current default-OFF native regression and observer equivalence after limited public CPU wiring; not a public-ON XML/physical test';source_freeze=(Entry $freezePath);inputs=$inputs;driver_calls=$driverCalls;groups=$groups;actual_native_frame_pairs=$total;native_ids_per_pair=1040;existing_arrays_per_pair=15;all_bits_0ULP=$true;clock_step_dterror_exact=$true;exclusions=0;physical_acceptance=$false;raw_BI4_cloud_backup_claimed=$false})
Write-Output "PASSED default-OFF140 native pairs: $target"

