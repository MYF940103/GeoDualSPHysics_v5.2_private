param(
  [Parameter(Mandatory=$true)][ValidateSet('Build','Run')][string]$Mode,
  [Parameter(Mandatory=$true)][ValidateSet('State','Theta')][string]$Fixture,
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized
)
# Exactly one chosen component/action. No source edit, main-program/solver run or Git.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src';$logs=Join-Path $tests 'logs';$outputs=Join-Path $tests 'outputs'
$leaf=$Fixture.ToLowerInvariant();$cpp=Join-Path $PSScriptRoot ('upl_gpu_observer_'+$leaf+'_r1.cpp')
$note=Join-Path $tests ('notes\upl_gpu_observer_'+$leaf+'_r1.json')
$gpuPath=Join-Path $logs ('upl_gpu_observer_'+$Configuration+'_r1.build.json')
$smokePath=Join-Path $logs 'upl_gpu_observer_Smoke_r1.review.check.json'
$name='upl_gpu_observer_'+$Fixture+'_'+$Configuration+'_r1'
$folder=Join-Path $outputs ('upl_gpu_observer_component_'+$Fixture+'_'+$Configuration+'_r1')
$buildPath=Join-Path $logs ($name+'.build.json');$checkPath=Join-Path $logs ($name+'.check.json')
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function CopyBound($r,[string]$p){Verify @($r);if(Test-Path -LiteralPath $p){throw 'Retained copy protected'};Copy-Item -LiteralPath $r.path -Destination $p;$a=Entry $p;if($a.sha256 -ne $r.sha256){throw 'Copy differs'};@{original=$r;copy=$a}}
function InvokeOwned([string]$exe,[string[]]$argv,[string]$label){
  $log=Join-Path $logs ($label+'.log');$receipt=Join-Path $logs ($label+'.call.json')
  if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt)){throw 'Owned call retained; no retry'}
  $program=Entry $exe;$start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@())
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';& $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  Verify @($program);NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$program;arguments=$argv;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);physical_acceptance=$false})
  if($code -ne 0){throw "Owned build/component failed; preserve $receipt"};Entry $receipt
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root review and explicit single-action authorization required'}
$smoke=Get-Content -Raw -LiteralPath $smokePath|ConvertFrom-Json
if(!$smoke.passed -or $smoke.configuration -ne 'Debug' -or $smoke.samples -ne 3 -or !$smoke.all_original15_exact -or !$smoke.final_live_native_csv_exact){throw 'Completed Debug native smoke+memcheck review required before components'}
Verify @($smoke.build,$smoke.completion);Verify $smoke.files;Verify $smoke.calls;Verify $smoke.solvers;Verify $smoke.live_native_equal
foreach($s in $smoke.solvers){$v=Get-Content -Raw -LiteralPath $s.path|ConvertFrom-Json;if(!$v.passed){throw 'Smoke solver receipt failed'};Verify $v.files;Verify @($v.call,$v.build)}
$gpu=Get-Content -Raw -LiteralPath $gpuPath|ConvertFrom-Json
if($gpu.status -ne 'full_authoritative_GPU_Rebuild_passed_no_fixture_or_program_run' -or $gpu.configuration -ne $Configuration -or !$gpu.objects_exclude_main -or $gpu.objects.Count -lt 80 -or !$gpu.canonical_GPU_unchanged){throw 'Frozen authoritative observer project objects required'}
$baseline=Get-Content -Raw -LiteralPath $gpu.baseline.path|ConvertFrom-Json
$inputs=@(Entry $PSCommandPath;Entry $cpp;Entry $note;Entry $gpuPath;Entry $smokePath)
$seed=$null
if($Fixture -eq 'State'){
  $p=Join-Path $logs 'upl_gpu_observer_native_r1.inputs.json';$prepared=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
  if($prepared.status -ne 'three_explicit_native_windows_prepared_not_run'){throw 'Sealed512 no-wall periodic seed required'}
  $selected=@($prepared.jobs|Where-Object {$_.window -eq 'Smoke'});if($selected.Count -ne 1 -or $selected[0].native -ne 512 -or $selected[0].fixed -ne 0){throw 'State seed count/scope differs'}
  $seed=$selected[0];Verify @($seed.xml,$seed.bi4);$inputs+=@(Entry $p;$seed.xml;$seed.bi4)
}
$dependencies=@(Entry $smokePath)
if($Configuration -eq 'Release'){
  $p=Join-Path $logs ('upl_gpu_observer_'+$Fixture+'_Debug_r1.check.json');$prior=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
  if(!$prior.passed -or $prior.fixture -ne $Fixture -or !$prior.memcheck_executed -or !$prior.memcheck_zero_errors_and_leaks){throw 'Own Debug component memcheck pass required before Release'}
  Verify $prior.files;Verify @($prior.build,$prior.call,$prior.completion);$dependencies+=Entry $p
}
function VerifyGpu {Verify $inputs;Verify $dependencies;Verify $gpu.inputs;Verify $gpu.tools;Verify $gpu.objects;Verify @($gpu.baseline,$gpu.source_freeze,$gpu.project_call,$gpu.isolated_GPU_program);Verify $baseline.canonical_GPU;foreach($r in $gpu.runtime){Verify @($r.original,$r.snapshot)}}
VerifyGpu
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $buildPath)){throw 'Component build retained'}
  [void](New-Item -ItemType Directory -Path $folder);$snapshots=@();foreach($p in @($PSCommandPath,$cpp,$note)){$snapshots+=CopyBound (Entry $p) (Join-Path $folder ([IO.Path]::GetFileName($p)))}
  $runtime=@();foreach($r in $gpu.runtime){$runtime+=CopyBound $r.snapshot (Join-Path $folder ([IO.Path]::GetFileName($r.snapshot.path)))}
  $env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $cuda=$env:CUDA_PATH_V11_7;$cl=Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\cl.exe';$link=Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\link.exe'
  $tools=@(Entry $cl;Entry $link;Entry (Join-Path $cuda 'compute-sanitizer\compute-sanitizer.exe'))
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$Configuration.lib","LibJNumexLib_x64_v143_$Configuration.lib","LibJWaveGen_x64_v143_$Configuration.lib","LibDSphMoorDyn_x64_v143_$Configuration.lib")
  $libraries=@($libs|ForEach-Object {Entry (Join-Path $src ('lib\vs2022\'+$_))})+@(Entry (Join-Path $cuda 'lib\x64\cudart_static.lib'))
  $obj=Join-Path $folder 'observer_component.obj';$exe=Join-Path $folder ('upl_gpu_observer_'+$leaf+'_r1.exe');$flags=if($Configuration -eq 'Debug'){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/D_WITHGPU',"/I$src\source","/I$cuda\include","/Fo$obj","/Fd$folder\compile.pdb")+$flags+@($cpp)
  $cc=InvokeOwned $cl $compile ($name+'_compile')
  $system=@('kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $argsLink=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$src\lib\vs2022","/LIBPATH:$cuda\lib\x64",$obj)+@($gpu.objects.path)+$libs+$system+@('cudart_static.lib');if($Configuration -eq 'Debug'){$argsLink+=@('/DEBUG',"/PDB:$folder\link.pdb")}
  $lc=InvokeOwned $link $argsLink ($name+'_link');VerifyGpu;Verify $tools;Verify $libraries
  NewJson $buildPath ([ordered]@{status='actual_authoritative_GPU_object_component_linked_not_run';fixture=$Fixture;configuration=$Configuration;source_build=(Entry $gpuPath);inputs=$inputs;dependencies=$dependencies;snapshots=$snapshots;runtime=$runtime;program=(Entry $exe);tools=$tools;libraries=$libraries;compile_call=$cc;link_call=$lc;other_fixture_bound=$false;canonical_GPU_unchanged=$true;program_executed=$false;physical_acceptance=$false})
  Write-Output 'BUILT only this chosen component; explicit Run required';exit 0
}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if($build.status -ne 'actual_authoritative_GPU_object_component_linked_not_run' -or $build.fixture -ne $Fixture -or $build.configuration -ne $Configuration){throw 'Chosen component build unavailable'}
function VerifyBuild {VerifyGpu;Verify $build.inputs;Verify $build.dependencies;Verify $build.tools;Verify $build.libraries;Verify @($build.source_build,$build.program,$build.compile_call,$build.link_call);foreach($r in $build.runtime){Verify @($r.original,$r.copy)};foreach($r in $build.snapshots){Verify @($r.original,$r.copy)}}
VerifyBuild
$out=Join-Path $outputs ($name+'_data');if((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $checkPath)){throw 'Component output/check retained'}
if($Fixture -eq 'State'){$argv=@('--state','-gpu','-stable',$seed.prefix,$out,'-dirdataout','data','-svres');$completion=Join-Path $out 'state_complete.json'}else{$argv=@('--out',$out,'--device','0');$completion=Join-Path $out 'completion.json'}
$memcheck=$Configuration -eq 'Debug'
if($memcheck){$tool=@($build.tools|Where-Object {[IO.Path]::GetFileName($_.path) -eq 'compute-sanitizer.exe'});if($tool.Count -ne 1){throw 'Sanitizer tool ambiguous'};$call=InvokeOwned $tool[0].path (@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$build.program.path)+$argv) ($name+'_memcheck')}else{$call=InvokeOwned $build.program.path $argv ($name+'_component')}
$owned=Get-Content -Raw -LiteralPath $call.path|ConvertFrom-Json
if($memcheck){$log=[IO.File]::ReadAllText($owned.log.path);if($log -notmatch 'ERROR SUMMARY:\s*0 errors' -or $log -notmatch 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'){throw 'Actual Debug zero-error/zero-leak report missing'}}
$done=Get-Content -Raw -LiteralPath $completion|ConvertFrom-Json
if(!$done.passed -or $done.physical_acceptance){throw 'Component rejected or scope changed'}
if($Fixture -eq 'State'){
  if($done.native_count -ne 512 -or $done.fixed_count -ne 0 -or !$done.real_cell_reorder -or $done.actual_nonzero_prefix_cell_division -or !$done.periodic_JPre_with_PosPre_NULL -or $done.clone_of_clone_checks -le 0 -or !$done.live_JPre_resize_preserved -or $done.new_GPU_capacity -le $done.old_GPU_capacity -or !$done.corrector_recurrence_checked -or !$done.predictor_history_released -or $done.invalid_J_rejections -ne 3 -or !$done.native_plastic_rejected -or !$done.periodic_plastic_poison_ignored -or $done.periodic_plastic_poison_slots -le 0 -or !$done.copy_sort_resize_bit_exact -or $done.corrector_tail_guard_slots -ne 7 -or $done.component_extra_RunCellDivide_calls -ne 3 -or !$done.actual_LoadConfig_ConfigDomain_InitRunGpu -or !$done.actual_J_host_and_CUDA_helpers -or $done.actual_force_calls -ne 0 -or $done.completed_physics_steps -ne 0 -or [double]$done.actual_time_s -ne 0 -or $done.Nstep -ne 0 -or $done.public_GPU_dynamic_mode -or $done.feedback){throw 'State lifecycle/recurrence/negative-control/no-physics gates differ'}
  [void](Entry (Join-Path $out 'state.csv'))
}else{
  if($done.cases -ne 10 -or $done.actual_kernel_calls -ne 30 -or $done.node_output_rows -ne 270 -or $done.particles -ne 9 -or $done.center_ID -ne 4 -or $done.native_OFF_ON_output_pairs -ne 180 -or $done.NULL_theta_sentinel_checks -ne 90 -or $done.same_stage_reset_theta_pairs -ne 90 -or $done.nonzero_trace_ON_checks -ne 8 -or $done.drained_nonzero_theta_zero_pore_rate_checks -ne 4 -or $done.nonempty_shear_stress_checks -ne 4 -or !$done.correction_supplied_from_independent_center_moment -or !$done.actual_force_kernel_only -or $done.general_C_matrix_solver_tested -or $done.physical_drained_run_admitted -or $done.time_integrated -or $done.feedback_tested){throw 'Theta force-kernel manufacturing/count/scope gates differ'}
  foreach($p in @(@('moment.csv',8),@('node_outputs.csv',270),@('theta_cases.csv',10))){if(@(Import-Csv -LiteralPath (Join-Path $out $p[0])).Count -ne $p[1]){throw 'Theta CSV row count differs'}}
}
VerifyBuild;$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object {Entry $_.FullName})
NewJson $checkPath ([ordered]@{passed=$true;fixture=$Fixture;configuration=$Configuration;build=(Entry $buildPath);native_smoke=(Entry $smokePath);completion=(Entry $completion);call=$call;files=$files;memcheck_executed=$memcheck;memcheck_zero_errors_and_leaks=$memcheck;canonical_GPU_unchanged=$true;general_GPU_dynamic_or_physical_acceptance=$false;physical_acceptance=$false})
Write-Output 'PASSED chosen observer implementation component only'
