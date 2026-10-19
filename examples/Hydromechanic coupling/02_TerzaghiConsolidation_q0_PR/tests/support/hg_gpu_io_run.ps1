param(
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='hg_gpu_io_r1',
  [string]$GpuExe='',
  [Parameter(Mandatory=$true)][string]$BuildLog,
  [switch]$ProductionBuildConfirmed
)
# One fresh 20-step GPU SaveData -> existing production-loader inspection.
# No build, GenCase, formal-input edit, automatic retry, or physical acceptance.
$ErrorActionPreference='Stop'
if(!$ProductionBuildConfirmed){throw 'Review the new GPU Release build first, then pass -ProductionBuildConfirmed. A build-log hash alone does not prove source-to-executable freshness.'}
$tests=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $tests
$repo=(Resolve-Path -LiteralPath (Join-Path $caseRoot '..\..\..')).Path
if(!$GpuExe){$GpuExe=Join-Path $repo 'bin\windows\DualSPHysics5.2_GEO_win64.exe'}
$GpuExe=(Resolve-Path -LiteralPath $GpuExe).Path
$BuildLog=(Resolve-Path -LiteralPath $BuildLog).Path
$stem=Join-Path $caseRoot 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_out\CaseTerzaghiConsolidation_q0_PR_full_k1em4'
$inspectorRecord=Join-Path $tests 'logs\stress_io_r2.json'
$inspector=Join-Path $tests 'outputs\stress_io_r2\stress_io.exe'
$output=Join-Path $tests "outputs\$Label"
$data=Join-Path $output 'data'
$logs=Join-Path $tests 'logs'
$startPath=Join-Path $logs "$Label.start.json"
$runPath=Join-Path $logs "$Label.run.json"
$checkPath=Join-Path $logs "$Label.check.json"
$stdout=Join-Path $logs "$Label.stdout.log"
$stderr=Join-Path $logs "$Label.stderr.log"
$inspectOut=Join-Path $logs "$Label.inspect.json"
$inspectErr=Join-Path $logs "$Label.inspect.stderr.log"
foreach($p in @($output,$startPath,$runPath,$checkPath,$stdout,$stderr,$inspectOut,$inspectErr)){
  if(Test-Path -LiteralPath $p){throw "Refusing existing artifact: $p"}
}
function Hashes([string[]]$Paths){
  @($Paths|Sort-Object -Unique|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})
}
function Verify($Entries){foreach($e in $Entries){if((Get-FileHash -LiteralPath $e.path -Algorithm SHA256).Hash -ne $e.sha256){throw "Input hash changed: $($e.path)"}}}
function Record([string]$Path,$Value){
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 9)+"`n")
  $file=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try{$file.Write($bytes,0,$bytes.Length)}finally{$file.Dispose()}
}
function Arguments([string[]]$Values){($Values|ForEach-Object{'"'+$_+'"'}) -join ' '}
function Number($Value){[double]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture)}

