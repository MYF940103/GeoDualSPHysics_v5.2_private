param(
 [Parameter(Mandatory=$true)][ValidateSet('RunJob','ReviewJob')][string]$Mode,
 [Parameter(Mandatory=$true)][ValidateSet('periodic_constant','periodic_variable','wall_constant','wall_variable','OFF_g0','OFF_g9p81_k0')][string]$Job
)
# Explicit one-job execution only. Parent delegated unique native ownership.
# No old solver/GenCase/build, retries, input/source edits or automatic next job.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot
$manifest=Join-Path $t 'logs\upl_gravity_cpu_native_r1.inputs.json'
$qc=Join-Path $t 'support\upl_gravity_cpu_native_qc_r1.py'
$name='upl_gravity_cpu_native_r1_'+$Job;$logs=Join-Path $t 'logs'
$runPath=Join-Path $logs ($name+'.run.json');$checkPath=Join-Path $logs ($name+'.check.json')
function E([string]$p){$f=Get-Item -Force -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Json([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained file/output protected: $p"}}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 24)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Verify($rows){foreach($r in $rows){$f=E $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $f.bytes -ne $r.bytes -or $f.sha256 -ine $r.sha256){throw "Binding changed: $($r.path)"}}}
if((E $manifest).sha256 -cne '2764eed1811ecb4d03a12e82e5574e1b4e7b21ac72a11a0c5c762b1e7caa8efe'){throw 'Independently adopted initial manifest identity differs'}
$m=Json $manifest;if($m.status -cne 'six_candidate_only_actual_main_commands_prepared_NOT_run' -or @($m.jobs).Count -ne 6 -or @($m.bindings).Count -ne 2060){throw 'Declared six-job manifest required'}
$selected=@($m.jobs|Where-Object {$_.job -ceq $Job});if($selected.Count -ne 1){throw 'Exactly one selected job required'};$j=$selected[0]
Verify $m.bindings;$authors=@(E $PSCommandPath;E $qc;E $manifest)
function Inventory([string]$dir){@(Get-ChildItem -LiteralPath $dir -Recurse -File|Sort-Object FullName|ForEach-Object {E $_.FullName})}
function Call($program,[string[]]$argv,[string]$label,[string]$cwd,[string]$stdoutCsv=''){
 Verify @($program);$log=Join-Path $logs ($label+'.log');$receipt=Join-Path $logs ($label+'.call.json');Fresh @($log,$receipt)
 if($stdoutCsv){Fresh @($stdoutCsv)};[IO.File]::WriteAllBytes($log,[byte[]]@())
 $start=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null
 Push-Location $cwd;try{if($stdoutCsv){& $program.path @argv 2> $log | Out-File -LiteralPath $stdoutCsv -Encoding ascii;$code=$LASTEXITCODE}else{& $program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}}finally{Pop-Location;$ErrorActionPreference=$old}
 $typed=$code -is [int]
 Save $receipt ([ordered]@{program=$program;arguments=$argv;working_directory=$cwd;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=$typed;owned_call_exited=$typed;exit_code=$code;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(E $log);stdout_csv=$(if($stdoutCsv){E $stdoutCsv}else{$null});recipe=$authors;physical_acceptance=$false})
 Verify @($program);if(!$typed -or $code -ne 0){throw "Owned native call failed: $label; completed solver must not be rerun"};E $receipt
}
if($Mode -eq 'RunJob'){
 Fresh @($j.new_output,$j.new_review,$runPath,$checkPath)
 $call=Call $j.program @($j.solver_arguments) ($name+'_solver') $j.working_directory
 # Seal complete raw output before any reader/QC. Native completion is separate
 # from old Prepare's unknown shell exit; only this direct owned call proves exit.
 $files=Inventory $j.new_output;$parts=@(Get-ChildItem -LiteralPath (Join-Path $j.new_output 'data') -Filter 'Part_????.bi4' -File)
 $text=[IO.File]::ReadAllText((Join-Path $j.new_output 'Run.out'))
 Save $runPath ([ordered]@{job=$Job;source_build=$m.source_build;manifest=(E $manifest);call=$call;program=$j.program;inputs=$j.inputs;files=$files;native_frames=$parts.Count;expected_frames=$j.samples;owned_solver_exit0=$true;normal_finish_marker=$text.Contains('Finished execution (code=0)');prepare_exit_used_as_solver_evidence=$false;physical_acceptance=$false})
 Verify $m.bindings;Verify $authors;Verify $files
 if($parts.Count -ne $j.samples -or !$text.Contains('Finished execution (code=0)')){throw 'Solver completed but declared frames/finish marker missing; preserve solve, no retry'}
 Write-Output ('SEALED_SOLVER '+$Job+' frames='+$parts.Count);return
}
Fresh @($checkPath,$j.new_review)
$run=Json $runPath;if(!$run.owned_solver_exit0 -or !$run.normal_finish_marker -or $run.native_frames -ne $j.samples){throw 'Sealed successful matching actual main required before reader'}
Verify @($run.call,$run.manifest,$run.source_build);Verify $run.files
$calls=@();if($j.comparison.kind -eq 'lossless_native_38_CSV_binary64_comparison'){
 [void](New-Item -ItemType Directory -Path $j.new_review)
 $part=0;foreach($r in $j.reader_commands){
  $calls+=Call $r.program @($r.arguments) ($name+'_candidate_part'+$part) $j.working_directory $r.stdout_csv
  $calls+=Call $r.program @($r.retained_arguments) ($name+'_retained_read_part'+$part) $j.working_directory $r.retained_stdout_csv
  $part++
 }
}else{foreach($r in $j.reader_commands){$calls+=Call $r.program @($r.arguments) ($name+'_reader') $j.working_directory}}
$reviewFiles=Inventory $j.new_review
# QC is offline only and receives the sealed manifest/solver. It never invokes a
# process or imports old orchestration scripts. Failure may only repair analysis.
$python=E 'D:\anaconda3\python.exe';$qcOut=Join-Path $logs ($name+'.native_qc.json')
$qcCall=Call $python @('-B',$qc,'--manifest',$manifest,'--job',$Job,'--run',$runPath,'--out',$qcOut) ($name+'_offline_qc') $j.working_directory
$result=Json $qcOut;if(!$result.passed){throw 'Offline exact/native safety QC failed; retain solver'}
Verify $m.bindings;Verify $authors;Verify $run.files;Verify $reviewFiles;Verify $calls
Save $checkPath ([ordered]@{passed=$true;job=$Job;scope=$j.comparison;source_build=$m.source_build;manifest=(E $manifest);source_run=(E $runPath);solver_call=$run.call;reader_calls=$calls;qc_call=$qcCall;native_qc=(E $qcOut);files=$reviewFiles;input_hash_is_not_output_truth=$true;unknown_Prepare_exit_not_adopted_as_solver_exit=$true;all_main_and_reader_exits_direct_typed_zero=$true;no_old_solver_rerun=$true;no_half_or_theory_claim=$true;physical_acceptance=$false})
Write-Output ('PASSED_NATIVE_EXACT '+$Job)
