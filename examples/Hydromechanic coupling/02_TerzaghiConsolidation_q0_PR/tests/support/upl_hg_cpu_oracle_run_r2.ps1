param([Parameter(Mandatory=$true)][ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration,[switch]$ExecutionAuthorized)
# One short actual-class call; no physical solver or public enablement.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root reviewed execution required'}
$Configuration=if($Configuration -ieq 'DebugCPU'){'DebugCPU'}else{'ReleaseCPU'}
$tests=Split-Path -Parent $PSScriptRoot;$tag='upl_hg_cpu_oracle_'+$Configuration+'_r2';$logs=Join-Path $tests 'logs'
$callPath=Join-Path $logs ($tag+'.call.json');$runPath=Join-Path $logs ($tag+'.run.json');$check=Join-Path $logs ($tag+'.check.json');$log=Join-Path $logs ($tag+'.run.log')
function Need([bool]$b,[string]$why){if(!$b){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function V($entries){foreach($e in @($entries)){$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed bound artifact: '+$e.path)}}
function Fresh($paths){foreach($p in @($paths)){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
Fresh @($callPath,$runPath,$check,$log)
$helperE=E (Join-Path $logs ($tag+'.helper.json'));$h=J $helperE.path
Need ($h.passed -and $h.stage -ceq 'upl_hg_cpu_oracle_build_r2' -and $h.configuration -ceq $Configuration -and $h.object_count -eq 85 -and $h.frozen_inputs_unchanged -and $h.actual_project_classes_no_stubs -and !$h.program_run -and !$h.solver_run) 'Passed current actual-class build required'
$bindings=@($helperE,$h.program,$h.helper_object,$h.compile_call,$h.link_call,$h.compiler_dependency_record,(E $PSCommandPath),(E (Join-Path $tests 'notes\upl_hg_cpu_oracle_run_r2.json')))+@($h.inputs)+@($h.actual_includes)+@($h.project_objects)
foreach($pair in $h.runtime){$bindings+=@($pair.original,$pair.copy)}
if($Configuration -ceq 'ReleaseCPU'){$debugE=E (Join-Path $logs 'upl_hg_cpu_oracle_DebugCPU_r2.run.json');$d=J $debugE.path;Need ($d.passed -and $d.typed_owned_exit0 -and $d.physical_acceptance -eq $false) 'Reviewed Debug oracle required first';$bindings+=@($debugE,$d.call,$d.check)}
V $bindings;$argv=@('--json',$check);$start=[DateTime]::UtcNow.ToString('o');$code=$null;$why=$null;$prior=$ErrorActionPreference;$working=Split-Path -Parent $h.program.path
Push-Location $working
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $h.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$why=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
Save $callPath ([ordered]@{program=$h.program;arguments=$argv;working_directory=$working;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$why;log=(E $log);solver_run=$false})
$failure=$why;$unchanged=$false;$result=$null;$checked=$null
try{
  V $bindings;$unchanged=$true
  Need ($code -is [int] -and $code -eq 0 -and !$why) 'Actual oracle returned no typed exit0'
  $checked=E $check;$result=J $check
  Need ($result.passed -and !$result.reason -and $result.status -ceq 'actual_CPU_operator_verified_not_coupled_acceptance' -and $result.physical_acceptance -eq $false -and $result.solver_run -eq $false -and @($result.passed_cases).Count -eq 69) 'Oracle case completion differs'
  foreach($metric in $result.metrics.PSObject.Properties){$m=$metric.Value;Need ($m.checks -gt 0 -and ![double]::IsNaN([double]$m.max_error_over_limit) -and ![double]::IsInfinity([double]$m.max_error_over_limit) -and $m.max_error_over_limit -le 1) ('Fixed component gate failed: '+$metric.Name)}
}catch{$failure=$_.Exception.Message}
$passed=(!$failure -and $unchanged -and $null -ne $result)
Save $runPath ([ordered]@{stage='upl_hg_cpu_oracle_run_r2';passed=$passed;configuration=$Configuration;helper=$helperE;call=(E $callPath);check=$checked;inputs=$bindings;typed_owned_exit0=($code -is [int] -and $code -eq 0 -and !$why);frozen_inputs_unchanged=$unchanged;failure=$failure;fixed_gate_values_changed=$false;actual_project_classes_no_stubs=$true;case_count=$(if($result){@($result.passed_cases).Count}else{0});solver_run=$false;public_dynamic_HG_enabled=$false;physical_acceptance=$false})
if(!$passed){throw ('Oracle rejected; inspect retained check/call, no automatic rerun: '+$runPath)};Write-Output ('Actual CPU oracle passed; coupled gates remain: '+$runPath)
