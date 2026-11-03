param([Parameter(Mandatory=$true)][ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration,[switch]$ExecutionAuthorized)
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root reviewed single-call execution required'}
$Configuration=if($Configuration -ieq 'DebugCPU'){'DebugCPU'}else{'ReleaseCPU'}
$tests=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $tests 'logs';$tag='upl_hg_cpu_legacy_'+$Configuration+'_r1'
$callPath=Join-Path $logs ($tag+'.call.json');$check=Join-Path $logs ($tag+'.check.json');$record=Join-Path $logs ($tag+'.run.json');$log=Join-Path $logs ($tag+'.run.log')
function Need([bool]$b,[string]$why){if(!$b){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function V($entries){foreach($e in @($entries)){$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed bound artifact: '+$e.path)}}
function Fresh($paths){foreach($p in @($paths)){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
Fresh @($callPath,$check,$record,$log)
$helperE=E (Join-Path $logs ($tag+'.helper.json'));$h=J $helperE.path
Need ($h.passed -and $h.stage -ceq 'upl_hg_cpu_legacy_build_r1' -and $h.configuration -ceq $Configuration -and $h.link_object_count -eq 87 -and $h.exact_link_object_closure_verified -and $h.frozen_inputs_unchanged -and $h.actual_project_classes_no_stubs) 'Passed actual legacy helper required'
$bindings=@($helperE,$h.program,$h.link_call,(E $PSCommandPath),(E (Join-Path $tests 'notes\upl_hg_cpu_legacy_run_r1.json')))+@($h.inputs)+@($h.actual_includes)+@($h.project_objects)+@($h.helper_objects)+@($h.compile_calls)+@($h.compiler_dependency_records)
foreach($pair in $h.runtime){$bindings+=@($pair.original,$pair.copy)}
if($Configuration -ceq 'ReleaseCPU'){$de=E (Join-Path $logs 'upl_hg_cpu_legacy_DebugCPU_r1.run.json');$d=J $de.path;Need ($d.passed -and $d.typed_owned_exit0 -and $d.all_shared_fields_0ULP) 'Actual Debug legacy regression required before Release';$bindings+=@($de,$d.call,$d.check)}
V $bindings;$argv=@($check,'20');$working=Split-Path -Parent $h.program.path;$start=[DateTime]::UtcNow.ToString('o');$code=$null;$why=$null;$prior=$ErrorActionPreference
Push-Location $working
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $h.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$why=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
Save $callPath ([ordered]@{program=$h.program;arguments=$argv;working_directory=$working;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$why;log=(E $log);solver_run=$false})
$failure=$why;$unchanged=$false;$checked=$null;$k=$null
try{
  V $bindings;$unchanged=$true;Need ($code -is [int] -and $code -eq 0 -and !$why) 'Actual legacy fixture did not return typed exit0'
  $checked=E $check;$k=J $check
  Need ($k.passed -and $k.stage -ceq 'upl_hg_cpu_legacy_r1' -and $k.required_max_ulp -eq 0 -and $k.differing_field_bytes -eq 0 -and $k.scalar_bit_checks -gt 0 -and $k.actual_JObject_JException -and !$k.JObject_stub -and $k.actual_guard_exceptions -eq 24 -and @($k.scenarios).Count -eq 11 -and $k.repeat_per_batch -eq 20 -and $k.current_cache_counters_independently_verified -and !$k.solver_run -and !$k.physical_acceptance) 'Fixed legacy bit/guard/cache gate failed'
}catch{$failure=$_.Exception.Message}
$passed=(!$failure -and $unchanged -and $null -ne $k)
Save $record ([ordered]@{stage='upl_hg_cpu_legacy_run_r1';passed=$passed;configuration=$Configuration;helper=$helperE;call=(E $callPath);check=$checked;inputs=$bindings;typed_owned_exit0=($code -is [int] -and $code -eq 0 -and !$why);frozen_inputs_unchanged=$unchanged;all_shared_fields_0ULP=$passed;fixed_guards_and_cache_passed=$passed;timing_is_not_controlled_benchmark=$true;solver_run=$false;physical_acceptance=$false;failure=$failure})
if(!$passed){throw ('Legacy fixture rejected; retain evidence: '+$record)};Write-Output ('Actual default-legacy class0ULP passed: '+$record)
