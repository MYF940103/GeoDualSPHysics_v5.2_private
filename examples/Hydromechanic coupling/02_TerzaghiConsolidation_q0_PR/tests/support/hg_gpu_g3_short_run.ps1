param(
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [string]$GpuDebugExe='', [string]$GpuReleaseExe='', [string]$CpuReleaseExe='',
  [Parameter(Mandatory=$true)][string]$GpuDebugBuildLog,
  [Parameter(Mandatory=$true)][string]$GpuReleaseBuildLog,
  [Parameter(Mandatory=$true)][string]$CpuReleaseBuildLog,
  [Parameter(Mandatory=$true)][string]$ReaderBuild,
  [string]$OperatorCheck='',
  [switch]$ProductionBuildConfirmed,
  [switch]$Run
)
# Default: read-only. -Run starts five fresh 20-step solvers in sequence:
# HG off GPU Debug/Release, then HG .1 GPU Debug/Release/CPU Release.
# Adopt the completed G2 controls; never rerun them, retry, or overwrite evidence.
$ErrorActionPreference='Stop'
if($Run -and !$ProductionBuildConfirmed){throw 'Review the opened-guard production builds before -Run -ProductionBuildConfirmed.'}
$tests=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $tests
$repo=(Resolve-Path -LiteralPath (Join-Path $caseRoot '..\..\..')).Path
$logs=Join-Path $tests 'logs'
$tag="hg_gpu_g3_short_$Label"
$seed=Join-Path $tests 'configs\hg_gpu_band_r1_seed'
$onSeed=Join-Path $tests "configs\${tag}_on_seed"
$startPath=Join-Path $logs "$tag.start.json"
$checkPath=Join-Path $logs "$tag.check.json"
if(!$GpuDebugExe){$GpuDebugExe=Join-Path $repo 'bin\windows\DualSPHysics5.2_win64_debug.exe'}
if(!$GpuReleaseExe){$GpuReleaseExe=Join-Path $repo 'bin\windows\DualSPHysics5.2_GEO_win64.exe'}
if(!$CpuReleaseExe){$CpuReleaseExe=Join-Path $repo 'bin\windows\DualSPHysics5.2CPU_win64.exe'}
function Hashes([string[]]$Paths){@($Paths|Sort-Object -Unique|ForEach-Object{[ordered]@{path=(Resolve-Path -LiteralPath $_).Path;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})}
function Verify($Entries){foreach($e in $Entries){if((Get-FileHash -LiteralPath $e.path -Algorithm SHA256).Hash -ne $e.sha256){throw "Changed bound artifact: $($e.path)"}}}
function Record([string]$Path,$Value){
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 14)+"`n")
  $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
