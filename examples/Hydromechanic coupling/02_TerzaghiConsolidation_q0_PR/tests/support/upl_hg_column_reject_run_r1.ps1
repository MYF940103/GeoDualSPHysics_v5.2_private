param([Parameter(Mandatory=$true)][ValidateSet('variable_k','visco_time','no_slip')][string]$Case,[switch]$ExecutionAuthorized)
# One expected-rejection entry check, not a physical trajectory or following-job launcher.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root reviewed negative-entry execution required'}
$Case=$Case.ToLowerInvariant();$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src';$logs=Join-Path $tests 'logs';$tag='upl_hg_column_reject_DebugCPU_'+$Case+'_r1'
function Need([bool]$b,[string]$why){if(!$b){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function V($entries){foreach($e in @($entries)){$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed bound artifact: '+$e.path)}}
function Fresh($paths){foreach($p in @($paths)){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
$manifestE=E (Join-Path $logs 'upl_hg_column_reject_r1.inputs.json');$m=J $manifestE.path
Need ($m.stage -ceq 'upl_hg_column_reject_prepare_r1' -and $m.prepared -and $m.preparation_complete -and !$m.negative_tests_executed) 'Fresh prepared negative entries required'
$rows=@($m.jobs|Where-Object{$_.case -ceq $Case});Need ($rows.Count -eq 1) 'One declared negative job required';$job=$rows[0]
$out=[string]$job.proposed_output;$callPath=[string]$job.proposed_logs.call;$record=[string]$job.proposed_logs.run;$log=[string]$job.proposed_logs.console
Need ($out -ieq (Join-Path $tests ('outputs\'+$tag)) -and $callPath -ieq (Join-Path $logs ($tag+'.call.json')) -and $record -ieq (Join-Path $logs ($tag+'.run.json'))) 'Declared output identity differs'
Fresh @($out,$callPath,$record,$log)
$buildE=E (Join-Path $logs 'upl_hg_column_DebugCPU_r1.build.json');$b=J $buildE.path
Need ($b.passed -and $b.stage -ceq 'upl_hg_column_build_r1' -and $b.configuration -ceq 'DebugCPU' -and $b.exact_object_basename_closure -and $b.source_bindings_unchanged -and $b.canonical_programs_unchanged -and $b.runtime_unchanged) 'Current actual DebugCPU build required'
$bindings=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_hg_column_reject_run_r1.json')),$manifestE,$buildE,$b.program,$b.project_call,$b.log,$b.binlog,$job.configuration,$job.runtime,$job.initial_BI4,$job.normals)+@($m.inputs)+@($b.inputs)+@($b.objects)+@($b.canonical_programs_before)
if($job.viscosity_schedule){$bindings+=@($job.viscosity_schedule)}
foreach($pair in @($b.source_snapshot)+@($b.documentation_snapshot,$b.case_readme_snapshot)){$bindings+=@($pair.original,$pair.snapshot)}
foreach($pair in $b.runtime){$bindings+=@($pair.original,$pair.copy)}
V $bindings;$active=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'DualSPHysics%CPU%.exe'");Need ($active.Count -eq 0) 'Another actual CPU program is active'
$argv=@($job.solver_arguments);Need ($argv.Count -eq 10 -and $argv[0] -ceq '-cpu' -and $argv[4] -ceq $job.input_prefix -and $argv[5] -ceq $out -and $argv[9] -ceq '-nsteps:2') 'Exact negative program arguments required'
$start=[DateTime]::UtcNow.ToString('o');$code=$null;$why=$null;$prior=$ErrorActionPreference;[IO.File]::WriteAllBytes($log,[byte[]]@());Push-Location $src
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $b.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$why=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
Save $callPath ([ordered]@{program=$b.program;arguments=$argv;working_directory=$src;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$why;log=(E $log);expected_rejection=$true;physical_acceptance=$false})
$failure=$why;$unchanged=$false;$expectedMessage=$false;$noAdvanced=$false;$files=@()
try{
  Need ($code -is [int] -and $code -ne 0 -and !$why) 'Expected actual owned nonzero rejection missing'
  $text=[IO.File]::ReadAllText($log);$expectedMessage=$text.Contains('Text: '+[string]$job.expected_error_substring)
  Need ($expectedMessage -and !$text.Contains('Finished execution (code=0)')) 'A different error or successful program is not a passed scope rejection'
  $parts=@();if(Test-Path -LiteralPath (Join-Path $out 'data')){$parts=@(Get-ChildItem -LiteralPath (Join-Path $out 'data') -Filter 'Part_*.bi4' -File)}
  $advanced=@($parts|Where-Object{$_.Name -cne 'Part_0000.bi4'});$noAdvanced=($advanced.Count -eq 0 -and !$text.Contains('[Initialising simulation'))
  Need $noAdvanced 'Rejected entry reached a simulation loop or saved stepped PART'
}catch{$failure=$_.Exception.Message}
try{V $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -File -Recurse|Sort-Object FullName|ForEach-Object{E $_.FullName})}
$passed=(!$failure -and $unchanged -and $expectedMessage -and $noAdvanced)
Save $record ([ordered]@{stage='upl_hg_column_reject_run_r1';passed=$passed;case=$Case;source_build=$buildE;manifest=$manifestE;job=$job;call=(E $callPath);inputs=$bindings;files=$files;typed_owned_nonzero_expected=($code -is [int] -and $code -ne 0);exact_guard_message_observed=$expectedMessage;no_advanced_PART_or_loop=$noAdvanced;raw_step_count_not_fabricated=$true;frozen_inputs_and_canonical_unchanged=$unchanged;failure=$failure;GPU_program_invoked=$false;physical_acceptance=$false})
if(!$passed){throw ('Expected-rejection check failed; preserve actual call: '+$record)};Write-Output ('Actual expected scope rejection verified: '+$record)
