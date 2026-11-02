param([switch]$ExecutionAuthorized)
# One actual frozen affine component call only. No solver, build, auto-next or physical acceptance.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root review and explicit -ExecutionAuthorized required'}
$tests=Split-Path -Parent $PSScriptRoot;$tag='upl_case02_flux_affine_check_r1'
$record=Join-Path $tests "logs\$tag.run.json";$log=Join-Path $tests "logs\$tag.log";$out=Join-Path $tests "outputs\$tag"
$buildPath=Join-Path $tests 'logs\upl_case02_flux_affine_DebugCPU_r1.helper.json';$inputsPath=Join-Path $tests 'logs\upl_case02_short_r1.inputs.json'
$note=Join-Path $tests 'notes\upl_case02_flux_affine_run_r1.json'
function Entry([string]$path){$f=Get-Item -Force -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($e in $items){if(!$e.path -or $null -eq $e.bytes -or !$e.sha256){throw 'Missing bound artifact'};$n=Entry $e.path;if($n.bytes -ne $e.bytes -or $n.sha256 -ine $e.sha256){throw "Changed evidence: $($e.path)"}}}
function Json([string]$path){[IO.File]::ReadAllText($path)|ConvertFrom-Json}
foreach($p in @($record,$log,$out)){if(Test-Path -LiteralPath $p){throw "Retained component protected: $p"}}
$build=Json $buildPath
if(!$build.passed -or $build.stage -cne 'upl_case02_flux_affine_build_r1' -or $build.kind -cne 'affine' -or $build.configuration -cne 'DebugCPU' -or $build.status -cne 'current_CPU_flux_affine_helper_linked_not_run' -or !$build.build_and_source_bindings_unchanged -or !$build.exact_link_closure_verified -or $build.program_run -ne $false -or $build.CPU_non_main_objects -ne 85 -or $build.link_object_count -ne 86 -or @($build.objects).Count -ne 85 -or @($build.source_snapshot).Count -ne 265 -or @($build.libraries).Count -ne 17 -or @($build.runtime).Count -ne 4 -or @($build.canonical_programs_before).Count -ne 7){throw 'Expected passed current Debug affine85/265 helper'}
if([IO.Path]::GetFileName($build.program.path) -cne 'upl_case02_flux_affine_r1.exe'){throw 'Only the affine component program is allowed'}
$inputs=Json $inputsPath;$xml=Join-Path $tests 'outputs\upl_case02_short_r1_seed\upl_case02_short_coarse_r1.xml';$seed=@($inputs.jobs|Where-Object{$_.window -ceq 'coarse'})
if(!$inputs.prepared -or $seed.Count -ne 1 -or $seed[0].runtime.path -ine $xml -or $seed[0].initial_BI4.sha256 -ine 'f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac' -or $seed[0].normals.sha256 -ine '0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97'){throw 'Expected sealed existing coarse seed and original geometry/normals'}
$bindings=@((Entry $PSCommandPath),(Entry $note),(Entry $buildPath),(Entry $inputsPath),$build.program,$build.source_build,$build.retained_compiler_recipe,$build.environment_source,$build.compile_call,$build.link_call,$build.compiler_dependency_record,$build.helper_object)+@($build.author_files)+@($build.objects)+@($build.compile_sources)+@($build.libraries)+@($build.tools)+@($build.environment.tools)+@($build.canonical_programs_before)+@($build.canonical_runtime_before)+@($seed[0].configuration,$seed[0].runtime,$seed[0].initial_BI4,$seed[0].normals)
foreach($pair in $build.source_snapshot){if($pair.original.bytes -ne $pair.snapshot.bytes -or $pair.original.sha256 -ine $pair.snapshot.sha256){throw 'Source snapshot pair differs'};$bindings+=@($pair.original,$pair.snapshot)}
$bindings+=@($build.documentation_snapshot.original,$build.documentation_snapshot.snapshot)
if($build.documentation_snapshot.original.sha256 -ine $build.documentation_snapshot.snapshot.sha256){throw 'Frozen documentation pair differs'}
foreach($r in $build.runtime){if($r.original.bytes -ne $r.copy.bytes -or $r.original.sha256 -ine $r.copy.sha256){throw 'Runtime pair differs'};$bindings+=@($r.original,$r.copy)}
foreach($entry in @($build.compile_call,$build.link_call)){$c=Json $entry.path;if(!$c.direct_native_call -or !$c.typed_LASTEXITCODE_captured_immediately -or !$c.owned_call_exited -or $c.exit_code -ne 0 -or $c.invocation_failure){throw 'Actual typed successful compiler/link calls required'};$bindings+=@($c.program,$c.log)}
Verify $bindings
$argv=@('--input',$xml,'--out',$out);$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
[IO.File]::WriteAllBytes($log,[byte[]]@())
Push-Location (Split-Path -Parent $build.program.path)
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $build.program.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$unchanged=$false;try{Verify $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$completion=$null;$component=$false;$files=@()
try{
  $completionPath=Join-Path $out 'completion.json'
  if(Test-Path -LiteralPath $completionPath){
    $completion=Entry $completionPath;$done=Json $completionPath
    $component=($done.passed -and $done.stage -ceq 'upl_case02_flux_affine_r1' -and $done.native_count -eq 1000 -and $done.fixed_count -eq 40 -and $done.field_cases -eq 3 -and $done.normal_variants -eq 3 -and $done.actual_force_calls -eq 1 -and $done.explicit_complete_rate_calls -eq 11 -and $done.expected_exact_method_rejections -eq 2 -and $done.rate_rows -eq 9000 -and $done.periodic_owner_checks -gt 0 -and $done.covered_snapshot_restores -gt 0 -and $done.covered_state_and_scratch_bytes_restored -eq $true -and $done.actual_wall_MLS_and_Ace_periodic_extension -eq $true -and $done.reference_conditioned_on_actual_C_and_Ace -eq $true -and $done.manufactured_not_mechanical_trajectory -eq $true -and $done.Run_ComputeStep_SaveData_called -eq $false -and $done.actual_time_s -eq 0 -and $done.completed_physical_steps -eq 0 -and $done.physical_acceptance -eq $false)
    foreach($k in @('max_rate_error_over_original_budget','max_normal_invariance_over_original_budget','incompatible_correction_over_old_new_budget')){$v=[double]$done.$k;if($null -eq $done.$k -or [double]::IsNaN($v) -or [double]::IsInfinity($v) -or $v -lt 0){$component=$false}}
    $component=($component -and $done.max_rate_error_over_original_budget -le 1 -and $done.max_normal_invariance_over_original_budget -le 1 -and $done.incompatible_correction_over_old_new_budget -gt 100)
    foreach($pair in @(@('rates.csv',9000),@('summary.csv',9),@('guards.csv',2))){$p=Join-Path $out $pair[0];if(@(Import-Csv -LiteralPath $p).Count -ne $pair[1]){$component=$false}}
    if(!(Test-Path -LiteralPath (Join-Path $out 'Run.out'))){$component=$false}
  }
}catch{if(!$failure){$failure=$_.Exception.Message}}
if(Test-Path -LiteralPath $out){$files=@(Get-ChildItem -LiteralPath $out -File|ForEach-Object{Entry $_.FullName})}
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $component)
$result=[ordered]@{stage=$tag;passed=$passed;configuration='DebugCPU';kind='affine';source_build=$build.source_build;helper=(Entry $buildPath);sealed_inputs=(Entry $inputsPath);program=$build.program;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;bindings=$bindings;bindings_unchanged=$unchanged;completion=$completion;component_completion_verified=$component;files=$files;log=(Entry $log);caller_reconstructed_neighbour_reference=$false;solver_trajectory_started=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 15)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Affine component rejected; preserve partials and inspect $record"}
Write-Output "Affine frozen component passed, no physical trajectory: $record"
