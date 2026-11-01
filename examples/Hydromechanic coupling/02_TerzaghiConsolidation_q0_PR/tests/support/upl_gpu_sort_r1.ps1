param(
  [Parameter(Mandatory=$true)][ValidateSet('FreezeBaseline','Build','Run')][string]$Mode,
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# One explicit action. No solver, GenCase, notifier, canonical overwrite or retry.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src';$logs=Join-Path $tests 'logs';$outputs=Join-Path $tests 'outputs'
$project=Join-Path $src 'VS\DualSPHysics5Re.vcxproj';$solution=Join-Path $src 'VS\DualSPHysics5Re.sln'
$cpp=Join-Path $PSScriptRoot 'upl_gpu_sort_r1.cpp';$note=Join-Path $tests 'notes\upl_gpu_sort_r1.json'
$baselinePath=Join-Path $logs 'upl_gpu_sort_r1.baseline.json'
$publicCheck=Join-Path $logs 'upl_cpu_public_independent_r1.check.json'
$allowed=@('JCellDivGpu.h','JCellDivGpu.cpp','JCellDivGpu_ker.h','JCellDivGpu_ker.cu')
function Entry([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ne $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function NewJson([string]$p,$value){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function InvokeOwned([string]$exe,[string[]]$argv,[string]$label){
  $log=Join-Path $logs ($label+'.log');$receipt=Join-Path $logs ($label+'.call.json')
  if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt)){throw 'Owned tool call retained; no retry'}
  $program=Entry $exe;$start=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@())
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$exitcode=$LASTEXITCODE;$ErrorActionPreference=$old
  Verify @($program)
  NewJson $receipt ([ordered]@{exit_code=$exitcode;owned_call_exited=$true;program=$program;arguments=$argv;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $log);physical_acceptance=$false})
  if($exitcode -ne 0){throw "Owned component/build call failed; preserve $receipt"};Entry $receipt
}
if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Root source review and explicit single-action authorization required'}
$cpu=Get-Content -LiteralPath $publicCheck -Raw|ConvertFrom-Json
if(!$cpu.passed -or $cpu.source_files -ne 7 -or $cpu.identity_mismatches -ne 0 -or $cpu.jobs.Count -ne 9 -or $cpu.rejections.Count -ne 11){throw 'Reviewed public CPU nine-job/eleven-invalid stage required'}
$baseFolder=Join-Path $outputs 'upl_gpu_sort_prebuild_r1'
if($Mode -eq 'FreezeBaseline'){
  if((Test-Path -LiteralPath $baselinePath) -or (Test-Path -LiteralPath $baseFolder)){throw 'Pre-edit baseline retained'}
  [void](New-Item -ItemType Directory -Path $baseFolder)
  $source=@(Get-ChildItem -LiteralPath (Join-Path $src 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl','.cpp','.cu'}|ForEach-Object {Entry $_.FullName})
  $oldSources=@();foreach($leaf in $allowed){$p=Join-Path $src ('source\'+$leaf);$target=Join-Path $baseFolder $leaf;Copy-Item -LiteralPath $p -Destination $target;$a=Entry $p;$b=Entry $target;if($a.sha256 -ne $b.sha256){throw 'Old source snapshot differs'};$oldSources+=@{original=$a;snapshot=$b}}
  $runtimePaths=@(Join-Path $repo 'bin\windows\DualSPHysics5.2_win64_debug.exe';Join-Path $repo 'bin\windows\DualSPHysics5.2_GEO_win64.exe';Join-Path $repo 'bin\windows\DsphConfig.xml')+@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})
  $runtime=@();foreach($p in $runtimePaths){$a=Entry $p;$target=Join-Path $baseFolder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $target;$b=Entry $target;if($a.sha256 -ne $b.sha256){throw 'Old canonical/runtime snapshot differs'};$runtime+=@{original=$a;snapshot=$b}}
  Verify $source;foreach($r in $runtime){Verify @($r.original,$r.snapshot)}
  NewJson $baselinePath ([ordered]@{status='pre_four_edit_source_and_old_GPU_binaries_frozen';root_verified_CPU_checkpoint='25f40dc13b8bfacf698aab3e7668ec2afb252788';inputs=@(Entry $PSCommandPath;Entry $cpp;Entry $note;Entry $publicCheck;Entry $project;Entry $solution);source=$source;old_four_sources=$oldSources;old_GPU_runtime=$runtime;old_binary_build_source_identity_claimed=$false;program_executed=$false;physical_acceptance=$false})
  Write-Output 'FROZEN only; root may now apply exactly four source overload edits';exit 0
}
$baseline=Get-Content -LiteralPath $baselinePath -Raw|ConvertFrom-Json
if($baseline.status -ne 'pre_four_edit_source_and_old_GPU_binaries_frozen' -or $baseline.old_four_sources.Count -ne 4){throw 'Pre-edit baseline missing'}
Verify $baseline.inputs;foreach($r in $baseline.old_four_sources){Verify @($r.snapshot)};foreach($r in $baseline.old_GPU_runtime){Verify @($r.original,$r.snapshot)}
# The four old source originals are expected to change; all other sources must not.
Verify @($baseline.source|Where-Object {[IO.Path]::GetFileName($_.path) -notin $allowed})
$changed=@();foreach($r in $baseline.old_four_sources){$current=Entry $r.original.path;if($current.sha256 -eq $r.original.sha256){throw 'Expected overload source edit is absent'};$changed+=$current}
$name='upl_gpu_sort_'+$Configuration+'_r1';$folder=Join-Path $outputs $name
$buildPath=Join-Path $logs ($name+'.build.json');$checkPath=Join-Path $logs ($name+'.check.json')
if($Configuration -eq 'Release'){
  $priorPath=Join-Path $logs 'upl_gpu_sort_Debug_r1.check.json';$prior=Get-Content -LiteralPath $priorPath -Raw|ConvertFrom-Json
  if(!$prior.passed -or !$prior.memcheck_zero_errors -or $prior.cases -ne 576){throw 'Actual Debug memcheck gate required first'};Verify $prior.files;Verify @($prior.completion,$prior.call,$prior.build)
}
if($Mode -eq 'Build'){
  $intdir=Join-Path ([IO.Path]::GetTempPath()) ('upl_gpu_sort_r1\'+$Configuration+'\int\')
  if($intdir -match '\s'){throw 'CUDA intermediate directory must have no spaces'}
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $intdir) -or (Test-Path -LiteralPath $buildPath)){throw 'Build/intermediate directory retained; choose a reviewed new label'}
  [void](New-Item -ItemType Directory -Path $folder);[void](New-Item -ItemType Directory -Path $intdir)
  $snapshots=@();foreach($r in $changed){$target=Join-Path $folder ([IO.Path]::GetFileName($r.path));Copy-Item -LiteralPath $r.path -Destination $target;$a=Entry $target;if($a.sha256 -ne $r.sha256){throw 'New four-source prebuild snapshot differs'};$snapshots+=@{original=$r;snapshot=$a}}
  $inputs=@(Entry $PSCommandPath;Entry $cpp;Entry $note;Entry $baselinePath;Entry $publicCheck;Entry $project;Entry $solution)+@(Get-ChildItem -LiteralPath (Join-Path $src 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl','.cpp','.cu'}|ForEach-Object {Entry $_.FullName})
  $sourceFreeze=Join-Path $logs ($name+'.source.json');NewJson $sourceFreeze ([ordered]@{status='four_new_sort_sources_frozen_before_full_GPU_Rebuild';baseline=(Entry $baselinePath);source=$snapshots;inputs=$inputs;program_executed=$false})
  $env:VSCMD_SKIP_SENDTELEMETRY='1';$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment failed'};foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $cuda=$env:CUDA_PATH_V11_7;$msbuild='D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe'
  [void](Entry (Join-Path $cuda 'bin\nvcc.exe'));[void](Entry (Join-Path $cuda 'lib\x64\cudart_static.lib'))
  $toolInputs=@(Entry $msbuild;Entry (Join-Path $cuda 'bin\nvcc.exe');Entry (Join-Path $cuda 'compute-sanitizer\compute-sanitizer.exe');Entry (Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\cl.exe');Entry (Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\link.exe'))
  $gpuout=Join-Path $folder 'gpu\';[void](New-Item -ItemType Directory -Path $gpuout)
  $buildArgs=@($solution,'/m:1','/nr:false','/t:Rebuild','/v:minimal',"/p:Configuration=$Configuration",'/p:Platform=x64','/p:PlatformToolset=v143','/p:VCToolsVersion=14.36.32532','/p:BuildProjectReferences=false','/p:PostBuildEventUseInBuild=false',('/p:OutDir='+$gpuout.Replace('\','/')),('/p:IntDir='+$intdir.Replace('\','/')),('/bl:'+(Join-Path $logs ($name+'.binlog'))))
  $buildCall=InvokeOwned $msbuild $buildArgs ($name+'_project')
  Verify $inputs;foreach($r in $baseline.old_GPU_runtime){Verify @($r.original,$r.snapshot)}
  # Resolve every authoritative active project object in this fresh no-space IntDir.
  [xml]$xml=Get-Content -LiteralPath $project -Raw;$objects=@();$sourcePaths=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include] | //*[local-name()='CudaCompile'][@Include]")){
    $excluded=$false;foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){$condition=$e.GetAttribute('Condition').Replace('$(Configuration)',$Configuration).Replace('$(Platform)','x64').Replace(' ','');if(!$condition -or $condition -eq "'$Configuration|x64'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $include=$node.GetAttribute('Include');$leaf=[IO.Path]::GetFileNameWithoutExtension($include);if($excluded -or $leaf -eq 'main'){continue}
    $objLeaf=if($node.LocalName -eq 'CudaCompile'){[IO.Path]::GetFileName($include)+'.obj'}else{$leaf+'.obj'}
    $p=Join-Path $intdir $objLeaf;[void](Entry $p);$objects+=$p;$sourcePaths+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $include))
  }
  if($objects.Count -lt 80){throw 'Incomplete authoritative GPU object closure'}
  $suffix=$Configuration;$libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib")
  $system=@('kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs|ForEach-Object {Entry (Join-Path $src ('lib\vs2022\'+$_))})+@(Entry (Join-Path $cuda 'lib\x64\cudart_static.lib'))
  $obj=Join-Path $folder 'sort_fixture.obj';$exe=Join-Path $folder 'upl_gpu_sort_r1.exe'
  $flags=if($Configuration -eq 'Debug'){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/D_WITHGPU',"/I$src\source","/I$cuda\include","/Fo$obj","/Fd$folder\compile.pdb")+$flags+@($cpp)
  $compileCall=InvokeOwned (Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\cl.exe') $compile ($name+'_fixture_compile')
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$src\lib\vs2022","/LIBPATH:$cuda\lib\x64",$obj)+$objects+$libs+$system+@('cudart_static.lib');if($Configuration -eq 'Debug'){$link+=@('/DEBUG',"/PDB:$folder\link.pdb")}
  $linkCall=InvokeOwned (Join-Path $env:VCToolsInstallDir 'bin\Hostx64\x64\link.exe') $link ($name+'_fixture_link')
  $runtime=@();foreach($r in $baseline.old_GPU_runtime){if([IO.Path]::GetExtension($r.original.path) -eq '.exe'){continue};$target=Join-Path $folder ([IO.Path]::GetFileName($r.original.path));Copy-Item -LiteralPath $r.original.path -Destination $target;$runtime+=Entry $target}
  Verify $inputs;Verify $toolInputs;Verify $libraries;foreach($r in $baseline.old_GPU_runtime){Verify @($r.original,$r.snapshot)}
  $gpuLeaf=if($Configuration -eq 'Debug'){'DualSPHysics5.2_win64_debug.exe'}else{'DualSPHysics5.2_GEO_win64.exe'}
  NewJson $buildPath ([ordered]@{status='full_GPU_Rebuild_and_actual_object_fixture_link_passed_not_run';configuration=$Configuration;baseline=(Entry $baselinePath);source_freeze=(Entry $sourceFreeze);inputs=$inputs;tools=$toolInputs;objects=@($objects|ForEach-Object {Entry $_});libraries=$libraries;runtime=$runtime;project_call=$buildCall;compile_call=$compileCall;link_call=$linkCall;isolated_GPU_program=(Entry (Join-Path $gpuout $gpuLeaf));program=(Entry $exe);no_space_IntDir=$intdir;isolated_GPU_OutDir=$gpuout;canonical_GPU_unchanged=$true;physics_or_default_OFF_solver_tested=$false;physical_acceptance=$false})
  Write-Output 'BUILT only; root may explicitly Run this configuration';exit 0
}
$build=Get-Content -LiteralPath $buildPath -Raw|ConvertFrom-Json
if($build.status -ne 'full_GPU_Rebuild_and_actual_object_fixture_link_passed_not_run' -or $build.configuration -ne $Configuration){throw 'Actual project-object fixture build required'}
Verify $build.inputs;Verify $build.tools;Verify $build.objects;Verify $build.libraries;Verify $build.runtime;Verify @($build.isolated_GPU_program,$build.program,$build.source_freeze,$build.project_call,$build.compile_call,$build.link_call)
if(Test-Path -LiteralPath $checkPath){throw 'Component check retained'}
$output=Join-Path $outputs ($name+'_data');if(Test-Path -LiteralPath $output){throw 'Component output retained'}
$memcheck=$Configuration -eq 'Debug'
if($memcheck){$tool=Join-Path $env:CUDA_PATH_V11_7 'compute-sanitizer\compute-sanitizer.exe';$call=InvokeOwned $tool @('--tool','memcheck','--leak-check','full','--error-exitcode','99',$build.program.path,'--run',$output) ($name+'_memcheck')}
else{$call=InvokeOwned $build.program.path @('--run',$output) ($name+'_component')}
$donePath=Join-Path $output 'complete.json';$done=Get-Content -LiteralPath $donePath -Raw|ConvertFrom-Json
if(!$done.passed -or $done.cases -ne 576 -or $done.direct_cases -ne 288 -or $done.wrapper_cases -ne 288 -or $done.zero_size_cases -ne 96 -or !$done.byte_exact -or !$done.source_unchanged -or !$done.map_unchanged -or !$done.tail_unchanged -or !$done.actual_class_wrapper -or $done.actual_cell_division_tested -or $done.physics_or_J_state_tested){throw 'Component completion gates differ'}
$rows=@(Import-Csv -LiteralPath (Join-Path $output 'cases.csv'));if($rows.Count -ne 576 -or @($rows|Where-Object {$_.output_exact -ne 'true' -or $_.source_unchanged -ne 'true' -or $_.map_unchanged -ne 'true' -or $_.tail_unchanged -ne 'true'}).Count){throw 'Not every component copy/prefix/guard row passed'}
$owned=Get-Content -LiteralPath $call.path -Raw|ConvertFrom-Json
if($memcheck -and (Get-Content -LiteralPath $owned.log.path -Raw) -notmatch 'ERROR SUMMARY: 0 errors'){throw 'Debug memcheck zero-error report missing'}
Verify $build.inputs;Verify $build.tools;Verify $build.objects;Verify $build.libraries;Verify $build.runtime;foreach($r in $baseline.old_GPU_runtime){Verify @($r.original,$r.snapshot)}
$files=@(Get-ChildItem -LiteralPath $output -File|ForEach-Object {Entry $_.FullName})
NewJson $checkPath ([ordered]@{passed=$true;configuration=$Configuration;cases=576;direct_cases=288;wrapper_cases=288;memcheck_executed=$memcheck;memcheck_zero_errors=$memcheck;build=(Entry $buildPath);completion=(Entry $donePath);call=$call;files=$files;canonical_GPU_unchanged=$true;actual_cell_division_tested=$false;J_state_or_physics_tested=$false;default_OFF_native_solver_regression_passed=$false;physical_acceptance=$false})
Write-Output 'PASSED copy/sort component only; no solver or physical admission'
