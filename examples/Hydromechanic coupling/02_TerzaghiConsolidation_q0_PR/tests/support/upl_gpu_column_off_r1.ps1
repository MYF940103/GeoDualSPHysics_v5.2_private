param([switch]$ExecutionAuthorized)
# One new current Release canonical explicit-OFF solver call only; no Prepare, reader, build or control rerun.
$ErrorActionPreference='Stop';$tests=Split-Path -Parent $PSScriptRoot;$case=Split-Path -Parent $tests;$logs=Join-Path $tests 'logs';$tag='upl_gpu_column_off_r1'
$folder=Join-Path $tests ('outputs\'+$tag);$inputPath=Join-Path $logs ($tag+'.inputs.json');$runPath=Join-Path $logs ($tag+'.run.json');$donePath=Join-Path $logs ($tag+'.completion.json');$callPath=Join-Path $logs ($tag+'.call.json');$log=Join-Path $logs ($tag+'.log')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function V($rows){foreach($r in $rows){if(!$r.path -or !$r.sha256 -or $null -eq $r.bytes){throw 'Missing artifact binding'};$a=E $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed artifact: $($r.path)"}}}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained path protected: $p"}}}
function Save([string]$p,$value){Fresh @($p);[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if(!$ExecutionAuthorized){throw 'Root full-read and explicit single-solver authorization required'}
Fresh @($folder,$inputPath,$runPath,$donePath,$callPath,$log,(Join-Path $logs ($tag+'.exact.json')))
$buildPath=Join-Path $logs 'upl_gpu_column_Release_r1.build.json';$build=J $buildPath;$source=J $build.source_freeze.path;$project=J $build.project_call.path
if(!$build.passed -or $build.configuration -cne 'Release' -or $build.status -cne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or !$build.objects_exclude_main -or !$build.source_and_protected_artifacts_unchanged -or @($build.objects).Count -ne 110 -or @($build.runtime).Count -ne 4){throw 'Fresh current column Release GPU build required'}
if(@($source.source).Count -ne 265 -or @($source.current_source_snapshot).Count -ne 265 -or @($source.targets).Count -ne 3 -or $source.other_source_count -ne 262 -or @($source.canonical_programs_before).Count -ne 7){throw 'Current265/three-target/canonical7 source closure required'}
if(!$project.owned_call_exited -or !$project.typed_LASTEXITCODE_captured_immediately -or $project.exit_code -isnot [int] -or $project.exit_code -ne 0){throw 'Actual authoritative project owned exit0 required'}
$bindings=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_gpu_column_off_r1.json')),(E $buildPath),$build.source_freeze,$build.project_call,$project.program,$project.log,$build.isolated_GPU_program,$build.project_main_object,$source.documentation_snapshot.original,$source.documentation_snapshot.snapshot)+@($source.source)+@($source.canonical_programs_before)+@($source.runtime_before)+@($source.authoritative_projects)+@($build.tools)+@($build.libraries)+@($build.objects)
foreach($p in $source.current_source_snapshot){$bindings+=@($p.snapshot)}
foreach($r in $build.runtime){$bindings+=@($r.original,$r.copy);if((Split-Path -Parent $r.copy.path) -ine (Split-Path -Parent $build.isolated_GPU_program.path)){throw 'Runtime must accompany the actual selected program'}}
$gateEntries=@()
foreach($cfg in @('Debug','Release')){
  $p=Join-Path $logs ('upl_gpu_column_component_'+$cfg+'_r4.check.json');$g=J $p
  if(!$g.passed -or !$g.call -or !$g.completion -or !$g.helper -or !$g.source_build){throw 'Both fresh component passed records with owned call/completion/build/helper bindings required'}
  $c=J $g.call.path;$d=J $g.completion.path;$h=J $g.helper.path
  if(!$c.owned_call_exited -or !$c.typed_LASTEXITCODE_captured_immediately -or $c.exit_code -isnot [int] -or $c.exit_code -ne 0 -or !$d.passed -or !$h.passed -or $h.kind -cne 'component' -or $h.configuration -cne $cfg){throw 'Component owned exit/completion/helper gate failed'}
  if($g.source_build.path -ine (Join-Path $logs ('upl_gpu_column_'+$cfg+'_r1.build.json')) -or $h.source_build.sha256 -ine $g.source_build.sha256){throw 'Component must use this round matching source build'}
  $gateEntries+=@(E $p);$bindings+=@((E $p),$g.call,$g.completion,$g.helper,$g.source_build,$c.program,$c.log)+@($g.inputs)+@($g.files)
}
$oldPath=Join-Path $logs 'upl_gpu_public_explicit_off_r1.check.json';$old=J $oldPath;$m=J $old.input.path;$oldRun=J $old.source_run.path;$oldCall=J $old.solver_call.path;$oldDone=J $old.solver_completion.path
if(!$old.passed -or !$old.actual_main_owned_exit0_proven -or !$old.all_native_typed15_and_actual_clock_step_signed_dterror_exact -or !$old.dynamic_arrays_and_public_metadata_absent -or !$old.original_HG_guard_preserved -or $old.native_frame_pairs -ne 151 -or $old.native_count -ne 1040 -or $old.original_arrays -ne 15){throw 'Sealed accepted explicit-OFF151 native control required'}
if(!$oldCall.owned_call_exited -or !$oldCall.typed_LASTEXITCODE_captured_immediately -or $oldCall.exit_code -isnot [int] -or $oldCall.exit_code -ne 0 -or !$oldDone.owned_exited -or $oldDone.exit_code -ne 0){throw 'Old real owned completion required; omitted-key null-exit evidence is not a control'}
if(!$m.only_three_zero_keys_added -or !$m.reverse_DOM_exact -or $m.frames -ne 151 -or $m.steps -ne 15000 -or [double]$m.dt_s -ne 1e-5 -or [double]$m.cadence_s -ne .001){throw 'Original explicit input and clock contract differs'}
$expected=@('-gpu','-ompthreads:1','-stable','-mdbc',$m.input_prefix,$m.output,'-dirdataout','data','-svres','-svextraparts:1','-nsteps:15000')
if(($oldCall.arguments -join [char]0) -cne ($expected -join [char]0) -or ($m.arguments -join [char]0) -cne ($expected -join [char]0) -or $oldCall.working_directory -ine $case){throw 'Retained actual CLI/working directory differs'}
$argv=@($oldCall.arguments);$argv[5]=$folder
$bindings+=@((E $oldPath),$old.input,$old.source_run,$old.solver_call,$old.solver_completion,$old.source_build,$m.source_freeze,$oldCall.program,$oldCall.log,$m.new_runtime_XML,$m.original_runtime_XML)+@($old.files)+@($oldDone.files)+@($m.inputs)
foreach($r in $m.copied_inputs){$bindings+=@($r.original,$r.copy)}
foreach($r in $m.runtime){$bindings+=@($r.copy);$match=@($build.runtime|Where-Object{[IO.Path]::GetFileName($_.copy.path) -ieq [IO.Path]::GetFileName($r.copy.path)});if($match.Count -ne 1 -or $match[0].copy.bytes -ne $r.copy.bytes -or $match[0].copy.sha256 -ine $r.copy.sha256){throw 'New program runtime differs from accepted OFF runtime'}}
$xml=New-Object Xml.XmlDocument;$xml.Load($m.new_runtime_XML.path);foreach($key in @('HydroMechDynamicSeepage','HydroMechConductivityModel','HydroMechConductivityCk')){$node=$xml.SelectSingleNode('/case/execution/special/hydromechanics/'+$key);if(!$node -or $node.GetAttribute('value') -cne '0'){throw 'Three explicit public OFF keys required'}}
$reader=J $old.helper.path;if(!$reader.offline_reader_only -or $reader.fixture -cne 'OffReader' -or $reader.configuration -cne 'Release'){throw 'Retained pure typed15 comparison implementation required'}
$bindings+=@($old.helper,$reader.program)+@($reader.author_files);foreach($r in $reader.runtime){$bindings+=@($r.copy)}
V $bindings
if(@(Get-CimInstance Win32_Process|Where-Object{$_.Name -like 'DualSPHysics*.exe'}).Count){throw 'An existing solver is active; no concurrent solver allowed'}
Save $inputPath ([ordered]@{stage=$tag;source_build=(E $buildPath);source_freeze=$build.source_freeze;program=$build.isolated_GPU_program;runtime=$build.runtime;component_gates=$gateEntries;retained_control=(E $oldPath);retained_control_data=(Join-Path $m.output 'data');input_prefix=$m.input_prefix;runtime_XML=$m.new_runtime_XML;initial_files=$m.copied_inputs;arguments=$argv;working_directory=$case;expected_frames=151;expected_native=1040;expected_steps=15000;dt_s=1e-5;bindings=$bindings;inputs_copied_or_written=$false;old_solver_rerun=$false;offline_reader=$reader.program;future_exact_receipt=(Join-Path $logs ($tag+'.exact.json'));physical_acceptance=$false})
[IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o');$nativeExit=$null;$failure=$null;$saved=$ErrorActionPreference
Push-Location $case
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.isolated_GPU_program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$nativeExit=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
$typed=($nativeExit -is [int])
Save $callPath ([ordered]@{program=$build.isolated_GPU_program;arguments=$argv;working_directory=$case;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_invocation=$true;typed_LASTEXITCODE_captured_immediately=$typed;owned_call_exited=$typed;exit_code=$nativeExit;invocation_failure=$failure;log=(E $log);actual_solver_call=$true;old_solver_rerun=$false;physical_acceptance=$false})
# Native exit is sealed before enumerating raw output or performing source/post-run checks.
$files=@();if(Test-Path -LiteralPath $folder){$files=@(Get-ChildItem -LiteralPath $folder -Recurse -File|Sort-Object FullName|ForEach-Object{E $_.FullName})}
$survivors=@(Get-CimInstance Win32_Process|Where-Object{$_.ExecutablePath -ieq $build.isolated_GPU_program.path -or ($_.Name -like 'DualSPHysics*.exe' -and $_.CommandLine -like ('*'+$folder+'*'))}|Select-Object ProcessId,ParentProcessId,Name,CommandLine)
$unchanged=$false;try{V $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$owned0=($typed -and $nativeExit -eq 0 -and !$failure -and $unchanged -and !$survivors.Count)
Save $donePath ([ordered]@{passed_owned_exit_and_bindings_only=$owned0;call=(E $callPath);typed_LASTEXITCODE_captured_immediately=$typed;owned_exited=$typed;exit_code=$nativeExit;source_input_control_runtime_canonical_unchanged=$unchanged;survivors=$survivors;files=$files;sealed_before_offline_native_comparison=$true;original15_exact_or_HG_checked_by_owner=$false;failure=$failure;physical_acceptance=$false})
Save $runPath ([ordered]@{passed=$owned0;scope='One fresh main owned exit and identity only, NOT native equality or numerical acceptance';input=(E $inputPath);source_build=(E $buildPath);source_freeze=$build.source_freeze;program=$build.isolated_GPU_program;component_gates=$gateEntries;call=(E $callPath);completion=(E $donePath);files=$files;bindings=$bindings;retained_control=(E $oldPath);fresh_solver_calls=1;old_solver_rerun=$false;native_exact_checked=$false;original_HG_guard_checked=$false;source_input_runtime_canonical_unchanged=$unchanged;failure=$failure;physical_acceptance=$false})
if(!$owned0){throw "OFF solver ownership/identity failed; preserve $runPath and never automatically rerun"}
Write-Output "Owned new explicit-OFF main exited0; numerical exact gate is still pending: $runPath"
