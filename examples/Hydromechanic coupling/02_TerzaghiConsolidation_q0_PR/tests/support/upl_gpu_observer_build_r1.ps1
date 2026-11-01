param(
  [Parameter(Mandatory=$true)][ValidateSet('FreezeBaseline','Build')][string]$Mode,
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# One explicit baseline/build action only. No helper interface, program, solver or Git action.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src';$logs=Join-Path $tests 'logs';$outputs=Join-Path $tests 'outputs'
$solution=Join-Path $src 'VS\DualSPHysics5Re.sln';$project=Join-Path $src 'VS\DualSPHysics5Re.vcxproj'
$plan=Join-Path $tests 'notes\upl_gpu_state_plan_r1.md'
$baselinePath=Join-Path $logs 'upl_gpu_observer_r1.baseline.json'
$baseFolder=Join-Path $outputs 'upl_gpu_observer_prebuild_r1'
$sortBaselinePath=Join-Path $logs 'upl_gpu_sort_r1.baseline.json'
$allowed=@('JSphGpu.h','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$value){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Sources {Get-ChildItem -LiteralPath (Join-Path $src 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl','.cpp','.cu'}|ForEach-Object {Entry $_.FullName}}
function CopyBound($original,[string]$target){Verify @($original);if(Test-Path -LiteralPath $target){throw 'Snapshot retained'};Copy-Item -LiteralPath $original.path -Destination $target;$copy=Entry $target;if($copy.sha256 -ne $original.sha256){throw 'Snapshot differs'};@{original=$original;snapshot=$copy}}
function InvokeBuild([string]$exe,[string[]]$argv,[string]$label){
  $log=Join-Path $logs ($label+'.log');$receipt=Join-Path $logs ($label+'.call.json')
  if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt)){throw 'Owned build retained; no retry'}
  $program=Entry $exe;$start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@())
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  Verify @($program)
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$program;arguments=$argv;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);program_or_solver_executed=$false;physical_acceptance=$false})
  if($code -ne 0){throw "Authoritative build failed; preserve $receipt"};Entry $receipt
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root source review and explicit single-action authorization required'}
if($Mode -eq 'FreezeBaseline'){
  if((Test-Path -LiteralPath $baselinePath) -or (Test-Path -LiteralPath $baseFolder)){throw 'Pre-edit baseline retained'}
  $source=@(Sources);$inputs=@(Entry $PSCommandPath;Entry $plan;Entry $solution;Entry $project;Entry $sortBaselinePath)
  $sortBaseline=Get-Content -LiteralPath $sortBaselinePath -Raw|ConvertFrom-Json
  $canonical=@($sortBaseline.old_GPU_runtime|ForEach-Object {$_.original});Verify $canonical
  $retained=@()
  foreach($cfg in @('Debug','Release')){
    $checkPath=Join-Path $logs ('upl_gpu_sort_'+$cfg+'_r1.check.json');$c=Get-Content -LiteralPath $checkPath -Raw|ConvertFrom-Json
    if(!$c.passed -or $c.configuration -ne $cfg -or $c.cases -ne 576 -or !$c.canonical_GPU_unchanged){throw 'Both retained sort component checks required'}
    Verify @($c.build,$c.completion,$c.call);Verify $c.files
    $b=Get-Content -LiteralPath $c.build.path -Raw|ConvertFrom-Json
    if($b.status -ne 'full_GPU_Rebuild_and_actual_object_fixture_link_passed_not_run'){throw 'Retained authoritative sort project program required'}
    Verify $b.inputs;Verify @($b.isolated_GPU_program,$b.source_freeze);Verify $b.runtime
    $inputs+=@(Entry $checkPath;Entry $c.build.path)
    $retained+=@{configuration=$cfg;build=$c.build;check=(Entry $checkPath);program_entry=$b.isolated_GPU_program;runtime_entries=$b.runtime}
  }
  [void](New-Item -ItemType Directory -Path $baseFolder)
  $oldSources=@();foreach($leaf in $allowed){$p=Join-Path $src ('source\'+$leaf);$oldSources+=CopyBound (Entry $p) (Join-Path $baseFolder $leaf)}
  $programs=@();foreach($r in $retained){$program=CopyBound $r.program_entry (Join-Path $baseFolder ($r.configuration+'_'+[IO.Path]::GetFileName($r.program_entry.path)));$runtime=@();foreach($a in $r.runtime_entries){$runtime+=CopyBound $a (Join-Path $baseFolder ($r.configuration+'_'+[IO.Path]::GetFileName($a.path)))};$programs+=@{configuration=$r.configuration;build=$r.build;check=$r.check;program=$program;runtime=$runtime}}
  Verify $source;Verify $inputs;Verify $canonical
  NewJson $baselinePath ([ordered]@{status='pre_five_observer_edits_source_and_retained_sort_GPU_programs_frozen';root_verified_checkpoint='18235c6d054958c60c1226872216ceb315f1966c';inputs=$inputs;source=$source;old_five_sources=$oldSources;retained_sort_GPU_programs=$programs;canonical_GPU=$canonical;current_program_reference='retained isolated authoritative sort full-project GPU builds, not old canonical binaries';old_canonical_build_source_identity_claimed=$false;program_or_solver_executed=$false;physical_acceptance=$false})
  Write-Output 'FROZEN only; root may now edit the five observer source files';exit 0
}
$baseline=Get-Content -LiteralPath $baselinePath -Raw|ConvertFrom-Json
if($baseline.status -ne 'pre_five_observer_edits_source_and_retained_sort_GPU_programs_frozen' -or $baseline.old_five_sources.Count -ne 5){throw 'Pre-edit observer baseline required'}
Verify $baseline.inputs;Verify $baseline.canonical_GPU
foreach($r in $baseline.old_five_sources){Verify @($r.snapshot)}
foreach($r in $baseline.retained_sort_GPU_programs){Verify @($r.program.original,$r.program.snapshot);foreach($v in $r.runtime){Verify @($v.original,$v.snapshot)}}
Verify @($baseline.source|Where-Object {[IO.Path]::GetFileName($_.path) -notin $allowed})
$name='upl_gpu_observer_'+$Configuration+'_r1';$folder=Join-Path $outputs $name
$buildPath=Join-Path $logs ($name+'.build.json');$freezePath=Join-Path $logs ($name+'.source.json')
if($Configuration -eq 'Release'){$p=Join-Path $logs 'upl_gpu_observer_Debug_r1.build.json';$prior=Get-Content -LiteralPath $p -Raw|ConvertFrom-Json;if($prior.status -ne 'full_authoritative_GPU_Rebuild_passed_no_fixture_or_program_run'){throw 'Debug authoritative build required first'};Verify @($prior.source_freeze,$prior.project_call,$prior.isolated_GPU_program)}
$intdir=Join-Path ([IO.Path]::GetTempPath()) ('upl_gpu_observer_r1\'+$Configuration+'\int\')
if($intdir -match '\s'){throw 'CUDA intermediate directory must have no spaces'}
foreach($p in @($folder,$intdir,$buildPath,$freezePath)){if(Test-Path -LiteralPath $p){throw "Retained build artifact: $p"}}
[void](New-Item -ItemType Directory -Path $folder);[void](New-Item -ItemType Directory -Path $intdir)
$snapshots=@();foreach($leaf in $allowed){$p=Join-Path $src ('source\'+$leaf);$snapshots+=CopyBound (Entry $p) (Join-Path $folder $leaf)}
$inputs=@(Entry $PSCommandPath;Entry $plan;Entry $solution;Entry $project;Entry $baselinePath)+@(Sources)
NewJson $freezePath ([ordered]@{status='five_observer_sources_frozen_before_authoritative_GPU_Rebuild';baseline=(Entry $baselinePath);source=$snapshots;inputs=$inputs;program_or_solver_executed=$false})
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$cuda=$env:CUDA_PATH_V11_7;$msbuild='D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe'
$tools=@(Entry $msbuild;Entry (Join-Path $cuda 'bin\nvcc.exe');Entry (Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\cl.exe');Entry (Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\link.exe'))
$gpuout=Join-Path $folder 'gpu\';[void](New-Item -ItemType Directory -Path $gpuout)
$argv=@($solution,'/m:1','/nr:false','/t:Rebuild','/v:minimal',"/p:Configuration=$Configuration",'/p:Platform=x64','/p:PlatformToolset=v143','/p:VCToolsVersion=14.36.32532','/p:BuildProjectReferences=false','/p:PostBuildEventUseInBuild=false',('/p:OutDir='+$gpuout.Replace('\','/')),('/p:IntDir='+$intdir.Replace('\','/')),('/bl:'+(Join-Path $logs ($name+'.binlog'))))
$call=InvokeBuild $msbuild $argv ($name+'_project')
Verify $inputs;Verify $tools;Verify $baseline.canonical_GPU
# Bind actual authoritative objects for a later separately authored helper; do not link one here.
[xml]$xml=Get-Content -LiteralPath $project -Raw;$objects=@()
foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include] | //*[local-name()='CudaCompile'][@Include]")){
  $excluded=$false;foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){$condition=$e.GetAttribute('Condition').Replace('$(Configuration)',$Configuration).Replace('$(Platform)','x64').Replace(' ','');if(!$condition -or $condition -eq "'$Configuration|x64'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}}
  $include=$node.GetAttribute('Include');$leaf=[IO.Path]::GetFileNameWithoutExtension($include);if($excluded -or $leaf -eq 'main'){continue}
  $objLeaf=if($node.LocalName -eq 'CudaCompile'){[IO.Path]::GetFileName($include)+'.obj'}else{$leaf+'.obj'};$objects+=Entry (Join-Path $intdir $objLeaf)
}
if($objects.Count -lt 80){throw 'Incomplete authoritative GPU object closure'}
$priorRuntime=@($baseline.retained_sort_GPU_programs|Where-Object {$_.configuration -eq $Configuration});if($priorRuntime.Count -ne 1){throw 'Retained runtime configuration ambiguous'}
$runtime=@();foreach($r in $priorRuntime[0].runtime){Verify @($r.original,$r.snapshot);$target=Join-Path $gpuout ([IO.Path]::GetFileName($r.original.path));$runtime+=CopyBound $r.snapshot $target}
$gpuLeaf=if($Configuration -eq 'Debug'){'DualSPHysics5.2_win64_debug.exe'}else{'DualSPHysics5.2_GEO_win64.exe'}
Verify $inputs;Verify $tools;Verify $baseline.canonical_GPU
NewJson $buildPath ([ordered]@{status='full_authoritative_GPU_Rebuild_passed_no_fixture_or_program_run';configuration=$Configuration;baseline=(Entry $baselinePath);source_freeze=(Entry $freezePath);inputs=$inputs;tools=$tools;objects=$objects;objects_exclude_main=$true;project_call=$call;isolated_GPU_program=(Entry (Join-Path $gpuout $gpuLeaf));runtime=$runtime;no_space_IntDir=$intdir;isolated_GPU_OutDir=$gpuout;canonical_GPU_unchanged=$true;helper_interface_defined=$false;helper_linked=$false;program_or_solver_executed=$false;observer_or_default_OFF_native_tested=$false;physical_acceptance=$false})
Write-Output 'BUILT only; observer helper and native tests require separate reviewed authoring/authorization'
