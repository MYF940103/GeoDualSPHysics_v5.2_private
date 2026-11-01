param([switch]$ExecutionAuthorized)
# Inventory only. Never stage/commit/push, build, launch a program, clean, or copy raw artifacts.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Root full inventory review and explicit authorization required'}
$t=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$manifest=Join-Path $t 'logs\upl_gpu_perm_publish_r1.json'
if(Test-Path -LiteralPath $manifest){throw 'Retained inventory protected'}
$gatePath=Join-Path $t 'logs\upl_gpu_perm_stage_r1.check.json'
$gate=[IO.File]::ReadAllText($gatePath)|ConvertFrom-Json
if(!$gate.PSObject.Properties['passed'] -or $gate.passed -ne $true -or !$gate.PSObject.Properties['physical_acceptance'] -or $gate.physical_acceptance -ne $false -or !$gate.PSObject.Properties['public_GPU_dynamic_accepted'] -or $gate.public_GPU_dynamic_accepted -ne $false){throw 'Verified bounded smooth-k stage with explicit false physical/public scope required'}
$paths=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
function Add([string]$p){$f=Get-Item -LiteralPath $p;if($f.PSIsContainer){throw 'Exact files only'};[void]$paths.Add($f.FullName)}
foreach($leaf in @('JSphGpu.h','JSphGpu.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')){Add (Join-Path $repo ('src\source\'+$leaf))}
Add (Join-Path $repo 'doc\xml_format\_FmtXML_ElastoplasticSoil.xml')
Add (Join-Path $repo 'examples\Hydromechanic coupling\validation\upl_current_status.json')
# Shallow current-tag author/receipt/figure files only; no archived/control directory recursion.
foreach($dir in @('support','notes','logs','figures')){
 foreach($f in Get-ChildItem -LiteralPath (Join-Path $t $dir) -Filter 'upl_gpu_perm_*' -File){
  if(($dir -eq 'support' -and $f.Extension -in @('.ps1','.cpp','.py')) -or ($dir -eq 'notes' -and $f.Extension -in @('.json','.md')) -or ($dir -eq 'logs' -and $f.Extension -in @('.json','.log')) -or ($dir -eq 'figures' -and $f.Extension -in @('.json','.csv','.png'))){Add $f.FullName}
 }
}
$componentLeaves=@('Run.out','completion.json','perm_completion.json','prefix.csv','owner_negatives.csv','host_owner_negative.csv','patch_rates.csv','patch_summary.csv','periodic_rates.csv','periodic_summary.csv','scales.csv','requests.csv','law_rates.csv','law_summary.csv','law_scales.csv','law_guards.csv','law_cache.csv','law_requests.csv','law_periodic_rates.csv','law_periodic_summary.csv')
foreach($cfg in @('Debug','Release')){foreach($leaf in $componentLeaves){Add (Join-Path $t ('outputs\upl_gpu_perm_component_'+$cfg+'_run_r1\'+$leaf))}}
$seedFiles=@(Get-ChildItem -LiteralPath (Join-Path $t 'outputs\upl_gpu_perm_actual_seed_r1') -Filter '*.xml' -File)
if($seedFiles.Count -ne 10){throw 'Expected exactly ten fresh runtime XML seeds; BI4 remains local/hash-bound'}
foreach($f in $seedFiles){Add $f.FullName}
foreach($job in @('OFF_smoke','Observer_smoke','Feedback_smoke','OFF_extended','Observer_extended','Feedback_c','Feedback_h')){
 $root=Join-Path $t ('outputs\upl_gpu_perm_legacy_'+$job+'_r1');$review=$root+'_review'
 Add (Join-Path $root 'Run.out');Add (Join-Path $review 'completion.json');Add (Join-Path $review 'batch\batch_complete.json')
 if($job.StartsWith('Observer')){foreach($leaf in @('observer_complete.json','observer_final.csv')){Add (Join-Path $root $leaf)}}
 if($job.StartsWith('Feedback')){
  foreach($leaf in @('actual_complete.json','live_final.csv')){Add (Join-Path $root $leaf)}
  foreach($leaf in @('completion.json','history.csv','native_ids.csv')){Add (Join-Path $review ('new_33\'+$leaf))}
 }
}
foreach($job in @('Smoke','GPU_k0_c','GPU_k0_h','GPU_constant_c','GPU_constant_h','VariableSmoke','GPU_variable_c','GPU_variable_h','CPU_variable_c','CPU_variable_h')){
 $root=Join-Path $t ('outputs\upl_gpu_perm_actual_'+$job+'_r1')
 foreach($leaf in @('completion.json','history.csv','native_ids.csv','last_poro.csv')){Add (Join-Path ($root+'_review') $leaf)}
 Add (Join-Path $root 'Run.out')
 # Canonical CPU runs have no private GPU actual_complete/live export; never fabricate or demand them.
 if(!$job.StartsWith('CPU_')){foreach($leaf in @('actual_complete.json','live_final.csv')){Add (Join-Path $root $leaf)}}
}
$records=@()
foreach($p in @($paths|Sort-Object)){
 $rel=$p.Substring($repo.Length+1).Replace('\','/')
 if($rel -match '\.(bi4|ibi4|obi4|exe|obj|dll|lib|pdb|exp|binlog|bin|vtk|vtu)$' -or $rel -match '/batch/poro_|cpu_posdiv\.csv$|/(old|new)_33/physical\.bin$'){throw 'Raw/large/native sidecar excluded from inventory'}
 $f=Get-Item -LiteralPath $p;if($f.Length -gt 2MB){throw "Unexpected oversized selected artifact: $rel"}
 $records+=@{path=$rel;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
}
[long]$totalBytes=0;foreach($row in $records){$totalBytes+=[long]$row.bytes}
$gateFile=Get-Item -LiteralPath $gatePath
$report=[ordered]@{stage='upl_gpu_perm_publish_r1';kind='exact_local_file_whitelist_before_selective_Git';base_checkpoint='8052637f52176814ba529c06160d6f96ac5b149c';branch='upl-dev';prerequisite_stage=@{path=$gatePath;bytes=$gateFile.Length;sha256=(Get-FileHash -LiteralPath $gatePath -Algorithm SHA256).Hash.ToLowerInvariant()};artifact_count=$records.Count;artifact_bytes=$totalBytes;files=$records;manifest_self_excluded=$true;changed_GPU_source_files=4;JSphGpuSingle_cpp_selected=$false;shallow_current_tag_selection_only=$true;retained_raw_BI4_physical_bin_executable_runtime_local_hash_bound_not_cloud=$true;raw_BI4_program_physical_bin_perPART_poro_or_cpu_PosDiv_cloud_backup_claim=$false;physical_acceptance=$false;public_GPU_dynamic_accepted=$false;Git_commands_executed=$false}
[IO.File]::WriteAllText($manifest,($report|ConvertTo-Json -Depth 8)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
[pscustomobject]@{files=$records.Count;bytes=$report.artifact_bytes;manifest=$manifest}|ConvertTo-Json

