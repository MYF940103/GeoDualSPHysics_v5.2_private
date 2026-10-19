param(
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [string]$GpuDebugExe='', [string]$GpuReleaseExe='', [string]$CpuReleaseExe='',
  [Parameter(Mandatory=$true)][string]$GpuDebugBuildLog,
  [Parameter(Mandatory=$true)][string]$GpuReleaseBuildLog,
  [Parameter(Mandatory=$true)][string]$CpuReleaseBuildLog,
  [Parameter(Mandatory=$true)][string]$ReaderBuild,
  [switch]$ProductionBuildConfirmed,
  [switch]$Run
)
# Default: read-only preparation check. -Run starts exactly three fresh 20-step
# real solvers, serially; no build/retry/notifier and no formal-input changes.
$ErrorActionPreference='Stop'
if($Run -and !$ProductionBuildConfirmed){throw 'Review all three production builds before -Run -ProductionBuildConfirmed.'}
$tests=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $tests
$repo=(Resolve-Path -LiteralPath (Join-Path $caseRoot '..\..\..')).Path
$logs=Join-Path $tests 'logs'
$tag="hg_gpu_band_$Label"
$stem=Join-Path $tests "configs\${tag}_seed"
$originalStem=Join-Path $caseRoot 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_out\CaseTerzaghiConsolidation_q0_PR_full_k1em4'
$startPath=Join-Path $logs "$tag.start.json"
$checkPath=Join-Path $logs "$tag.check.json"
if(!$GpuDebugExe){$GpuDebugExe=Join-Path $repo 'bin\windows\DualSPHysics5.2_win64_debug.exe'}
if(!$GpuReleaseExe){$GpuReleaseExe=Join-Path $repo 'bin\windows\DualSPHysics5.2_GEO_win64.exe'}
if(!$CpuReleaseExe){$CpuReleaseExe=Join-Path $repo 'bin\windows\DualSPHysics5.2CPU_win64.exe'}
function Hashes([string[]]$Paths){@($Paths|Sort-Object -Unique|ForEach-Object{[ordered]@{path=(Resolve-Path -LiteralPath $_).Path;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})}
function Verify($Entries){foreach($e in $Entries){if((Get-FileHash -LiteralPath $e.path -Algorithm SHA256).Hash -ne $e.sha256){throw "Input changed: $($e.path)"}}}
function Record([string]$Path,$Value){
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 12)+"`n")
  $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
