param([switch]$ExecutionAuthorized)
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Root reviewed exact three-file cleanup required'}
$hydro=Split-Path -Parent $PSScriptRoot
$case=Join-Path $hydro '01_SelfWeightConsolidation_PR'
$before=Join-Path $PSScriptRoot 'remove_sw_link_cache_r1.before.json'
$after=Join-Path $PSScriptRoot 'remove_sw_link_cache_r1.check.json'
foreach($record in @($before,$after)){if(Test-Path -LiteralPath $record){throw 'Existing cleanup record protected'}}
$expected=@(
  @{relative='tests\outputs\sw_pore_cell_build_r1\Debug\out\DualSPHysics5.2_win64_debug.ilk';bytes=43768032;sha256='21f8ba26ca8bcbb10e8dac5997649220e6a3696a18780a121ad07a2b1b1cb6f9'},
  @{relative='tests\outputs\sw_pore_cell_build_r1\DebugCPU\out\DualSPHysics5.2CPU_win64_debug.ilk';bytes=35908880;sha256='1aadbb5c12908f0ff60182e1780f2333b3fc77f1c947359c501ee9203dd306c1'},
  @{relative='tests\outputs\sw_release_build_r1\DebugCPU\out\DualSPHysics5.2CPU_win64_debug.ilk';bytes=35907544;sha256='46a7de7ff8c7553832396dde3f23d9359ad87eb2496761acf400a87c348ad932'}
)
function Entry([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Save([string]$p,$v){if(Test-Path -LiteralPath $p){throw 'Existing record protected'};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 8)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
$targets=@();$programs=@{}
foreach($item in $expected){
  $path=[IO.Path]::GetFullPath((Join-Path $case $item.relative))
  if(!$path.StartsWith(([IO.Path]::GetFullPath((Join-Path $case 'tests\outputs'))+'\'),[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($path) -ine '.ilk'){throw 'Cleanup target leaves intended cache roots'}
  $f=Get-Item -LiteralPath $path
  if($f.PSIsContainer -or ($f.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Only literal regular cache files admitted'}
  $e=Entry $path;if($e.bytes -ne $item.bytes -or $e.sha256 -ine $item.sha256){throw 'Reviewed cache identity changed'}
  $targets+=@($e)
  foreach($retained in Get-ChildItem -LiteralPath $f.DirectoryName -File|Where-Object{$_.Extension -in @('.exe','.pdb')}){$programs[$retained.FullName]=Entry $retained.FullName}
}
if(@(Get-CimInstance Win32_Process|Where-Object{$_.CommandLine -and ($_.CommandLine -like '*sw_pore_cell_build_r1*' -or $_.CommandLine -like '*sw_release_build_r1*') -and $_.ProcessId -ne $PID}).Count){throw 'A target build owner is active'}
Save $before ([ordered]@{stage='remove_sw_link_cache_r1';utc=[DateTime]::UtcNow.ToString('o');targets=$targets;retained_program_and_PDB=@($programs.Values);scope='Three unreferenced cold incremental-link caches only. No result/program/PDB/OBJ/source/config deletion.';reference_audit='Root and independent read-only audit found no ILK consumer in case01/02/04 log JSON and validation records. Native tests consume retained programs/PARTs, not these caches.';regeneration='A future authoritative MSBuild link recreates .ilk; original per-configuration .build.json commands and source snapshots are retained. Cache bit identity is not a physical reproducibility requirement.'})
$failure=$null;$removed=@()
try{
  foreach($entry in $targets){Remove-Item -LiteralPath $entry.path -Force;if(Test-Path -LiteralPath $entry.path){throw 'Literal cache removal failed'};$removed+=@($entry)}
  foreach($entry in $programs.Values){$actual=Entry $entry.path;if($actual.bytes -ne $entry.bytes -or $actual.sha256 -ine $entry.sha256){throw 'Retained program/PDB changed'}}
}catch{$failure=$_.Exception.Message}
Save $after ([ordered]@{stage='remove_sw_link_cache_r1';passed=(!$failure -and $removed.Count -eq 3);before=(Entry $before);deleted_files=$removed;deleted_bytes=($removed|Measure-Object -Property bytes -Sum).Sum;retained_program_and_PDB_unchanged=(!$failure);formal_raw_results_figures_configs_sources_untouched=$true;development_jobs_stopped=$false;failure=$failure})
if($failure){throw $failure}
Write-Output ('Removed only three cold link caches: '+$after)
