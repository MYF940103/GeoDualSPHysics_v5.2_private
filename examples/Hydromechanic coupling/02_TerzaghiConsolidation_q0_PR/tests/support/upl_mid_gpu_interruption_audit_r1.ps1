# Seal interrupted, already stopped jobs only. Never launch/stop a producer or manufacture its exit.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$cryer=Join-Path ((Get-Item -LiteralPath $tests).Parent.Parent.FullName) '04_CryerProblem_PR\tests'
$dest=Join-Path $tests 'logs\upl_mid_gpu_interruption_r1.check.json'
function Need([bool]$b,[string]$w){if(!$b){throw $w}}
function E([string]$p){$f=Get-Item -LiteralPath $p;Need (!$f.PSIsContainer) 'File required';return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function Verify($es){$seen=@{};foreach($e in @($es)){$k=$e.path.ToLowerInvariant();if(!$seen.ContainsKey($k)){$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ceq $e.sha256) ('Changed binding: '+$e.path);$seen[$k]=$a}};return @($seen.Values|Sort-Object path)}
Need (!(Test-Path -LiteralPath $dest)) 'Retained audit protected'
$observed=@()
foreach($pass in @(0,1)){
  $p=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(DualSPHysics.*|upl_.*|compute-sanitizer)\.exe$'} | Select-Object Name,ProcessId,ParentProcessId,CreationDate,CommandLine)
  $observed+=@{utc=[DateTime]::UtcNow.ToString('o');project_processes=$p}
  Need ($p.Count -eq 0) 'A surviving project process requires ownership diagnosis; never duplicate'
  if(!$pass){Start-Sleep -Seconds 2}
}
$mid=Join-Path $tests 'outputs\upl_damp_mid_CPU_coarse_r1'
$gpu=Join-Path $cryer 'outputs\upl_cryer_gpu_component_Debug_probe_r2'
$missing=@()
foreach($p in @((Join-Path $tests 'logs\upl_damp_mid_CPU_coarse_r1.call.json'),(Join-Path $tests 'logs\upl_damp_mid_CPU_coarse_r1.run.json'),(Join-Path $cryer 'logs\upl_cryer_gpu_component_Debug_probe_r2.call.json'),(Join-Path $cryer 'logs\upl_cryer_gpu_component_Debug_probe_r2.run.json'),(Join-Path $gpu 'completion.json'))){Need (!(Test-Path -LiteralPath $p)) 'A real seal now exists; audit it instead of synthesizing an interruption';$missing+=@($p)}
$prepE=E (Join-Path $tests 'logs\upl_damp_mid_r1.inputs.json');$m=J $prepE.path
$bE=E (Join-Path $tests 'logs\upl_damp_ReleaseCPU_r2.build.json');$b=J $bE.path
$adE=E (Join-Path $tests 'logs\upl_damp_mid_CPU_coarse_r1.admission.json');$ad=J $adE.path
$hE=E (Join-Path $cryer 'logs\upl_cryer_gpu_component_Debug_r2.helper.json');$h=J $hE.path
Need ($m.passed -and $b.passed -and $ad.passed -and $h.passed) 'Original prepared/build/admission evidence missing'
$bindings=@($prepE,$bE,$adE,$hE,(E $PSCommandPath),(E (Join-Path $tests 'support\upl_damp_mid_run_r1.ps1')),(E (Join-Path $tests 'notes\upl_damp_mid_run_r1.json')))+@($m.inputs)+@($m.files)+@($ad.inputs)+@($b.objects)+@($b.source_snapshot|ForEach-Object{$_.snapshot})+@($b.runtime|ForEach-Object{$_.copy})+@($h.inputs)+@($h.author_files)+@($h.objects)+@($h.source_snapshots265)+@($h.runtime|ForEach-Object{$_.copy})+@($h.program,$b.program)
$verified=Verify $bindings
$raw=@(Get-ChildItem -LiteralPath (Join-Path $mid 'data') -File -Filter 'Part_*.bi4'|Sort-Object Name)
$want=@(0..1672|ForEach-Object{'Part_{0:D4}.bi4' -f $_})
Need ($raw.Count -eq 1673 -and !(Compare-Object $raw.Name $want)) 'Partial raw membership differs: do not infer another sealed time'
$midRun=E (Join-Path $mid 'Run.out');$text=[IO.File]::ReadAllText($midRun.path)
Need ($text -notmatch '\[Simulation finished' -and $text -match '(?m)^Part_1672\s+6\.875000\s+3604480\s') 'Do not call a completed or differently stopped run this interruption'
$all=@()
foreach($out in @($mid,$gpu)){$all+=@(Get-ChildItem -LiteralPath $out -Recurse -File|Sort-Object FullName|ForEach-Object{E $_.FullName})}
$logs=@((E (Join-Path $tests 'logs\upl_damp_mid_CPU_coarse_r1.log')),(E (Join-Path $cryer 'logs\upl_cryer_gpu_component_Debug_probe_r2.log')),(E (Join-Path $cryer 'logs\upl_cryer_gpu_component_Debug_probe_r2.memcheck.log')))
$events=@(Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=[datetime]'2026-11-03 11:58:00';EndTime=[datetime]'2026-11-03 12:03:30';Id=1000,1001} -ErrorAction SilentlyContinue|Select-Object TimeCreated,Id,ProviderName,Message)
$final=Verify (@($verified)+$all+$logs)
$result=[ordered]@{stage='upl_mid_gpu_interruption_r1';interruption_audited=$true;all_observed_owned_processes_absent=$true;observations=$observed;real_exit_code=$null;typed_exit_evidence_available=$false;normal_completion_or_failure_exit_invented=$false;cause='Not established. Both tracked owners and children are absent; tool sessions no longer available. No reboot observed. Application RADAR_PRE_LEAK_64 is retained but is not by itself a crash/termination cause.';last_boot_utc=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o');application_events=$events;missing_real_seals=$missing;mid=@{tag='upl_damp_mid_CPU_coarse_r1';planned_frames=1746;planned_completed_steps=4798782;observed_raw_frames=1673;last_console_part=1672;last_console_time_s=6.875;last_console_completed_steps=3604480;native_clock_or_safety_checked=$false;planned_window_completed=$false;run_out=$midRun;prepared=$prepE;source_build=$bE;admission=$adE};GPU=@{tag='upl_cryer_gpu_component_Debug_probe_r2';helper=$hE;completed_six_probes=$false;memcheck_pass_claimed=$false;real_tool_exit=$null;program_or_physics_changes=$false};original_calls_or_outputs_modified=$false;producer_or_decoder_executed=$false;restart_or_retry_performed=$false;old_full_gate_preserved=$true;physical_acceptance=$false;verified_input_bindings=$verified;retained_output_files=$all;retained_logs=$logs;independent_final_rehash_count=$final.Count}
[IO.File]::WriteAllText($dest,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output $dest
