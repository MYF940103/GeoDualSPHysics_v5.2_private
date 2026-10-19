param(
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$CompareLabel='r2',
  [ValidatePattern('^(|[A-Za-z0-9_-]+)$')][string]$AdoptMode0Label='',
  [ValidateSet(0,1,2,3,4)][int[]]$Modes=@(0,1,2,3,4),
  [string]$GpuExe='',
  [Parameter(Mandatory=$true)][string]$BuildLog,
  [switch]$ProductionBuildConfirmed
)
# Fresh G1/G2 old-mode runs only: 20 steps, all 21 PART files, no physical acceptance.
# Only the test XML load-mode value changes. Formal XML/BAT and retained results stay read-only.
$ErrorActionPreference='Stop'
if(!$ProductionBuildConfirmed){throw 'Review the G2 GPU Release build before passing -ProductionBuildConfirmed; a log hash alone cannot prove executable freshness.'}
if(!$Modes.Count -or @($Modes|Sort-Object -Unique).Count -ne $Modes.Count){throw 'Select one or more distinct legacy modes 0..4.'}
if($AdoptMode0Label -and ($AdoptMode0Label -eq $Label -or 0 -notin $Modes)){throw 'Mode-0 adoption requires a different old label and mode 0 in this sequence.'}
$tests=Split-Path -Parent $PSScriptRoot
$caseRoot=Split-Path -Parent $tests
$repo=(Resolve-Path -LiteralPath (Join-Path $caseRoot '..\..\..')).Path
$logs=Join-Path $tests 'logs'
$tag="hg_gpu_g2_off_$Label"
if(!$GpuExe){$GpuExe=Join-Path $repo 'bin\windows\DualSPHysics5.2_GEO_win64.exe'}
$GpuExe=(Resolve-Path -LiteralPath $GpuExe).Path
$BuildLog=(Resolve-Path -LiteralPath $BuildLog).Path
$snapshotPath=Join-Path $logs 'gpu_g1_verified.snapshot.json'
$frozen=Join-Path $tests 'outputs\gpu_g1_verified'
$baseline=Join-Path $frozen 'bin\DualSPHysics5.2_GEO_win64.exe'
$compareManifest=Join-Path $logs "hg_gpu_off_compare_$CompareLabel.build.json"
$comparator=Join-Path $tests "outputs\hg_gpu_off_compare_$CompareLabel\hg_gpu_off_compare.exe"
$startPath=Join-Path $logs "$tag.start.json"
$checkPath=Join-Path $logs "$tag.check.json"
$originalStem=Join-Path $caseRoot 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_out\CaseTerzaghiConsolidation_q0_PR_full_k1em4'
$modeNames=@('None','TopVertical','FlexibleConfinement','TopStripVertical','LianFlexibleStrip')
function Hashes([string[]]$Paths){@($Paths|Sort-Object -Unique|ForEach-Object{[ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}})}
function Verify($Entries){foreach($e in $Entries){if((Get-FileHash -LiteralPath $e.path -Algorithm SHA256).Hash -ne $e.sha256){throw "Input changed: $($e.path)"}}}
function Record([string]$Path,$Value){
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 12)+"`n")
  $file=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try{$file.Write($bytes,0,$bytes.Length)}finally{$file.Dispose()}
}
function Arguments([string[]]$Values){($Values|ForEach-Object{'"'+$_+'"'}) -join ' '}
function Number($Value){[double]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture)}
function Absent($Process){if(!$Process){return $true};return $null -eq (Get-CimInstance Win32_Process -Filter "ProcessId=$($Process.Id)" -ErrorAction Stop)}
function RunSummary([string]$Output){
  $text=Get-Content -LiteralPath (Join-Path $Output 'Run.out') -Raw
  $summary=(Get-Content -LiteralPath (Join-Path $Output 'Run.csv') -Raw).TrimStart('#')|ConvertFrom-Csv -Delimiter ';'
  $steps=[regex]::Match($text,'Steps of simulation\.+:\s*(\d+)')
  $excluded=[regex]::Match($text,'Excluded particles\.+:\s*(\d+)')
  if(!$text.Contains('Finished execution (code=0).') -or $text -notmatch 'RunMode=.*Single-GPU' -or !$steps.Success -or [int]$steps.Groups[1].Value -ne 20 -or !$excluded.Success -or [int]$excluded.Groups[1].Value -ne 0){throw 'Run.out does not confirm GPU/20 steps/zero exclusion/normal completion'}
  if([long]$summary.Steps -ne 20 -or [int]$summary.PartsOut -ne 0 -or [int]$summary.Np -ne 1040 -or [int]$summary.PartFiles -ne 21 -or [Math]::Abs((Number $summary.PhysicalTime)-0.0002) -gt 1e-12){throw 'Run.csv count/time mismatch'}
  return $summary
}

