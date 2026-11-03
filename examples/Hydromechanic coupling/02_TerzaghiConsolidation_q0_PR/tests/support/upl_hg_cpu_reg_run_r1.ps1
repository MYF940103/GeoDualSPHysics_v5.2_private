param([Parameter(Mandatory=$true)][ValidateSet('LegacyOff','DynamicXi0')][string]$Case,[switch]$ExecutionAuthorized)
# One same-input, same-backend project-main regression. Old controls are never rerun.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root reviewed execution required'}
$Case=if($Case -ieq 'LegacyOff'){'LegacyOff'}else{'DynamicXi0'}
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$tag='upl_hg_reg_'+$Case+'_r1';$out=Join-Path $tests ('outputs\'+$tag);$record=Join-Path $logs ($tag+'.run.json');$callPath=Join-Path $logs ($tag+'.call.json');$startPath=Join-Path $logs ($tag+'.start.json');$log=Join-Path $logs ($tag+'.log')
function Need([bool]$b,[string]$why){if(!$b){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function V($entries){foreach($e in @($entries)){$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed bound artifact: '+$e.path)}}
function Fresh($paths){foreach($p in @($paths)){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
Fresh @($out,$record,$callPath,$startPath,$log)
$buildE=E (Join-Path $logs 'upl_hg_ReleaseCPU_r1.build.json');$b=J $buildE.path
Need ($b.passed -and $b.stage -ceq 'upl_hg_build_r1' -and $b.configuration -ceq 'ReleaseCPU' -and $b.source_bindings_unchanged -and $b.canonical_programs_unchanged -and $b.runtime_unchanged -and $b.exact_object_basename_closure -and @($b.objects).Count -eq 86 -and @($b.source_snapshot).Count -eq 265) 'Passed current authoritative ReleaseCPU required'
$bindings=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_hg_cpu_reg_r1.json')),$buildE,$b.project_call,$b.program,$b.log,$b.binlog)+@($b.inputs)+@($b.objects)+@($b.canonical_programs_before)
foreach($pair in @($b.source_snapshot)+@($b.documentation_snapshot,$b.case_readme_snapshot)){$bindings+=@($pair.original,$pair.snapshot)}
foreach($pair in $b.runtime){$bindings+=@($pair.original,$pair.copy)}
foreach($cfg in @('DebugCPU','ReleaseCPU')){
  $e=E (Join-Path $logs ('upl_hg_cpu_oracle_'+$cfg+'_r2.run.json'));$r=J $e.path;$c=J $r.call.path;$k=J $r.check.path
  Need ($r.passed -and $r.typed_owned_exit0 -and $r.frozen_inputs_unchanged -and $r.case_count -eq 69 -and $k.passed -and $c.owned_call_exited -and $c.exit_code -is [int] -and $c.exit_code -eq 0) 'Both actual-class oracle configurations must pass first'
  $bindings+=@($e,$r.call,$r.check,$r.helper)
}
$oldE=E (Join-Path $logs $(if($Case -ceq 'LegacyOff'){'upl_case02_flux_legacy_off_r1.run.json'}else{'upl_damp_long_CPU_coarse_r1.run.json'}));$old=J $oldE.path
$oldCallE=if($Case -ceq 'LegacyOff'){$old.owned_exit_record}else{$old.call};$oldCall=J $oldCallE.path
Need ($old.passed -and $oldCall.direct_native_call -and $oldCall.typed_LASTEXITCODE_captured_immediately -and $oldCall.owned_call_exited -and $oldCall.exit_code -is [int] -and $oldCall.exit_code -eq 0 -and !$oldCall.invocation_failure) 'Retained actual CPU control requires typed owned exit0'
$argv=@($oldCall.arguments);$oldOut=$argv[5];$prefix=$argv[4]
if($Case -ceq 'LegacyOff'){
  $steps=2001;$frames=21;$expected=@('-cpu','-ompthreads:1','-stable','-mdbc',$prefix,$oldOut,'-dirdataout','data','-svres','-svextraparts:1','-nsteps:2001')
  Need ($prefix -ieq (Join-Path $tests 'outputs\upl_case02_legacy_off_r1_seed\upl_case02_legacy_off_r1') -and $oldOut -ieq (Join-Path $tests 'outputs\upl_case02_flux_legacy_off_r1')) 'Retained legacy input/output identity differs'
}else{
  $steps=262144;$frames=1469;$expected=@('-cpu','-ompthreads:8','-stable','-mdbc_freeslip',$prefix,$oldOut,'-dirdataout','data','-svres','-nsteps:262144')
  Need ($prefix -ieq (Join-Path $tests 'outputs\upl_damp_long_seed_r1\upl_damp_long_coarse_r1') -and $oldOut -ieq (Join-Path $tests 'outputs\upl_damp_long_CPU_coarse_r1')) 'Retained dynamic input/output identity differs'
}
Need (($argv -join [char]0) -ceq ($expected -join [char]0)) 'Retained argument vector differs; only output/program changes are permitted'
$seed=@((E ($prefix+'.xml')),(E ($prefix+'.bi4')),(E ($prefix+'_Normals.nbi4')))
$oldSeed=if($Case -ceq 'LegacyOff'){$old.prepared_inputs}else{$old.inputs}
foreach($e in $seed){$same=@($oldSeed|Where-Object{$_.path -ieq $e.path -and $_.bytes -eq $e.bytes -and $_.sha256 -ieq $e.sha256});Need ($same.Count -gt 0) 'Current seed must match a frozen old-run input binding'}
$bindings+=@($oldE,$oldCallE,$oldCall.program)+$seed+@($old.files)
$argv[5]=$out;V $bindings
# The separately owned GPU zero-step component may continue. Reject a second CPU solver.
$cpu=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'DualSPHysics%CPU%.exe'");Need ($cpu.Count -eq 0) 'A CPU solver is already active; no duplicate launch'
$owner=Get-CimInstance Win32_Process -Filter ('ProcessId='+$PID)
Save $startPath ([ordered]@{stage='upl_hg_cpu_reg_start_r1';case=$Case;utc=[DateTime]::UtcNow.ToString('o');owner_pid=$PID;owner_creation_utc=$owner.CreationDate.ToUniversalTime().ToString('o');owner_script=(E $PSCommandPath);program=$b.program;arguments=$argv;retained_control=$oldE;physical_acceptance=$false})
$bindings+=@(E $startPath);$start=[DateTime]::UtcNow.ToString('o');$code=$null;$why=$null;$prior=$ErrorActionPreference
Push-Location $src
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $b.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$why=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
Save $callPath ([ordered]@{program=$b.program;arguments=$argv;working_directory=$src;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$why;log=(E $log);actual_solver_call=$true;public_project_main=$true;restart=$false;physical_acceptance=$false})
$failure=$why;$unchanged=$false;$files=@();$actualFrames=0;$actualSteps=$null;$finished=$false;$hg=$null
try{
  Need ($code -is [int] -and $code -eq 0 -and !$why) 'Actual project program did not return typed exit0'
  $text=[IO.File]::ReadAllText((Join-Path $out 'Run.out'));$s=[regex]::Match($text,'Steps of simulation[.]+:\s*(\d+)');$actualSteps=if($s.Success){[int]$s.Groups[1].Value}else{$null}
  $finished=$text.Contains('Finished execution (code=0)');Need ($finished -and $actualSteps -eq $steps -and $text -match 'Excluded particles[.]+:\s*0(?:\s|$)') 'Finished/step/no-exclusion guard failed'
  $parts=@(Get-ChildItem -LiteralPath (Join-Path $out 'data') -File -Filter 'Part_*.bi4');$actualFrames=$parts.Count;$wanted=@(0..($frames-1)|ForEach-Object{'Part_{0:D4}.bi4' -f $_})
  Need ($actualFrames -eq $frames -and !(Compare-Object ($parts.Name|Sort-Object) ($wanted|Sort-Object))) 'Native frame membership differs'
  if($Case -ceq 'LegacyOff'){
    Need ($text -match 'SoilHourglassXi: 0\.1\s' -and $text -match 'SoilDampingCoef=0\.04(?:\s|$)' -and $text.Contains('SoilBoundaryDerivativeSPR="MirroredWallDerivatives"')) 'Legacy positive auxiliaries differ'
    $f=[regex]::Match($text,'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)');$c=[regex]::Match($text,'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)');$t=[regex]::Match($text,'max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)')
    Need ($f.Success -and $c.Success -and $t.Success -and [int]$f.Groups[1].Value -eq 4002 -and [int]$f.Groups[2].Value -eq 2001 -and [int]$f.Groups[3].Value -eq 2001 -and [int]$f.Groups[4].Value -eq 4002 -and [int]$c.Groups[1].Value -eq 2002 -and [int]$c.Groups[2].Value -eq 2000) 'Original HG call/cache counts differ'
    $tau=[double]::Parse($t.Groups[1].Value,[Globalization.CultureInfo]::InvariantCulture);$spin=[double]::Parse($t.Groups[2].Value,[Globalization.CultureInfo]::InvariantCulture);Need ($tau -ge 0 -and $tau -le .2 -and $spin -ge 0 -and $spin -lt .01) 'Original HG dt/spin guard failed';$hg=@{forcecalls=4002;ratecalls=4002;calculations=2002;reuses=2000;max_dt_tau=$tau;spin=$spin}
  }else{Need (!$text.Contains('SoilHourglass: forcecalls=')) 'xi0 unexpectedly executed HG'}
}catch{$failure=$_.Exception.Message}
try{V $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|Sort-Object FullName|ForEach-Object{E $_.FullName})}
$passed=(!$failure -and $unchanged -and $finished -and $actualFrames -eq $frames)
Save $record ([ordered]@{stage='upl_hg_cpu_reg_run_r1';passed=$passed;case=$Case;source_build=$buildE;program=$b.program;call=(E $callPath);retained_control=$oldE;retained_call=$oldCallE;arguments=$argv;input_prefix=$prefix;steps=$actualSteps;native_frames=$actualFrames;HG=$hg;inputs=$bindings;files=$files;frozen_inputs_control_canonical_unchanged=$unchanged;old_control_rerun=$false;raw_bit_comparison_pending=$true;all22_bit_exact_claimed=$false;physical_acceptance=$false;failure=$failure})
if(!$passed){throw ('Regression solve/check rejected; preserve and diagnose without duplicate solve: '+$record)};Write-Output ('New regression solve sealed; raw native comparison remains: '+$record)
