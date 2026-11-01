param(
  [Parameter(Mandatory=$true)][ValidateSet('FreezeBaseline','BuildGpu','BuildHelper')][string]$Mode,
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [ValidateSet('Feedback','Native','State','Theta')][string]$Fixture='Feedback',
  [switch]$ProductionBuildConfirmed,[switch]$ExecutionAuthorized
)
# Build support only: no program/component/solver execution, canonical overwrite or Git mutation.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src';$logs=Join-Path $tests 'logs';$outputs=Join-Path $tests 'outputs'
$checkpoint='c91ee27f2d89639db202333e6fc2331f57daa640'
$plan=Join-Path $tests 'notes\upl_gpu_feedback_plan_r1.json';$priorStage=Join-Path $logs 'upl_gpu_observer_stage_r1.check.json'
$baselinePath=Join-Path $logs 'upl_gpu_feedback_r1.baseline.json';$baseFolder=Join-Path $outputs 'upl_gpu_feedback_prebuild_r1'
$solution=Join-Path $src 'VS\DualSPHysics5Re.sln';$project=Join-Path $src 'VS\DualSPHysics5Re.vcxproj'
$five=@('JSphGpu.h','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu')
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Resolve([string]$p){if([IO.Path]::IsPathRooted($p)){$p}else{Join-Path $repo $p}}
function Verify($rows){foreach($r in $rows){$a=Entry (Resolve $r.path);if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function CopyBound($r,[string]$p){Verify @($r);if(Test-Path -LiteralPath $p){throw 'Retained copy protected'};Copy-Item -LiteralPath (Resolve $r.path) -Destination $p;$a=Entry $p;if($a.sha256 -ne $r.sha256){throw 'Copy differs'};@{original=$r;copy=$a}}
function Sources {Get-ChildItem -LiteralPath (Join-Path $src 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl','.cpp','.cu'}|ForEach-Object {Entry $_.FullName}}
function InvokeOwned([string]$exe,[string[]]$argv,[string]$label){
  $log=Join-Path $logs ($label+'.log');$record=Join-Path $logs ($label+'.call.json');if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $record)){throw 'Owned build retained; no retry'}
  $program=Entry $exe;$start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@())
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue';& $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE;$ErrorActionPreference=$old
  Verify @($program);NewJson $record ([ordered]@{exit_code=$code;owned_call_exited=$true;program=$program;arguments=$argv;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);program_or_component_run=$false;physical_acceptance=$false})
  if($code -ne 0){throw "Build failed; preserve $record"};Entry $record
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root review and explicit single-action authorization required'}
$old=$ErrorActionPreference;$ErrorActionPreference='Continue';$head=& git -C $repo rev-parse HEAD;$code=$LASTEXITCODE;$ErrorActionPreference=$old
if($code -or $head -ne $checkpoint){throw 'Exact verified observer checkpoint required'}
if($Mode -eq 'FreezeBaseline'){
  if((Test-Path -LiteralPath $baselinePath) -or (Test-Path -LiteralPath $baseFolder)){throw 'Pre-edit feedback baseline retained'}
  $stage=Get-Content -Raw -LiteralPath $priorStage|ConvertFrom-Json
  if(!$stage.passed -or $stage.native.Count -ne 3 -or $stage.components.Count -ne 4 -or !$stage.all_other_source_and_old_canonical_GPU_hashes_unchanged -or $stage.physical_acceptance){throw 'Accepted bounded observer aggregate required'}
  Verify $stage.source;Verify $stage.source_builds;Verify @($stage.context,$stage.pre_edit_baseline)
  $observerBase=Get-Content -Raw -LiteralPath (Resolve $stage.pre_edit_baseline.path)|ConvertFrom-Json;$canonical=$observerBase.canonical_GPU;Verify $canonical
  $source=@(Sources);$inputs=@(Entry $PSCommandPath;Entry $plan;Entry $priorStage;Entry $solution;Entry $project);$oldPrograms=@()
  foreach($cfg in @('Debug','Release')){
    $p=Join-Path $logs ('upl_gpu_observer_'+$cfg+'_r1.build.json');$b=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json
    if($b.status -ne 'full_authoritative_GPU_Rebuild_passed_no_fixture_or_program_run' -or $b.configuration -ne $cfg -or !$b.canonical_GPU_unchanged){throw 'Actual retained observer GPU full-project build required'}
    Verify $b.inputs;Verify @($b.isolated_GPU_program,$b.source_freeze);foreach($r in $b.runtime){Verify @($r.original,$r.snapshot)}
    $oldPrograms+=@{configuration=$cfg;build=(Entry $p);program=$b.isolated_GPU_program;runtime=$b.runtime};$inputs+=Entry $p
  }
  [void](New-Item -ItemType Directory -Path $baseFolder);$oldSources=@()
  foreach($leaf in $five){$oldSources+=CopyBound (Entry (Join-Path $src ('source\'+$leaf))) (Join-Path $baseFolder $leaf)}
  $programs=@();foreach($b in $oldPrograms){$program=CopyBound $b.program (Join-Path $baseFolder ($b.configuration+'_'+[IO.Path]::GetFileName($b.program.path)));$runtime=@();foreach($r in $b.runtime){$runtime+=CopyBound $r.snapshot (Join-Path $baseFolder ($b.configuration+'_'+[IO.Path]::GetFileName($r.snapshot.path)))};$programs+=@{configuration=$b.configuration;build=$b.build;program=$program;runtime=$runtime}}
  Verify $source;Verify $inputs;Verify $canonical
  NewJson $baselinePath ([ordered]@{status='pre_five_feedback_edits_source_and_retained_observer_GPU_programs_frozen';root_verified_checkpoint=$checkpoint;inputs=$inputs;source=$source;old_five_sources=$oldSources;retained_observer_GPU_programs=$programs;canonical_GPU=$canonical;reference='Actual isolated observer full-project GPU programs/runtime, not old canonical as current source truth';helper_author_files_frozen=$false;program_or_component_run=$false;physical_acceptance=$false})
  Write-Output 'FROZEN only; root may now apply the five-file private feedback patch';exit 0
}
$baseline=Get-Content -Raw -LiteralPath $baselinePath|ConvertFrom-Json
if($baseline.status -ne 'pre_five_feedback_edits_source_and_retained_observer_GPU_programs_frozen' -or $baseline.root_verified_checkpoint -ne $checkpoint -or $baseline.old_five_sources.Count -ne 5){throw 'Pre-edit feedback baseline required'}
Verify $baseline.inputs;Verify $baseline.canonical_GPU;Verify @($baseline.source|Where-Object {[IO.Path]::GetFileName($_.path) -notin $five})
foreach($r in $baseline.old_five_sources){Verify @($r.copy)};foreach($r in $baseline.retained_observer_GPU_programs){Verify @($r.program.original,$r.program.copy);foreach($v in $r.runtime){Verify @($v.original,$v.copy)}}
$name='upl_gpu_feedback_'+$Configuration+'_r1';$folder=Join-Path $outputs $name;$buildPath=Join-Path $logs ($name+'.build.json')
if($Mode -eq 'BuildGpu' -and $Configuration -eq 'Release'){$p=Join-Path $logs 'upl_gpu_feedback_Debug_r1.build.json';$d=Get-Content -Raw -LiteralPath $p|ConvertFrom-Json;if($d.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run'){throw 'Debug authoritative build required first'};Verify @($d.source_freeze,$d.project_call,$d.isolated_GPU_program)}
$env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$cuda=$env:CUDA_PATH_V11_7;$msbuild='D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe';$cl=Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\cl.exe';$link=Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\link.exe'
if($Mode -eq 'BuildGpu'){
  $freezePath=Join-Path $logs ($name+'.source.json');$intdir=Join-Path ([IO.Path]::GetTempPath()) ('upl_gpu_feedback_r1\'+$Configuration+'\int\')
  if($intdir -match '\s'){throw 'CUDA intermediate directory must have no spaces'};foreach($p in @($folder,$intdir,$buildPath,$freezePath)){if(Test-Path -LiteralPath $p){throw "Retained build artifact: $p"}}
  [void](New-Item -ItemType Directory -Path $folder);[void](New-Item -ItemType Directory -Path $intdir);$snapshots=@()
  foreach($leaf in $five){$snapshots+=CopyBound (Entry (Join-Path $src ('source\'+$leaf))) (Join-Path $folder $leaf)}
  $inputs=@(Entry $PSCommandPath;Entry $plan;Entry $baselinePath;Entry $solution;Entry $project)+@(Sources)
  NewJson $freezePath ([ordered]@{status='five_feedback_sources_frozen_before_authoritative_GPU_Rebuild';baseline=(Entry $baselinePath);source=$snapshots;inputs=$inputs;helper_author_files_frozen=$false;program_or_component_run=$false})
  $tools=@(Entry $msbuild;Entry (Join-Path $cuda 'bin\nvcc.exe');Entry $cl;Entry $link);$gpuout=Join-Path $folder 'gpu\';[void](New-Item -ItemType Directory -Path $gpuout)
  $argv=@($solution,'/m:1','/nr:false','/t:Rebuild','/v:minimal',"/p:Configuration=$Configuration",'/p:Platform=x64','/p:PlatformToolset=v143','/p:VCToolsVersion=14.36.32532','/p:BuildProjectReferences=false','/p:PostBuildEventUseInBuild=false',('/p:OutDir='+$gpuout.Replace('\','/')),('/p:IntDir='+$intdir.Replace('\','/')),('/bl:'+(Join-Path $logs ($name+'.binlog'))))
  $call=InvokeOwned $msbuild $argv ($name+'_project');Verify $inputs;Verify $tools;Verify $baseline.canonical_GPU
  [xml]$xml=Get-Content -Raw -LiteralPath $project;$objects=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include] | //*[local-name()='CudaCompile'][@Include]")){
    $excluded=$false;foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){$condition=$e.GetAttribute('Condition').Replace('$(Configuration)',$Configuration).Replace('$(Platform)','x64').Replace(' ','');if(!$condition -or $condition -eq "'$Configuration|x64'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $include=$node.GetAttribute('Include');$leaf=[IO.Path]::GetFileNameWithoutExtension($include);if($excluded -or $leaf -eq 'main'){continue};$objLeaf=if($node.LocalName -eq 'CudaCompile'){[IO.Path]::GetFileName($include)+'.obj'}else{$leaf+'.obj'};$objects+=Entry (Join-Path $intdir $objLeaf)
  }
  if($objects.Count -lt 80){throw 'Incomplete authoritative GPU object closure'}
  $r=@($baseline.retained_observer_GPU_programs|Where-Object {$_.configuration -eq $Configuration});if($r.Count -ne 1){throw 'Retained runtime ambiguous'};$runtime=@();foreach($v in $r[0].runtime){$runtime+=CopyBound $v.copy (Join-Path $gpuout ([IO.Path]::GetFileName($v.original.path)))}
  $gpuLeaf=if($Configuration -eq 'Debug'){'DualSPHysics5.2_win64_debug.exe'}else{'DualSPHysics5.2_GEO_win64.exe'};Verify $inputs;Verify $tools;Verify $baseline.canonical_GPU
  NewJson $buildPath ([ordered]@{status='full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run';configuration=$Configuration;baseline=(Entry $baselinePath);source_freeze=(Entry $freezePath);inputs=$inputs;tools=$tools;objects=$objects;objects_exclude_main=$true;project_call=$call;isolated_GPU_program=(Entry (Join-Path $gpuout $gpuLeaf));runtime=$runtime;no_space_IntDir=$intdir;isolated_GPU_OutDir=$gpuout;helper_author_files_frozen=$false;canonical_GPU_unchanged=$true;program_or_component_run=$false;physical_acceptance=$false})
  Write-Output 'BUILT GPU only; optional helper requires a separate BuildHelper action';exit 0
}
$gpu=Get-Content -Raw -LiteralPath $buildPath|ConvertFrom-Json
if($gpu.status -ne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $gpu.configuration -ne $Configuration -or !$gpu.objects_exclude_main){throw 'Actual authoritative feedback GPU objects required'}
$stem=if($Fixture -eq 'Feedback'){'upl_gpu_feedback_r1'}else{'upl_gpu_observer_'+$Fixture.ToLowerInvariant()+'_r1'}
$cpp=Join-Path $PSScriptRoot ($stem+'.cpp');$note=Join-Path $tests ('notes\'+$stem+'.json')
$helperName='upl_gpu_feedback_'+$Fixture+'_'+$Configuration+'_r1';$helperFolder=Join-Path $outputs $helperName;$helperPath=Join-Path $logs ($helperName+'.helper.json')
if((Test-Path -LiteralPath $helperFolder) -or (Test-Path -LiteralPath $helperPath)){throw 'Chosen helper build retained'}
$inputs=@(Entry $PSCommandPath;Entry $plan;Entry $cpp;Entry $note;Entry $buildPath)
function VerifyGpu {Verify $inputs;Verify $gpu.inputs;Verify $gpu.tools;Verify $gpu.objects;Verify @($gpu.baseline,$gpu.source_freeze,$gpu.project_call,$gpu.isolated_GPU_program);Verify $baseline.canonical_GPU;foreach($v in $gpu.runtime){Verify @($v.original,$v.copy)}}
VerifyGpu;[void](New-Item -ItemType Directory -Path $helperFolder);$snapshots=@();foreach($p in @($PSCommandPath,$cpp,$note)){$snapshots+=CopyBound (Entry $p) (Join-Path $helperFolder ([IO.Path]::GetFileName($p)))}
$runtime=@();foreach($v in $gpu.runtime){$runtime+=CopyBound $v.copy (Join-Path $helperFolder ([IO.Path]::GetFileName($v.copy.path)))}
$libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$Configuration.lib","LibJNumexLib_x64_v143_$Configuration.lib","LibJWaveGen_x64_v143_$Configuration.lib","LibDSphMoorDyn_x64_v143_$Configuration.lib")
$libraries=@($libs|ForEach-Object {Entry (Join-Path $src ('lib\vs2022\'+$_))})+@(Entry (Join-Path $cuda 'lib\x64\cudart_static.lib'));$tools=@(Entry $cl;Entry $link)
$obj=Join-Path $helperFolder 'helper.obj';$exe=Join-Path $helperFolder ($stem+'.exe');$flags=if($Configuration -eq 'Debug'){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
$compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/D_WITHGPU',"/I$src\source","/I$cuda\include","/Fo$obj","/Fd$helperFolder\compile.pdb")+$flags+@($cpp)
$cc=InvokeOwned $cl $compile ($helperName+'_compile');$system=@('kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
$argv=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$src\lib\vs2022","/LIBPATH:$cuda\lib\x64",$obj)+@($gpu.objects.path)+$libs+$system+@('cudart_static.lib');if($Configuration -eq 'Debug'){$argv+=@('/DEBUG',"/PDB:$helperFolder\link.pdb")}
$lc=InvokeOwned $link $argv ($helperName+'_link');VerifyGpu;Verify $tools;Verify $libraries
NewJson $helperPath ([ordered]@{status='actual_authoritative_GPU_objects_helper_linked_not_run';fixture=$Fixture;configuration=$Configuration;source_build=(Entry $buildPath);inputs=$inputs;snapshots=$snapshots;runtime=$runtime;program=(Entry $exe);tools=$tools;libraries=$libraries;compile_call=$cc;link_call=$lc;only_chosen_helper_author_files_frozen=$true;other_helper_inputs_bound=$false;canonical_GPU_unchanged=$true;program_or_component_run=$false;physical_acceptance=$false})
Write-Output 'BUILT chosen helper only; root separately owns all component/native calls and gates'
