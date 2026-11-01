param(
  [Parameter(Mandatory=$true)][ValidateSet('Prepare','Build','RunOld','RunNew','RunObserver','Review')][string]$Mode,
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [ValidateSet('Smoke','Short','Extended')][string]$Window='Smoke',
  [switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized
)
# Explicit one-action driver. No GenCase, auto-batch, canonical overwrite, restart or Git.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src';$logs=Join-Path $tests 'logs';$outputs=Join-Path $tests 'outputs'
$cpp=Join-Path $PSScriptRoot 'upl_gpu_observer_native_r1.cpp'
$readerNote=Join-Path $tests 'notes\upl_gpu_observer_native_r1.json';$runNote=Join-Path $tests 'notes\upl_gpu_observer_run_r1.json'
$baselinePath=Join-Path $logs 'upl_gpu_observer_r1.baseline.json';$publicPlanPath=Join-Path $logs 'upl_cpu_public_r1.inputs.json'
$inputsPath=Join-Path $logs 'upl_gpu_observer_native_r1.inputs.json'
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function CopyBound($r,[string]$p){Verify @($r);if(Test-Path -LiteralPath $p){throw 'Retained copy protected'};Copy-Item -LiteralPath $r.path -Destination $p;$a=Entry $p;if($a.sha256 -ne $r.sha256){throw 'Copy differs'};@{original=$r;copy=$a}}
function ReviewPath([string]$w){Join-Path $logs ('upl_gpu_observer_'+$w+'_r1.review.check.json')}
function NeedReview([string]$w){$p=ReviewPath $w;$x=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json;if(!$x.passed -or !$x.all_original15_exact -or !$x.final_live_native_csv_exact){throw 'Required earlier native review unavailable'};Verify $x.files;Verify @($x.completion);Entry $p}
function InvokeOwned([string]$exe,[string[]]$argv,[string]$label){
  $log=Join-Path $logs ($label+'.log');$receipt=Join-Path $logs ($label+'.call.json')
  foreach($p in @($log,$receipt)){if(Test-Path -LiteralPath $p){throw 'Owned call retained; no retry'}}
  $program=Entry $exe;$start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@())
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'; & $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  Verify @($program);NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$program;arguments=$argv;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);physical_acceptance=$false})
  if($code -ne 0){throw "Owned call failed; preserve $receipt"};Entry $receipt
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root source review and explicit single-action authorization required'}
$baseline=Get-Content -Raw -LiteralPath $baselinePath|ConvertFrom-Json
if($baseline.status -ne 'pre_five_observer_edits_source_and_retained_sort_GPU_programs_frozen' -or $baseline.retained_sort_GPU_programs.Count -ne 2){throw 'Five-file pre-edit observer baseline required'}
Verify $baseline.inputs;Verify $baseline.canonical_GPU
$recipe=@(Entry $PSCommandPath;Entry $cpp;Entry $readerNote;Entry $runNote;Entry $baselinePath;Entry $publicPlanPath)
if($Mode -eq 'Prepare'){
  if(Test-Path -LiteralPath $inputsPath){throw 'Prepared inputs retained'}
  $public=Get-Content -Raw -LiteralPath $publicPlanPath|ConvertFrom-Json;$selected=@($public.jobs|Where-Object {$_.label -ceq 'OFF_default'})
  if($selected.Count -ne 1){throw 'Select exactly the sealed public OFF_default seed'};$j=$selected[0]
  if($j.native -ne 512 -or $j.fixed -ne 0 -or $j.steps -ne 8 -or $j.samples -ne 9 -or [double]$j.dt -ne [Math]::Pow(2,-24) -or [double]$j.cadence -ne [double]$j.dt -or [double]$j.end -ne 8*[double]$j.dt){throw 'Unexpected retained seed clock/count'}
  Verify @($j.runtime,$j.copied_geometry);$raw=[IO.File]::ReadAllText($j.runtime.path);[xml]$xml=$raw
  $master=@($xml.SelectNodes("//*[local-name()='HydroMechDynamicSeepage'] | //*[@key='HydroMechDynamicSeepage']"));foreach($m in $master){if($m.GetAttribute('value') -notin '0','false'){throw 'Public dynamic GPU master must remain OFF'}}
  $timeRx=New-Object Text.RegularExpressions.Regex('(<parameter\s+key="TimeMax"\s+value=")[^"]+(\")')
  if($timeRx.Matches($raw).Count -ne 1){throw 'Expected one TimeMax value, no general XML rewrite'}
  $jobs=@();foreach($w in @('Smoke','Short','Extended')){
    $steps=if($w -eq 'Smoke'){2}elseif($w -eq 'Short'){8}else{16};$cfg=if($w -eq 'Smoke'){'Debug'}else{'Release'}
    $folder=Join-Path $outputs ('upl_gpu_observer_seed_'+$w+'_r1');if(Test-Path -LiteralPath $folder){throw 'Seed copy retained'};[void](New-Item -ItemType Directory -Path $folder)
    $prefix=Join-Path $folder 'CaseUplObserver';$end=$steps*[double]$j.dt
    if($w -eq 'Short'){[IO.File]::WriteAllBytes(($prefix+'.xml'),[IO.File]::ReadAllBytes($j.runtime.path))}
    else{$value=$end.ToString('R',[Globalization.CultureInfo]::InvariantCulture);$changed=$timeRx.Replace($raw,[Text.RegularExpressions.MatchEvaluator]{param($m)$m.Groups[1].Value+$value+$m.Groups[2].Value});[IO.File]::WriteAllText(($prefix+'.xml'),$changed,(New-Object Text.UTF8Encoding($false)));if($timeRx.Replace($changed,'TIME_MAX') -cne $timeRx.Replace($raw,'TIME_MAX')){throw 'A field other than TimeMax changed'}}
    [void](CopyBound $j.copied_geometry ($prefix+'.bi4'));$a=Entry ($prefix+'.xml')
    if($w -eq 'Short' -and $a.sha256 -ne $j.runtime.sha256){throw 'Nine-frame input must be byte-identical'}
    $jobs+=@{window=$w;configuration=$cfg;steps=$steps;samples=$steps+1;dt=[double]$j.dt;end=$end;n0=.25;native=512;fixed=0;prefix=$prefix;xml=$a;bi4=(Entry ($prefix+'.bi4'));TimeMax_only_change=($w -ne 'Short');original_XML_byte_identical=($w -eq 'Short')}
  }
  Verify $recipe;Verify @($j.runtime,$j.copied_geometry)
  NewJson $inputsPath ([ordered]@{status='three_explicit_native_windows_prepared_not_run';inputs=$recipe;retained_seed=@($j.runtime,$j.copied_geometry);jobs=$jobs;GenCase_executed=$false;solver_executed=$false;physical_acceptance=$false})
  Write-Output 'PREPARED only: Debug2steps, Release8/16steps; no solver';exit 0
}
$prepared=Get-Content -Raw -LiteralPath $inputsPath|ConvertFrom-Json
if($prepared.status -ne 'three_explicit_native_windows_prepared_not_run' -or $prepared.jobs.Count -ne 3){throw 'Prepared immutable three-window inputs required'}
Verify $prepared.inputs;Verify $prepared.retained_seed;foreach($j in $prepared.jobs){Verify @($j.xml,$j.bi4)}
$dependencies=@();if($Mode -ne 'Build'){$job=@($prepared.jobs|Where-Object {$_.window -ceq $Window})[0];$Configuration=$job.configuration}
if($Configuration -eq 'Release'){$dependencies+=NeedReview 'Smoke'}
if($Mode -ne 'Build' -and $Window -eq 'Extended'){$dependencies+=NeedReview 'Short'}
$gpuPath=Join-Path $logs ('upl_gpu_observer_'+$Configuration+'_r1.build.json');$gpu=Get-Content -Raw -LiteralPath $gpuPath|ConvertFrom-Json
if($gpu.status -ne 'full_authoritative_GPU_Rebuild_passed_no_fixture_or_program_run' -or $gpu.configuration -ne $Configuration -or !$gpu.objects_exclude_main -or $gpu.objects.Count -lt 80 -or !$gpu.canonical_GPU_unchanged){throw 'Authoritative current observer GPU object build required'}
function VerifyGpu {Verify $recipe;Verify $gpu.inputs;Verify $gpu.tools;Verify $gpu.objects;Verify @($gpu.source_freeze,$gpu.project_call,$gpu.isolated_GPU_program);Verify $baseline.canonical_GPU;foreach($r in $gpu.runtime){Verify @($r.original,$r.snapshot)}}
VerifyGpu
$folder=Join-Path $outputs ('upl_gpu_observer_native_'+$Configuration+'_r1');$buildPath=Join-Path $logs ('upl_gpu_observer_native_'+$Configuration+'_r1.build.json')
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $buildPath)){throw 'Helper/program copies retained'}
  $old=@($baseline.retained_sort_GPU_programs|Where-Object {$_.configuration -eq $Configuration});if($old.Count -ne 1){throw 'Retained sort actual GPU program ambiguous'}
  Verify @($old[0].program.original,$old[0].program.snapshot)
  [void](New-Item -ItemType Directory -Path $folder);$snapshots=@();foreach($p in @($PSCommandPath,$cpp,$readerNote,$runNote)){$snapshots+=CopyBound (Entry $p) (Join-Path $folder ([IO.Path]::GetFileName($p)))}
  $oldMain=CopyBound $old[0].program.snapshot (Join-Path $folder 'old_gpu_main.exe');$newMain=CopyBound $gpu.isolated_GPU_program (Join-Path $folder 'new_gpu_main.exe');$runtime=@()
  foreach($r in $gpu.runtime){$runtime+=CopyBound $r.snapshot (Join-Path $folder ([IO.Path]::GetFileName($r.snapshot.path)))}
  $env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $cuda=$env:CUDA_PATH_V11_7;$cl=Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\cl.exe';$link=Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\link.exe';$tools=@(Entry $cl;Entry $link;Entry (Join-Path $cuda 'compute-sanitizer\compute-sanitizer.exe'))
  $suffix=$Configuration;$libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib")
  $libraries=@($libs|ForEach-Object {Entry (Join-Path $src ('lib\vs2022\'+$_))})+@(Entry (Join-Path $cuda 'lib\x64\cudart_static.lib'))
  $obj=Join-Path $folder 'observer_native.obj';$exe=Join-Path $folder 'upl_gpu_observer_native_r1.exe';$flags=if($Configuration -eq 'Debug'){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/D_WITHGPU',"/I$src\source","/I$cuda\include","/Fo$obj","/Fd$folder\compile.pdb")+$flags+@($cpp)
  $cc=InvokeOwned $cl $compile ('upl_gpu_observer_native_'+$Configuration+'_r1_compile')
  $system=@('kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $argsLink=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$src\lib\vs2022","/LIBPATH:$cuda\lib\x64",$obj)+@($gpu.objects.path)+$libs+$system+@('cudart_static.lib');if($Configuration -eq 'Debug'){$argsLink+=@('/DEBUG',"/PDB:$folder\link.pdb")}
  $lc=InvokeOwned $link $argsLink ('upl_gpu_observer_native_'+$Configuration+'_r1_link')
  VerifyGpu;Verify $tools;Verify $libraries
  NewJson $buildPath ([ordered]@{status='actual_authoritative_GPU_object_helper_linked_not_run';configuration=$Configuration;source_build=(Entry $gpuPath);prepared_inputs=(Entry $inputsPath);inputs=$recipe;dependencies=$dependencies;snapshots=$snapshots;runtime=$runtime;old_main=$oldMain;new_main=$newMain;program=(Entry $exe);tools=$tools;libraries=$libraries;compile_call=$cc;link_call=$lc;canonical_GPU_unchanged=$true;solver_executed=$false;physical_acceptance=$false})
  Write-Output 'BUILT helper only; choose exactly one subsequent Run action';exit 0
}
$build=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if($build.status -ne 'actual_authoritative_GPU_object_helper_linked_not_run' -or $build.configuration -ne $Configuration){throw 'Current helper build unavailable'}
function VerifyBuild {VerifyGpu;Verify $build.inputs;Verify $build.tools;Verify $build.libraries;Verify @($build.source_build,$build.prepared_inputs,$build.old_main.original,$build.old_main.copy,$build.new_main.original,$build.new_main.copy,$build.program,$build.compile_call,$build.link_call);foreach($r in $build.runtime){Verify @($r.original,$r.copy)};foreach($r in $build.snapshots){Verify @($r.original,$r.copy)}}
VerifyBuild
$prefix='upl_gpu_observer_'+$Window+'_r1'
function Output([string]$kind){Join-Path $outputs ($prefix+'_'+$kind)}
function SolverCheck([string]$kind){Join-Path $logs ($prefix+'_'+$kind+'.solver.check.json')}
function NeedSolver([string]$kind){$p=SolverCheck $kind;$r=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json;if(!$r.passed -or $r.kind -ne $kind -or $r.native_frames -ne $job.samples){throw 'Required preceding completed solver unavailable'};Verify $r.files;Verify @($r.call,$r.build);$r}
if($Mode -in 'RunOld','RunNew','RunObserver'){
  $kind=if($Mode -eq 'RunOld'){'oldoff'}elseif($Mode -eq 'RunNew'){'newoff'}else{'observer'}
  if($kind -eq 'newoff'){[void](NeedSolver 'oldoff')};if($kind -eq 'observer'){[void](NeedSolver 'newoff')}
  $out=Output $kind;$check=SolverCheck $kind;if((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $check)){throw 'Retained solver output protected'}
  $argv=@('-gpu','-stable',$job.prefix,$out,'-dirdataout','data','-svres');$memcheck=$kind -eq 'observer' -and $Configuration -eq 'Debug'
  if($kind -eq 'observer'){$program=$build.program.path;$argv=@('--solver','1')+$argv}else{$program=if($kind -eq 'oldoff'){$build.old_main.copy.path}else{$build.new_main.copy.path}}
  if($memcheck){$tool=@($build.tools|Where-Object {[IO.Path]::GetFileName($_.path) -eq 'compute-sanitizer.exe'});if($tool.Count -ne 1){throw 'Sanitizer tool ambiguous'};$call=InvokeOwned $tool[0].path (@('--tool','memcheck','--leak-check','full','--error-exitcode','99',$program)+$argv) ($prefix+'_'+$kind)}else{$call=InvokeOwned $program $argv ($prefix+'_'+$kind)}
  $owned=Get-Content -Raw -LiteralPath $call.path|ConvertFrom-Json
  if($memcheck){$text=[IO.File]::ReadAllText($owned.log.path);if($text -notmatch 'ERROR SUMMARY:\s*0 errors' -or $text -notmatch 'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations'){throw 'Actual Debug zero-error/zero-leak memcheck report required'}}
  [void](Entry (Join-Path $out 'Run.out'));$parts=@(Get-ChildItem -LiteralPath (Join-Path $out 'data') -Filter 'Part_????.bi4' -File);if($parts.Count -ne $job.samples){throw 'Native frame count incomplete'}
  VerifyBuild;$files=@(Get-ChildItem -LiteralPath $out -Recurse -File|ForEach-Object {Entry $_.FullName})
  NewJson $check ([ordered]@{passed=$true;kind=$kind;window=$Window;build=(Entry $buildPath);call=$call;files=$files;native_frames=$parts.Count;memcheck_executed=$memcheck;memcheck_zero_errors_and_leaks=$memcheck;native_review_passed=$false;physical_acceptance=$false})
  Write-Output 'SEALED completed solver only; explicitly choose next action/Review';exit 0
}
$old=NeedSolver 'oldoff';$new=NeedSolver 'newoff';$on=NeedSolver 'observer';$final=ReviewPath $Window
$review=Join-Path $outputs ($prefix+'_review');if((Test-Path -LiteralPath $review) -or (Test-Path -LiteralPath $final)){throw 'Offline review retained; never rerun solver to repair analysis'}
if($Configuration -eq 'Debug' -and !$on.memcheck_zero_errors_and_leaks){throw 'Debug actual observer memcheck gate required'}
[void](New-Item -ItemType Directory -Path $review);$calls=@();$reports=@();$maxJDelta=0.;$maxTheta=0.
for($part=0;$part -lt $job.samples;$part++){
  $tag=$part.ToString('D4');$t=$part*[double]$job.dt;$step=if($part){$part-1}else{0}
  foreach($pair in @(@('oldoff','newoff'),@('newoff','observer'))){$json=Join-Path $review ($pair[0]+'_'+$pair[1]+'_'+$tag+'.json');$calls+=InvokeOwned $build.program.path @('--compare',(Join-Path (Output $pair[0]) 'data'),(Join-Path (Output $pair[1]) 'data'),"$part",'512',$json) ($prefix+'_compare_'+$pair[0]+'_'+$tag);$c=Get-Content -Raw -LiteralPath $json|ConvertFrom-Json
    if(!$c.passed -or $c.arrays -ne 15 -or $c.native_count -ne 512 -or !$c.all_original_physical_array_bits_identical -or !$c.native_ID_aligned -or !$c.saved_time_step_dterror_exact -or !$c.no_exclusions -or [double]$c.actual_time_s -ne $t -or $c.saved_step -ne $step -or [double]$c.dterror_s -gt 1e-14 -or $c.observer_schema_a -or [bool]$c.observer_schema_b -ne ($pair[1] -eq 'observer')){throw 'Original15/clock/signed-dterror/observer-schema exact gate failed'};$reports+=Entry $json
  }
  $csv=Join-Path $review ('poro_'+$tag+'.csv');$json=Join-Path $review ('poro_'+$tag+'.json');$calls+=InvokeOwned $build.program.path @('--read-poro',(Join-Path (Output 'observer') 'data'),"$part",'512','0','.25',$csv,$json) ($prefix+'_poro_'+$tag);$p=Get-Content -Raw -LiteralPath $json|ConvertFrom-Json
  if(!$p.passed -or $p.double_arrays -ne 3 -or $p.native_count -ne 512 -or $p.fixed_count -ne 0 -or !$p.derived_n_exact -or [double]$p.n0 -ne .25 -or [double]$p.actual_time_s -ne $t -or $p.saved_step -ne $step){throw 'Saved observer ledger/clock gate failed'}
  $maxJDelta=[Math]::Max($maxJDelta,[Math]::Max([Math]::Abs([double]$p.min_J-1),[Math]::Abs([double]$p.max_J-1)));$maxTheta=[Math]::Max($maxTheta,[double]$p.max_abs_theta_s_inv);$reports+=@(Entry $csv;Entry $json)
}
$donePath=Join-Path (Output 'observer') 'observer_complete.json';$done=Get-Content -Raw -LiteralPath $donePath|ConvertFrom-Json
if(!$done.passed -or !$done.observer -or !$done.actual_production_Run -or !$done.live_GPU_download -or !$done.predictor_history_released -or $done.public_dynamic_seepage -or $done.physical_fields_rewritten_by_fixture -or $done.feedback -or $done.physical_acceptance -or $done.native_count -ne 512 -or $done.fixed_count -ne 0 -or $done.completed_steps -ne $job.steps -or [double]$done.actual_time_s -ne [double]$job.end -or [double]$done.n0 -ne .25){throw 'Actual Run/final-live scope differs'}
$last=Entry (Join-Path $review ('poro_'+($job.samples-1).ToString('D4')+'.csv'));$live=Entry (Join-Path (Output 'observer') 'observer_final.csv')
if($last.bytes -ne $live.bytes -or $last.sha256 -ne $live.sha256 -or $maxJDelta -le 0 -or $maxTheta -le 0){throw 'Native/live observer mismatch or empty J/theta path'}
VerifyBuild;foreach($r in @($old,$new,$on)){Verify $r.files}
$files=@(Get-ChildItem -LiteralPath $review -File|ForEach-Object {Entry $_.FullName})
NewJson $final ([ordered]@{passed=$true;window=$Window;configuration=$Configuration;steps=$job.steps;samples=$job.samples;native=512;original_arrays=15;all_original15_exact=$true;all_actual_saved_time_step_signed_dterror_exact=$true;three_native_double_observer_arrays_checked=$true;max_abs_J_minus_1=$maxJDelta;max_abs_theta=$maxTheta;final_live_native_csv_exact=$true;completion=(Entry $donePath);live_native_equal=@($last,$live);build=(Entry $buildPath);solvers=@(Entry (SolverCheck 'oldoff');Entry (SolverCheck 'newoff');Entry (SolverCheck 'observer'));calls=$calls;files=$files;canonical_GPU_unchanged=$true;independent_theta_or_J_recurrence_tested=$false;dynamic_feedback_tested=$false;physical_acceptance=$false})
Write-Output 'PASSED bounded same-GPU observer nonfeedback native wiring only'
