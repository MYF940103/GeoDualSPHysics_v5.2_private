param(
  [Parameter(Mandatory=$true)][ValidateSet('Run','Read','ReadReference')][string]$Mode,
  [Parameter(Mandatory=$true)][string]$HelperReceipt,
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidateSet('constant','variable')][string]$Model='constant',
  [ValidateSet('smoke','coarse','half')][string]$Window='smoke',
  [ValidatePattern('^r[1-9][0-9]*$')][string]$Label='r1',
  [string]$InputPrefix,[string]$SourceRun,[switch]$ExecutionAuthorized
)
# ONE owned action. No preparation, build, old solver, audit or automatic next job.
$ErrorActionPreference='Stop';$t=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item $t).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $t 'logs';$stem="upl_gravity_wall_cpu_${Configuration}_${Model}_${Window}_${Label}";$out=Join-Path $t "outputs\$stem"
function Entry($p){$f=Get-Item -Force -LiteralPath $p;@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p).Hash.ToLowerInvariant()}}
function V($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or !$r.sha256 -or $a.sha256 -ine $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function J($p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained output protected: $p"}}}
function Save($p,$x){Fresh @($p);[IO.File]::WriteAllText($p,($x|ConvertTo-Json -Depth 22)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Files($p){if(Test-Path -LiteralPath $p){@(Get-ChildItem -LiteralPath $p -Recurse -File -Force|Sort-Object FullName|ForEach-Object {Entry $_.FullName})}else{@()}}
function CallOK($e){V @($e);$c=J $e.path;if($c.exit_code -ne 0 -or !$c.owned_call_exited -or !$c.typed_LASTEXITCODE_captured_immediately){throw 'Successful owned typed tool call required'};V @($c.program,$c.log)}
function Frozen{
  V (@($he,$h.source_build)+$authors);V $h.inputs;V $h.author_files;V $h.tools;V $h.libraries;V $h.objects;V @($h.program,$h.helper_object);CallOK $h.compile_call;CallOK $h.link_call
  V @($b.inputs|Where-Object {$_.path -notin @($b.git_identity_metadata.path)});V $b.author_files;V $b.source;V $b.protected_canonical_GPU_six_and_CPU_two;V @($b.program,$b.project_call)
  foreach($r in $b.current_source_snapshot){V @($r.original,$r.snapshot)};foreach($r in $b.objects){V @($r.source,$r.object)};foreach($r in @($b.runtime)+@($h.runtime)){V @($r.original,$r.copy)}
  $current=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src\source') -File|ForEach-Object {$_.FullName});if(@(Compare-Object ($current|Sort-Object) ($b.source.path|Sort-Object)).Count){throw 'Current271 source membership differs'}
}
function Owned([string[]]$argv,$suffix,$solver){
  $log=Join-Path $logs ($stem+$suffix+'.log');$cp=Join-Path $logs ($stem+$suffix+'.call.json');Fresh @($log,$cp);[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null
  Push-Location (Split-Path -Parent $h.program.path);try{& $h.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$old}
  Save $cp @{program=$h.program;arguments=$argv;working_directory=(Split-Path -Parent $h.program.path);direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);actual_solver_call=$solver;pure_reader_only=(!$solver);physical_acceptance=$false};Entry $cp
}
if(!$ExecutionAuthorized){throw 'Root single-action authorization required'}
if(($Window -eq 'smoke' -and ($Model -ne 'constant' -or $Configuration -ne 'DebugCPU')) -or ($Window -ne 'smoke' -and $Configuration -ne 'ReleaseCPU')){throw 'Only constant Debug smoke or declared Release full windows admitted'}
$he=Entry $HelperReceipt;$h=J $he.path;V @($h.source_build);$b=J $h.source_build.path
if(!$h.passed -or $h.configuration -cne $Configuration -or $h.CPU_non_main_objects -ne 85 -or $h.link_object_count -ne 86 -or !$h.exact_link_closure_verified -or !$h.program -or !$b.passed -or @($b.source).Count -ne 271 -or @($b.current_source_snapshot).Count -ne 271 -or @($b.objects).Count -ne 86 -or @($h.objects).Count -ne 85){throw 'Passed current271/85+1 closure required'}
$authors=@($PSCommandPath,(Join-Path $t 'notes\upl_gravity_wall_job_r1.json'))|ForEach-Object {Entry $_};Frozen
$prep=Entry (Join-Path $t 'notes\upl_gravity_wall_inputs_r1.json');$p=J $prep.path;$job=@($p.jobs|Where-Object {$_.model -ceq $Model -and $_.window -ceq $Window});if(!$p.passed -or $job.Count -ne 1){throw 'Sealed five-window preparation proof required'};$job=$job[0];V @($prep,$job.config,$p.chosen_geometry)
$dependencies=@($he,$h.source_build,$prep)+$authors;$inputs=@();$sourceFiles=@();$sourceIdentity=$null
if($Mode -eq 'Run'){
  if(!$InputPrefix){throw 'Stage XML/BI4 before Run'};$InputPrefix=[IO.Path]::GetFullPath($InputPrefix);$inputs=@((Entry ($InputPrefix+'.xml')),(Entry ($InputPrefix+'.bi4')))
  if($inputs[0].sha256 -ine $job.config.sha256 -or $inputs[0].bytes -ne $job.config.bytes -or $inputs[1].sha256 -ine $p.chosen_geometry.sha256 -or $inputs[1].bytes -ne $p.chosen_geometry.bytes){throw 'Exact prepared runtime/chosen h BI4 required'}
  $rp=Join-Path $logs ($stem+'.run.json');Fresh @($out,$rp);$call=Owned @('--solver',$Model,$Window,'-cpu','-ompthreads:1','-stable','-mdbc_freeslip',$InputPrefix,$out,'-dirdataout','data','-svres') '' $true;$c=J $call.path;$raw=@(Files $out);$donePath=Join-Path $out 'actual_complete.json';$done=if(Test-Path $donePath){J $donePath}else{$null}
  $post=$null;try{Frozen;V $inputs;V $dependencies}catch{$post=$_.Exception.Message};$ok=$c.exit_code -eq 0 -and $c.typed_LASTEXITCODE_captured_immediately -and $done.passed -eq $true -and !$post
  Save $rp @{passed=$ok;mode='Run';configuration=$Configuration;model=$Model;window=$Window;helper=$he;source_build=$h.source_build;dependencies=$dependencies;input_prefix=$InputPrefix;inputs=$inputs;output=$out;call=$call;files=$raw;actual_complete=$(if($done){Entry $donePath}else{$null});owned_solver_exit0=($c.exit_code -eq 0 -and $c.typed_LASTEXITCODE_captured_immediately);post_binding_failure=$post;native_review_performed=$false;physical_acceptance=$false};if(!$ok){throw 'Run failed; retain files'};return
}
if($Mode -eq 'Read'){
  if(!$SourceRun){throw 'SourceRun required'};$sourceIdentity=Entry $SourceRun;$s=J $SourceRun;if(!$s.passed -or !$s.owned_solver_exit0 -or $s.helper.sha256 -ine $he.sha256 -or $s.configuration -cne $Configuration -or $s.model -cne $Model -or $s.window -cne $Window){throw 'Matching completed Run required'};V (@($sourceIdentity,$s.helper,$s.source_build,$s.call)+$s.inputs);V $s.files;CallOK $s.call;$sourceFiles=@($s.files);$inputs=@($s.inputs);$data=Join-Path $s.output 'data';$xml=$s.input_prefix+'.xml';$target=$out+'_review';$action='--read'
}else{
  if($Window -eq 'smoke'){throw 'No reference smoke/old solver invocation'};$tag=if($Window -eq 'coarse'){'c'}else{'h'};$kind=if($Model -eq 'constant'){'constant'}else{'evolving'};$manifest=Entry (Join-Path $logs 'upl_cpu_public_r1.inputs.json');$m=J $manifest.path;$old=@($m.jobs|Where-Object {$_.label -ceq "wall_${kind}_${tag}"});$control=@($p.initial_native_equivalence.controls|Where-Object {$_.label -ceq "${Model}_${tag}"});if($old.Count -ne 1 -or $control.Count -ne 1){throw 'Exact retained reference selection missing'};$old=$old[0];$control=$control[0]
  V @($control.owned_solver_call,$control.original_solver_check,$control.runtime,$control.bi4);$sc=J $control.original_solver_check.path;$oc=J $control.owned_solver_call.path;if(!$sc.passed -or !$oc.owned_call_exited -or $oc.exit_code -ne 0 -or $sc.call.sha256 -ine $control.owned_solver_call.sha256 -or $old.planned_output -cne $oc.arguments[4] -or $old.input_prefix -cne $oc.arguments[3]){throw 'Retained actual public CPU owned0/raw control required'};V $sc.files;V @($oc.program,$oc.log,$old.runtime,$old.copied_geometry);$sourceFiles=@($sc.files);$inputs=@($control.runtime,$control.bi4);$sourceIdentity=$control.original_solver_check;$dependencies+=@($manifest,$control.owned_solver_call,$control.original_solver_check);$data=Join-Path $old.planned_output 'data';$xml=$control.runtime.path;$target=$out+'_reference_review';$action='--read-reference'
}
$suffix=if($Mode -eq 'Read'){'_reader'}else{'_reference_reader'};$check=Join-Path $logs ($stem+$suffix+'.check.json');Fresh @($target,$check);$call=Owned @($action,$Model,$Window,$data,$xml,$target) $suffix $false;$c=J $call.path;$donePath=Join-Path $target 'completion.json';$done=if(Test-Path $donePath){J $donePath}else{$null};$live=$null
if($Mode -eq 'Read' -and $done.passed){$a=Entry (Join-Path $s.output 'live_final.csv');$z=Entry (Join-Path $target 'last_poro.csv');$live=@{live=$a;native=$z;byte_exact=($a.bytes -eq $z.bytes -and $a.sha256 -ieq $z.sha256)}}
$post=$null;try{Frozen;V $inputs;V $sourceFiles;V $dependencies;V @($sourceIdentity)}catch{$post=$_.Exception.Message}
$ok=$c.exit_code -eq 0 -and $c.typed_LASTEXITCODE_captured_immediately -and $done.passed -eq $true -and $done.native_count -eq 1024 -and $done.fixed_count -eq 256 -and $done.samples -eq $job.samples -and $done.common_columns -eq 33 -and $done.model -ceq $Model -and $done.window -ceq $Window -and ($Mode -ne 'Read' -or $live.byte_exact) -and !$post
Save $check @{passed=$ok;mode=$Mode;configuration=$Configuration;model=$Model;window=$Window;helper=$he;source_build=$h.source_build;dependencies=$dependencies;source_run_or_old_control=$sourceIdentity;source_files=$sourceFiles;inputs=$inputs;call=$call;completion=$(if($done){Entry $donePath}else{$null});files=@(Files $target);live_final=$live;post_binding_failure=$post;pure_reader_only=$true;half_frame_body_or_wall_audit_performed=$false;physical_acceptance=$false};if(!$ok){throw 'Read failed; repair offline, never rerun solver'}