function Number($Value){[double]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture)}
function Finite([double]$Value){![double]::IsNaN($Value) -and ![double]::IsInfinity($Value)}
function Child([string]$Exe,[string[]]$Values,[string]$Working,[string]$Prefix){
  $process=$null
  try{
    $textArgs=($Values|ForEach-Object{'"'+$_+'"'}) -join ' '
    $process=Start-Process -FilePath $Exe -ArgumentList $textArgs -WorkingDirectory $Working -WindowStyle Hidden -RedirectStandardOutput "$Prefix.stdout.log" -RedirectStandardError "$Prefix.stderr.log" -PassThru
    $null=$process.Handle
    Record "$Prefix.process.json" ([ordered]@{pid=$process.Id;executable=$Exe;arguments=$Values;started_utc=[DateTime]::UtcNow.ToString('o')})
    $process.WaitForExit();$code=$process.ExitCode
    return [ordered]@{pid=$process.Id;exit_code=$code;owned_process_absent=($null -eq (Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)" -ErrorAction Stop))}
  }finally{if($process -and !$process.HasExited){$process.Kill();$process.WaitForExit()}}
}
function ChildPassed($Result){$null -ne $Result.exit_code -and $Result.exit_code -eq 0 -and $Result.owned_process_absent}
function Summary([string]$Output,[string]$Backend,[bool]$Hourglass){
  $text=Get-Content -LiteralPath (Join-Path $Output 'Run.out') -Raw
  $summary=(Get-Content -LiteralPath (Join-Path $Output 'Run.csv') -Raw).TrimStart('#')|ConvertFrom-Csv -Delimiter ';'
  $mode=if($Backend -eq 'gpu'){'RunMode=.*Single-GPU'}else{'RunMode=.*Single core'}
  $steps=[regex]::Match($text,'Steps of simulation\.+:\s*(\d+)');$excluded=[regex]::Match($text,'Excluded particles\.+:\s*(\d+)')
  if(!$text.Contains('Finished execution (code=0).') -or $text -notmatch $mode -or $text -notmatch 'HydroMechTopLoadMode="TopKernelBand"' -or !$steps.Success -or [int]$steps.Groups[1].Value -ne 20 -or !$excluded.Success -or [int]$excluded.Groups[1].Value -ne 0){throw 'Run.out backend/mode5/20-step/completion check failed'}
  if([long]$summary.Steps -ne 20 -or [int]$summary.PartsOut -ne 0 -or [int]$summary.Np -ne 1040 -or [int]$summary.PartFiles -ne 21 -or [Math]::Abs((Number $summary.PhysicalTime)-0.0002) -gt 1e-12){throw 'Run.csv count/time mismatch'}
  $hg=$null
  if($Hourglass){
    $calls=[regex]::Matches($text,'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)')
    $cache=[regex]::Matches($text,'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)')
    $limits=[regex]::Matches($text,'SoilHourglass: max\|sum\(m\*H\)\|=(\S+) max\|sum\(m\*deltaAce\)\|=(\S+) max\(dt/tau\)=(\S+) spinbound=(\S+)')
    if($calls.Count -ne 1 -or $cache.Count -ne 1 -or $limits.Count -ne 1 -or $summary.Configuration -notmatch 'GNOG\(0\.1\)'){throw 'Missing/duplicate HG configuration or summary'}
    $a=$calls[0].Groups;$b=$cache[0].Groups;$c=$limits[0].Groups
    if([int]$a[1].Value -ne 40 -or [int]$a[2].Value -ne 20 -or [int]$a[3].Value -ne 20 -or [int]$a[4].Value -ne 40 -or [int]$b[1].Value+[int]$b[2].Value -ne 40 -or [int]$b[1].Value -lt 21 -or [int]$b[2].Value -gt 19){throw 'HG phase/cache counters do not describe twenty full steps'}
    $net=Number $c[1].Value;$actual=Number $c[2].Value;$ratio=Number $c[3].Value;$spin=Number $c[4].Value
    if(!(Finite $net) -or !(Finite $actual) -or !(Finite $ratio) -or !(Finite $spin) -or $net -lt 0 -or $actual -lt 0 -or $ratio -le 0 -or $ratio -gt .2 -or $spin -lt 0 -or $spin -ge .01){throw 'HG finite/dt/spin summary guard failed'}
    $hg=[ordered]@{forcecalls=40;predictorupdates=20;correctorupdates=20;ratecalls=40;ratecalculations=[int]$b[1].Value;endpoint_rate_reuses=[int]$b[2].Value;max_net_history_force=$net;max_net_float_acceleration_force=$actual;max_dt_over_tau=$ratio;spinbound=$spin;precision='Run.out %g summary; production enforces guards at full precision'}
  }elseif($text -match 'SoilHourglass:|SoilHourglassXi:|GNOG\('){throw 'HG-off run unexpectedly instantiated hourglass'}
  return [ordered]@{run=$summary;hourglass=$hg}
}

# Operator evidence precedes opening the production guard. Preserve its historical
# source hashes; the later JSph.cpp guard change is not a fixture rerun.
if(!$OperatorCheck){$OperatorCheck=Join-Path $logs 'hg_gpu_hourglass_r1.check.json'}
$fixturePath=(Resolve-Path -LiteralPath $OperatorCheck).Path
$fixture=Get-Content -LiteralPath $fixturePath -Raw -Encoding UTF8|ConvertFrom-Json
if(!$fixture.passed -or !$fixture.inputs_unchanged -or $fixture.status -ne 'two_hg_operator_fixtures_passed_pending_review' -or $fixture.runs.Count -ne 2 -or $fixture.physical_acceptance){throw 'Both G3 operator fixtures must have passed before short trajectories'}
Verify $fixture.evidence
if((Get-FileHash -LiteralPath $fixture.stage_start -Algorithm SHA256).Hash -ne $fixture.stage_start_sha256){throw 'HG operator start binding changed'}
$fixtureStart=Get-Content -LiteralPath $fixture.stage_start -Raw -Encoding UTF8|ConvertFrom-Json
foreach($relative in @('JSphHourglassGpu.h','JSphHourglassGpu.cpp','JSphHourglassGpu_ker.h','JSphHourglassGpu_ker.cu','JSphHourglassCpu.h','JSphHourglassCpu.cpp')){
  $source=(Resolve-Path -LiteralPath (Join-Path $repo "src\source\$relative")).Path
  $binding=@($fixtureStart.inputs|Where-Object{$_.path -eq $source})
  if(!$binding.Count){throw "HG operator did not bind current module: $relative"}
  Verify $binding
}
$retained=@($fixturePath,$fixture.stage_start)
foreach($path in $fixture.runs){
  $r=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json
  if(!$r.passed -or !(ChildPassed $r.child) -or $r.child.stopped_by_runner -or !$r.metrics.passed -or $r.metrics.double_relative_plus_absolute_tolerance -ne 1e-8 -or $r.metrics.float_acceleration_epsilon_multiplier -ne 64 -or $r.metrics.gpu_cache_required_max_ulp -ne 0){throw 'HG operator run/limits failed'}
  Verify $r.outputs;$retained+=@($path)+@($r.outputs|ForEach-Object{$_.path})
}
$snapshotPath=Join-Path $logs 'gpu_g2_verified.snapshot.json'
$snapshot=Get-Content -LiteralPath $snapshotPath -Raw -Encoding UTF8|ConvertFrom-Json
if($snapshot.status -ne 'frozen_stage_baseline' -or !$snapshot.source_and_copy_hashes_verified){throw 'G2 frozen baseline receipt is missing'}
$oldStartPath=Join-Path $logs 'hg_gpu_band_r1.start.json'
$oldStart=Get-Content -LiteralPath $oldStartPath -Raw -Encoding UTF8|ConvertFrom-Json
Verify $oldStart.generated_inputs
$retained+=@($snapshotPath,$oldStartPath)+@($oldStart.generated_inputs|ForEach-Object{$_.path})
$controls=@{}
foreach($name in @('gpu_debug','gpu_release')){
  $path=Join-Path $logs "hg_gpu_band_r1_$name.run.json";$r=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json
  if(!$r.completed -or !(ChildPassed $r.solver) -or !(ChildPassed $r.inspector) -or !$r.metrics.passed -or $r.metrics.parts_checked -ne 21 -or (Get-FileHash -LiteralPath $oldStartPath -Algorithm SHA256).Hash -ne $r.stage_start_sha256){throw 'Retained G2 run is not complete/bound'}
  Verify $r.inputs;Verify $r.outputs
  $e=@($snapshot.entries|Where-Object{$_.relative -eq ('bin\'+[IO.Path]::GetFileName($r.executable))})
  $oldExe=@($oldStart.inputs|Where-Object{$_.path -eq $r.executable})
  if($e.Count -ne 1 -or $oldExe.Count -ne 1 -or $e[0].sha256 -ne $oldExe[0].sha256){throw 'Frozen G2 executable does not match original run'}
  $frozen=Join-Path $snapshot.snapshot $e[0].relative
  Verify @([ordered]@{path=$frozen;sha256=$e[0].sha256})
  $controls[$name]=Join-Path $tests "outputs\hg_gpu_band_r1_$name\data"
  $retained+=@($path,$frozen)+@($r.outputs|ForEach-Object{$_.path})
}
$compareBuild=Join-Path $logs 'hg_gpu_off_compare_r2.build.json'
$ReaderBuild=(Resolve-Path -LiteralPath $ReaderBuild).Path
$readers=@()
foreach($pair in @(@{path=$ReaderBuild;source='hg_gpu_band_part_check.cpp'},@{path=$compareBuild;source='hg_gpu_off_compare.cpp'})){
  $b=Get-Content -LiteralPath $pair.path -Raw -Encoding UTF8|ConvertFrom-Json
  if($b.status -ne 'built_not_run' -or !$b.source_unchanged){throw 'Invalid retained reader build'}
  $source=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot $pair.source)).Path
  $binding=@($b.source_inputs|Where-Object{$_.path -eq $source})
  if($binding.Count -ne 1){throw 'Reader source is not bound'}
  Verify $binding;Verify @([ordered]@{path=$b.executable;sha256=$b.executable_sha256})
  $readers+=,$b.executable;$retained+=@($pair.path,$b.executable,$source)
}
$reader=$readers[0];$comparator=$readers[1]
$utf8=[Text.UTF8Encoding]::new($false,$true);$xml=$utf8.GetString([IO.File]::ReadAllBytes("$seed.xml"))
[xml]$parsed=$xml.TrimStart([char]0xFEFF)
if($parsed.SelectSingleNode('//parameter[@key="SoilHourglassXi"]') -or $parsed.SelectSingleNode('//parameter[@key="SoilBoundaryDerivativeSPR"]') -or $parsed.SelectSingleNode('//HydroMechDrainageFixedGrid') -or $parsed.SelectSingleNode('//hydromechanics/HydroMechTopLoadMode').value -ne 'TopKernelBand'){throw 'Expected untouched G2 band seed with HG/SPR/fixed-grid absent'}
$anchor='        <parameters>'
if([regex]::Matches($xml,[regex]::Escape($anchor)).Count -ne 1){throw 'Seed parameters anchor changed'}
$newline=if($xml.Contains("`r`n")){"`r`n"}else{"`n"}
$onXml=$xml.Replace($anchor,$anchor+$newline+'            <parameter key="SoilHourglassXi" value="0.1" comment="GPU G3 twenty-step elastic hourglass smoke; not physical acceptance" />')
[xml]$onParsed=$onXml.TrimStart([char]0xFEFF)
if($onParsed.SelectSingleNode('//parameter[@key="SoilHourglassXi"]').value -ne '0.1'){throw 'HG-on seed validation failed'}
$backends=@(
  @{stage='gpu_debug';backend='gpu';exe=$GpuDebugExe;build=$GpuDebugBuildLog},
  @{stage='gpu_release';backend='gpu';exe=$GpuReleaseExe;build=$GpuReleaseBuildLog},
  @{stage='cpu_release';backend='cpu';exe=$CpuReleaseExe;build=$CpuReleaseBuildLog}
)
$plans=@();$reserved=@($startPath,$checkPath,"$onSeed.xml","$onSeed.bi4","${onSeed}_Normals.nbi4")
foreach($on in @($false,$true)){foreach($p in $backends){
  if(!$on -and $p.backend -eq 'cpu'){continue}
  $mode=if($on){'on'}else{'off'};$name="${tag}_${mode}_$($p.stage)";$prefix=Join-Path $logs $name
  $plan=[ordered]@{name=$name;stage=$p.stage;backend=$p.backend;hourglass=$on;exe=(Resolve-Path -LiteralPath $p.exe).Path;build_log=(Resolve-Path -LiteralPath $p.build).Path;seed=$(if($on){$onSeed}else{$seed});output=(Join-Path $tests "outputs\$name");prefix=$prefix;record="$prefix.run.json";parts="$prefix.parts.check.json";comparison="$prefix.compare.json"}
  $plans+=,$plan;$reserved+=@($plan.output,$plan.record,$plan.parts,$plan.comparison)
  foreach($suffix in @('.stdout.log','.stderr.log','.process.json','.reader.stdout.log','.reader.stderr.log','.reader.process.json','.compare.stdout.log','.compare.stderr.log','.compare.process.json')){$reserved+="$prefix$suffix"}
}}
foreach($path in $reserved){if(Test-Path -LiteralPath $path){throw "Refusing existing artifact: $path"}}
$sources=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\source') -File -Recurse|ForEach-Object{$_.FullName})
$projects=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\VS') -File|Where-Object{$_.Extension -in @('.sln','.vcxproj','.props')}|ForEach-Object{$_.FullName})
$runtime=@($plans|ForEach-Object{Get-ChildItem -LiteralPath (Split-Path -Parent $_.exe) -Filter '*.dll' -File|ForEach-Object{$_.FullName}})
$inputs=Hashes ($sources+$projects+$runtime+$retained+@($PSCommandPath)+@($plans|ForEach-Object{@($_.exe,$_.build_log)}))
if(!$Run){[ordered]@{status='dry_run_no_writes_no_solvers';plans=$plans;verified_hashes=$inputs.Count;adopted_g2_controls=$controls;steps=20;parts=21;dt_s=1e-5;final_time_s=.0002;physical_acceptance=$false}|ConvertTo-Json -Depth 6;return}
if(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^(DualSPHysics.*|hg_gpu_.*)\.exe$'}){throw 'A solver/GPU fixture is active; no new process started'}
[IO.File]::WriteAllBytes("$onSeed.xml",$utf8.GetBytes($onXml))
Copy-Item -LiteralPath "$seed.bi4" -Destination "$onSeed.bi4"
Copy-Item -LiteralPath "${seed}_Normals.nbi4" -Destination "${onSeed}_Normals.nbi4"
$generated=Hashes @("$onSeed.xml","$onSeed.bi4","${onSeed}_Normals.nbi4")
$started=[DateTime]::UtcNow
Record $startPath ([ordered]@{status='five_short_trajectories_started';utc_started=$started.ToString('o');plans=$plans;inputs=$inputs;generated_inputs=$generated;adopted_g2_controls=$controls;operator_prerequisite=$fixturePath;xml_edit='Only add SoilHourglassXi=0.1; binary geometry/normals unchanged';steps=20;parts=21;dt_s=1e-5;final_time_s=.0002;builds_review_confirmed=$true;physical_acceptance=$false})
$passed=$false;$reason='';$runs=@();$unchanged=$false
try{
  foreach($p in $plans){
    Verify $inputs;Verify $generated
    $backend=if($p.backend -eq 'gpu'){'-gpu:0'}else{'-cpu'}
    $args=@($backend,'-stable','-ompthreads:1','-mdbc','-nsteps:20','-svsteps:1','-sv:binx','-svres:1',$p.seed,$p.output,'-dirdataout','data')
    New-Item -ItemType Directory -Path $p.output|Out-Null
    $timer=[Diagnostics.Stopwatch]::StartNew();$solver=$null;$inspection=$null;$comparison=$null;$summary=$null;$metrics=$null;$exact=$null;$okay=$false;$errorText=''
    try{
      $solver=Child $p.exe $args $p.output $p.prefix
      if(!(ChildPassed $solver)){throw 'Solver exit/ownership check failed'}
      $summary=Summary $p.output $p.backend $p.hourglass
      $inspection=Child $reader @((Join-Path $p.output 'data'),$p.backend,$p.parts) $tests "$($p.prefix).reader"
      if(!(ChildPassed $inspection)){throw 'Actual PART inspection failed'}
      $metrics=Get-Content -LiteralPath $p.parts -Raw -Encoding UTF8|ConvertFrom-Json
      if(!$metrics.passed -or $metrics.parts_checked -ne 21 -or $metrics.backend -ne $p.backend -or $metrics.physical_acceptance){throw 'PART receipt failed/incomplete'}
      if(!$p.hourglass){
        $comparison=Child $comparator @($controls[$p.stage],(Join-Path $p.output 'data'),$p.comparison,'1040','1e-5') $tests "$($p.prefix).compare"
        if(!(ChildPassed $comparison)){throw 'HG-off G2/G3 exact comparison failed'}
        $exact=Get-Content -LiteralPath $p.comparison -Raw -Encoding UTF8|ConvertFrom-Json
        if(!$exact.passed -or $exact.parts_compared -ne 21 -or $exact.differing_bytes -ne 0){throw 'HG-off comparison is not complete zero-byte equality'}
      }
      Verify $inputs;Verify $generated;$okay=$true
    }catch{$errorText=$_.Exception.Message}
    $timer.Stop()
    $outputs=Hashes (@(Get-ChildItem -LiteralPath $p.output -Recurse -File|ForEach-Object{$_.FullName})+@($reserved|Where-Object{$_ -like "$($p.prefix).*" -and (Test-Path -LiteralPath $_)}))
    Record $p.record ([ordered]@{completed=$okay;reason=$errorText;stage=$p.stage;hourglass=$p.hourglass;executable=$p.exe;arguments=$args;solver=$solver;inspector=$inspection;comparator=$comparison;wall_seconds=$timer.Elapsed.TotalSeconds;summary=$summary;metrics=$metrics;exact_comparison=$exact;inputs=$(if($p.hourglass){$generated}else{$oldStart.generated_inputs});outputs=$outputs;stage_start=$startPath;stage_start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash;cross_backend_field_review_pending=$p.hourglass;physical_acceptance=$false})
    $runs+=,$p.record
    if(!$okay){throw "Stage $($p.name) failed: $errorText"}
  }
  Verify $inputs;Verify $generated
  foreach($path in $runs){$r=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json;Verify $r.outputs}
  $unchanged=$true;$passed=$true
}catch{$reason=$_.Exception.Message}
if(!$unchanged){try{Verify $inputs;Verify $generated;$unchanged=$true}catch{$reason+='; '+$_.Exception.Message}}
Record $checkPath ([ordered]@{passed=$passed;status=$(if($passed){'g3_off_exact_and_on_lifecycle_passed_pending_field_review'}else{'failed_retained_no_retry'});reason=$reason;utc_started=$started.ToString('o');utc_finished=[DateTime]::UtcNow.ToString('o');runs=$runs;evidence=(Hashes $runs);inputs_unchanged=$unchanged;stage_start=$startPath;stage_start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash;cross_backend_field_review_pending=$true;physical_acceptance=$false;full_cycle_admitted=$false;limitations=@('Twenty steps only; no full-cycle, restart, efficiency or physical acceptance.','HG-on pressure/material settlement/double-stress cross-backend and on/off differences require separate offline review.','PART does not contain HG history/rates; operator fixture plus runtime guards cover those, not independent per-step PART reconstruction.','CPU does not emit HydroMechLoadAce. Saved float positions limit settlement resolution.','G2 controls/readers retain historical source bindings; current G3 source/exe/build logs are bound separately.','Build-log hashes and explicit confirmation do not independently prove source-to-executable freshness.')})
if(!$passed){throw "G3 short sequence failed; preserve $checkPath : $reason"}
Write-Output "PASS HG-off exact/HG-on lifecycle only; field review pending: $checkPath"
