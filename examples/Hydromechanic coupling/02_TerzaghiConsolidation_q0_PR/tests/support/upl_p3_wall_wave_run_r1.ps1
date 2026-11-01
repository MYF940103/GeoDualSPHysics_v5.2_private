param(
  [ValidateSet('Prepare','Build','Smoke','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# One fixed bounded actual-wall stage; no automatic physical-case calculation.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$name="upl_p3_wall_wave_${Configuration}_r1";$buildOut=Join-Path $tests ("outputs\"+$name)
$harness=Join-Path $PSScriptRoot 'upl_p3_wall_wave_harness_r1.cpp'
$notes=Join-Path $tests 'notes\upl_p3_wall_wave_r1.json'
$exe=Join-Path $buildOut 'upl_p3_wall_wave_harness_r1.exe'
$buildReceipt=Join-Path $logs ($name+'.build.json')
$freezePath=Join-Path $logs 'upl_p3_wall_build_r1.json'
$prepPath=Join-Path $logs 'upl_p3_wall_wave_seed_r1.inputs.json'
$defPaths=@(foreach($tag in @('c','h')){Join-Path $tests ("configs\upl_p3_wall_wave_"+$tag+"_r1_Def.xml")})
function Entry([string]$path){$i=Get-Item -LiteralPath $path;[ordered]@{path=$i.FullName;bytes=$i.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function NewJson([string]$path,$value){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.sha256 -ne $r.sha256 -or $a.bytes -ne $r.bytes){throw "Frozen artifact changed: $($r.path)"}}}
if(!$ExecutionAuthorized -or !$ProductionBuildConfirmed){throw 'Wait for independent/root review and authoritative source freeze; authoring is not permission'}
$freeze=Get-Content -LiteralPath $freezePath -Raw|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'){throw 'Authoritative wall source freeze missing'}
foreach($pair in $freeze.source){Verify @($pair.original,$pair.snapshot)}
function InvokeProgram([string]$job,[string]$program,[string[]]$argv){
  $log=Join-Path $logs ($job+'.log');$receipt=Join-Path $logs ($job+'.run.json')
  if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt)){throw 'Retained job protected'}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o')
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $program @argv 2>&1|Tee-Object -FilePath $log|Out-Host
  $code=$LASTEXITCODE;$ErrorActionPreference=$old
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=(Entry $program);arguments=$argv;log=(Entry $log);physical_acceptance=$false})
  if($code -ne 0){throw "Program failed $job; preserve output and stop dependencies"}
  Entry $receipt
}
function Geometry([string]$prefix){
  [xml]$xml=Get-Content -LiteralPath ($prefix+'.xml') -Raw
  $bytes=[IO.File]::ReadAllBytes($prefix+'_All.vtk');$head=[Text.Encoding]::ASCII.GetString($bytes,0,[Math]::Min(256,$bytes.Length))
  $m=[regex]::Match($head,'(?m)^POINTS ([0-9]+) float\r?\n');if(!$m.Success){throw 'Expected binary float VTK points'}
  $count=[int]$m.Groups[1].Value;$offset=$m.Index+$m.Length;$dp=1./512.
  $pairs=New-Object 'Collections.Generic.HashSet[string]';$valid=$true;$soil=0;$left=0;$right=0
  for($i=0;$i -lt $count;$i++){
    $point=@();for($axis=0;$axis -lt 3;$axis++){$at=$offset+4*($i*3+$axis);$p=[byte[]]@($bytes[$at+3],$bytes[$at+2],$bytes[$at+1],$bytes[$at]);$point+=[double][BitConverter]::ToSingle($p,0)}
    $ix=[int][Math]::Round($point[0]/$dp-.5);$iz=[int][Math]::Round($point[2]/$dp-.5)
    if($ix -lt -4 -or $ix -ge 36 -or $iz -lt 0 -or $iz -ge 32 -or $point[0] -ne ($ix+.5)*$dp -or $point[1] -ne 0 -or $point[2] -ne ($iz+.5)*$dp -or !$pairs.Add("$ix,$iz")){$valid=$false}
    if($ix -lt 0){$left++}elseif($ix -ge 32){$right++}else{$soil++}
  }
  $sha=[Security.Cryptography.SHA256]::Create();$pointHash=[BitConverter]::ToString($sha.ComputeHash($bytes,$offset,12*$count)).Replace('-','').ToLowerInvariant();$sha.Dispose()
  [ordered]@{passed=($valid -and $count -eq 1280 -and [int]$xml.case.execution.particles.np -eq 1280 -and [int]$xml.case.execution.particles.nb -eq 256 -and $soil -eq 1024 -and $left -eq 128 -and $right -eq 128);total=$count;soil=$soil;left=$left;right=$right;exact_half_dp_lattice=$valid;point_bytes_sha256=$pointHash;xml=(Entry ($prefix+'.xml'));vtk=(Entry ($prefix+'_All.vtk'));physical_acceptance=$false}
}
if($Mode -eq 'Prepare'){
  if(Test-Path -LiteralPath $prepPath){throw 'Seeds already prepared; no duplicate GenCase calls'}
  $gencase=Join-Path $repo 'bin\windows\GenCase_win64.exe'
  $inputs=@(@($PSCommandPath,$harness,$notes,$gencase,$freezePath)+$defPaths|ForEach-Object {Entry $_});$jobs=@();$files=@();$geometries=@()
  foreach($tag in @('c','h')){
    $dir=Join-Path $tests ("outputs\upl_p3_wall_wave_seed_r1_"+$tag)
    if(Test-Path -LiteralPath $dir){throw 'Fresh seed directory required'}
    $def=Join-Path $tests ("configs\upl_p3_wall_wave_"+$tag+"_r1_Def.xml")
    [xml]$authored=Get-Content -LiteralPath $def -Raw
    if([double]$authored.case.casedef.geometry.definition.dp -ne 1./512.){throw 'Authored spacing changed'}
    New-Item -ItemType Directory -Path $dir|Out-Null;$raw=Join-Path $dir ("CaseUplWallRaw_"+$tag);$runtime=Join-Path $dir ("CaseUplWall_"+$tag)
    $jobs+=InvokeProgram ("upl_p3_wall_wave_seed_r1_"+$tag) $gencase @($def.Substring(0,$def.Length-4),$raw,'-save:all')
    $geo=Geometry $raw;$geometries+=$geo;$geoPath=Join-Path $logs ("upl_p3_wall_wave_seed_r1_"+$tag+".geometry.check.json");NewJson $geoPath $geo;$jobs+=Entry $geoPath
    if(!$geo.passed){throw 'Incorrect actual wall/soil geometry; later stages held'}
    $doc=New-Object Xml.XmlDocument;$doc.PreserveWhitespace=$true;$doc.Load($raw+'.xml')
    $oldDp=$doc.case.execution.constants.dp.GetAttribute('value')
    if([math]::Abs([double]$oldDp-1./512.) -gt 5.01e-9){throw 'Generated dp exceeds predeclared decimal serialization bound'}
    $original=$doc.DocumentElement.OuterXml;$doc.case.execution.constants.dp.SetAttribute('value','0.001953125')
    $settings=New-Object Xml.XmlWriterSettings;$settings.Encoding=New-Object Text.UTF8Encoding($false);$writer=[Xml.XmlWriter]::Create($runtime+'.xml',$settings);$doc.Save($writer);$writer.Close()
    $check=New-Object Xml.XmlDocument;$check.PreserveWhitespace=$true;$check.Load($runtime+'.xml')
    if([double]$check.case.execution.constants.dp.GetAttribute('value') -ne 1./512.){throw 'Exact runtime spacing missing'}
    $check.case.execution.constants.dp.SetAttribute('value',$oldDp)
    if($check.DocumentElement.OuterXml -cne $original){throw 'Runtime changed more than constants/dp'}
    Copy-Item -LiteralPath ($raw+'.bi4') -Destination ($runtime+'.bi4');$a=Entry ($raw+'.bi4');$b=Entry ($runtime+'.bi4')
    if($a.sha256 -ne $b.sha256){throw 'Runtime BI4 copy differs'}
    $fix=Join-Path $logs ("upl_p3_wall_wave_seed_r1_"+$tag+".runtime.json");NewJson $fix ([ordered]@{raw_dp=$oldDp;runtime_dp='0.001953125';only_runtime_xml_dp_changed=$true;raw_bi4=$a;runtime_bi4=$b;raw_xml=(Entry ($raw+'.xml'));runtime_xml=(Entry ($runtime+'.xml'));physical_acceptance=$false});$jobs+=Entry $fix
    $files+=Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Entry $_.FullName}
  }
  if($geometries[0].point_bytes_sha256 -ne $geometries[1].point_bytes_sha256){throw 'Coarse/half GenCase coordinates differ'}
  Verify $inputs;Verify $jobs;Verify $files
  NewJson $prepPath ([ordered]@{status='seeds_prepared_not_solved';new_gencase_calls=2;new_solver_calls=0;inputs=$inputs;jobs=$jobs;files=$files;physical_acceptance=$false});Write-Output "PREPARED $prepPath";exit 0
}
$prep=Get-Content -LiteralPath $prepPath -Raw|ConvertFrom-Json
if($prep.status -ne 'seeds_prepared_not_solved'){throw 'Wall seeds unavailable'}
Verify $prep.inputs;Verify $prep.jobs;Verify $prep.files
if($Mode -eq 'Build'){
  if(!$ProductionBuildConfirmed -or !$ExecutionAuthorized){throw 'Wait for the root agent to finish and freeze both authoritative CPU builds.'}
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
  $inputs=@(@($project,$harness,$PSCommandPath,$notes,$freezePath,$prepPath)+$defPaths+$objects+$sourceFiles+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $buildOut|Out-Null
  $snapshots=@()
  foreach($path in (@($harness,$PSCommandPath,$notes)+$defPaths)){
    $dest=Join-Path $buildOut ([IO.Path]::GetFileName($path))
    Copy-Item -LiteralPath $path -Destination $dest
    if((Entry $dest).sha256 -ne (Entry $path).sha256){throw 'Build recipe snapshot mismatch'}
    $snapshots+=Entry $dest
  }
  $obj=Join-Path $buildOut 'wall_wave.obj'
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

if(($Mode -eq 'Smoke' -and $Configuration -ne 'DebugCPU') -or ($Mode -eq 'Run' -and $Configuration -ne 'ReleaseCPU')){throw 'Only Debug smoke and Release bounded jobs are admitted'}
$b=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
if($b.status -ne 'built_not_run'){throw 'Fixture build missing'}
Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.copy)}
$smoke=$Mode -eq 'Smoke';$final=Join-Path $logs ($name+$(if($smoke){'.smoke.check.json'}else{'.check.json'}))
if(Test-Path -LiteralPath $final){throw 'Retained final receipt protected'}
if(!$smoke){$s=Get-Content -LiteralPath (Join-Path $logs 'upl_p3_wall_wave_DebugCPU_r1.smoke.check.json') -Raw|ConvertFrom-Json;if(!$s.passed){throw 'Debug actual smoke required'};Verify @($s.build);Verify $s.receipts;Verify $s.files}
$receipts=@();$files=@();$halfChecks=@();$jobs=0
foreach($physics in $(if($smoke){@('smoke')}else{@('k0','k1')})){
  $doneBy=@{}
  foreach($tag in $(if($smoke){@('c')}else{@('c','h')})){
    $steps=if($smoke){2}elseif($physics -eq 'k0'){if($tag -eq 'c'){16}else{32}}else{if($tag -eq 'c'){1024}else{2048}}
    $job=$name+'_'+$physics+$(if($smoke){''}else{'_'+$tag});$output=Join-Path $tests ("outputs\"+$job)
    if(Test-Path -LiteralPath $output){throw 'Retained actual output protected'}
    $seed=Join-Path $tests ("outputs\upl_p3_wall_wave_seed_r1_"+$tag+"\CaseUplWall_"+$tag)
    $receipts+=InvokeProgram $job $exe @('--job',"$steps",$(if($smoke){'1'}else{'0'}),$(if($physics -eq 'k0'){'1'}else{'0'}),'-cpu','-ompthreads:1','-stable',$seed,$output,'-dirdataout','data');$jobs++
    $d=Get-Content -LiteralPath (Join-Path $output 'complete.json') -Raw|ConvertFrom-Json
    $dt=if($tag -eq 'c'){1./33554432.}else{1./67108864.};$samples=if($smoke){3}elseif($physics -eq 'k0'){17}else{257}
    if(!$d.passed -or !$d.actual_ComputeStep_Sym -or $d.native_ids -ne 1024 -or $d.fixed_ids -ne 256 -or $d.Nx -ne 32 -or $d.Nz -ne 32 -or $d.steps -ne $steps -or $d.samples -ne $samples -or [double]$d.dt_actual -ne $dt -or [double]$d.actual_end_s -ne [double]($steps*$dt) -or [bool]$d.smoke -ne $smoke -or [bool]$d.k0 -ne ($physics -eq 'k0') -or $d.physical_acceptance){throw 'Actual wall completion differs from declared job'}
    $modeHistory=@(Import-Csv -LiteralPath (Join-Path $output 'modes.csv'));if($modeHistory.Count -ne $samples){throw 'Incomplete actual mode history'}
    for($i=0;$i -lt $samples;$i++){$stride=$steps/($samples-1);if([int]$modeHistory[$i].step -ne $i*$stride -or [double]$modeHistory[$i].time_s -ne $i*$stride*$dt){throw 'Actual common clocks/steps differ'}}
    $doneBy[$tag]=$output;$files+=Get-ChildItem -LiteralPath $output -Recurse -File|ForEach-Object {Entry $_.FullName}
  }
  if(!$smoke){
    $target=Join-Path $logs ($name+'_'+$physics+'_half.check.json')
    $receipts+=InvokeProgram ($name+'_'+$physics+'_half_compare') $exe @('--half',(Join-Path $doneBy.c 'physical.bin'),(Join-Path $doneBy.h 'physical.bin'),$target)
    if(!(Get-Content -LiteralPath $target -Raw|ConvertFrom-Json).passed){throw 'Independent wall half gate failed'}
    $halfChecks+=Entry $target
  }
}
Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.copy)}
Verify $prep.inputs;Verify $prep.jobs;Verify $prep.files;Verify $receipts;Verify $files;Verify $halfChecks
NewJson $final ([ordered]@{passed=$true;smoke_only=$smoke;actual_ComputeStep_Sym=$true;solver_jobs=$jobs;source_freeze=(Entry $freezePath);build=(Entry $buildReceipt);seeds=(Entry $prepPath);receipts=$receipts;half_checks=$halfChecks;files=$files;physical_acceptance=$false})
Write-Output "BOUNDED WALL JOBS COMPLETE $final"
