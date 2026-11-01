param([Parameter(Mandatory=$true)][ValidateSet('FreezeBaseline','BuildGpu')][string]$Mode,[ValidateSet('Debug','Release')][string]$Configuration='Debug',[switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized)
# Build-only replay: no helper, help command, physical solver, or Git mutation.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$out=Join-Path $t 'outputs';$base='7387fb0e435928c2a742281cc0406153e4605fc0'
$note=Join-Path $t 'notes\upl_gpu_darcy_build_r1.json';$baselinePath=Join-Path $logs 'upl_gpu_darcy_r1.baseline.json'
$acceptedPath=Join-Path $logs 'upl_gpu_k0_actual_stage_r2.check.json';$five=@('JSphGpu.h','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ResolveArtifactPath([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function V($rows){foreach($r in $rows){$a=E (ResolveArtifactPath $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){Get-Content -Raw -LiteralPath (ResolveArtifactPath $p)|ConvertFrom-Json}
function Save([string]$p,$x){if(Test-Path -LiteralPath $p){throw 'Retained record protected'};[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function BaseBlob([string]$relative){
  $p=New-Object Diagnostics.Process;$p.StartInfo.FileName='git';$p.StartInfo.Arguments='-C "'+$repo+'" cat-file blob '+$base+':'+$relative
  $p.StartInfo.UseShellExecute=$false;$p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true;$p.StartInfo.CreateNoWindow=$true
  [void]$p.Start();$m=New-Object IO.MemoryStream;$p.StandardOutput.BaseStream.CopyTo($m);$errorText=$p.StandardError.ReadToEnd();$p.WaitForExit();if($p.ExitCode){throw "Git base blob unavailable: $errorText"}
  $hash=[Security.Cryptography.SHA256]::Create();$m.Position=0;$digest=([BitConverter]::ToString($hash.ComputeHash($m))).Replace('-','').ToLowerInvariant()
  $entry=[ordered]@{git_base=$base;git_path=$relative;bytes=$m.Length;sha256=$digest};$hash.Dispose();$m.Dispose();$p.Dispose();$entry
}
function Call($tool,[string[]]$argv,[string]$label){
  V @($tool);$p=Join-Path $logs ($label+'.call.json');$log=Join-Path $logs ($label+'.log');if((Test-Path -LiteralPath $p) -or (Test-Path -LiteralPath $log)){throw 'Owned build retained'}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  Push-Location (Join-Path $repo 'src');try{& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}finally{Pop-Location;$ErrorActionPreference=$old}
  V @($tool);Save $p ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);program_or_component_run=$false;physical_acceptance=$false})
  if($code){throw 'Build failed; retain evidence'};E $p
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root review and explicit single-action authorization required'}
$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$old;if($code -or $head -ne $base){throw 'Exact verified 7387fb0 checkpoint required'}
if($Mode -eq 'FreezeBaseline'){
  if(Test-Path -LiteralPath $baselinePath){throw 'Baseline already frozen; never rearm'}
  $accepted=J $acceptedPath
  if(!$accepted.passed -or @($accepted.helpers).Count -ne 2 -or @($accepted.single_runs).Count -ne 5 -or @($accepted.independent_halves).Count -ne 2 -or @($accepted.same_dt_backend_cross).Count -ne 2 -or !$accepted.successful_Debug_Pre_Corr_smoke -or $accepted.nonzero_k_tested -or $accepted.public_GPU_dynamic_accepted -or $accepted.physical_acceptance){throw 'Accepted bounded private k0 actual stage required'}
  # Bind immutable reviewed predicates/receipts only; never traverse its publication manifest or mutable validation status.
  $controls=@($accepted.helpers)+@($accepted.prior_time_stage,$accepted.prepared_inputs)
  foreach($single in $accepted.single_runs){$controls+=@($single.check,$single.run,$single.reader_completion)}
  foreach($pair in @($accepted.independent_halves)+@($accepted.same_dt_backend_cross)){$controls+=@($pair.record)}
  V $controls
  $retained=@();$inventory=$null;$inputs=@(E $PSCommandPath;E $note;E $acceptedPath)+$controls
  foreach($cfg in @('Debug','Release')){
    $bp=Join-Path $logs ('upl_gpu_k0_time_'+$cfg+'_r1.build.json');$b=J $bp
    if($b.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $b.configuration -ne $cfg){throw 'Retained authoritative time-policy build required'}
    V @($b.source_freeze,$b.project_call,$b.isolated_GPU_program,$b.baseline);V $b.tools;foreach($r in $b.runtime){V @($r.original,$r.copy)}
    $s=J $b.source_freeze.path;$all=@($s.source|Sort-Object path -Unique)
    if($all.Count -ne 265){throw 'Retained 265-source inventory differs'}
    if($null -eq $inventory){$inventory=$all}else{foreach($a in $all){$same=@($inventory|Where-Object {$_.path -ieq $a.path});if($same.Count -ne 1 -or $same[0].sha256 -ine $a.sha256 -or $same[0].bytes -ne $a.bytes){throw 'Time Debug/Release source inventories differ'}}}
    $retained+=@{configuration=$cfg;build=(E $bp);source_freeze=$b.source_freeze;program=$b.isolated_GPU_program;runtime=$b.runtime;project_call=$b.project_call}
    $inputs+=@(E $bp;$b.source_freeze;$b.project_call;$b.baseline)
  }
  $oldBase=J $retained[0].build.path;$oldBase=J $oldBase.baseline.path;V $oldBase.canonical_GPU
  $projectInputs=@($oldBase.inputs|Where-Object {$_.path -match '\.(sln|vcxproj)$'});if($projectInputs.Count -ne 2){throw 'Authoritative solution/project identities missing'};V $projectInputs;$inputs+=$projectInputs
  $other=@($inventory|Where-Object {[IO.Path]::GetFileName($_.path) -notin $five});if($other.Count -ne 260){throw 'Expected five targets and260 other sources'};V $other
  # Git stores LF-normalised blobs; historical mixed-CRLF build bytes remain separately bound.
  $targets=@();foreach($name in $five){$e=@($inventory|Where-Object {[IO.Path]::GetFileName($_.path) -eq $name});if($e.Count -ne 1){throw 'Base target identity missing'};$raw=BaseBlob ('src/source/'+$name);$targets+=@{retained_source=$e[0];git_blob=$raw;raw_Git_equals_historical_build_bytes=($raw.bytes -eq $e[0].bytes -and $raw.sha256 -ieq $e[0].sha256);line_ending_normalisation_not_source_equivalence_gate=$true}}
  Save $baselinePath ([ordered]@{status='verified_private_k0_actual_base_and_retained_GPU_programs_frozen_no_copies';git_base=$base;accepted_actual_stage=(E $acceptedPath);source_control_receipts=$controls;mutable_validation_status_bound=$false;inputs=$inputs;base_source=$inventory;five_base_targets=$targets;other_source=$other;canonical_GPU=$oldBase.canonical_GPU;retained_GPU_programs=$retained;current_five_may_already_be_edited=$true;source_or_program_copies_made=0;program_or_component_run=$false;physical_acceptance=$false});exit 0
}
$b=J $baselinePath;if($b.git_base -ne $base -or $b.status -ne 'verified_private_k0_actual_base_and_retained_GPU_programs_frozen_no_copies'){throw 'New immutable baseline required'};V $b.inputs;V $b.other_source;V $b.canonical_GPU
$oldBuildPath=Join-Path $logs ('upl_gpu_k0_time_'+$Configuration+'_r1.build.json');$oldGpu=J $oldBuildPath;V @($oldGpu.source_freeze,$oldGpu.project_call,$oldGpu.isolated_GPU_program);V $oldGpu.tools
$oldCall=J $oldGpu.project_call.path;V @($oldCall.program,$oldCall.log);if($oldCall.exit_code -ne 0 -or $oldCall.arguments -notcontains '/t:Rebuild'){throw 'Successful authoritative full Rebuild vector required'}
if($Configuration -eq 'Release'){$d=J (Join-Path $logs 'upl_gpu_darcy_Debug_r1.build.json');if($d.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run'){throw 'Fresh Debug build required before Release'};V $d.inputs;V @($d.project_call,$d.isolated_GPU_program,$d.source_freeze)}
$source=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl','.cpp','.cu'}|Sort-Object FullName|ForEach-Object {E $_.FullName});if($source.Count -ne 265){throw 'Current source closure differs'}
$api=@();foreach($e in @($source|Where-Object {[IO.Path]::GetFileName($_.path) -in $five})){
  $line=0;foreach($text in Get-Content -LiteralPath $e.path){$line++;if($text -match 'DynamicPorePressure|ComputePorosityWaveSpeed2|ExtendDynamicPorePeriodic|PrepareDynamicPorePeriodicGpu|GetDynamicStepScalesGpu|Darcy'){ $api+=@{path=$e.path;line=$line;text=$text} }}
}
$name='upl_gpu_darcy_'+$Configuration+'_r1';$folder=Join-Path $out $name;$freeze=Join-Path $logs ($name+'.source.json');$record=Join-Path $logs ($name+'.build.json')
$int=Join-Path ([IO.Path]::GetTempPath()) ('upl_gpu_darcy_r1\'+$Configuration+'\int\');if($int -match '\s'){throw 'CUDA IntDir must have no spaces'}
foreach($p in @($folder,$int,$freeze,$record)){if(Test-Path -LiteralPath $p){throw 'Retained build protected; use a new reviewed label'}}
$inputs=@(E $PSCommandPath;E $note;E $baselinePath;E $oldBuildPath)+$source+@($b.inputs|Where-Object {$_.path -match '\.(sln|vcxproj)$'})
Save $freeze ([ordered]@{status='private_constant_k_Darcy_current_source_hashes_frozen_before_authoritative_build';git_base=$base;baseline=(E $baselinePath);source=$source;five_targets=@($source|Where-Object {[IO.Path]::GetFileName($_.path) -in $five});api_inventory=$api;api_inventory_is_text_capture_not_implementation_acceptance=$true;accepted_actual_stage=(E $acceptedPath);mutable_validation_status_bound=$false;inputs=$inputs;source_or_program_backup_copies_made=0})
[void](New-Item -ItemType Directory -Path $folder);[void](New-Item -ItemType Directory -Path $int);$gpuout=Join-Path $folder 'gpu\';[void](New-Item -ItemType Directory -Path $gpuout)
$args2=@();$replaced=0;foreach($a in $oldCall.arguments){if($a.StartsWith('/p:OutDir=',[StringComparison]::OrdinalIgnoreCase)){$args2+='/p:OutDir='+$gpuout.Replace('\','/');$replaced++}elseif($a.StartsWith('/p:IntDir=',[StringComparison]::OrdinalIgnoreCase)){$args2+='/p:IntDir='+$int.Replace('\','/');$replaced++}elseif($a.StartsWith('/bl:',[StringComparison]::OrdinalIgnoreCase)){$args2+='/bl:'+(Join-Path $logs ($name+'.binlog'));$replaced++}else{$args2+=$a}}
if($replaced -ne 3){throw 'Only three build path remaps permitted'}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$call=Call $oldCall.program $args2 ($name+'_project');$objects=@($oldGpu.objects|ForEach-Object {E (Join-Path $int ([IO.Path]::GetFileName($_.path)))});if($objects.Count -ne 110){throw '110-object authoritative closure excluding main required'}
$runtime=@();foreach($r in $oldGpu.runtime){V @($r.original,$r.copy);$p=Join-Path $gpuout ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $p;$v=E $p;if($v.sha256 -ne $r.copy.sha256){throw 'New runtime copy differs'};$runtime+=@{original=$r.copy;copy=$v}}
V $inputs;V $b.other_source;V $b.canonical_GPU;V $oldGpu.tools;$exe=Join-Path $gpuout ([IO.Path]::GetFileName($oldGpu.isolated_GPU_program.path))
Save $record ([ordered]@{status='full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run';configuration=$Configuration;git_base=$base;baseline=(E $baselinePath);source_freeze=(E $freeze);inputs=$inputs;tools=$oldGpu.tools;objects=$objects;objects_exclude_main=$true;project_call=$call;isolated_GPU_program=(E $exe);runtime=$runtime;no_space_IntDir=$int;isolated_GPU_OutDir=$gpuout;replayed_build=(E $oldBuildPath);remapped_GPU_arguments=3;canonical_GPU_unchanged=$true;source_or_program_backup_copies_made=0;private_constant_k_Darcy_candidate_build_only=$true;public_GPU_dynamic_accepted=$false;program_or_component_run=$false;physical_acceptance=$false})
