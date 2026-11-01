# Offline minimal text seal; no builds, solvers, Git or old-artifact writes.
$ErrorActionPreference='Stop';$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $tests 'logs'
function Entry([string]$p){$a=Get-Item -LiteralPath $p;[ordered]@{path=$a.FullName;bytes=$a.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($a in $items){$b=Entry $a.path;if($a.sha256 -ne $b.sha256 -or $a.bytes -ne $b.bytes){throw "Frozen evidence changed: $($a.path)"}}}
function D($v){[double]::Parse([string]$v,[Globalization.CultureInfo]::InvariantCulture)}
$target=Join-Path $logs 'upl_p3_timeguard_review_r1.check.json';if(Test-Path -LiteralPath $target){throw 'Retained review protected'}
$authPath=Join-Path $logs 'upl_p3_time_build_r1.json';$auth=Get-Content -LiteralPath $authPath -Raw|ConvertFrom-Json
foreach($a in $auth.source){Verify @($a.original,$a.snapshot)};Verify $auth.logs;Verify $auth.programs
$text=@($authPath)+@($auth.logs|ForEach-Object {$_.path});$raw=@();$programs=@();$checks=@();$maxRelativeScale=0.;$firstCases=0;$statePairs=0
foreach($config in @('DebugCPU','ReleaseCPU')){
  $name="upl_p3_timeguard_${config}_r2";$bpath=Join-Path $logs ($name+'.build.json');$cpath=Join-Path $logs ($name+'_run.check.json')
  $b=Get-Content -LiteralPath $bpath -Raw|ConvertFrom-Json;$c=Get-Content -LiteralPath $cpath -Raw|ConvertFrom-Json
  if(!$c.passed -or $b.compile_exit -ne 0 -or $b.link_exit -ne 0){throw 'An earlier implementation gate failed'}
  Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program,$b.log);foreach($r in $b.runtime){Verify @($r.original,$r.copy)}
  Verify $c.files;Verify @($c.run_receipt,$c.build_receipt);$programs+=$b.program;$raw+=$c.files;$checks+=Entry $cpath
  $folder=Join-Path $tests "outputs\${name}_run";$sc=@(Import-Csv -LiteralPath (Join-Path $folder 'scales.csv'));$state=@(Import-Csv -LiteralPath (Join-Path $folder 'state_scales.csv'))
  $domain=@(Import-Csv -LiteralPath (Join-Path $folder 'domain.csv'));$requests=@(Import-Csv -LiteralPath (Join-Path $folder 'requests.csv'));$first=@(Import-Csv -LiteralPath (Join-Path $folder 'first_step.csv'));$physical=@(Import-Csv -LiteralPath (Join-Path $folder 'first_step_states.csv'))
  if($sc.Count -ne 16 -or $state.Count -ne 286 -or $domain.Count -ne 12 -or $requests.Count -ne 20 -or $first.Count -ne 4 -or $physical.Count -ne 144){throw 'Guard CSV coverage differs from declaration'}
  foreach($r in $sc){
    if($r.positive_legacy_rho_poison_0ULP -ne 'true'){throw 'Passive rho poison affected scale'}
    foreach($pair in @(@('wave_actual_s','wave_reference_s'),@('pore_actual_s','pore_reference_s'))){$a=D $r.($pair[0]);$v=D $r.($pair[1]);if($a -ne $v){$relative=[Math]::Abs(($a-$v)/$v);if($relative -gt 256*2.220446049250313e-16){throw 'Saved scale violates reference bound'};$maxRelativeScale=[Math]::Max($maxRelativeScale,$relative)}}
  }
  foreach($r in $domain){if($r.expected_rejection -ne $r.actual_rejection){throw 'Domain gate mismatch'}}
  foreach($r in $requests){if($r.expected_rejection -ne $r.actual_rejection -or $r.physical_arrays_unchanged -ne 'true'){throw 'Requested guard mismatch'};if($r.actual_rejection -eq '0' -and ((D $r.selected_dt_s) -gt (D $r.bound_s) -or (D $r.selected_dt_s) -lt (D $r.DtMin_s))){throw 'Safe request clipped/uplifted'}}
  foreach($r in $first){if($r.rejected -ne 'true' -or $r.physical_arrays_0ULP -ne 'true' -or $r.predictor_histories_absent -ne 'true' -or (D $r.max_absolute_theta) -le .01 -or $r.native_ids -ne $r.assigned_native_rates){throw 'Actual first step rejection is vacuous or changed state'};$firstCases++}
  $after=@{};foreach($r in $physical|Where-Object {$_.phase -eq 'after'}){$after[$r.dimension+'|'+$r.case+'|'+$r.native_id]=$r}
  foreach($r in $physical|Where-Object {$_.phase -eq 'before'}){
    $a=$after[$r.dimension+'|'+$r.case+'|'+$r.native_id];if(!$a){throw 'Actual first-step material ID pair missing'}
    foreach($field in @('x','y','z','vx','vy','vz','passive_rho','J','p','p0','sxx','sxy','sxz','syy','syz','szz','kplastic')){if($r.$field -cne $a.$field){throw 'Saved first-step physical field changed'}};$statePairs++
  }
  $text+=@($bpath,$cpath,(Join-Path $logs ($name+'.build.log')),(Join-Path $logs ($name+'_run.run.json')),(Join-Path $logs ($name+'_run.log')))
  $text+=@(Get-ChildItem -LiteralPath $folder -File|Where-Object {$_.Extension -eq '.csv' -or $_.Name -eq 'complete.json'}|ForEach-Object {$_.FullName})
}
$oldBuildPath=Join-Path $logs 'upl_p3_timeguard_DebugCPU_r1.build.json';$old=Get-Content -LiteralPath $oldBuildPath -Raw|ConvertFrom-Json
Verify $old.inputs;Verify $old.libraries;Verify $old.snapshots;Verify @($old.program,$old.log);$programs+=$old.program
if(Test-Path -LiteralPath (Join-Path $logs 'upl_p3_timeguard_DebugCPU_r1_run.run.json')){throw 'The declared unused r1 binary was unexpectedly run'}
$text+=@($oldBuildPath,$old.log.path)
$comparison=@();foreach($file in @('scales.csv','state_scales.csv','domain.csv','requests.csv','first_step.csv','first_step_states.csv','complete.json')){
  $a=Entry (Join-Path $tests "outputs\upl_p3_timeguard_DebugCPU_r2_run\$file");$b=Entry (Join-Path $tests "outputs\upl_p3_timeguard_ReleaseCPU_r2_run\$file");$comparison+=@{file=$file;debug=$a;release=$b;byte_identical=($a.sha256 -eq $b.sha256)}
}
$text+=@(Get-ChildItem -LiteralPath $PSScriptRoot -File|Where-Object {$_.Name -like 'upl_p3_timeguard*' -and $_.Extension -in '.cpp','.ps1'}|ForEach-Object {$_.FullName})
$text+=@(Get-ChildItem -LiteralPath (Join-Path $tests 'notes') -File|Where-Object {$_.Name -like 'upl_p3_timeguard*' -and $_.Extension -eq '.json'}|ForEach-Object {$_.FullName})
$textEntries=@($text|Sort-Object -Unique|ForEach-Object {Entry $_});Verify $textEntries;Verify $raw;Verify $programs
$whitelist=@($textEntries|ForEach-Object {$_.path.Substring($repo.Length+1).Replace('\','/')})
$result=[ordered]@{passed=$true;utc=[DateTime]::UtcNow.ToString('o');scope='necessary private current-state time guards, not discrete-spectrum/physical acceptance';authoritative_build_receipt=(Entry $authPath);accepted_checks=$checks;unused_r1_build=(Entry $oldBuildPath);max_independent_scale_relative_error=$maxRelativeScale;actual_first_step_rejections=$firstCases;first_step_native_state_pairs=$statePairs;Debug_Release_text_comparison=$comparison;posthoc_raw_output_manifest=$raw;local_program_hash_bindings_not_cloud_data=$programs;text_files=$textEntries;git_text_whitelist_suggestion=$whitelist;output_manifest_posthoc=$true;pre_run_output_attestation=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($target,($result|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $target; $($textEntries.Count) minimal text whitelist items plus this seal"
