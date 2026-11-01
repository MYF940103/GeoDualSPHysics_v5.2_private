param([switch]$ExecutionAuthorized)
# Inventory only: no Git mutation, solver, build, cleanup, or raw-binary publication.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Root review required'}
$t=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$manifest=Join-Path $t 'logs\upl_gpu_darcy_publish_r1.json'
if(Test-Path -LiteralPath $manifest){throw 'Retained inventory protected'}
$gate=[IO.File]::ReadAllText((Join-Path $t 'logs\upl_gpu_darcy_stage_r1.check.json'))|ConvertFrom-Json
if(!$gate.passed -or $gate.physical_acceptance -or $gate.public_GPU_dynamic_accepted){throw 'Verified bounded stage required'}
$paths=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
function Add([string]$p){$f=Get-Item -LiteralPath $p;if($f.PSIsContainer){throw 'Exact files only'};[void]$paths.Add($f.FullName)}
foreach($leaf in @('JSphGpu.h','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')){Add (Join-Path $repo ('src\source\'+$leaf))}
Add (Join-Path $repo 'doc\xml_format\_FmtXML_ElastoplasticSoil.xml')
Add (Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json')
foreach($dir in @('support','notes','logs','figures')){
 foreach($f in Get-ChildItem -LiteralPath (Join-Path $t $dir) -Filter 'upl_gpu_darcy*' -File){
  if(($dir -eq 'support' -and $f.Extension -in @('.ps1','.cpp','.py')) -or ($dir -eq 'notes' -and $f.Extension -eq '.json') -or ($dir -eq 'logs' -and $f.Extension -in @('.json','.log')) -or ($dir -eq 'figures' -and $f.Extension -in @('.json','.csv','.png'))){Add $f.FullName}
 }
}
foreach($name in @('upl_gpu_darcy_component_Debug_run_r3','upl_gpu_darcy_component_Release_run_r4')){
 foreach($f in Get-ChildItem -LiteralPath (Join-Path $t ('outputs\'+$name)) -File){if($f.Extension -in @('.json','.csv','.out')){Add $f.FullName}}
}
foreach($f in Get-ChildItem -LiteralPath (Join-Path $t 'outputs\upl_gpu_darcy_actual_seed_r1') -Filter '*.xml' -File){Add $f.FullName}
foreach($job in @('OFF_smoke','Observer_smoke','Feedback_smoke','OFF_extended','Observer_extended','Feedback_c','Feedback_h')){
 $root=Join-Path $t ('outputs\upl_gpu_darcy_legacy_'+$job+'_r1');$review=$root+'_review'
 Add (Join-Path $root 'Run.out');Add (Join-Path $review 'completion.json');Add (Join-Path $review 'batch\batch_complete.json')
 foreach($leaf in @('observer_final.csv','live_final.csv','observer_complete.json','actual_complete.json')){if(Test-Path -LiteralPath (Join-Path $root $leaf)){Add (Join-Path $root $leaf)}}
 # The retained immutable33 reader has exactly these three compact leaves, not new Darcy's last_poro.csv.
 if($job.StartsWith('Feedback')){foreach($leaf in @('completion.json','history.csv','native_ids.csv')){Add (Join-Path $review ('new_33\'+$leaf))}}
}
foreach($job in @('Smoke','GPU_k0_c','GPU_k0_h','GPU_constant_c','GPU_constant_h','retained_GPU_legacy_k0_c','retained_GPU_legacy_k0_h','retained_CPU_constant_c','retained_CPU_constant_h')){
 $root=Join-Path $t ('outputs\upl_gpu_darcy_actual_'+$job+'_r1')
 foreach($leaf in @('completion.json','history.csv','native_ids.csv','last_poro.csv')){Add (Join-Path ($root+'_review') $leaf)}
 if(!$job.StartsWith('retained_')){foreach($leaf in @('Run.out','actual_complete.json','live_final.csv')){Add (Join-Path $root $leaf)}}
}
$records=@()
foreach($p in @($paths|Sort-Object)){
 $rel=$p.Substring($repo.Length+1).Replace('\','/')
 if($rel -match '\.(bi4|ibi4|obi4|exe|obj|dll|lib|pdb|exp|binlog|bin)$' -or $rel -match '/batch/poro_|cpu_posdiv\.csv$'){throw 'Raw/large output excluded from Git inventory'}
 $f=Get-Item -LiteralPath $p;$records+=@{path=$rel;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
}
[long]$totalBytes=0;foreach($row in $records){$totalBytes+=$row.bytes}
$report=[ordered]@{stage='upl_gpu_darcy_publish_r1';kind='exact_local_file_whitelist_before_selective_Git';base_checkpoint='7387fb0e435928c2a742281cc0406153e4605fc0';branch='upl-dev';artifact_count=$records.Count;artifact_bytes=$totalBytes;files=$records;manifest_self_excluded=$true;raw_BI4_program_physical_bin_or_perPART_sidecar_cloud_backup_claim=$false;physical_acceptance=$false;public_GPU_dynamic_accepted=$false}
[IO.File]::WriteAllText($manifest,($report|ConvertTo-Json -Depth 8)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
[pscustomobject]@{files=$records.Count;bytes=$report.artifact_bytes;manifest=$manifest}|ConvertTo-Json