$original=@(
  @{path="$originalStem.xml";sha256='BCE483AD4BF65FE7A4E84FEAA7FF8F2FFD7A2A588A7702E25DBE4E63639E7605'},
  @{path="$originalStem.bi4";sha256='4ABF3A19DE4F07F79B259A7DAB9081BD7BBBC32A4CA17524C347DAA3B98715A3'},
  @{path="${originalStem}_Normals.nbi4";sha256='66EB95E8C48C179CCC11E30DB25C9B206DC4056C805DA2798D9E0847DA20829B'}
)
Verify $original
$snapshot=Get-Content -LiteralPath $snapshotPath -Raw -Encoding UTF8|ConvertFrom-Json
if($snapshot.status -ne 'frozen_stage_baseline' -or !$snapshot.source_and_copy_hashes_verified -or $snapshot.snapshot -ne $frozen -or $snapshot.files -ne 702 -or $snapshot.entries.Count -ne 702){throw 'Not the verified frozen G1 snapshot'}
$frozenHashes=@($snapshot.entries|ForEach-Object{[ordered]@{path=(Join-Path $frozen $_.relative);sha256=$_.sha256}})
Verify $frozenHashes
if((Get-FileHash -LiteralPath $baseline -Algorithm SHA256).Hash -ne '530E4763FAF94BE0CE5B01B2731AD259571A6307E5FEEC26FC626CB51BCB3320'){throw 'Unexpected frozen G1 GPU Release executable'}
$build=Get-Content -LiteralPath $compareManifest -Raw -Encoding UTF8|ConvertFrom-Json
if($build.status -ne 'built_not_run' -or !$build.source_unchanged -or $build.executable -ne $comparator -or (Get-FileHash -LiteralPath $comparator -Algorithm SHA256).Hash -ne $build.executable_sha256){throw 'Comparator build/executable binding failed'}
Verify $build.source_inputs
if((Get-FileHash -LiteralPath $GpuExe -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $baseline -Algorithm SHA256).Hash){throw 'Current executable is still the frozen G1 executable'}
$sourceFiles=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\source') -File -Recurse|ForEach-Object{$_.FullName})
$projectFiles=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\VS') -File|Where-Object{$_.Extension -in @('.sln','.vcxproj','.props')}|ForEach-Object{$_.FullName})
$runtime=@(Get-ChildItem -LiteralPath (Split-Path -Parent $GpuExe) -File -Filter '*.dll'|ForEach-Object{$_.FullName})
$inputs=Hashes ($sourceFiles+$projectFiles+$runtime+@($GpuExe,$BuildLog,$PSCommandPath,$snapshotPath,$compareManifest,$comparator)+@($original|ForEach-Object{$_.path})+@($build.source_inputs|ForEach-Object{$_.path}))
$adoptEvidence=@();$adoptStart=$null;$adoptStartPath=''
if($AdoptMode0Label){
  $adoptStartPath=Join-Path $logs "hg_gpu_g2_off_$AdoptMode0Label.start.json"
  $adoptStart=Get-Content -LiteralPath $adoptStartPath -Raw -Encoding UTF8|ConvertFrom-Json
  # Only the reader/runner are being repaired. Every production source, project,
  # executable and runtime must still be exactly the original run's binding.
  $old=@{};foreach($entry in $adoptStart.source_executable_runtime_inputs){$old[$entry.path]=$entry.sha256}
  $oldProduction=@($adoptStart.source_executable_runtime_inputs|Where-Object{
    $_.path.StartsWith((Join-Path $repo 'src\source\'),[StringComparison]::OrdinalIgnoreCase) -or
    $_.path.StartsWith((Join-Path $repo 'src\VS\'),[StringComparison]::OrdinalIgnoreCase) -or
    $_.path.StartsWith((Join-Path $repo 'bin\windows\'),[StringComparison]::OrdinalIgnoreCase)
  })
  Verify $oldProduction # Also reject removal of a previously bound production file.
  $production=Hashes ($sourceFiles+$projectFiles+$runtime+@($GpuExe,$BuildLog,$snapshotPath))
  foreach($entry in $production){if(!$old.ContainsKey($entry.path) -or $old[$entry.path] -ne $entry.sha256){throw "Mode-0 adoption production binding differs: $($entry.path)"}}
  Verify $adoptStart.frozen_inputs;Verify $adoptStart.original_inputs
  $adoptEvidence=@(Hashes @($adoptStartPath))
}
$plans=@()
foreach($mode in $Modes){
  $stem=Join-Path $tests "configs\${tag}_m$mode"
  $plan=[ordered]@{mode=$mode;mode_name=$modeNames[$mode];stem=$stem;runs=@()}
  foreach($stage in @('g1','g2')){
    $adopt=($mode -eq 0 -and [bool]$AdoptMode0Label)
    $name=$(if($adopt){"hg_gpu_g2_off_${AdoptMode0Label}_m0_$stage"}else{"${tag}_m${mode}_$stage"})
    $plan.runs+=,[ordered]@{name=$name;stage=$stage;adopt=$adopt;exe=$(if($stage -eq 'g1'){$baseline}else{$GpuExe});output=(Join-Path $tests "outputs\$name");record=(Join-Path $logs "$name.run.json");stdout=(Join-Path $logs "$name.stdout.log");stderr=(Join-Path $logs "$name.stderr.log")}
  }
  $plan.compare=Join-Path $logs "${tag}_m${mode}.compare.json"
  $plan.compare_stdout=Join-Path $logs "${tag}_m${mode}.compare.stdout.log"
  $plan.compare_stderr=Join-Path $logs "${tag}_m${mode}.compare.stderr.log"
  $plans+=,$plan
}
$reserved=@($startPath,$checkPath)
foreach($p in $plans){$reserved+=@("$($p.stem).xml","$($p.stem).bi4","$($p.stem)_Normals.nbi4",$p.compare,$p.compare_stdout,$p.compare_stderr);foreach($r in $p.runs){if(!$r.adopt){$reserved+=@($r.output,$r.record,$r.stdout,$r.stderr)}}}
foreach($path in $reserved){if(Test-Path -LiteralPath $path){throw "Refusing existing artifact: $path"}}
# Do not race an unrelated long solver on the same device; this runner never stops it.
$live=@(Get-CimInstance Win32_Process|Where-Object{$_.Name -like 'DualSPHysics*.exe'})
if($live.Count){throw 'An existing DualSPHysics process is active; no G2 regression has been launched.'}
$utf8=[Text.UTF8Encoding]::new($false,$true)
$xmlText=$utf8.GetString([IO.File]::ReadAllBytes("$originalStem.xml"))
$pattern='(?<=<HydroMechTopLoadMode value=")TopVertical(?=")'
if([regex]::Matches($xmlText,$pattern).Count -ne 1){throw 'Seed must contain exactly one TopVertical mode attribute'}
foreach($p in $plans){
  $newText=[regex]::Replace($xmlText,$pattern,[string]$p.mode_name)
  [xml]$parsed=$newText.TrimStart([char]0xFEFF)
  if($parsed.SelectSingleNode('//hydromechanics/HydroMechTopLoadMode').value -ne $p.mode_name){throw 'Generated mode XML validation failed'}
  # Encoding roundtrip preserves any UTF-8 BOM, line endings, comments and all other text.
  [IO.File]::WriteAllBytes("$($p.stem).xml",$utf8.GetBytes($newText))
  Copy-Item -LiteralPath "$originalStem.bi4" -Destination "$($p.stem).bi4"
  Copy-Item -LiteralPath "${originalStem}_Normals.nbi4" -Destination "$($p.stem)_Normals.nbi4"
  $p.input_hashes=Hashes @("$($p.stem).xml","$($p.stem).bi4","$($p.stem)_Normals.nbi4")
  foreach($r in $p.runs){if($r.adopt){
    $receipt=Get-Content -LiteralPath $r.record -Raw -Encoding UTF8|ConvertFrom-Json
    if(!$receipt.completed -or $null -eq $receipt.exit_code -or $receipt.exit_code -ne 0 -or !$receipt.owned_process_absent -or $receipt.mode -ne 0 -or $receipt.stage -ne $r.stage -or $receipt.executable -ne $r.exe -or $receipt.exe_sha256 -ne (Get-FileHash -LiteralPath $r.exe -Algorithm SHA256).Hash -or $receipt.stage_start -ne $adoptStartPath -or $receipt.stage_start_sha256 -ne $adoptEvidence[0].sha256){throw 'Adopted mode-0 completion/executable/start binding failed'}
    Verify $receipt.inputs;Verify $receipt.outputs
    if($receipt.inputs.Count -ne 3){throw 'Adopted mode-0 requires exactly three generated inputs'}
    $oldMode=@($adoptStart.plans|Where-Object{$_.mode -eq 0})
    if($oldMode.Count -ne 1){throw 'Adopted sequence has no unique mode-0 plan'}
    $oldStem=$oldMode[0].stem
    foreach($suffix in @('.xml','.bi4','_Normals.nbi4')){if((Get-FileHash -LiteralPath "$oldStem$suffix" -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath "$($p.stem)$suffix" -Algorithm SHA256).Hash){throw "Adopted mode-0 seed mismatch: $suffix"}}
    $expectedArgs=@('-gpu:0','-stable','-mdbc','-nsteps:20','-svsteps:1','-sv:binx','-svres:1',$oldStem,$r.output,'-dirdataout','data')
    if((Arguments $receipt.arguments) -cne (Arguments $expectedArgs)){throw 'Adopted mode-0 solver arguments differ'}
    $null=RunSummary $r.output
    $adoptEvidence+=Hashes @($r.record)
  }}
}
$started=[DateTime]::UtcNow
Record $startPath ([ordered]@{status='prepared_not_accepted';started_utc=$started.ToString('o');plans=$plans;source_executable_runtime_inputs=$inputs;frozen_inputs=$frozenHashes;original_inputs=$original;adopted_mode0_evidence=$adoptEvidence;expected_steps=20;expected_parts=21;expected_native_count=1040;dt=1e-5;current_release_build_review_confirmed=$true;xml_edit='Only HydroMechTopLoadMode value; retained generated particle/normal bytes copied exactly';baseline_policy='Mode0 may adopt completed hash-verified G1/G2 runs; other modes are fresh; no old solver restart'})
$passed=$false;$reason='';$receipts=@();$comparisons=@();$unchanged=$false
try{
  foreach($p in $plans){
    foreach($r in $p.runs){
      Verify $p.input_hashes
      if($r.adopt){$receipts+=,$r.record;continue}
      $args=@('-gpu:0','-stable','-mdbc','-nsteps:20','-svsteps:1','-sv:binx','-svres:1',$p.stem,$r.output,'-dirdataout','data')
      New-Item -ItemType Directory -Path $r.output|Out-Null
      $process=$null;$summary=$null;$okay=$false;$runReason='';$ownedAbsent=$false
      $watch=[Diagnostics.Stopwatch]::StartNew()
      try{
        $process=Start-Process -FilePath $r.exe -ArgumentList (Arguments $args) -WorkingDirectory $r.output -WindowStyle Hidden -RedirectStandardOutput $r.stdout -RedirectStandardError $r.stderr -PassThru -Wait
        if($null -eq $process.ExitCode -or $process.ExitCode -ne 0){throw "Solver exit code is not zero: $($process.ExitCode)"}
        $ownedAbsent=Absent $process
        if(!$ownedAbsent){throw 'Owned solver process is still present'}
        $summary=RunSummary $r.output
        Verify $p.input_hashes;$okay=$true
      }catch{$runReason=$_.Exception.Message}
      $watch.Stop()
      if(!$ownedAbsent -and $process){$ownedAbsent=Absent $process}
      $outputs=Hashes (@(Get-ChildItem -LiteralPath $r.output -File -Recurse|ForEach-Object{$_.FullName})+@($r.stdout,$r.stderr|Where-Object{Test-Path -LiteralPath $_}))
      Record $r.record ([ordered]@{completed=$okay;reason=$runReason;stage=$r.stage;mode=$p.mode;executable=$r.exe;exe_sha256=(Get-FileHash -LiteralPath $r.exe -Algorithm SHA256).Hash;arguments=$args;pid=$(if($process){$process.Id}else{$null});exit_code=$(if($process){$process.ExitCode}else{$null});owned_process_absent=$ownedAbsent;wall_seconds=$watch.Elapsed.TotalSeconds;summary=$summary;inputs=$p.input_hashes;outputs=$outputs;stage_start=$startPath;stage_start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash;particle_comparison_pending=$true})
      $receipts+=,$r.record
      if(!$okay -or !$ownedAbsent){throw "Mode $($p.mode) $($r.stage) failed: $runReason"}
    }
    $compareArgs=@((Join-Path $p.runs[0].output 'data'),(Join-Path $p.runs[1].output 'data'),$p.compare,'1040','1e-5')
    $reader=Start-Process -FilePath $comparator -ArgumentList (Arguments $compareArgs) -WorkingDirectory $tests -WindowStyle Hidden -RedirectStandardOutput $p.compare_stdout -RedirectStandardError $p.compare_stderr -PassThru -Wait
    if($null -eq $reader.ExitCode -or $reader.ExitCode -ne 0 -or !(Absent $reader)){throw "Mode $($p.mode) reader failed/exited without success: $($reader.ExitCode)"}
    $comparison=Get-Content -LiteralPath $p.compare -Raw -Encoding UTF8|ConvertFrom-Json
    if(!$comparison.passed -or $comparison.parts_compared -ne 21 -or $comparison.differing_bytes -ne 0 -or $comparison.compared_bytes -le 0){throw "Mode $($p.mode) has no valid 21-PART byte-exact receipt"}
    $comparisons+=,[ordered]@{mode=$p.mode;mode_name=$p.mode_name;reader_exit_code=$reader.ExitCode;reader_owned_absent=$true;receipt=$p.compare;receipt_sha256=(Get-FileHash -LiteralPath $p.compare -Algorithm SHA256).Hash;parts_compared=$comparison.parts_compared;differing_bytes=$comparison.differing_bytes;compared_bytes=$comparison.compared_bytes}
  }
  Verify $inputs;Verify $frozenHashes;Verify $adoptEvidence;foreach($p in $plans){Verify $p.input_hashes}
  foreach($path in $receipts){$receipt=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json;Verify $receipt.outputs}
  $unchanged=$true;$passed=$true
}catch{$reason=$_.Exception.Message}
if(!$unchanged){try{Verify $inputs;Verify $frozenHashes;Verify $adoptEvidence;foreach($p in $plans){Verify $p.input_hashes};$unchanged=$true}catch{$reason+='; '+$_.Exception.Message}}
$evidence=Hashes (@($receipts)+@($plans|ForEach-Object{@($_.compare,$_.compare_stdout,$_.compare_stderr)}|Where-Object{Test-Path -LiteralPath $_}))
Record $checkPath ([ordered]@{
  passed=$passed;status=$(if($passed){'legacy_modes_emitted_fields_byte_exact'}else{'failed_retained_no_retry'});reason=$reason
  started_utc=$started.ToString('o');finished_utc=[DateTime]::UtcNow.ToString('o');modes=$Modes;comparisons=$comparisons;run_records=$receipts;evidence=$evidence
  input_and_source_hashes_unchanged=$unchanged;stage_start=$startPath;stage_start_sha256=(Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash
  limitations=@('Twenty fresh steps compare old mode behavior only; no physical/full-cycle acceptance.','Only emitted particle fields are compared, not unrecorded work arrays.','Mode 3/4 are configuration/old-path compatibility checks on case-02, not strip-footing physical validation at z=10.','No claim about new TopKernelBand physics or GPU HG/SPR.','Current source-to-executable freshness requires the separately reviewed authoritative Release build.')
  physical_acceptance=$false;full_cycle_admitted=$false
})
if(!$passed){throw "G2 old-mode regression failed; inspect $checkPath : $reason"}
Write-Output "PASS old-mode emitted fields, all 21 PARTs by native ID: $checkPath"
