param([Parameter(Mandatory=$true)][ValidateSet('Legacy','Dynamic')][string]$Case,[switch]$ExecutionAuthorized)
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root reviewed pure-reader execution required'}
$Case=if($Case -ieq 'Legacy'){'Legacy'}else{'Dynamic'};$tests=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $tests 'logs';$tag='upl_hg_raw_'+$Case+'_r1'
$out=Join-Path $tests ('outputs\'+$tag);$callPath=Join-Path $logs ($tag+'.call.json');$record=Join-Path $logs ($tag+'.check.json');$log=Join-Path $logs ($tag+'.log')
function Need([bool]$b,[string]$why){if(!$b){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function V($entries){foreach($e in @($entries)){$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed bound artifact: '+$e.path)}}
function Fresh($paths){foreach($p in @($paths)){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
Fresh @($out,$callPath,$record,$log)
$helperE=E (Join-Path $logs 'upl_hg_raw_compare_ReleaseCPU_r1.helper.json');$h=J $helperE.path
Need ($h.passed -and $h.stage -ceq 'upl_hg_raw_compare_build_r1' -and $h.object_count -eq 85 -and $h.frozen_inputs_unchanged -and $h.actual_project_classes_no_stubs -and !$h.solver_run) 'Passed pure native comparator build required'
$newCase=if($Case -ceq 'Legacy'){'LegacyOff'}else{'DynamicXi0'}
$newE=E (Join-Path $logs ('upl_hg_reg_'+$newCase+'_r1.run.json'));$n=J $newE.path;$nc=J $n.call.path
Need ($n.passed -and $n.case -ceq $newCase -and $n.frozen_inputs_control_canonical_unchanged -and $nc.direct_native_call -and $nc.typed_LASTEXITCODE_captured_immediately -and $nc.owned_call_exited -and $nc.exit_code -is [int] -and $nc.exit_code -eq 0 -and !$nc.invocation_failure) 'New completed project-main regression required'
$oldE=$n.retained_control;$o=J $oldE.path;$oldCallE=if($Case -ceq 'Legacy'){$o.owned_exit_record}else{$o.call};$oc=J $oldCallE.path
Need ($o.passed -and $oc.typed_LASTEXITCODE_captured_immediately -and $oc.owned_call_exited -and $oc.exit_code -is [int] -and $oc.exit_code -eq 0 -and !$oc.invocation_failure) 'Retained CPU control owned exit0 required'
$oldData=Join-Path $oc.arguments[5] 'data';$newData=Join-Path $nc.arguments[5] 'data';$frames=if($Case -ceq 'Legacy'){21}else{1469};$arrays=if($Case -ceq 'Legacy'){15}else{22}
Need ($n.native_frames -eq $frames -and $nc.program.sha256 -ceq $n.program.sha256) 'Actual fresh program/frame binding differs'
$bindings=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_hg_raw_compare_run_r1.json')),$helperE,$h.program,$h.helper_object,$h.compile_call,$h.link_call,$h.compiler_dependency_record,$newE,$n.call,$oldE,$oldCallE,$nc.program,$oc.program)+@($h.inputs)+@($h.actual_includes)+@($h.project_objects)+@($n.files)+@($o.files)
foreach($pair in $h.runtime){$bindings+=@($pair.original,$pair.copy)}
V $bindings;$argv=@('--compare',$Case,$oldData,$newData,$out);$working=Split-Path -Parent $h.program.path;$start=[DateTime]::UtcNow.ToString('o');$code=$null;$why=$null;$prior=$ErrorActionPreference
[IO.File]::WriteAllBytes($log,[byte[]]@());Push-Location $working
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $h.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$why=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
Save $callPath ([ordered]@{program=$h.program;arguments=$argv;working_directory=$working;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$why;log=(E $log);pure_native_reader=$true;solver_run=$false})
$failure=$why;$unchanged=$false;$done=$null;$k=$null;$files=@()
try{
  Need ($code -is [int] -and $code -eq 0 -and !$why) 'Pure raw comparator returned no typed exit0; preserve mismatches'
  $done=E (Join-Path $out 'completion.json');$k=J $done.path
  Need ($k.passed -and $k.complete -and $k.stage -ceq 'upl_hg_raw_compare_r1' -and $k.mode -ceq $Case -and $k.frames_compared -eq $frames -and $k.arrays_per_frame -eq $arrays -and $k.array_different_bytes -eq 0 -and $k.clock_different_bytes -eq 0 -and $k.metadata_different_fields -eq 0 -and $k.total_native_count -eq 1040 -and $k.clock_bytes_per_frame -eq 28 -and !$k.physical_acceptance) 'Full raw field/clock/physical metadata equality failed'
}catch{$failure=$_.Exception.Message}
try{V $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -File|Sort-Object Name|ForEach-Object{E $_.FullName})}
$passed=(!$failure -and $unchanged -and $null -ne $k)
Save $record ([ordered]@{stage='upl_hg_raw_compare_run_r1';passed=$passed;case=$Case;helper=$helperE;source_new=$newE;source_old=$oldE;call=(E $callPath);completion=$done;inputs=$bindings;files=$files;frozen_inputs_and_both_raw_sequences_unchanged=$unchanged;all_declared_native_arrays_0ULP=$passed;all_actual_clock28_0ULP=$passed;typed_physical_metadata_equal=$passed;metadata_exclusions=$(if($k){@($k.excluded_header_values)+@($k.excluded_PART_values)}else{@()});solver_or_control_rerun=$false;physical_acceptance=$false;failure=$failure})
if(!$passed){throw ('Raw comparison rejected; inspect retained native evidence: '+$record)};Write-Output ('Actual raw native field/clock0ULP passed: '+$record)
