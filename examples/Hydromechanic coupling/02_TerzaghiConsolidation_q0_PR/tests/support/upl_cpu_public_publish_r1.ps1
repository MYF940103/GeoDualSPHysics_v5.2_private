param([ValidateSet('List','Seal','Stage')][string]$Mode='List',[switch]$StageAuthorized,[string]$ReviewedManifestSha256='')
# Explicit limited public-CPU stage only. List is read-only; no commit/push in any mode.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$expectedBase='d8bdcef8b3cf723f954769c598d2dbb2fa19f714'
$target=Join-Path $tests 'logs\upl_cpu_public_publish_r1.json'
$stagePath=Join-Path $tests 'logs\upl_cpu_public_stage_r1.check.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[pscustomobject]@{path=$f.FullName.Substring($repo.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Candidates {
  $paths=@()
  foreach($p in @('src\source\JSph.h','src\source\JSph.cpp','src\source\JSphCpu.h','src\source\JSphCpu.cpp','src\source\JSphCpuSingle.cpp','src\source\JPartsLoad4.cpp','doc\xml_format\_FmtXML_ElastoplasticSoil.xml','examples\Hydromechanic coupling\validation\upl_current_status.json')){$paths+=Join-Path $repo $p}
  foreach($p in @('notes\upl_gpu_port_audit_r1.md','notes\upl_gpu_port_audit_r1.json')){$paths+=Join-Path $tests $p}
  foreach($part in @('support','notes','configs','logs','figures')){
    $paths+=Get-ChildItem -LiteralPath (Join-Path $tests $part) -File|Where-Object {$_.Name -like 'upl_cpu_public_*' -and $_.Name -ne 'upl_cpu_public_publish_r1.json' -and $_.Extension -in '.cpp','.ps1','.py','.json','.md','.xml','.csv','.log','.png'}|ForEach-Object {$_.FullName}
  }
  # Exactly the two source-revision default-OFF labels, not any other prior/dirty tests.
  $paths+=Get-ChildItem -LiteralPath (Join-Path $tests 'logs') -File|Where-Object {$_.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_cpu_public_r[12][._]' -and $_.Extension -in '.json','.log'}|ForEach-Object {$_.FullName}
  foreach($dir in (Get-ChildItem -LiteralPath (Join-Path $tests 'outputs') -Directory)){
    if($dir.Name -match '^upl_cpu_public_source_r[123]$'){
      # Three small immutable source/document text snapshots preserve compile/failure lineage.
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'JSph.h','JSph.cpp','JSphCpu.h','JSphCpu.cpp','JSphCpuSingle.cpp','JPartsLoad4.cpp','_FmtXML_ElastoplasticSoil.xml'}|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_cpu_public_program_(DebugCPU_r[12]|ReleaseCPU_r2)$' -or $dir.Name -eq 'upl_cpu_public_part_program_r1'){
      # Failed reader source and recipe are retained; canonical binaries/runtime never enter Git.
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'upl_cpu_public_native_r1.cpp','upl_cpu_public_native_r1.json','upl_cpu_public_run_r1.ps1','upl_cpu_public_run_r2.ps1','upl_cpu_public_part_tag_r1.cpp','upl_cpu_public_part_run_r1.ps1','upl_cpu_public_part_r1.json','compile.dependencies.json'}|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_cpu_public_seed_r1_(debug_wall_evolving_smoke|periodic_constant_[ch]|wall_constant_[ch]|wall_evolving_[ch]|OFF_default|OFF_explicit)$' -or $dir.Name -match '^upl_cpu_public_reject_r1_[a-z_]+_seed$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File -Filter '*.xml'|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_cpu_public_review_r1_(debug_wall_evolving_smoke|periodic_constant_[ch]|wall_constant_[ch]|wall_evolving_[ch]|OFF_default|OFF_explicit)$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'native_ids.csv','fixed_ids.csv','history.csv','complete.json'}|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_cpu_public_r1_(debug_wall_evolving_smoke|periodic_constant_[ch]|wall_constant_[ch]|wall_evolving_[ch]|OFF_default|OFF_explicit)$' -or $dir.Name -match '^upl_cpu_public_reject_r1_[a-z_]+_out$' -or $dir.Name -match '^upl_cpu_public_part_(OFF_from_FALSE|OFF_from_ON|ON_from_OFF)_r1$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'Run.out','Run.csv'}|ForEach-Object {$_.FullName}
    }elseif($dir.Name -match '^upl_p2_(DebugCPU|ReleaseCPU)_cpu_public_r[12](_(state|pair|(open_)?s(8|128)_o[01]))?$'){
      $paths+=Get-ChildItem -LiteralPath $dir.FullName -File|Where-Object {$_.Name -in 'compile.dependencies.json','observer_complete.json','observer_final.csv','state_complete.json','theta_pairs.csv','Run.csv','Run.out'}|ForEach-Object {$_.FullName}
    }
  }
  @($paths|Sort-Object -Unique)
}
if($Mode -eq 'Stage'){
  if(!$StageAuthorized -or $ReviewedManifestSha256 -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine $ReviewedManifestSha256){throw 'Explicit StageAuthorized and exact root-reviewed manifest SHA required'}
  $manifest=Get-Content -Raw -LiteralPath $target|ConvertFrom-Json
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  if($code -or !$manifest.ready_for_root_review -or $manifest.base -ne $expectedBase -or $head -ne $expectedBase){throw 'Changed Git base or unready manifest'}
  foreach($r in $manifest.files){$a=Entry (Join-Path $repo $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Changed candidate: $($r.path)"}}
  $paths=@($manifest.files.path)+@($target.Substring($repo.Length+1).Replace('\','/'))
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';$index=@(& git -C $repo -c core.quotepath=false diff --cached --name-only);$code=$LASTEXITCODE;$ErrorActionPreference=$old
  if($code){throw 'Cannot inspect index; no stage attempted'}
  foreach($p in $index){if($p -and $p -notin $paths){throw 'Unrelated staged changes preserved; root must resolve scope'}}
  for($i=0;$i -lt $paths.Count;$i+=20){
    $last=[Math]::Min($i+19,$paths.Count-1);$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
    $message=& git -C $repo --literal-pathspecs add -f -- @($paths[$i..$last]) 2>&1;$code=$LASTEXITCODE;$ErrorActionPreference=$old
    $message|Out-Host;if($code){throw 'Exact stage failed; preserve partial index and inspect without resetting'}
  }
  Write-Output "STAGED $($paths.Count) explicit reviewed paths only; no commit or push";exit 0
}
$paths=Candidates
$missingCandidates=@($paths|Where-Object {!(Test-Path -LiteralPath $_)})
$files=@(foreach($p in $paths){
  if(!(Test-Path -LiteralPath $p)){continue}
  if(!$p.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Escaped repository'}
  $e=Entry $p
  if($e.bytes -gt 2097152 -or [IO.Path]::GetExtension($p) -notin '.h','.cpp','.ps1','.py','.json','.md','.xml','.csv','.log','.out','.png'){throw "Unexpected large/unapproved candidate: $p"};$e
})
$required=@('logs\upl_cpu_public_build_r3.json','logs\upl_cpu_public_off_r2.check.json','logs\upl_cpu_public_debug_wall_evolving_smoke_r1.review.check.json','logs\upl_cpu_public_periodic_constant_r1.half.check.json','logs\upl_cpu_public_wall_constant_r1.half.check.json','logs\upl_cpu_public_wall_evolving_r1.half.check.json','logs\upl_cpu_public_OFF_r1.exact.check.json','logs\upl_cpu_public_compare_r1.check.json','logs\upl_cpu_public_compare_r1_layout_r3.check.json','logs\upl_cpu_public_independent_r1.check.json','logs\upl_cpu_public_part_r1.check.json','logs\upl_cpu_public_stage_r1.check.json')
foreach($label in @('drainage','fixed_zero','gravity','hydro_off','model_invalid','model_master_off','model_missing_ck','periodic_crossinc','pore_safety_overflow','spr_conflict','wall_noslip')){$required+='logs\upl_cpu_public_reject_r1_'+$label+'.run.json'}
$missing=@($required|Where-Object {!(Test-Path -LiteralPath (Join-Path $tests $_))})+@($missingCandidates|ForEach-Object {$_.Substring($repo.Length+1)})
if($Mode -eq 'List'){[pscustomobject]@{base=$expectedBase;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;missing=$missing;files=$files;Git_mutated=$false};return}
if((Test-Path -LiteralPath $target) -or $missing.Count){throw 'Manifest retained or final reviews/inputs/snapshots missing'}
foreach($p in $required){
  $r=Get-Content -Raw -LiteralPath (Join-Path $tests $p)|ConvertFrom-Json
  if($p -eq 'logs\upl_cpu_public_build_r3.json'){
    if($r.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests' -or $r.source.Count -ne 7 -or $r.msbuild_exit_codes.DebugCPU -ne 0 -or $r.msbuild_exit_codes.ReleaseCPU -ne 0){throw 'Seven-file authoritative full Rebuild r3 unavailable'}
  }elseif(!$r.passed){throw "Required final gate not passed: $p"}
}
$freeze=Get-Content -Raw -LiteralPath (Join-Path $tests 'logs\upl_cpu_public_build_r3.json')|ConvertFrom-Json
foreach($s in $freeze.source){
  $copy=Get-Item -LiteralPath $s.snapshot.path
  if($copy.Length -ne $s.snapshot.bytes -or (Get-FileHash -LiteralPath $copy.FullName -Algorithm SHA256).Hash -ine $s.snapshot.sha256){throw 'Immutable build snapshot changed'}
  if([IO.Path]::GetExtension($s.original.path) -in '.h','.cpp'){
    $a=Get-Item -LiteralPath $s.original.path
    if($a.Length -ne $s.original.bytes -or (Get-FileHash -LiteralPath $a.FullName -Algorithm SHA256).Hash -ine $s.original.sha256){throw 'Production source changed since tested Rebuild r3'}
  }
}
$doc=Entry (Join-Path $repo 'doc\xml_format\_FmtXML_ElastoplasticSoil.xml')
$buildDoc=@($freeze.source|Where-Object {[IO.Path]::GetFileName($_.original.path) -eq '_FmtXML_ElastoplasticSoil.xml'})
if($buildDoc.Count -ne 1){throw 'Build-time document identity missing'}
$docSame=$doc.bytes -eq $buildDoc[0].original.bytes -and $doc.sha256 -eq $buildDoc[0].original.sha256
if(!$docSame){
  # An intentional post-test documentation update is separate from the tested code identity.
  $stage=Get-Content -Raw -LiteralPath $stagePath|ConvertFrom-Json
  $r=$stage.documentation_after_build
  if(!$stage.documentation_after_build_reviewed -or !$r -or $r.bytes -ne $doc.bytes -or $r.sha256 -ne $doc.sha256){throw 'Changed final documentation requires explicit final-stage audited identity'}
}
$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$headCode=$LASTEXITCODE;$branch=& git -C $repo branch --show-current;$branchCode=$LASTEXITCODE;$ErrorActionPreference=$old
if($headCode -or $branchCode -or $head -ne $expectedBase){throw 'Cannot bind exact stage Git base'}
$comparison=Get-Content -Raw -LiteralPath (Join-Path $tests 'logs\upl_cpu_public_compare_r1.check.json')|ConvertFrom-Json
$manifest=[ordered]@{base=$head;branch=$branch;ready_for_root_review=$true;scope='Limited explicit CPU public dynamic-seepage/J-porosity switch and optional smooth-k wiring; bounded canonical/rejection coverage only';files=$files;count=$files.Count;bytes=($files|Measure-Object bytes -Sum).Sum;required_checks=$required;tested_source_build=(Entry (Join-Path $tests 'logs\upl_cpu_public_build_r3.json'));documentation_at_build=$buildDoc[0].snapshot;documentation_at_publish=$doc;documentation_equal_to_build=$docSame;documentation_not_misrepresented_as_posttest_binary=$true;raw_native_trajectory_or_program_cloud_backup_claimed=$false;excluded='rawBI4/physical.bin/original15.bin/largeledger/exe/obj/pdb/ilk/runtimeDLL/lib/DsphConfig.xml/prebuildcanonical/crash/unrelateddirtyfiles';public_scope='fresh CPU2D,g0,elastic,rectangular periodic or two opposing static parallel axis FreeSlip walls,constant dyadic step; default old u-pw unchanged';not_accepted='GPU/runtime rejection without fresh GPU build,PART interoperability,gravity/generalwalls/NoSlip/curves/motion/plasticity/large rotation/full physical/formal release';complete_private_raw26_equivalence_passed=[bool]$comparison.complete_private_raw26_equivalence_passed;private_wall_flux_or_negative_control_inherited=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($target,($manifest|ConvertTo-Json -Depth 14)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $($files.Count) paths, $($manifest.bytes) bytes; inspect before explicit Stage."

