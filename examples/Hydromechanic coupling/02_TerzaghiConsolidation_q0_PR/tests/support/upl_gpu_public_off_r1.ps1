param([Parameter(Mandatory=$true)][ValidateSet('Prepare','RunJob','ReviewJob')][string]$Mode,[string]$ReaderBuildReceipt,[switch]$ExecutionAuthorized)
# Exactly one explicit action. No GenCase, builds, old solver, restart, help or auto-retry.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$case=Split-Path -Parent $t
$logs=Join-Path $t 'logs';$outputs=Join-Path $t 'outputs';$tag='upl_gpu_public_off_r1';$oldname='symc_1d_short_r1_gpu_old'
$old=Join-Path $outputs $oldname;$seed=Join-Path $outputs ($tag+'_seed');$folder=Join-Path $outputs $tag
$manifest=Join-Path $logs ($tag+'.inputs.json');$runpath=Join-Path $logs ($tag+'.run.json');$complete=Join-Path $logs ($tag+'.completion.json');$checkpath=Join-Path $logs ($tag+'.check.json')
$note=Join-Path $t 'notes\upl_gpu_public_off_r1.json';$readerCpp=Join-Path $t 'support\upl_gpu_public_off_native_r1.cpp'
$gpuPath=Join-Path $logs 'upl_gpu_public_Release_r1.build.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function V($rows){foreach($r in $rows){if(!$r.path -or !$r.sha256 -or $null -eq $r.bytes){throw 'Incomplete artifact binding'};$a=E $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed frozen artifact: $($r.path)"}}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Save([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 22)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Existing output protected: $p"}}}
function N($v){if($null -eq $v){throw 'Missing numeric field'};$x=[double]$v;if([double]::IsNaN($x)-or[double]::IsInfinity($x)){throw 'Nonfinite number'};$x}
function NoSolver{if(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -like 'DualSPHysics*.exe'}).Count){throw 'An existing solver is active; this action will not stop it or launch another'}}
function CurrentBuild {
  $g=J $gpuPath;if($g.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $g.configuration -ne 'Release' -or @($g.objects).Count -ne 110 -or !$g.objects_exclude_main -or !$g.canonical_GPU_unchanged){throw 'Authoritative public Release build required'}
  V $g.inputs;V $g.tools;V $g.objects;V @($g.baseline,$g.source_freeze,$g.project_call,$g.isolated_GPU_program)
  $s=J $g.source_freeze.path;if(@($s.source).Count -ne 265 -or @($s.four_targets).Count -ne 4 -or $s.unchanged_source_count -ne 261){throw 'Public four/261/265 source closure differs'};V $s.source
  $b=J $g.baseline.path;if(@($b.canonical_GPU).Count -ne 6 -or @($b.other_source).Count -ne 261 -or @($b.target_copies).Count -ne 4){throw 'Protected canonical/source baseline closure differs'};V $b.inputs;V $b.other_source;V $b.canonical_GPU;V $b.source_control_receipts;foreach($r in $b.target_copies){V @($r.copy)}
  foreach($r in $g.runtime){V @($r.original,$r.copy)};$c=J $g.project_call.path;V @($c.program,$c.log);if(!$c.owned_call_exited -or $c.exit_code -ne 0 -or $c.arguments -notcontains '/t:Rebuild'){throw 'Actual owned full Rebuild did not pass'}
  return $g
}
function Control {
  $prepPath=Join-Path $logs 'symc_1d_short_r1.inputs.json';$oldrunPath=Join-Path $logs 'symc_1d_short_r1.run.json';$receiptPath=Join-Path $logs ($oldname+'.receipt.json');$completionPath=Join-Path $logs ($oldname+'.completion.json')
  $p=J $prepPath;$r=J $oldrunPath;$a=J $receiptPath;$c=J $completionPath
  V @($r.prepared);$job=@($p.jobs|Where-Object {$_.name -ceq $oldname});if($job.Count -ne 1){throw 'Unique retained old GPU job missing'};$job=$job[0]
  $sealed=@($r.jobs|Where-Object {$_.path -ieq $receiptPath});if($sealed.Count -ne 1){throw 'Old run does not bind old receipt'};V $sealed;V @($a.sealed_completion,$a.history)
  if(!$a.passed -or @($a.rows).Count -ne 151 -or !$c.solver_finished -or !$c.owned_exited -or $c.exit_code -ne 0 -or @($c.surviving_owned).Count){throw 'Retained151-frame old GPU control was not complete and safe'}
  V @($job.program,$job.config,$job.bat,$job.build,$c.program,$c.config,$c.bat);V $job.runtime;V $c.outputs
  $base=J $job.build.path;if($base.status -ne 'pre_edit_exact_baseline_archived'){throw 'Old source/program snapshot provenance differs'};foreach($v in $base.files){V @($v.snapshot)} # Never revalidate deliberately changed historical original source/canonical paths.
  $raw=@($c.outputs|Where-Object {[IO.Path]::GetFileName($_.path)-match '^Part_\d{4}\.bi4$'});if($raw.Count -ne 151){throw 'Old sealed raw PART coverage differs'}
  if((N $a.rows[-1].time_s) -ne [double]0.15000000000000924 -or $a.rows[-1].saved_step -ne 14999 -or $a.hourglass.force_calls -ne 30000 -or $a.hourglass.rate_calls -ne 30000 -or $a.hourglass.calculations -ne 15001 -or $a.hourglass.cache_hits -ne 14999){throw 'Retained complete clock/HG counters differ'}
  foreach($row in $a.rows){if((N $row.dterror_s) -gt 1e-14 -or (N $row.pore_dt_s) -lt 1e-5 -or !$row.load_available){throw 'Retained original safety record failed'}}
  return @{job=$job;receipt=$a;completion=$c;bindings=@(E $prepPath;E $oldrunPath;E $receiptPath;E $completionPath;E $a.history.path;E $job.build.path)}
}
function OwnedCall($tool,[string[]]$argv,[string]$label,[string]$cwd,[bool]$solver){
  V @($tool);$call=Join-Path $logs ($label+'.call.json');$stdout=Join-Path $logs ($label+'.stdout.log');$stderr=Join-Path $logs ($label+'.stderr.log');Fresh @($call,$stdout,$stderr)
  $quoted=@($argv|ForEach-Object {if($_.Contains('"')){throw 'Unexpected embedded quote'};'"'+$_+'"'}) -join ' ';$start=[DateTime]::UtcNow.ToString('o')
  $p=Start-Process -FilePath $tool.path -ArgumentList $quoted -WorkingDirectory $cwd -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
  $pidOwned=$p.Id;$p.WaitForExit();$p.Refresh();$code=$p.ExitCode;$exited=$p.HasExited
  $survivors=@(Get-CimInstance Win32_Process|Where-Object {$_.ProcessId -eq $pidOwned -or $_.ParentProcessId -eq $pidOwned}|Select-Object ProcessId,ParentProcessId,Name,CommandLine)
  V @($tool);Save $call ([ordered]@{program=$tool;arguments=$argv;working_directory=$cwd;owned_pid=$pidOwned;owned_call_exited=$exited;exit_code=$code;surviving_owned=$survivors;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');stdout=(E $stdout);stderr=(E $stderr);actual_solver_call=$solver;offline_reader_only=(!$solver);physical_acceptance=$false})
  return (E $call)
}
if(!$ExecutionAuthorized){throw 'Root full-read and explicit one-action authorization required; no action executed'}
if($Mode -eq 'Prepare'){
  Fresh @($seed,$folder,$manifest,$runpath,$complete,$checkpath);$g=CurrentBuild;$c=Control
  $prefix=Join-Path $seed $oldname;$copies=@();$oldprefix=Join-Path $old $oldname
  foreach($suffix in @('.xml','.bi4','_Normals.nbi4')){V @($c.completion.outputs|Where-Object {$_.path -ieq ($oldprefix+$suffix)});if(!(Test-Path -LiteralPath ($oldprefix+$suffix))){throw 'Required sealed seed missing'}}
  [xml]$xml=[IO.File]::ReadAllText($oldprefix+'.xml');$hm=$xml.SelectSingleNode('/case/execution/special/hydromechanics')
  foreach($k in @('HydroMechDynamicSeepage','HydroMechConductivityModel','HydroMechConductivityCk','PoreDarcySymmetricCorr')){if($hm.SelectSingleNode($k)){throw 'Default omission input unexpectedly contains a new/symC switch'}}
  foreach($pair in @(@('DtIni','0.00001'),@('DtFixed','0.00001'),@('TimeMax','0.15'),@('TimeOut','0.001'),@('Boundary','2'))){$node=$xml.SelectSingleNode('/case/execution/parameters/parameter[@key="'+$pair[0]+'"]');if(!$node -or (N $node.GetAttribute('value')) -ne (N $pair[1])){throw 'Original solver configuration differs'}}
  [void](New-Item -ItemType Directory -Path $seed);foreach($suffix in @('.xml','.bi4','_Normals.nbi4')){$source=E ($oldprefix+$suffix);$target=$prefix+$suffix;Copy-Item -LiteralPath $source.path -Destination $target;$copy=E $target;if($source.bytes -ne $copy.bytes -or $source.sha256 -ine $copy.sha256){throw 'Input copy changed bytes'};$copies+=@{original=$source;copy=$copy}}
  Save $manifest ([ordered]@{stage=$tag;sole_old_control=$oldname;inputs=@(E $PSCommandPath;E $note;E $readerCpp;E $gpuPath)+$c.bindings;source_build=(E $gpuPath);source_freeze=$g.source_freeze;program=$g.isolated_GPU_program;runtime=$g.runtime;control_receipt=(E (Join-Path $logs ($oldname+'.receipt.json')));control_completion=(E (Join-Path $logs ($oldname+'.completion.json')));control_build=$c.job.build;control_program=$c.job.program;control_runtime=$c.job.runtime;copied_inputs=$copies;input_prefix=$prefix;output=$folder;arguments=@('-gpu','-ompthreads:1','-stable','-mdbc',$prefix,$folder,'-dirdataout','data','-svres','-svextraparts:1','-nsteps:15000');steps=15000;frames=151;native_count=1040;fixed_count=40;dt_s=1e-5;cadence_s=.001;dynamic_input_omitted=$true;GenCase_called=$false;old_program_run=$false;solver_started=$false;physical_acceptance=$false});return
}
$m=J $manifest;V $m.inputs;V @($m.source_build,$m.source_freeze,$m.program,$m.control_receipt,$m.control_completion,$m.control_build,$m.control_program);V $m.control_runtime
foreach($r in $m.copied_inputs){V @($r.original,$r.copy)};foreach($r in $m.runtime){V @($r.original,$r.copy)};$g=CurrentBuild;$c=Control
if($Mode -eq 'RunJob'){
  Fresh @($folder,$runpath,$complete,$checkpath);NoSolver;$call=OwnedCall $m.program $m.arguments $tag $case $true;$owned=J $call.path
  $files=@();if(Test-Path -LiteralPath $folder){$files=@(Get-ChildItem -LiteralPath $folder -File -Recurse|Sort-Object FullName|ForEach-Object {E $_.FullName})}
  $text=if(Test-Path -LiteralPath (Join-Path $folder 'Run.out')){[IO.File]::ReadAllText((Join-Path $folder 'Run.out'))}else{''}
  Save $complete ([ordered]@{owned_call=$call;owned_exited=$owned.owned_call_exited;exit_code=$owned.exit_code;surviving_owned=$owned.surviving_owned;solver_finished=($owned.exit_code -eq 0 -and $text.Contains('Finished execution (code=0)'));files=$files;sealed_before_offline_analysis=$true;physical_acceptance=$false})
  Save $runpath ([ordered]@{status='owned_solver_completed_pending_offline_review';input=(E $manifest);source_build=$m.source_build;program=$m.program;runtime=$m.runtime;call=$call;completion=(E $complete);files=$files;old_program_run=$false;new_solver_calls=1;physical_acceptance=$false})
  if(!$owned.owned_call_exited -or $owned.exit_code -ne 0 -or @($owned.surviving_owned).Count -or !$text.Contains('Finished execution (code=0)')){throw 'Owned new solver failed/interrupted; preserved exact completion and partial outputs; do not rerun'};return
}
Fresh @($checkpath,(Join-Path $outputs ($tag+'_review')));$r=J $runpath;$done=J $complete;V @($r.input,$r.source_build,$r.program,$r.call,$r.completion);V $done.files;$call=J $r.call.path;V @($call.program,$call.stdout,$call.stderr)
if(!$done.solver_finished -or !$done.owned_exited -or $done.exit_code -ne 0 -or @($done.surviving_owned).Count){throw 'Completed successful new owned solver required; offline failure must not rerun it'}
$text=[IO.File]::ReadAllText((Join-Path $folder 'Run.out'))
$steps=[regex]::Match($text,'Steps of simulation\.*:\s*(\d+)');$hg=[regex]::Match($text,'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)');$cache=[regex]::Match($text,'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)');$bounds=[regex]::Match($text,'max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)')
if(!$steps.Success -or [int]$steps.Groups[1].Value -ne 15000 -or !$hg.Success -or !$cache.Success -or !$bounds.Success){throw 'Completed step/HG telemetry missing'}
if([int]$hg.Groups[1].Value -ne 30000 -or [int]$hg.Groups[2].Value -ne 15000 -or [int]$hg.Groups[3].Value -ne 15000 -or [int]$hg.Groups[4].Value -ne 30000 -or [int]$cache.Groups[1].Value -ne 15001 -or [int]$cache.Groups[2].Value -ne 14999 -or (N $bounds.Groups[1].Value) -lt 0 -or (N $bounds.Groups[1].Value) -gt .2 -or (N $bounds.Groups[2].Value) -lt 0 -or (N $bounds.Groups[2].Value) -ge .01){throw 'Original HG work/cache/dt/spin guard failed'}
if([string]::IsNullOrWhiteSpace($ReaderBuildReceipt)){throw 'ReviewJob requires explicit -ReaderBuildReceipt for the passed r2 offline helper; failed r1 is not inherited'}
$helperPath=(Get-Item -LiteralPath $ReaderBuildReceipt).FullName
$h=J $helperPath;if($h.status -ne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $h.fixture -ne 'OffReader' -or $h.configuration -ne 'Release' -or !$h.offline_reader_only -or $h.link_object_count -ne 111 -or !$h.exact_link_closure_verified -or $h.source_build.sha256 -ine $m.source_build.sha256){throw 'Explicit current pure-offline reader build required'}
V $h.inputs;V $h.author_files;V $h.tools;V $h.libraries;V $h.objects;V @($h.source_build,$h.program,$h.compile_call,$h.link_call);foreach($v in $h.runtime){V @($v.original,$v.copy)}
$review=Join-Path $outputs ($tag+'_review');$readcall=OwnedCall $h.program @('--compare',(Join-Path $old 'data'),(Join-Path $folder 'data'),$review) ($tag+'_reader') $case $false;$rc=J $readcall.path
if(!$rc.owned_call_exited -or $rc.exit_code -ne 0 -or @($rc.surviving_owned).Count){throw 'Offline typed comparison failed; no completed solver may be rerun'}
$native=J (Join-Path $review 'complete.json');if(!$native.passed -or $native.frames -ne 151 -or $native.native_count -ne 1040 -or $native.original_arrays -ne 15 -or $native.different_bytes -ne 0 -or !$native.all_native_original15_typed_bits_exact -or !$native.actual_time_step_signed_dterror_exact -or !$native.typed_signed_dterror_present_finite_safe -or !$native.dynamic_arrays_and_metadata_absent_both -or !$native.native_set_elastic_finite_no_exclusions -or (N $native.max_signed_dterror_s) -gt 1e-14){throw 'Complete strict native comparison/absence guard failed'}
$rows=@(Import-Csv -LiteralPath (Join-Path $review 'comparison.csv'));if($rows.Count -ne 151){throw 'All151 CSV rows required'};for($p=0;$p -lt 151;$p++){if([int]$rows[$p].part -ne $p -or [int]$rows[$p].arrays -ne 15 -or [int]$rows[$p].native_count -ne 1040 -or [int]$rows[$p].different_bytes -ne 0 -or (N $rows[$p].dterror_s) -gt 1e-14){throw 'Complete CSV row guard failed'}}
V $m.inputs;V $done.files;[void](Control);[void](CurrentBuild)
Save $checkpath ([ordered]@{passed=$true;stage=$tag;input=(E $manifest);source_build=$m.source_build;helper=(E $helperPath);source_run=(E $runpath);solver_call=$r.call;call=$readcall;solver_completion=(E $complete);completion=(E (Join-Path $review 'complete.json'));files=@(E (Join-Path $review 'complete.json');E (Join-Path $review 'comparison.csv'));sole_old_control=$oldname;retained_old_solver_not_rerun=$true;new_actual_solver_calls=1;native_frame_pairs=151;native_count=1040;original_arrays=15;all_native_typed15_and_actual_clock_step_signed_dterror_exact=$true;dynamic_arrays_and_public_metadata_absent=$true;original_HG_guard_preserved=$true;original_physical_safety_inherited_by_exact_native_equality_and_identical_input=$true;physical_acceptance=$false;public_dynamic_ON_acceptance=$false;raw_BI4_cloud_backup_claimed=$false})
