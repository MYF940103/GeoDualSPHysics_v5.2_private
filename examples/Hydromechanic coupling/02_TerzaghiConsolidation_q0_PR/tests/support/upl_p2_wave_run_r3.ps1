param(
  [ValidateSet('Prepare','Build','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r3',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Bounded actual-step wave. Prepare/Run require explicit root authorization.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$logs=Join-Path $tests 'logs'
$name="upl_p2_wave_${Configuration}_$Label"
$buildOut=Join-Path $tests "outputs\$name"
$harness=Join-Path $PSScriptRoot 'upl_p2_wave_harness_r2.cpp'
$notes=Join-Path $tests 'notes\upl_p2_wave_r3.json'
$coarse=Join-Path $tests 'configs\upl_p2_wave_c_r2_Def.xml'
$addendum=Join-Path $tests 'configs\upl_p2_wave_h_r2_Def.xml'
$exe=Join-Path $buildOut 'upl_p2_wave_harness_r2.exe'
$buildReceipt=Join-Path $logs ($name+'.build.json')
function Entry([string]$path){
  $item=Get-Item -LiteralPath $path
  [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function NewJson([string]$path,$value){
  if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"}
  [IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
}
function Verify($entries){
  foreach($item in $entries){
    $now=Entry $item.path
    if($now.sha256 -ne $item.sha256 -or $now.bytes -ne $item.bytes){throw "Frozen artifact changed: $($item.path)"}
  }
}


function SeedGeometry([string]$prefix){
  [xml]$xml=Get-Content -LiteralPath ($prefix+'.xml') -Raw -Encoding UTF8
  $bytes=[IO.File]::ReadAllBytes($prefix+'_All.vtk')
  $head=[Text.Encoding]::ASCII.GetString($bytes,0,[Math]::Min(256,$bytes.Length))
  $match=[regex]::Match($head,'(?m)^POINTS ([0-9]+) float\r?\n')
  if(!$match.Success){throw 'Expected GenCase binary float VTK points for independent seed-coordinate check.'}
  $count=[int]$match.Groups[1].Value;$offset=$match.Index+$match.Length
  $xs=New-Object 'Collections.Generic.HashSet[double]';$zs=New-Object 'Collections.Generic.HashSet[double]';$pairs=New-Object 'Collections.Generic.HashSet[string]'
  $lattice=$true
  for($i=0;$i -lt $count;$i++){
    $p=@()
    for($axis=0;$axis -lt 3;$axis++){
      $at=$offset+4*($i*3+$axis)
      $little=[byte[]]@($bytes[$at+3],$bytes[$at+2],$bytes[$at+1],$bytes[$at])
      $p+=[double][BitConverter]::ToSingle($little,0)
    }
    [void]$xs.Add($p[0]);[void]$zs.Add($p[2])
    $ix=[int][Math]::Round($p[0]*128-.5);$iz=[int][Math]::Round($p[2]*128-.5)
    if($ix -lt 0 -or $ix -ge 16 -or $iz -lt 0 -or $iz -ge 8 -or $p[0] -ne (($ix+.5)/128) -or $p[1] -ne 0 -or $p[2] -ne (($iz+.5)/128) -or !$pairs.Add("$ix,$iz")){$lattice=$false}
  }
  $passed=[int]$xml.case.execution.particles.np -eq 128 -and [int]$xml.case.execution.particles.nb -eq 0 -and $count -eq 128 -and $xs.Count -eq 16 -and $zs.Count -eq 8 -and $pairs.Count -eq 128 -and $lattice
  [ordered]@{passed=$passed;xml_native_count=[int]$xml.case.execution.particles.np;xml_boundary_count=[int]$xml.case.execution.particles.nb;vtk_count=$count;unique_x=$xs.Count;unique_z=$zs.Count;cartesian_pairs=$pairs.Count;exact_half_dp_lattice=$lattice;position_x_range=@(($xs|Measure-Object -Minimum).Minimum,($xs|Measure-Object -Maximum).Maximum);position_z_range=@(($zs|Measure-Object -Minimum).Minimum,($zs|Measure-Object -Maximum).Maximum);xml=(Entry ($prefix+'.xml'));vtk=(Entry ($prefix+'_All.vtk'));physical_acceptance=$false}
}

if($Mode -eq 'Prepare'){
  if(!$ExecutionAuthorized){throw 'Authoring is not execution authorization. Wait for root approval.'}
  $prep=Join-Path $logs 'upl_p2_wave_seed_r2.inputs.json'
  if(Test-Path -LiteralPath $prep){throw 'Seed preparation is sealed; never overwrite.'}
  $gencase=Join-Path $repo 'bin\windows\GenCase_win64.exe'
  $before=@($coarse,$addendum,$notes,$PSCommandPath,$gencase)|ForEach-Object {Entry $_}
  $jobs=@()
  foreach($tag in @('c','h')){
    $def=Join-Path $tests ("configs\upl_p2_wave_"+$tag+"_r2_Def.xml")
    $dir=Join-Path $tests ("outputs\upl_p2_wave_seed_r2_"+$tag)
    $prefix=Join-Path $dir ("CaseUplWave_"+$tag);$log=Join-Path $logs ("upl_p2_wave_seed_r2_"+$tag+".log")
    if((Test-Path -LiteralPath $dir) -or (Test-Path -LiteralPath $log)){throw 'Retained seed target protected.'}
    New-Item -ItemType Directory -Path $dir|Out-Null
    [IO.File]::WriteAllBytes($log,[byte[]]@())
    $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
    & $gencase ($def.Substring(0,$def.Length-4)) $prefix '-save:all' 2>&1|Tee-Object -FilePath $log|Out-Host
    $exit=$LASTEXITCODE;$ErrorActionPreference=$oldAction
    $files=@(Get-ChildItem -LiteralPath $dir -Recurse -File|Sort-Object FullName|ForEach-Object {Entry $_.FullName})
    $receipt=Join-Path $logs ("upl_p2_wave_seed_r2_"+$tag+".run.json")
    NewJson $receipt ([ordered]@{exit_code=$exit;program=(Entry $gencase);definition=(Entry $def);prefix=$prefix;files=$files;log=(Entry $log);solver_started=$false})
    if($exit -ne 0 -or !(Test-Path -LiteralPath ($prefix+'.bi4'))){throw 'GenCase failed; preserve and diagnose without retry.'}
    $geometry=SeedGeometry $prefix
    $geometryReceipt=Join-Path $logs ("upl_p2_wave_seed_r2_"+$tag+".geometry.check.json")
    NewJson $geometryReceipt $geometry
    if(!$geometry.passed){throw 'Wrong generated seed geometry; no Build/Run admitted.'}
    $jobs+=Entry $receipt
    $jobs+=Entry $geometryReceipt
  }
  Verify $before
  NewJson $prep ([ordered]@{status='seeds_prepared_not_solved';inputs=$before;jobs=$jobs;files=@($jobs|ForEach-Object {$j=Get-Content -LiteralPath $_.path -Raw|ConvertFrom-Json;if($j.files){$j.files}});solver_started=$false})
  Write-Output "PREPARED $prep";exit 0
}

if($Mode -eq 'Build'){
  if(!$ProductionBuildConfirmed){throw 'Wait for the root agent to finish and freeze both authoritative CPU builds.'}
  if((Test-Path -LiteralPath $buildOut) -or (Test-Path -LiteralPath $buildReceipt)){throw 'Use a fresh label; never overwrite a build.'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'Visual Studio environment setup failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj'
  [xml]$xml=Get-Content -LiteralPath $project -Raw
  $objects=@();$sourceFiles=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false
    foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){
      if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq "'`$(Configuration)|`$(Platform)'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}
    }
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){
      $objects+=Join-Path $source "VS\Intermediate\DualSPHysics_${Configuration}_x64\$stem.obj"
      $sourceFiles+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))
    }
  }
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($project,$harness,$PSCommandPath,$notes,$coarse,$addendum)+$objects+$sourceFiles+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $buildOut|Out-Null
  $snapshots=@()
  foreach($path in @($harness,$PSCommandPath,$notes,$coarse,$addendum)){
    $dest=Join-Path $buildOut ([IO.Path]::GetFileName($path))
    Copy-Item -LiteralPath $path -Destination $dest
    if((Entry $dest).sha256 -ne (Entry $path).sha256){throw 'Build recipe snapshot mismatch'}
    $snapshots+=Entry $dest
  }
  $obj=Join-Path $buildOut 'upl_p2_wave_harness_r2.obj'
  $log=Join-Path $logs ($name+'.build.log')
  if(Test-Path -LiteralPath $log){throw 'Build log already exists'}
  [IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$buildOut\compile.pdb",'/sourceDependencies',(Join-Path $buildOut 'compile.dependencies.json'))+$flags+@($harness)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs
  if($debug){$link+=@('/DEBUG',"/PDB:$buildOut\link.pdb")}
  $started=[DateTime]::UtcNow.ToString('o')
  $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host
  $compileExit=$LASTEXITCODE;$linkExit=$null
  if($compileExit -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$linkExit=$LASTEXITCODE}
  $ErrorActionPreference=$oldAction
  Verify $inputs;Verify $libraries;Verify $snapshots
  $runtime=@()
  if($compileExit -eq 0 -and $linkExit -eq 0){
    $runtimeSources=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml')
    foreach($path in $runtimeSources){
      $original=Entry $path;$dest=Join-Path $buildOut ([IO.Path]::GetFileName($path));Copy-Item -LiteralPath $path -Destination $dest
      $copy=Entry $dest;if($copy.sha256 -ne $original.sha256 -or (Entry $path).sha256 -ne $original.sha256){throw 'Runtime changed during copy'}
      $runtime+=@{original=$original;copy=$copy}
    }
  }
  NewJson $buildReceipt ([ordered]@{status=if($compileExit -eq 0 -and $linkExit -eq 0){'built_not_run'}else{'build_failed_retained'};configuration=$Configuration;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');git_head=(& git -C $repo rev-parse HEAD);compile_exit=$compileExit;link_exit=$linkExit;inputs=$inputs;libraries=$libraries;snapshots=$snapshots;compile=$compile;link=$link;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};log=(Entry $log);runtime=$runtime;physical_acceptance=$false})
  if($compileExit -ne 0 -or $linkExit -ne 0){throw 'Fixture build failed; inspect retained log and receipt. Do not overwrite.'}
  Write-Output "BUILT $exe";exit 0
}

if($Mode -eq 'Run'){
  if(!$ExecutionAuthorized -or !$ProductionBuildConfirmed){throw 'Wait for explicit root run authorization and authoritative build freeze.'}
  $build=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
  if($build.status -ne 'built_not_run'){throw 'No successful frozen build.'}
  Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program)
  foreach($item in $build.runtime){Verify @($item.copy)}
  $prepPath=Join-Path $logs 'upl_p2_wave_seed_r2.inputs.json'
  $prep=Get-Content -LiteralPath $prepPath -Raw|ConvertFrom-Json
  Verify $prep.inputs;Verify $prep.jobs;Verify $prep.files
  $final=Join-Path $logs ($name+'.check.json')
  if(Test-Path -LiteralPath $final){throw 'Retained final check protected.'}
  $program=Entry $exe;$receipts=@();$outputFolders=@();$completed=@{}
  function InvokeWave([string]$job,[string[]]$arguments){
    $log=Join-Path $logs ($job+'.log');$receipt=Join-Path $logs ($job+'.run.json')
    if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt)){throw 'Retained job protected.'}
    [IO.File]::WriteAllBytes($log,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o')
    $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
    & $exe @arguments 2>&1|Tee-Object -FilePath $log|Out-Host
    $exit=$LASTEXITCODE;$ErrorActionPreference=$oldAction
    NewJson $receipt ([ordered]@{exit_code=$exit;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');program=$program;build=(Entry $buildReceipt);arguments=$arguments;log=(Entry $log);owned_call_exited=$true;physical_acceptance=$false})
    if($exit -ne 0){throw "Wave job rejected: $job. Preserve evidence; do not retry automatically."}
    Entry $receipt
  }
  foreach($tag in @('c','h')){
    $steps=if($tag -eq 'c'){256}else{512};$prefix=Join-Path $tests ("outputs\upl_p2_wave_seed_r2_"+$tag+"\CaseUplWave_"+$tag)
    foreach($engine in @('audit','actual','rho')){
      $job=$name+"_"+$tag+"_"+$engine;$out=Join-Path $tests ("outputs\"+$job)
      if(Test-Path -LiteralPath $out){throw 'Retained wave output protected.'}
      $actualEngine=if($engine -eq 'audit'){'audit'}else{'actual'};$poison=if($engine -eq 'rho'){'1'}else{'0'}
      $arguments=@('--job',$actualEngine,$poison,"$steps",'-cpu','-ompthreads:1','-stable',$prefix,$out,'-dirdataout','data')
      $receipts+=InvokeWave $job $arguments
      $done=Get-Content -LiteralPath (Join-Path $out 'complete.json') -Raw|ConvertFrom-Json
      if(!$done.passed -or $done.native_ids -ne 128 -or $done.samples -ne 257 -or $done.steps -ne $steps -or $done.actual_end_s -ne (1./32768.) -or $done.physical_acceptance){throw 'Incomplete or invalid wave completion.'}
      if($engine -eq 'audit' -and $done.force_stage_audits -ne 2*$steps){throw 'Missing audited force stages.'}
      $completed[$tag+'_'+$engine]=$out;$outputFolders+=$out
    }
    foreach($kind in @('exact','rho')){
      $other=if($kind -eq 'exact'){'audit'}else{'rho'};$job=$name+"_"+$tag+"_"+$kind+"_compare"
      $target=Join-Path $logs ($job+'.check.json')
      if(Test-Path -LiteralPath $target){throw 'Retained comparison protected.'}
      $arguments=@('--compare',(Join-Path $completed[$tag+'_actual'] 'physical.bin'),(Join-Path $completed[$tag+'_'+$other] 'physical.bin'),$kind,$target)
      $receipts+=InvokeWave $job $arguments
      if(!(Get-Content -LiteralPath $target -Raw|ConvertFrom-Json).passed){throw 'Comparison did not pass.'}
      $receipts+=Entry $target
    }
  }
  $job=$name+'_half';$target=Join-Path $logs ($job+'.check.json')
  if(Test-Path -LiteralPath $target){throw 'Retained half comparison protected.'}
  $arguments=@('--compare',(Join-Path $completed['c_actual'] 'physical.bin'),(Join-Path $completed['h_actual'] 'physical.bin'),'half',$target)
  $receipts+=InvokeWave $job $arguments;$receipts+=Entry $target
  Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify @($build.program)
  foreach($item in $build.runtime){Verify @($item.copy)}
  Verify $prep.inputs;Verify $prep.jobs;Verify $prep.files;Verify $receipts
  $files=@($outputFolders|ForEach-Object {Get-ChildItem -LiteralPath $_ -Recurse -File}|Sort-Object FullName|ForEach-Object {Entry $_.FullName})
  NewJson $final ([ordered]@{passed=$true;stage='bounded2Dk0coupledComputeStep';build=(Entry $buildReceipt);seeds=(Entry $prepPath);receipts=$receipts;files=$files;actual_time_pairs=257;native_ids=128;physical_columns=25;legacy_rho_also_exact_for_audit=$true;rho_causal_exception_only=$true;dynamic_Darcy=$false;whole_Run_output_scheduling=$false;physical_acceptance=$false})
  Write-Output "PASSED bounded wave gates; pending physical review: $final";exit 0
}
