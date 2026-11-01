# Offline review/seal only. Never builds or runs a program.
$ErrorActionPreference='Stop';$tests=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $tests 'logs'
function Entry([string]$p){$a=Get-Item -LiteralPath $p;[ordered]@{path=$a.FullName;bytes=$a.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($a in $items){$b=Entry $a.path;if($a.sha256 -ne $b.sha256 -or $a.bytes -ne $b.bytes){throw "Frozen input changed: $($a.path)"}}}
function D($v){[double]::Parse([string]$v,[Globalization.CultureInfo]::InvariantCulture)}
function NewJson($p,$v){if(Test-Path -LiteralPath $p){throw "Retained evidence protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
$out=Join-Path $logs 'upl_p3_actual_review_r1.check.json';if(Test-Path -LiteralPath $out){throw 'Review already sealed'}
$authoritative=Join-Path $logs 'upl_p3_actual_build_r2.json';$auth=Get-Content -LiteralPath $authoritative -Raw|ConvertFrom-Json
foreach($a in $auth.source){Verify @($a.original,$a.snapshot)}
$configurations=@();$maxError=0.;$maxNonzeroKError=0.;$maxNormalized=0.;$maxNull=0.;$minC=[double]::PositiveInfinity;$minGhostPairs=[double]::PositiveInfinity
$allFiles=@();$checks=@();$builds=@();$rateRows=0;$ctNodes=0;$proofs=0
foreach($config in @('DebugCPU','ReleaseCPU')){
  $name="upl_p3_actual_${config}_r3";$buildPath=Join-Path $logs ($name+'.build.json');$checkPath=Join-Path $logs ($name+'_run.check.json')
  $b=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json;$c=Get-Content -LiteralPath $checkPath -Raw|ConvertFrom-Json
  if(!$c.passed -or $b.compile_exit -ne 0 -or $b.link_exit -ne 0){throw 'Earlier implementation gate failed'}
  Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify $b.controls;Verify @($b.program,$b.log);foreach($r in $b.runtime){Verify @($r.original,$r.copy)}
  Verify $c.files;Verify @($c.run_receipt,$c.build_receipt)
  foreach($r in $c.retained_P2_default_OFF_byte_comparisons){Verify @($r.retained,$r.current);if(!$r.byte_identical -or $r.retained.sha256 -ne $r.current.sha256){throw 'Default-OFF P2 control changed'}}
  if($c.retained_P2_default_OFF_byte_comparisons.Count -ne 6){throw 'P2 control file coverage missing'}
  $folder=Join-Path $tests "outputs\${name}_run"
  $rates=@(Import-Csv -LiteralPath (Join-Path $folder 'rates.csv'));$summaries=@(Import-Csv -LiteralPath (Join-Path $folder 'summary.csv'))
  $sentinels=@(Import-Csv -LiteralPath (Join-Path $folder 'ct_values.csv'));$theta=@(Import-Csv -LiteralPath (Join-Path $folder 'ct_suppression.csv'));$cproof=@(Import-Csv -LiteralPath (Join-Path $folder 'periodic_c.csv'))
  if($rates.Count -ne 744 -or $summaries.Count -ne 40 -or $sentinels.Count -ne 144 -or $theta.Count -ne 8 -or $cproof.Count -ne 12){throw 'CSV coverage mismatch'}
  foreach($r in $rates){
    $actual=D $r.actual_rate_pa_s;$reference=D $r.reference_rate_pa_s;$absError=D $r.absolute_error;$limit=D $r.limit
    if([double]::IsNaN($actual) -or [double]::IsInfinity($actual) -or $actual -eq 1234567 -or $absError -gt $limit -or [Math]::Abs([Math]::Abs($actual-$reference)-$absError) -gt 1e-10){throw 'Saved rate violates predeclared bound'}
    $maxError=[Math]::Max($maxError,$absError);$maxNormalized=[Math]::Max($maxNormalized,$absError/$limit)
    if($r.field -like 'k0_*'){if([single]$reference -ne [single]$actual){throw 'k0 exact stored-float rate failed'}}else{$maxNonzeroKError=[Math]::Max($maxNonzeroKError,$absError)}
    if($r.periodic -eq '0' -and $r.field -in @('affine_equilibrium','constant_flux')){if([Math]::Abs($actual) -gt .001){throw 'Affine/null bound failed'};$maxNull=[Math]::Max($maxNull,[Math]::Abs($actual))}
  }
  foreach($r in $sentinels){if((D $r.actual_rate_sentinel) -ne 1234567){throw 'ct sentinel changed'}}
  foreach($r in $theta){if((D $r.max_absolute_theta) -le .01 -or $r.sentinel_unchanged -ne 'true'){throw 'ct suppression is vacuous'}}
  foreach($r in $cproof){if($r.poisoned -ne '2' -or $r.repaired -ne '2' -or (D $r.minimum_owner_C_L1) -le 1e-12){throw 'C ownership proof is vacuous'};$minC=[Math]::Min($minC,(D $r.minimum_owner_C_L1))}
  foreach($r in $summaries){if($r.periodic -eq '1'){if($r.ghosts -ne '2' -or (D $r.ghost_neighbor_pairs) -lt 1){throw 'Periodic neighbor proof empty'};$minGhostPairs=[Math]::Min($minGhostPairs,(D $r.ghost_neighbor_pairs))}}
  $rateRows+=$rates.Count;$ctNodes+=$sentinels.Count;$proofs+=$cproof.Count;$checks+=Entry $checkPath;$builds+=Entry $buildPath;$allFiles+=$c.files
  $configurations+=@{configuration=$config;rate_rows=$rates.Count;ct_nodes=$sentinels.Count;C_proofs=$cproof.Count;retained_P2_files_byte_identical=6;program=$b.program;run_receipt=$c.run_receipt}
}
$cross=@();foreach($file in @('rates.csv','summary.csv','ct_suppression.csv','periodic_c.csv','ct_values.csv','complete.json')){
  $a=Entry (Join-Path $tests "outputs\upl_p3_actual_DebugCPU_r3_run\$file");$b=Entry (Join-Path $tests "outputs\upl_p3_actual_ReleaseCPU_r3_run\$file");$cross+=@{file=$file;debug=$a;release=$b;byte_identical=($a.sha256 -eq $b.sha256)}
}
$failures=@();foreach($label in @('r1','r2')){
  $path=Join-Path $logs "upl_p3_actual_DebugCPU_$label.failure_seal.json";$f=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
  Verify $f.raw_outputs;Verify $f.frozen_fixture;Verify @($f.build_receipt,$f.run_receipt,$f.authoritative_receipt,$f.seal_recipe)
  # Current production intentionally differs from r1. Verify archived snapshots, never demand old current-source hashes.
  foreach($s in $f.production_snapshot){Verify @($s.snapshot)}
  $failures+=Entry $path;$allFiles+=$f.raw_outputs
}
$textCandidates=@(Get-ChildItem -LiteralPath $PSScriptRoot -File|Where-Object {$_.Name -like 'upl_p3_actual*' -and $_.Extension -in '.cpp','.ps1'}|ForEach-Object {$_.FullName})
$textCandidates+=@(Get-ChildItem -LiteralPath (Join-Path $tests 'notes') -File|Where-Object {$_.Name -like 'upl_p3_actual*' -and $_.Extension -eq '.json'}|ForEach-Object {$_.FullName})
$textCandidates+=@(Get-ChildItem -LiteralPath $logs -File|Where-Object {$_.Name -like 'upl_p3_actual*' -and $_.Extension -in '.json','.log'}|ForEach-Object {$_.FullName})
foreach($dir in @('upl_p3_actual_DebugCPU_r1','upl_p3_actual_DebugCPU_r2','upl_p3_actual_DebugCPU_r3','upl_p3_actual_ReleaseCPU_r3','upl_p3_actual_source_r1','upl_p3_actual_source_r2')){
  $textCandidates+=@(Get-ChildItem -LiteralPath (Join-Path $tests "outputs\$dir") -File|Where-Object {$_.Extension -in '.cpp','.h','.ps1','.json','.out','.csv','.log'}|ForEach-Object {$_.FullName})
}
$allFiles+=@($textCandidates|Sort-Object -Unique|ForEach-Object {Entry $_});$allFiles=@($allFiles|Sort-Object path -Unique);Verify $allFiles
$whitelist=@($allFiles|ForEach-Object {$_.path.Substring((Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName.Length+1).Replace('\','/')})
NewJson $out ([ordered]@{
  passed=$true;utc=[DateTime]::UtcNow.ToString('o');scope='private actual CPU P3 component implementation, not physical-model acceptance'
  authoritative_build_receipt=(Entry $authoritative);accepted_build_receipts=$builds;accepted_check_receipts=$checks;configurations=$configurations
  total_rate_rows=$rateRows;total_ct_sentinel_nodes=$ctNodes;total_C_proofs=$proofs;max_double_reference_rounding_error_pa_s=$maxError;max_nonzero_k_reference_error_pa_s=$maxNonzeroKError;max_error_over_declared_limit=$maxNormalized
  max_nonperiodic_affine_or_constant_flux_null_pa_s=$maxNull;minimum_owner_C_L1=$minC;minimum_ghost_neighbor_pairs=$minGhostPairs
  Debug_Release_csv_comparison=$cross;retained_failures=$failures;files=$allFiles;posthoc_output_manifest=$true;pre_run_output_attestation=$false
  git_text_whitelist_suggestion=$whitelist;not_cloud_backed_here=@('executables','objects','PDBs','DLLs');physical_acceptance=$false
})
Write-Output "SEALED $out with $($allFiles.Count) text/output bindings"