# These retained generated inputs have TopVertical, k=1e-4, DtFixed=1e-5;
# HG, SPR, stress-gradient correction and fixed-grid drainage are all disabled.
$original=@(
  @{path="$stem.xml";sha256='BCE483AD4BF65FE7A4E84FEAA7FF8F2FFD7A2A588A7702E25DBE4E63639E7605'},
  @{path="$stem.bi4";sha256='4ABF3A19DE4F07F79B259A7DAB9081BD7BBBC32A4CA17524C347DAA3B98715A3'},
  @{path="${stem}_Normals.nbi4";sha256='66EB95E8C48C179CCC11E30DB25C9B206DC4056C805DA2798D9E0847DA20829B'}
)
Verify $original
$io=Get-Content -LiteralPath $inspectorRecord -Raw -Encoding UTF8|ConvertFrom-Json
if(!$io.passed -or $io.executable -ne $inspector -or (Get-FileHash -LiteralPath $inspector -Algorithm SHA256).Hash -ne $io.executable_sha256){throw 'Retained inspector build/executable is not verified'}
Verify $io.source_inputs
$dlls=@(Get-ChildItem -LiteralPath (Split-Path -Parent $GpuExe) -File -Filter '*.dll'|ForEach-Object{$_.FullName})
$inputs=Hashes (@($GpuExe,$BuildLog,$inspector,$inspectorRecord,$PSCommandPath)+@($original|ForEach-Object{$_.path})+@($io.source_inputs|ForEach-Object{$_.path})+$dlls)
$arguments=@('-gpu:0','-stable','-mdbc','-nsteps:20','-svsteps:1','-sv:binx','-svres:1',$stem,$output,'-dirdataout','data')
$inspectArguments=@('inspect',$data,'20')
New-Item -ItemType Directory -Path $output|Out-Null
$started=[DateTime]::UtcNow
Record $startPath ([ordered]@{status='started_not_accepted';utc_started=$started.ToString('o');executable=$GpuExe;arguments=$arguments;inputs=$inputs;release_build_review_confirmed=$true;expected_steps=20;expected_time_s=0.0002;expected_native_particles=1040;expected_soil_particles=1000})
$watch=[Diagnostics.Stopwatch]::StartNew()
$solver=$null;$inspection=$null;$inspectionExit=$null;$summary=$null;$reason='';$passed=$false;$unchanged=$false
try{
  $solver=Start-Process -FilePath $GpuExe -ArgumentList (Arguments $arguments) -WorkingDirectory $output -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -Wait
  if($solver.ExitCode -ne 0){throw "GPU solver exit code $($solver.ExitCode)"}
  $text=Get-Content -LiteralPath (Join-Path $output 'Run.out') -Raw
  $summary=(Get-Content -LiteralPath (Join-Path $output 'Run.csv') -Raw).TrimStart('#')|ConvertFrom-Csv -Delimiter ';'
  $steps=[regex]::Match($text,'Steps of simulation\.+:\s*(\d+)')
  $excluded=[regex]::Match($text,'Excluded particles\.+:\s*(\d+)')
  if(!$text.Contains('Finished execution (code=0).') -or $text -notmatch 'RunMode=.*Single-GPU' -or !$steps.Success -or [int]$steps.Groups[1].Value -ne 20 -or !$excluded.Success -or [int]$excluded.Groups[1].Value -ne 0){throw 'Run.out does not confirm normal GPU exit, 20 steps and zero exclusions'}
  if([long]$summary.Steps -ne 20 -or [int]$summary.PartsOut -ne 0 -or [int]$summary.Np -ne 1040 -or [int]$summary.PartFiles -ne 21 -or [Math]::Abs((Number $summary.PhysicalTime)-0.0002) -gt 1e-12){throw 'Run.csv coverage/count/time mismatch'}
  $parts=@(Get-ChildItem -LiteralPath $data -File -Filter 'Part_*.bi4'|Sort-Object Name)
  if($parts.Count -ne 21){throw 'Expected exactly 21 actual PART files'}
  for($i=0;$i -le 20;$i++){if($parts[$i].Name -ne ('Part_{0:D4}.bi4' -f $i)){throw 'Missing or unexpected PART sequence'}}
  $reader=Start-Process -FilePath $inspector -ArgumentList (Arguments $inspectArguments) -WorkingDirectory $output -WindowStyle Hidden -RedirectStandardOutput $inspectOut -RedirectStandardError $inspectErr -PassThru -Wait
  $inspectionExit=$reader.ExitCode
  if($inspectionExit -ne 0){throw "Stress loader inspection exit code $inspectionExit; no relaxation or retry"}
  $inspection=Get-Content -LiteralPath $inspectOut -Raw -Encoding UTF8|ConvertFrom-Json
  if(!$inspection.passed -or $inspection.part -ne 20 -or $inspection.pieces -ne 1 -or $inspection.particles -ne 1040 -or $inspection.soil_particles -ne 1000 -or [Math]::Abs((Number $inspection.time)-0.0002) -gt 1e-12 -or !$inspection.types_counts_ids_valid -or !$inspection.loader_six_components_exact -or !$inspection.legacy_float_casts_exact -or $inspection.soil_nonfloat_components -le 0){throw 'Actual PART double/native-ID/legacy projection/low-bit coverage did not pass'}
  Verify $inputs;$unchanged=$true;$passed=$true
}catch{$reason=$_.Exception.Message}
$watch.Stop()
if(!$unchanged){try{Verify $inputs;$unchanged=$true}catch{$reason+='; '+$_.Exception.Message}}
$outputs=Hashes (@(Get-ChildItem -LiteralPath $output -File -Recurse|ForEach-Object{$_.FullName})+@($stdout,$stderr,$inspectOut,$inspectErr|Where-Object{Test-Path -LiteralPath $_}))
Record $runPath ([ordered]@{
  status=$(if($passed){'completed_io_verified_not_physical_acceptance'}else{'failed_retained_no_retry'});passed=$passed;reason=$reason
  utc_started=$started.ToString('o');utc_finished=[DateTime]::UtcNow.ToString('o');elapsed_seconds=$watch.Elapsed.TotalSeconds
  executable=$GpuExe;arguments=$arguments;solver_pid=$(if($solver){$solver.Id}else{$null});solver_exit_code=$(if($solver){$solver.ExitCode}else{$null})
  inspector=$inspector;inspect_arguments=$inspectArguments;inspector_exit_code=$inspectionExit;actual_run_summary=$summary
  inputs=$inputs;inputs_unchanged=$unchanged;outputs=$outputs;start_record=$startPath;start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash
})
Record $checkPath ([ordered]@{
  passed=$passed;reason=$reason;scope='Actual GPU SaveData PART20 -> production JPartsLoad4: native IDs, double stress low bits and legacy float projection only'
  run_record=$runPath;run_sha256=(Get-FileHash -LiteralPath $runPath -Algorithm SHA256).Hash;inspection=$inspection
  limits=@('Release source-to-executable freshness is confirmed separately by the reviewed build.','20-step coverage is not coupled physical acceptance or full restart trajectory equivalence.','Initial zero stress PART is not required to contain nonfloat low bits; final PART20 is required.')
  physical_accuracy_accepted=$false;full_cycle_admitted=$false
})
if(!$passed){throw "GPU PART IO failed; retained evidence: $checkPath; $reason"}
Write-Output "PASS actual GPU PART IO only: $checkPath"
