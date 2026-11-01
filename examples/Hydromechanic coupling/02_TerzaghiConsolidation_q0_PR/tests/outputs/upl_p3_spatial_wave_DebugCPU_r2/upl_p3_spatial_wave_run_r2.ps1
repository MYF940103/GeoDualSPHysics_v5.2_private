param(
  [ValidateSet('Prepare','Build','Smoke','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r2',
  [switch]$ProductionBuildConfirmed,
  [switch]$ExecutionAuthorized
)
# Fixed32/64 actual refinement only. Merely preparing this script is not permission to execute.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$name="upl_p3_spatial_wave_${Configuration}_$Label"
$buildOut=Join-Path $tests ("outputs\"+$name)
$harness=Join-Path $PSScriptRoot 'upl_p3_spatial_wave_harness_r2.cpp'
$notes=Join-Path $tests 'notes\upl_p3_spatial_wave_r2.json'
$exe=Join-Path $buildOut 'upl_p3_spatial_wave_harness_r2.exe'
$buildReceipt=Join-Path $logs ($name+'.build.json')
$freezePath=Join-Path $logs 'upl_p3_time_build_r1.json'
$baselinePath=Join-Path $logs 'upl_p3_time_wave_ReleaseCPU_r1.check.json'
$symbolPath=Join-Path $logs 'upl_p3_spatial_symbol_r2.check.json'
$prepPath=Join-Path $logs 'upl_p3_spatial_seed_r1.inputs.json'
$defPaths=@(foreach($nx in @(32,64)){foreach($tag in @('c','h')){Join-Path $tests ("configs\upl_p3_spatial_n"+$nx+"_"+$tag+"_r1_Def.xml")}})
function Entry([string]$path){$i=Get-Item -LiteralPath $path;[ordered]@{path=$i.FullName;bytes=$i.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function NewJson([string]$path,$v){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($v|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Verify($rows){foreach($r in $rows){$n=Entry $r.path;if($n.sha256 -ne $r.sha256 -or $n.bytes -ne $r.bytes){throw "Frozen artifact changed: $($r.path)"}}}
if(!$ExecutionAuthorized -or !$ProductionBuildConfirmed){throw 'Authoring is not execution permission; wait for root review and both explicit flags'}
$freeze=Get-Content -LiteralPath $freezePath -Raw|ConvertFrom-Json
if($freeze.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'){throw 'Authoritative source freeze missing'}
foreach($pair in $freeze.source){Verify @($pair.original,$pair.snapshot)}
$baseline=Get-Content -LiteralPath $baselinePath -Raw|ConvertFrom-Json
$symbol=Get-Content -LiteralPath $symbolPath -Raw|ConvertFrom-Json
if(!$baseline.passed -or !$symbol.passed){throw 'Prior actual16 control or offline symbol audit not admitted'}
Verify @($baseline.build);Verify $baseline.receipts;Verify $baseline.files
Verify $symbol.files
function InvokeProgram([string]$job,[string]$program,[string[]]$argv){
  $log=Join-Path $logs ($job+'.log');$receipt=Join-Path $logs ($job+'.run.json')
  if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt)){throw 'Retained job protected'}
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o')
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $program @argv 2>&1|Tee-Object -FilePath $log|Out-Host
  $code=$LASTEXITCODE;$ErrorActionPreference=$old
  NewJson $receipt ([ordered]@{exit_code=$code;owned_call_exited=$true;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');program=(Entry $program);arguments=$argv;log=(Entry $log);physical_acceptance=$false})
  if($code -ne 0){throw "Program failed $job; retain output and stop dependencies"}
  Entry $receipt
}
function Geometry([string]$prefix,[int]$nx){
  [xml]$xml=Get-Content -LiteralPath ($prefix+'.xml') -Raw
  $bytes=[IO.File]::ReadAllBytes($prefix+'_All.vtk');$head=[Text.Encoding]::ASCII.GetString($bytes,0,[Math]::Min(256,$bytes.Length))
  $m=[regex]::Match($head,'(?m)^POINTS ([0-9]+) float\r?\n');if(!$m.Success){throw 'Expected binary float VTK points'}
  $count=[int]$m.Groups[1].Value;$offset=$m.Index+$m.Length;$dp=.125/$nx
  $pairs=New-Object 'Collections.Generic.HashSet[string]';$xs=New-Object 'Collections.Generic.HashSet[double]';$zs=New-Object 'Collections.Generic.HashSet[double]';$valid=$true
  for($i=0;$i -lt $count;$i++){
    $point=@();for($axis=0;$axis -lt 3;$axis++){$at=$offset+4*($i*3+$axis);$p=[byte[]]@($bytes[$at+3],$bytes[$at+2],$bytes[$at+1],$bytes[$at]);$point+=[double][BitConverter]::ToSingle($p,0)}
    $ix=[int][Math]::Round($point[0]/$dp-.5);$iz=[int][Math]::Round($point[2]/$dp-.5)
    [void]$xs.Add($point[0]);[void]$zs.Add($point[2])
    if($ix -lt 0 -or $ix -ge $nx -or $iz -lt 0 -or $iz -ge $nx/2 -or $point[0] -ne ($ix+.5)*$dp -or $point[1] -ne 0 -or $point[2] -ne ($iz+.5)*$dp -or !$pairs.Add("$ix,$iz")){$valid=$false}
  }
  $passed=$valid -and $count -eq $nx*$nx/2 -and [int]$xml.case.execution.particles.np -eq $count -and [int]$xml.case.execution.particles.nb -eq 0 -and $pairs.Count -eq $count -and $xs.Count -eq $nx -and $zs.Count -eq $nx/2
  [ordered]@{passed=$passed;nx=$nx;nz=$nx/2;native=$count;exact_half_dp_lattice=$valid;unique_x=$xs.Count;unique_z=$zs.Count;xml=(Entry ($prefix+'.xml'));vtk=(Entry ($prefix+'_All.vtk'));physical_acceptance=$false}
}
if($Mode -eq 'Prepare'){
  if(Test-Path -LiteralPath $prepPath){throw 'Seeds already prepared; do not repeat'}
  $gencase=Join-Path $repo 'bin\windows\GenCase_win64.exe'
  $inputs=@(@($PSCommandPath,$harness,$notes,$gencase,$freezePath,$symbolPath,$baselinePath)+$defPaths|ForEach-Object {Entry $_});$jobs=@();$files=@()
  foreach($nx in @(32,64)){
    $dir=Join-Path $tests ("outputs\upl_p3_spatial_seed_r1_n"+$nx+"_c");$halfdir=Join-Path $tests ("outputs\upl_p3_spatial_seed_r1_n"+$nx+"_h")
    if((Test-Path -LiteralPath $dir) -or (Test-Path -LiteralPath $halfdir)){throw 'Fresh seed directories required'}
    $def=Join-Path $tests ("configs\upl_p3_spatial_n"+$nx+"_c_r1_Def.xml")
    $halfdef=Join-Path $tests ("configs\upl_p3_spatial_n"+$nx+"_h_r1_Def.xml")
    [xml]$dc=Get-Content -LiteralPath $def -Raw;[xml]$dh=Get-Content -LiteralPath $halfdef -Raw
    if($dc.case.casedef.OuterXml -ne $dh.case.casedef.OuterXml -or $dc.case.execution.special.OuterXml -ne $dh.case.execution.special.OuterXml){throw 'Coarse/half geometry or material differs'}
    New-Item -ItemType Directory -Path $dir|Out-Null;$prefix=Join-Path $dir ("CaseUplSpatial_n"+$nx+"_c")
    $jobs+=InvokeProgram ("upl_p3_spatial_seed_r1_n"+$nx) $gencase @($def.Substring(0,$def.Length-4),$prefix,'-save:all')
    $geo=Geometry $prefix $nx;$geoPath=Join-Path $logs ("upl_p3_spatial_seed_r1_n"+$nx+".geometry.check.json");NewJson $geoPath $geo;$jobs+=Entry $geoPath
    if(!$geo.passed){throw 'Wrong GenCase geometry; no fixture build/run admitted'}
    New-Item -ItemType Directory -Path $halfdir|Out-Null;$hp=Join-Path $halfdir ("CaseUplSpatial_n"+$nx+"_h")
    Copy-Item -LiteralPath ($prefix+'.bi4') -Destination ($hp+'.bi4')
    $runtime=New-Object Xml.XmlDocument;$runtime.PreserveWhitespace=$true;$runtime.Load($prefix+'.xml')
    foreach($key in @('DtIni','DtFixed')){
      $target=@($runtime.case.execution.parameters.parameter|Where-Object {$_.key -eq $key})[0];$input=@($dh.case.execution.parameters.parameter|Where-Object {$_.key -eq $key})[0]
      $target.SetAttribute('value',$input.value)
      if($input.HasAttribute('comment')){$target.SetAttribute('comment',$input.comment)}else{$target.RemoveAttribute('comment')}
    }
    $settings=New-Object Xml.XmlWriterSettings;$settings.Encoding=New-Object Text.UTF8Encoding($false);$writer=[Xml.XmlWriter]::Create($hp+'.xml',$settings);$runtime.Save($writer);$writer.Close()
    $src=Entry ($prefix+'.bi4');$dst=Entry ($hp+'.bi4');if($src.sha256 -ne $dst.sha256){throw 'Half initial BI4 copy differs'}
    $copyPath=Join-Path $logs ("upl_p3_spatial_seed_r1_n"+$nx+".half_copy.json");NewJson $copyPath ([ordered]@{copied_initial_BI4_byte_exact=$true;original=$src;copy=$dst;runtime_xml=(Entry ($hp+'.xml'));changed_runtime_parameters=@('DtIni','DtFixed');independent_GenCase_for_half=$false});$jobs+=Entry $copyPath
    $files+=Get-ChildItem -LiteralPath $dir,$halfdir -File|ForEach-Object {Entry $_.FullName}
  }
  Verify $inputs;Verify $jobs;Verify $files
  NewJson $prepPath ([ordered]@{status='seeds_prepared_not_solved';inputs=$inputs;jobs=$jobs;files=$files;new_gencase_calls=2;new_solver_calls=0;physical_acceptance=$false})
  Write-Output "PREPARED two new geometries: $prepPath";exit 0
}
$prep=Get-Content -LiteralPath $prepPath -Raw|ConvertFrom-Json
if($prep.status -ne 'seeds_prepared_not_solved'){throw 'New seeds not admitted'}
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
  $inputs=@(@($project,$harness,$PSCommandPath,$notes,$freezePath,$prepPath,$baselinePath,$symbolPath)+$defPaths+$objects+$sourceFiles+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
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
  $obj=Join-Path $buildOut 'spatial_wave.obj'
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


if($Mode -in @('Smoke','Run')){
  if(($Mode -eq 'Smoke' -and $Configuration -ne 'DebugCPU') -or ($Mode -eq 'Run' -and $Configuration -ne 'ReleaseCPU')){throw 'Only Debug smoke and Release full windows are admitted'}
  $b=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
  if($b.status -ne 'built_not_run'){throw 'Companion build missing'}
  Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.copy)}
  $smoke=$Mode -eq 'Smoke';$final=Join-Path $logs ($name+$(if($smoke){'.smoke.check.json'}else{'.check.json'}))
  if(Test-Path -LiteralPath $final){throw 'Fresh final label required'}
  if(!$smoke){$smokePath=Join-Path $logs ("upl_p3_spatial_wave_DebugCPU_"+$Label+".smoke.check.json");$s=Get-Content -LiteralPath $smokePath -Raw|ConvertFrom-Json;if(!$s.passed -or $s.solver_jobs -ne 2){throw 'Two Debug smokes are required'};Verify $s.receipts;Verify $s.files}
  $receipts=@();$files=@();$doneBy=@{};$halfChecks=@()
  foreach($nx in @(32,64)){
    $tags=if($smoke){@('c')}else{@('c','h')}
    foreach($tag in $tags){
      $steps=if($smoke){2}else{256*($nx/16)*$(if($tag -eq 'h'){2}else{1})}
      $suffix=if($smoke){'smoke'}else{$tag};$job=$name+"_n"+$nx+"_"+$suffix;$output=Join-Path $tests ("outputs\"+$job)
      if(Test-Path -LiteralPath $output){throw 'Retained actual output protected'}
      $seed=Join-Path $tests ("outputs\upl_p3_spatial_seed_r1_n"+$nx+"_"+$tag+"\CaseUplSpatial_n"+$nx+"_"+$tag)
      $receipts+=InvokeProgram $job $exe @('--job',"$nx","$steps",$(if($smoke){'1'}else{'0'}),'-cpu','-ompthreads:1','-stable',$seed,$output,'-dirdataout','data')
      $d=Get-Content -LiteralPath (Join-Path $output 'complete.json') -Raw|ConvertFrom-Json
      $dt=(1./8388608.)/($nx/16)/$(if($tag -eq 'h'){2}else{1});$samples=if($smoke){3}else{257}
      $cu=[math]::Sqrt((89478488.+4.*134217728./3.+67108864./.25)/2048.);$Pstar=(67108864./.25)*(1./512.)/$cu;$Ustar=(1./512.)/($cu*2*[math]::PI/.125)
      if(!$d.passed -or !$d.actual_ComputeStep_Sym -or $d.native_ids -ne $nx*$nx/2 -or $d.samples -ne $samples -or $d.steps -ne $steps -or $d.actual_end_s -ne $steps*$dt -or $d.physical_acceptance -or $d.cu -ne $cu -or $d.Pstar -ne $Pstar -or $d.Ustar -ne $Ustar){throw 'Wrong actual completion/material characteristic scale'}
      $mode=@(Import-Csv -LiteralPath (Join-Path $output 'modes.csv'));if($mode.Count -ne $samples){throw 'Incomplete mode history'}
      for($i=0;$i -lt $samples;$i++){$factor=if($smoke){1}else{$steps/256};if([int]$mode[$i].step -ne $i*$factor -or [double]$mode[$i].time_s -ne $i*$factor*$dt){throw 'Actual saved time-step identity differs'}}
      $sym=Import-Csv -LiteralPath (Join-Path $tests 'outputs\upl_p3_spatial_symbol_r2\symbols.csv')|Where-Object {[int]$_.nx -eq $nx}
      foreach($pair in @(@('discrete_Kr','Kr'),@('discrete_Ks','Ks'),@('discrete_Ksig','Ksig'),@('discrete_ell','ell'))){$a=[double]$d.($pair[0]);$e=[double]$sym.($pair[1]);if([math]::Abs($a-$e) -gt 32768*2.2204460492503131e-16*[math]::Max(1,[math]::Abs($e))){throw 'Actual new-seed symbol differs from frozen header prediction'}}
      $doneBy["$nx$tag"]=@{directory=$output;completion=$d};$files+=Get-ChildItem -LiteralPath $output -Recurse -File|ForEach-Object {Entry $_.FullName}
    }
    if(!$smoke){
      $left=$doneBy["${nx}c"];$right=$doneBy["${nx}h"];$target=Join-Path $logs ($name+"_n"+$nx+"_half.check.json")
      $receipts+=InvokeProgram ($name+"_n"+$nx+"_half_compare") $exe @('--half',(Join-Path $left.directory 'physical.bin'),(Join-Path $right.directory 'physical.bin'),"$Pstar","$Ustar",$target)
      if(!(Get-Content -LiteralPath $target -Raw|ConvertFrom-Json).passed){throw 'Fine-grid independent half failed'}
      $halfChecks+=Entry $target
    }
  }
  Verify $b.inputs;Verify $b.libraries;Verify $b.snapshots;Verify @($b.program);foreach($r in $b.runtime){Verify @($r.copy)};Verify $prep.inputs;Verify $prep.jobs;Verify $prep.files;Verify $files;Verify $receipts;Verify $halfChecks;Verify $symbol.files
  NewJson $final ([ordered]@{passed=$true;smoke_only=$smoke;actual_ComputeStep_Sym=$true;source_freeze=(Entry $freezePath);build=(Entry $buildReceipt);seeds=(Entry $prepPath);retained16=(Entry $baselinePath);offline_symbols=(Entry $symbolPath);solver_jobs=if($smoke){2}else{4};receipts=$receipts;half_checks=$halfChecks;files=$files;continuum_accuracy_pending_offline_root_review=$true;physical_acceptance=$false})
  Write-Output "PASSED actual spatial ${Mode}; pending root review: $final";exit 0
}