function Arguments([string[]]$Values){($Values|ForEach-Object{'"'+$_+'"'}) -join ' '}
function Number($Value){[double]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture)}
function Child([string]$Exe,[string[]]$Values,[string]$Working,[string]$Prefix){
  $process=$null
  try{
    $process=Start-Process -FilePath $Exe -ArgumentList (Arguments $Values) -WorkingDirectory $Working -WindowStyle Hidden -RedirectStandardOutput "$Prefix.stdout.log" -RedirectStandardError "$Prefix.stderr.log" -PassThru
    # Cache the process handle before waiting; avoid the PowerShell -Wait/null
    # ExitCode failure previously encountered by the zero-step fixture runner.
    $null=$process.Handle
    Record "$Prefix.process.json" ([ordered]@{pid=$process.Id;executable=$Exe;arguments=$Values;started_utc=[DateTime]::UtcNow.ToString('o')})
    $process.WaitForExit();$code=$process.ExitCode
    $absent=$null -eq (Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)" -ErrorAction Stop)
    return [ordered]@{pid=$process.Id;exit_code=$code;owned_process_absent=$absent}
  }finally{
    if($process -and !$process.HasExited){$process.Kill();$process.WaitForExit()}
  }
}
function Summary([string]$Output,[string]$Backend){
  $text=Get-Content -LiteralPath (Join-Path $Output 'Run.out') -Raw
  $summary=(Get-Content -LiteralPath (Join-Path $Output 'Run.csv') -Raw).TrimStart('#')|ConvertFrom-Csv -Delimiter ';'
  $mode=if($Backend -eq 'gpu'){'RunMode=.*Single-GPU'}else{'RunMode=.*Single core'}
  $steps=[regex]::Match($text,'Steps of simulation\.+:\s*(\d+)');$excluded=[regex]::Match($text,'Excluded particles\.+:\s*(\d+)')
  if(!$text.Contains('Finished execution (code=0).') -or $text -notmatch $mode -or $text -notmatch 'HydroMechTopLoadMode="TopKernelBand"' -or !$steps.Success -or [int]$steps.Groups[1].Value -ne 20 -or !$excluded.Success -or [int]$excluded.Groups[1].Value -ne 0){throw 'Run.out does not verify backend/mode5/20 steps/no exclusion/normal completion'}
  if([long]$summary.Steps -ne 20 -or [int]$summary.PartsOut -ne 0 -or [int]$summary.Np -ne 1040 -or [int]$summary.PartFiles -ne 21 -or [Math]::Abs((Number $summary.PhysicalTime)-0.0002) -gt 1e-12){throw 'Run.csv count/time mismatch'}
  return $summary
}
$original=@(
  @{path="$originalStem.xml";sha256='BCE483AD4BF65FE7A4E84FEAA7FF8F2FFD7A2A588A7702E25DBE4E63639E7605'},
  @{path="$originalStem.bi4";sha256='4ABF3A19DE4F07F79B259A7DAB9081BD7BBBC32A4CA17524C347DAA3B98715A3'},
  @{path="${originalStem}_Normals.nbi4";sha256='66EB95E8C48C179CCC11E30DB25C9B206DC4056C805DA2798D9E0847DA20829B'}
)
Verify $original
$ReaderBuild=(Resolve-Path -LiteralPath $ReaderBuild).Path
$readerRecord=Get-Content -LiteralPath $ReaderBuild -Raw -Encoding UTF8|ConvertFrom-Json
$reader=(Resolve-Path -LiteralPath $readerRecord.executable).Path
if($readerRecord.status -ne 'built_not_run' -or !$readerRecord.source_unchanged -or (Get-FileHash -LiteralPath $reader -Algorithm SHA256).Hash -ne $readerRecord.executable_sha256){throw 'Reader build/executable binding failed'}
Verify $readerRecord.source_inputs
$readerSource=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'hg_gpu_band_part_check.cpp')).Path
if(!@($readerRecord.source_inputs|Where-Object {$_.path -eq $readerSource}).Count){throw 'Reader manifest does not bind the mode5 PART inspector source'}
$plans=@(
  [ordered]@{stage='gpu_debug';backend='gpu';exe=(Resolve-Path -LiteralPath $GpuDebugExe).Path;build_log=(Resolve-Path -LiteralPath $GpuDebugBuildLog).Path},
  [ordered]@{stage='gpu_release';backend='gpu';exe=(Resolve-Path -LiteralPath $GpuReleaseExe).Path;build_log=(Resolve-Path -LiteralPath $GpuReleaseBuildLog).Path},
  [ordered]@{stage='cpu_release';backend='cpu';exe=(Resolve-Path -LiteralPath $CpuReleaseExe).Path;build_log=(Resolve-Path -LiteralPath $CpuReleaseBuildLog).Path}
)
$reserved=@($startPath,$checkPath,"$stem.xml","$stem.bi4","${stem}_Normals.nbi4")
foreach($p in $plans){
  $p.name="${tag}_$($p.stage)";$p.output=Join-Path $tests "outputs\$($p.name)";$p.logprefix=Join-Path $logs $p.name
  $p.record="$($p.logprefix).run.json";$p.parts="$($p.logprefix).parts.check.json"
  $reserved+=@($p.output,$p.record,$p.parts)
  foreach($suffix in @('.stdout.log','.stderr.log','.process.json','.reader.stdout.log','.reader.stderr.log','.reader.process.json')){$reserved+="$($p.logprefix)$suffix"}
}
foreach($path in $reserved){if(Test-Path -LiteralPath $path){throw "Refusing existing artifact: $path"}}
$sourceFiles=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\source') -File -Recurse|ForEach-Object{$_.FullName})
$projectFiles=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\VS') -File|Where-Object{$_.Extension -in @('.sln','.vcxproj','.props')}|ForEach-Object{$_.FullName})
$runtime=@($plans|ForEach-Object{Get-ChildItem -LiteralPath (Split-Path -Parent $_.exe) -Filter '*.dll' -File|ForEach-Object{$_.FullName}})
$inputs=Hashes ($sourceFiles+$projectFiles+$runtime+@($PSCommandPath,$ReaderBuild,$reader)+@($plans|ForEach-Object{@($_.exe,$_.build_log)})+@($original|ForEach-Object{$_.path})+@($readerRecord.source_inputs|ForEach-Object{$_.path}))
$utf8=[Text.UTF8Encoding]::new($false,$true);$xml=$utf8.GetString([IO.File]::ReadAllBytes("$originalStem.xml"))
$pattern='(?<=<HydroMechTopLoadMode value=")TopVertical(?=")'
if([regex]::Matches($xml,$pattern).Count -ne 1){throw 'Seed must have exactly one TopVertical attribute'}
$newXml=[regex]::Replace($xml,$pattern,'TopKernelBand');[xml]$parsed=$newXml.TrimStart([char]0xFEFF)
if($parsed.SelectSingleNode('//hydromechanics/HydroMechTopLoadMode').value -ne 'TopKernelBand'){throw 'Mode5 XML validation failed'}
if(!$Run){[ordered]@{status='dry_run_no_writes_no_solvers';plans=$plans;input_hashes_verified=$inputs.Count;shared_generated_seed=$stem;steps=20;parts=21;final_time_s=0.0002}|ConvertTo-Json -Depth 6;return}
if(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^(DualSPHysics.*|hg_gpu_load.*)\.exe$'}){throw 'A solver/load fixture is active; this sequence has not started and will not stop it'}
# Preserve byte representation of the seed; only this one attribute changes.
[IO.File]::WriteAllBytes("$stem.xml",$utf8.GetBytes($newXml))
Copy-Item -LiteralPath "$originalStem.bi4" -Destination "$stem.bi4"
Copy-Item -LiteralPath "${originalStem}_Normals.nbi4" -Destination "${stem}_Normals.nbi4"
$generated=Hashes @("$stem.xml","$stem.bi4","${stem}_Normals.nbi4")
$started=[DateTime]::UtcNow
Record $startPath ([ordered]@{status='prepared_not_accepted';utc_started=$started.ToString('o');plans=$plans;inputs=$inputs;original_inputs=$original;generated_inputs=$generated;steps=20;parts=21;dt_s=1e-5;final_time_s=0.0002;xml_edit='Only TopVertical -> TopKernelBand attribute; particle/normal bytes identical';builds_review_confirmed=$true;physical_acceptance=$false})
$passed=$false;$reason='';$runs=@();$unchanged=$false
try{
  foreach($p in $plans){
    Verify $inputs;Verify $generated
    $backendArg=if($p.backend -eq 'gpu'){'-gpu:0'}else{'-cpu'}
    $args=@($backendArg,'-stable','-ompthreads:1','-mdbc','-nsteps:20','-svsteps:1','-sv:binx','-svres:1',$stem,$p.output,'-dirdataout','data')
    New-Item -ItemType Directory -Path $p.output|Out-Null
    $timer=[Diagnostics.Stopwatch]::StartNew();$solver=$null;$inspection=$null;$summary=$null;$metrics=$null;$okay=$false;$errorText=''
    try{
      $solver=Child $p.exe $args $p.output $p.logprefix
      if($null -eq $solver.exit_code -or $solver.exit_code -ne 0 -or !$solver.owned_process_absent){throw "Solver did not finish successfully: $($solver|ConvertTo-Json -Compress)"}
      $summary=Summary $p.output $p.backend
      $inspection=Child $reader @((Join-Path $p.output 'data'),$p.backend,$p.parts) $tests "$($p.logprefix).reader"
      if($null -eq $inspection.exit_code -or $inspection.exit_code -ne 0 -or !$inspection.owned_process_absent){throw 'Actual PART inspector failed; no rerun or relaxed limits'}
      $metrics=Get-Content -LiteralPath $p.parts -Raw -Encoding UTF8|ConvertFrom-Json
      if(!$metrics.passed -or $metrics.parts_checked -ne 21 -or $metrics.backend -ne $p.backend -or $metrics.physical_acceptance){throw 'Actual PART receipt is incomplete or claims unsupported acceptance'}
      Verify $inputs;Verify $generated;$okay=$true
    }catch{$errorText=$_.Exception.Message}
    $timer.Stop()
    $outputs=Hashes (@(Get-ChildItem -LiteralPath $p.output -Recurse -File|ForEach-Object{$_.FullName})+@($reserved|Where-Object{$_ -like "$($p.logprefix).*" -and (Test-Path -LiteralPath $_)}))
    Record $p.record ([ordered]@{completed=$okay;reason=$errorText;stage=$p.stage;executable=$p.exe;arguments=$args;solver=$solver;inspector=$inspection;wall_seconds=$timer.Elapsed.TotalSeconds;summary=$summary;parts_check=$p.parts;metrics=$metrics;inputs=$generated;outputs=$outputs;stage_start=$startPath;stage_start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash;cross_backend_field_review_pending=$true;physical_acceptance=$false})
    $runs+=,$p.record
    if(!$okay){throw "Stage $($p.stage) failed: $errorText"}
  }
  Verify $inputs;Verify $generated;foreach($path in $runs){$r=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json;Verify $r.outputs};$unchanged=$true;$passed=$true
}catch{$reason=$_.Exception.Message}
if(!$unchanged){try{Verify $inputs;Verify $generated;$unchanged=$true}catch{$reason+='; '+$_.Exception.Message}}
Record $checkPath ([ordered]@{passed=$passed;status=$(if($passed){'mode5_lifecycle_outputs_verified_pending_cross_backend_review'}else{'failed_retained_no_retry'});reason=$reason;utc_started=$started.ToString('o');utc_finished=[DateTime]::UtcNow.ToString('o');runs=$runs;evidence=(Hashes $runs);inputs_unchanged=$unchanged;stage_start=$startPath;stage_start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash;cross_backend_field_review_pending=$true;physical_acceptance=$false;full_cycle_admitted=$false;limitations=@('Three real 20-step trajectories, not physical/full-cycle acceptance.','CPU does not emit HydroMechLoadAce; CPU external-force verification is not claimed.','GPU saved load uses base time t_n; output positions are corrected endpoints.','No bitwise CPU/GPU equality assumption; parent must review numerical field differences.','Fresh builds are confirmed separately; a build-log hash alone does not prove source-to-executable freshness.')})
if(!$passed){throw "Mode5 short lifecycle sequence failed; retain $checkPath : $reason"}
Write-Output "PASS lifecycle/output checks only; cross-backend review pending: $checkPath"
