param(
  [Parameter(Mandatory=$true)][ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration,
  [Parameter(Mandatory=$true)][ValidateSet('smoke','short_c','short_h','coarse','half')][string]$Window,
  [string]$Admission,
  [switch]$ExecutionAuthorized
)
# One manifest-selected current CPU project-main run only. Never build, decode or queue another job.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root full-read and explicit one-job execution required'}
$Configuration=if($Configuration -ieq 'DebugCPU'){'DebugCPU'}else{'ReleaseCPU'};$Window=$Window.ToLowerInvariant()
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$tag='upl_hg_column_'+$Configuration+'_'+$Window+'_r1';$out=Join-Path $tests ('outputs\'+$tag)
$record=Join-Path $logs ($tag+'.run.json');$callPath=Join-Path $logs ($tag+'.call.json');$startPath=Join-Path $logs ($tag+'.start.json');$log=Join-Path $logs ($tag+'.log')
function Need([bool]$b,[string]$why){if(!$b){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function V($entries){foreach($e in @($entries)){Need ($e.path -and $e.sha256 -and $null -ne $e.bytes) 'Incomplete bound identity';$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed bound artifact: '+$e.path)}}
function Fresh($paths){foreach($p in @($paths)){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 22)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function N([string]$s){$v=[double]::Parse($s,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture);Need (![double]::IsNaN($v) -and ![double]::IsInfinity($v)) 'Nonfinite actual diagnostic';return $v}
function Typed($e){
  V @($e);$c=J $e.path
  Need ($c.direct_native_call -and $c.typed_LASTEXITCODE_captured_immediately -and $c.owned_call_exited -and $c.exit_code -is [int] -and $c.exit_code -eq 0 -and !$c.invocation_failure) 'Actual owned typed exit0 required'
  V @($c.program);if($c.log){V @($c.log)};return $c
}
Fresh @($out,$record,$callPath,$startPath,$log)
$manifestE=E (Join-Path $logs 'upl_hg_column_r1.inputs.json');$m=J $manifestE.path
Need ($m.stage -ceq 'upl_hg_column_prepare_r1' -and $m.passed -and $m.prepared -and $m.input_sources_unchanged -and @($m.variants).Count -eq 3 -and @($m.jobs).Count -eq 6 -and @($m.files).Count -eq 12 -and !$m.solver_reader_or_build_invoked -and !$m.physical_acceptance) 'Successful retained-runtime HG-only preparation required'
$rows=@($m.jobs|Where-Object{$_.tag -ceq $tag -and $_.configuration -ceq $Configuration -and $_.window -ceq $Window});Need ($rows.Count -eq 1) 'Exactly one declared configuration/window job required'
$job=$rows[0];$variantRows=@($m.variants|Where-Object{$_.window -ceq $job.input_variant});Need ($variantRows.Count -eq 1) 'One prepared input variant required';$variant=$variantRows[0]
$factor=if($job.input_variant -ceq 'half'){2}else{1};$dt=[Math]::Pow(2,-19)/$factor
$steps=if($Window -ceq 'smoke'){2}elseif($Window -ceq 'short_c'){13120}elseif($Window -ceq 'short_h'){26240}elseif($Window -ceq 'coarse'){262144}else{524288}
$frames=if($Window -ceq 'smoke'){3}elseif($Window.StartsWith('short_')){458}else{1469}
Need ($job.threads -eq 8 -and $job.steps -eq $steps -and $job.expected_samples -eq $frames -and @($job.saved_clock_table).Count -eq $frames -and $job.dt_s -eq $dt -and $job.end_s -eq $steps*$dt -and $job.expected_native_total_arrays -eq 22 -and $job.expected_total_native_count -eq 1040 -and $job.output_directory -ieq $out -and $job.input_prefix -ieq $variant.input_prefix -and $variant.runtime.path -ieq ($job.input_prefix+'.xml') -and $variant.inverse_runtime_bytes_exact -and $variant.original_initial_particle_fields_unchanged) 'Declared CPU8 native22 clock/input scope differs'
Need ($job.saved_clock_table[0].completed_steps -eq 0 -and $job.saved_clock_table[$frames-1].completed_steps -eq $steps) 'Declared initial/terminal saved steps differ'
$expected=@('-cpu','-ompthreads:8','-stable','-mdbc_freeslip',$job.input_prefix,$out,'-dirdataout','data','-svres',('-nsteps:'+$steps));$argv=@($job.arguments)
Need (($argv -join [char]0) -ceq ($expected -join [char]0)) 'Only exact prepared project-main argv is admitted'
$counterExpect=@{forcecalls=(2*$steps);ratecalls=(2*$steps);predictorupdates=$steps;correctorupdates=$steps;ratecalculations=($steps+1);ratecachehits=($steps-1)}
foreach($key in $counterExpect.Keys){Need ($job.expected_HG_counters.$key -eq $counterExpect[$key]) 'Prepared HG counter declaration differs'}
$buildE=E (Join-Path $logs ('upl_hg_column_'+$Configuration+'_r1.build.json'));$b=J $buildE.path
Need ($b.passed -and $b.stage -ceq 'upl_hg_column_build_r1' -and $b.configuration -ceq $Configuration -and $b.platform -ceq 'x64' -and $b.source_bindings_unchanged -and $b.canonical_programs_unchanged -and $b.runtime_unchanged -and $b.exact_object_basename_closure -and $b.objects_include_project_main -and @($b.objects).Count -eq 86 -and @($b.source_snapshot).Count -eq 265 -and @($b.runtime).Count -eq 4 -and @($b.canonical_programs_before).Count -eq 7 -and !$b.canonical_program_installed) 'Passed current isolated authoritative CPU86/source265/runtime4/canonical7 build required'
$project=Typed $b.project_call
Need ($project.program.sha256 -ieq $b.build_tool.sha256 -and ($project.arguments -join [char]0) -ceq ($b.arguments -join [char]0)) 'Actual project build tool/argument vector differs'
$bindings=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_hg_column_run_r2.json')),$manifestE,$buildE,$b.project_call,$b.build_tool,$b.program,$b.log,$b.binlog)+@($m.inputs)+@($m.files)+@($b.inputs)+@($b.tools)+@($b.libraries)+@($b.objects)+@($b.compile_sources)+@($b.canonical_programs_before)+@($b.runtime_before)
foreach($pair in @($b.source_snapshot)+@($b.documentation_snapshot,$b.case_readme_snapshot)){$bindings+=@($pair.original,$pair.snapshot)}
foreach($pair in $b.runtime){$bindings+=@($pair.original,$pair.copy)}
foreach($pair in $b.compiler_linker_command_tlogs){$bindings+=@($pair.original,$pair.snapshot)}
$prerequisites=@();$admissionE=$null
function NativeGate([string]$priorTag){
  $ne=E (Join-Path $logs ($priorTag+'.native_r2.json'));$n=J $ne.path;$re=E (Join-Path $logs ($priorTag+'.run.json'));$r=J $re.path
  Need ($n.passed -and !$n.physical_acceptance -and $n.source_run.path -ieq $re.path -and $n.source_run.bytes -eq $re.bytes -and $n.source_run.sha256 -ieq $re.sha256) 'Passed preceding actual native owner must bind the exact preceding run'
  Need ($r.passed -and $r.stage -in @('upl_hg_column_run_r1','upl_hg_column_run_r2') -and $r.job.tag -ceq $priorTag -and $r.backend -ceq 'CPU' -and $r.bindings_unchanged -and !$r.physical_acceptance) 'Preceding current-column run is not a passed native prerequisite'
  [void](Typed $r.call);V @($r.run_out,$r.source_build,$r.program)
  $entries=@($ne,$re,$r.call,$r.run_out,$r.source_build,$r.program);if($n.reader_call){[void](Typed $n.reader_call);$entries+=@($n.reader_call)};if($n.completion){V @($n.completion);$entries+=@($n.completion)}
  return [ordered]@{tag=$priorTag;native=$ne;source_run=$re;bindings=$entries}
}
if($Configuration -ceq 'ReleaseCPU'){
  $priorTag=if($Window -ceq 'smoke'){'upl_hg_column_DebugCPU_smoke_r1'}elseif($Window -ceq 'short_c'){'upl_hg_column_ReleaseCPU_smoke_r1'}elseif($Window -ceq 'short_h'){'upl_hg_column_ReleaseCPU_short_c_r1'}else{$null}
  if($priorTag){$p=NativeGate $priorTag;$prerequisites+=@($p);$bindings+=@($p.bindings)}
  if($Window -ceq 'coarse' -or $Window -ceq 'half'){
    foreach($priorTag in @('upl_hg_column_ReleaseCPU_short_c_r1','upl_hg_column_ReleaseCPU_short_h_r1')){$p=NativeGate $priorTag;$prerequisites+=@($p);$bindings+=@($p.bindings)}
    Need (![string]::IsNullOrWhiteSpace($Admission)) 'Full .5s job requires the separate root short-physical-review admission path'
    $admissionE=E $Admission;$a=J $admissionE.path
    Need ($a.stage -ceq 'upl_hg_column_admission_r1' -and $a.passed -and @($a.allowed_jobs) -ccontains $tag -and $a.physical_acceptance -eq $false -and @($a.inputs).Count -gt 0) 'Separate passed root short-review admission must allow this exact full job'
    V $a.inputs;$bindings+=@($admissionE)+@($a.inputs)
  }
}
function VerifyAll{
  V $bindings
  foreach($pair in @($b.source_snapshot)+@($b.documentation_snapshot,$b.case_readme_snapshot)){Need ($pair.original.bytes -eq $pair.snapshot.bytes -and $pair.original.sha256 -ieq $pair.snapshot.sha256) 'Current source/document snapshot pair differs'}
  $current=@(Get-ChildItem -LiteralPath (Join-Path $src 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|ForEach-Object{$_.FullName})
  Need ($current.Count -eq 265 -and !(Compare-Object ($current|Sort-Object) (@($b.source_snapshot|ForEach-Object{$_.original.path})|Sort-Object))) 'Current265 source/header membership differs'
}
VerifyAll
# Permit the separately owned frozen GPU component; reject another actual CPU solver.
$cpu=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'DualSPHysics%CPU%.exe'");Need ($cpu.Count -eq 0) 'An actual CPU solver is active; no duplicate CPU launch'
$owner=Get-CimInstance Win32_Process -Filter ('ProcessId='+$PID);Need ($null -ne $owner -and $null -ne $owner.CreationDate) 'Current owner PID/creation identity required'
Save $startPath ([ordered]@{stage='upl_hg_column_start_r1';tag=$tag;configuration=$Configuration;window=$Window;utc=[DateTime]::UtcNow.ToString('o');owner_pid=$PID;owner_creation_utc=$owner.CreationDate.ToUniversalTime().ToString('o');owner_script=(E $PSCommandPath);program=$b.program;arguments=$argv;input_manifest=$manifestE;source_build=$buildE;job=$job;admission=$admissionE;GPU_component_allowed_to_continue=$true;physical_acceptance=$false})
$startE=E $startPath;$bindings+=@($startE);VerifyAll
$start=[DateTime]::UtcNow.ToString('o');$code=$null;$why=$null;$prior=$ErrorActionPreference;[IO.File]::WriteAllBytes($log,[byte[]]@());Push-Location $src
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $b.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$why=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
# Seal the actual typed result before reading Run.out or inspecting any PART.
Save $callPath ([ordered]@{program=$b.program;target_program=$b.program;arguments=$argv;target_arguments=$argv;working_directory=$src;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$why;log=(E $log);tag=$tag;configuration=$Configuration;window=$Window;start_record=$startE;actual_solver_call=$true;public_project_main=$true;fixture_or_Run_override=$false;direct_target_call=$true;restart=$false;physical_acceptance=$false})
$failure=$why;$unchanged=$false;$files=@();$actualFrames=0;$actualSteps=$null;$finished=$false;$hg=$null;$runOut=$null
try{
  if(Test-Path -LiteralPath (Join-Path $out 'Run.out')){$runOut=E (Join-Path $out 'Run.out')}
  Need ($code -is [int] -and $code -eq 0 -and !$why) 'Actual project-main program did not return typed exit0'
  Need ($null -ne $runOut) 'Actual Run.out is missing';$text=[IO.File]::ReadAllText($runOut.path)
  $s=[regex]::Match($text,'Steps of simulation[.]+:\s*(\d+)');$actualSteps=if($s.Success){[int]$s.Groups[1].Value}else{$null};$finished=$text.Contains('Finished execution (code=0)')
  Need ($finished -and $actualSteps -eq $steps -and $text -match 'OpenMP\(Threads:8\)' -and $text -match 'Excluded particles[.]+:\s*0(?:\s|$)') 'Actual normal CPU8 finish/step/no-exclusion gate failed'
  Need ($text -match 'SoilHourglassXi: 0\.1\s' -and $text.Contains('SoilDamping="BuiFukagawa2013"') -and $text -match 'SoilDampingCoef=0\.02(?:\s|$)' -and $text.Contains('SoilBoundaryDerivativeSPR="None"')) 'Prepared HG/eta/SPR configuration differs'
  $f=[regex]::Match($text,'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)');$c=[regex]::Match($text,'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)')
  Need ($f.Success -and $c.Success -and [int]$f.Groups[1].Value -eq 2*$steps -and [int]$f.Groups[2].Value -eq $steps -and [int]$f.Groups[3].Value -eq $steps -and [int]$f.Groups[4].Value -eq 2*$steps -and [int]$c.Groups[1].Value -eq $steps+1 -and [int]$c.Groups[2].Value -eq $steps-1) 'Actual HG full-stage/cache counts differ'
  $d=[regex]::Match($text,'SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)')
  Need $d.Success 'Actual single-J reference-force/current-inertia diagnostic is missing'
  $net=N $d.Groups[1].Value;$actualNet=N $d.Groups[2].Value;$tau=N $d.Groups[3].Value;$spin=N $d.Groups[4].Value
  Need ($net -ge 0 -and $actualNet -ge 0 -and $tau -ge 0 -and $tau -le .2 -and $spin -ge 0 -and $spin -lt .01) 'Original actual HG finite/dt/tau/spin safety gate failed'
  $hg=@{forcecalls=2*$steps;predictorupdates=$steps;correctorupdates=$steps;ratecalls=2*$steps;ratecalculations=$steps+1;ratecachehits=$steps-1;max_reference_history_net_force=$net;max_actual_float_add_net_force=$actualNet;max_dt_over_tau=$tau;spinbound=$spin;reference_history_is_Q_over_M0=$true;actual_inertia_is_current_mi=$true}
  $parts=@(Get-ChildItem -LiteralPath (Join-Path $out 'data') -File -Filter 'Part_*.bi4');$actualFrames=$parts.Count;$wanted=@(0..($frames-1)|ForEach-Object{'Part_{0:D4}.bi4' -f $_})
  Need ($actualFrames -eq $frames -and !(Compare-Object ($parts.Name|Sort-Object) ($wanted|Sort-Object))) 'Actual native PART sequence differs from declared3/458/1469 window'
}catch{$failure=$_.Exception.Message}
if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|Sort-Object FullName|ForEach-Object{E $_.FullName})}
try{VerifyAll;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$passed=(!$failure -and $unchanged -and $finished -and $actualFrames -eq $frames -and $null -ne $hg)
Save $record ([ordered]@{stage='upl_hg_column_run_r2';passed=$passed;tag=$tag;backend='CPU';configuration=$Configuration;window=$Window;threads=8;job=$job;input_manifest=$manifestE;source_build=$buildE;program=$b.program;call=(E $callPath);start_record=$startE;run_out=$runOut;arguments=$argv;input_prefix=$job.input_prefix;output_directory=$out;steps=$actualSteps;native_frames=$actualFrames;HG=$hg;prerequisites=$prerequisites;admission=$admissionE;inputs=$bindings;files=$files;bindings_unchanged=$unchanged;source_bindings_unchanged=$unchanged;public_project_main=$true;fixture_or_Run_override=$false;old_control_rerun=$false;independent_GPU_component_rearmed=$false;native_decoder_invoked=$false;all22_native_fields_review_pending=$true;actual_native_clocks_review_pending=$true;HG_ON_vs_OFF_bit_identity_claimed=$false;physical_acceptance=$false;failure=$failure})
if(!$passed){throw ('Column actual run/check rejected; preserve without duplicate solve: '+$record)};Write-Output ('One actual CPU HG column run sealed; native review remains: '+$record)
