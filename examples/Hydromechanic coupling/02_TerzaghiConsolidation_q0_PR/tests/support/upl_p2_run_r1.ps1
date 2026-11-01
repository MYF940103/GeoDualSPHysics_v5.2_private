param(
  [ValidateSet('Snapshot','Prepare','PrepareState','PrepareOpen','Baseline','BaselineOpen','Build','Run','RunOpen')][string]$Mode='Snapshot',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [switch]$ProductionBuildConfirmed
)
# P2 is an observer-only CPU diagnostic. Never starts long or automatic runs.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$logs=Join-Path $tests 'logs'
function Entry([string]$path){
  $file=Get-Item -LiteralPath $path
  [ordered]@{path=$file.FullName;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function NewJson([string]$path,$value){
  if(Test-Path -LiteralPath $path){throw "Refusing overwrite: $path"}
  $text=$value|ConvertTo-Json -Depth 12
  [IO.File]::WriteAllText($path,$text+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
}
if($Mode -eq 'Snapshot'){
  $output=Join-Path $tests 'outputs\upl_p2_base_r1'
  $receipt=Join-Path $logs 'upl_p2_base_r1.snapshot.json'
  if((Test-Path -LiteralPath $output) -or (Test-Path -LiteralPath $receipt)){throw 'P2 baseline already exists; do not overwrite it.'}
  $paths=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -File|Where-Object {$_.Name -match '^(JSphCpu|JSphCpuSingle|JCellDivCpu|JArraysCpu)' }|ForEach-Object {$_.FullName})
  $paths+=@('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DsphConfig.xml')|ForEach-Object {Join-Path $repo "bin\windows\$_"}
  $paths+=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})
  $before=@($paths|Sort-Object -Unique|ForEach-Object {Entry $_})
  New-Item -ItemType Directory -Path $output|Out-Null
  $copies=@()
  foreach($item in $before){
    $folder=if($item.path.StartsWith((Join-Path $source 'source'),[StringComparison]::OrdinalIgnoreCase)){'source'}else{'runtime'}
    $targetFolder=Join-Path $output $folder
    if(!(Test-Path -LiteralPath $targetFolder)){New-Item -ItemType Directory -Path $targetFolder|Out-Null}
    $target=Join-Path $targetFolder ([IO.Path]::GetFileName($item.path))
    Copy-Item -LiteralPath $item.path -Destination $target
    $copy=Entry $target
    if($copy.sha256 -ne $item.sha256 -or (Entry $item.path).sha256 -ne $item.sha256){throw 'Baseline changed while copying'}
    $copies+=@{original=$item;snapshot=$copy}
  }
  NewJson $receipt ([ordered]@{status='sealed_not_run';utc=[DateTime]::UtcNow.ToString('o');git_head=(& git -C $repo rev-parse HEAD);git_branch=(& git -C $repo branch --show-current);files=$copies;solver_started=$false;physical_acceptance=$false})
  Write-Output "SEALED $receipt"
  exit 0
}
$seed=Join-Path $tests 'outputs\upl_p2_seed_r1\CaseTCq0_upl_p2_r1'
$stateSeed=Join-Path $tests 'outputs\upl_p2_state_seed_r1\CaseTCq0_upl_p2_state_r1'
$openSeed=Join-Path $tests 'outputs\upl_p2_open_seed_r1\CaseTCq0_upl_p2_open_r1'
if($Mode -eq 'PrepareOpen'){
  $folder=Split-Path -Parent $openSeed;$cfg=Join-Path $tests 'configs\upl_p2_open_r1.xml'
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $cfg)){throw 'P2 open-drain input exists'}
  $text=[IO.File]::ReadAllText($seed+'.xml')
  $rx=New-Object Text.RegularExpressions.Regex('(<HydroMechDrainageStartTime value=")[^"]+("[^\r\n]+)')
  if($rx.Matches($text).Count -ne 1){throw 'Missing drainage event setting'}
  $text=$rx.Replace($text,{param($m) $m.Groups[1].Value+'0'+$m.Groups[2].Value})
  New-Item -ItemType Directory -Path $folder|Out-Null
  [IO.File]::WriteAllText($cfg,$text,(New-Object Text.UTF8Encoding($false)))
  [IO.File]::WriteAllText($openSeed+'.xml',$text,(New-Object Text.UTF8Encoding($false)))
  Copy-Item -LiteralPath ($seed+'.bi4') -Destination ($openSeed+'.bi4')
  Copy-Item -LiteralPath ($seed+'_Normals.nbi4') -Destination ($openSeed+'_Normals.nbi4')
  NewJson (Join-Path $logs 'upl_p2_open_r1.inputs.json') ([ordered]@{status='prepared_not_run';only_changed_setting='HydroMechDrainageStartTime=0';inputs=@(Entry $cfg;Entry ($openSeed+'.xml');Entry ($openSeed+'.bi4');Entry ($openSeed+'_Normals.nbi4'));steps=128;physical_acceptance=$false})
  Write-Output 'PREPARED open-drain implementation regression; not run';exit 0
}
if($Mode -eq 'PrepareState'){
  $folder=Split-Path -Parent $stateSeed;$cfg=Join-Path $tests 'configs\upl_p2_state_r1.xml'
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $cfg)){throw 'P2 state input exists'}
  $text=[IO.File]::ReadAllText($seed+'.xml')
  foreach($key in @('SoilHourglassXi','SoilDamping')){
    $rx=New-Object Text.RegularExpressions.Regex('(<parameter key="'+$key+'" value=")[^"]+("[^\r\n]+)')
    if($rx.Matches($text).Count -ne 1){throw "Missing state setting $key"}
    $text=$rx.Replace($text,{param($m) $m.Groups[1].Value+'0'+$m.Groups[2].Value})
  }
  $rx=New-Object Text.RegularExpressions.Regex('(<HydroMechTopLoadMode value=")[^"]+("[^\r\n]+)')
  if($rx.Matches($text).Count -ne 1){throw 'Missing state load setting'}
  $text=$rx.Replace($text,{param($m) $m.Groups[1].Value+'0'+$m.Groups[2].Value})
  New-Item -ItemType Directory -Path $folder|Out-Null
  [IO.File]::WriteAllText($cfg,$text,(New-Object Text.UTF8Encoding($false)))
  [IO.File]::WriteAllText($stateSeed+'.xml',$text,(New-Object Text.UTF8Encoding($false)))
  Copy-Item -LiteralPath ($seed+'.bi4') -Destination ($stateSeed+'.bi4')
  Copy-Item -LiteralPath ($seed+'_Normals.nbi4') -Destination ($stateSeed+'_Normals.nbi4')
  NewJson (Join-Path $logs 'upl_p2_state_r1.inputs.json') ([ordered]@{status='prepared_not_run';changed_parameters=@('SoilHourglassXi=0','SoilDamping=0','HydroMechTopLoadMode=0');inputs=@(Entry $cfg;Entry ($stateSeed+'.xml');Entry ($stateSeed+'.bi4');Entry ($stateSeed+'_Normals.nbi4'));physical_acceptance=$false})
  Write-Output 'PREPARED standalone manufactured state lifecycle; not run';exit 0
}
if($Mode -eq 'Prepare'){
  $old=Join-Path $tests 'outputs\hg_release_dbg03_r2_input\CaseTCq0_hg_release_dbg03_r2'
  $folder=Split-Path -Parent $seed
  $cfg=Join-Path $tests 'configs\upl_p2_r1.xml'
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $cfg)){throw 'P2 input already exists'}
  $text=[IO.File]::ReadAllText($old+'.xml')
  foreach($item in @(@('TimeMax','0.00128'),@('TimeOut','0.00008'),@('SavePosDouble','1'))){
    $pattern='(<parameter key="'+$item[0]+'" value=")[^"]+("[^\r\n]+)'
    $rx=New-Object Text.RegularExpressions.Regex($pattern)
    if($rx.Matches($text).Count -ne 1){throw "Missing setting $($item[0])"}
    $value=$item[1];$text=$rx.Replace($text,{param($m) $m.Groups[1].Value+$value+$m.Groups[2].Value})
  }
  New-Item -ItemType Directory -Path $folder|Out-Null
  [IO.File]::WriteAllText($cfg,$text,(New-Object Text.UTF8Encoding($false)))
  [IO.File]::WriteAllText($seed+'.xml',$text,(New-Object Text.UTF8Encoding($false)))
  Copy-Item -LiteralPath ($old+'.bi4') -Destination ($seed+'.bi4')
  Copy-Item -LiteralPath ($old+'_Normals.nbi4') -Destination ($seed+'_Normals.nbi4')
  NewJson (Join-Path $logs 'upl_p2_r1.inputs.json') ([ordered]@{status='prepared_not_run';inputs=@(Entry ($old+'.xml');Entry ($old+'.bi4');Entry ($old+'_Normals.nbi4');Entry $cfg;Entry ($seed+'.xml');Entry ($seed+'.bi4');Entry ($seed+'_Normals.nbi4'));steps=128;fixed_dt_s=1e-5;physical_acceptance=$false})
  Write-Output 'PREPARED P2 128-step runtime; not run';exit 0
}
function Execute([string]$exe,[string[]]$arguments,[string]$name){
  $log=Join-Path $logs ($name+'.log');$receipt=Join-Path $logs ($name+'.run.json')
  if((Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $receipt)){throw "Retained run protected: $name"}
  $program=Entry $exe;$started=[DateTime]::UtcNow.ToString('o')
  [IO.File]::WriteAllBytes($log,[byte[]]@()) # A successful decoder/diagnostic may be completely silent.
  $oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @arguments 2>&1|Tee-Object -FilePath $log|Out-Host
  $code=$LASTEXITCODE
  $ErrorActionPreference=$oldAction
  NewJson $receipt ([ordered]@{exit_code=$code;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');program=$program;arguments=$arguments;log=(Entry $log);owned_call_exited=$true;physical_acceptance=$false})
  if($code -ne 0){throw "Job failed ($code), retained without retry: $name"}
}
function CompareFolders([string]$exe,[string]$left,[string]$right,[string]$label){
  $a=@(Get-ChildItem -LiteralPath (Join-Path $left 'data') -Filter 'Part_????.bi4' -File|Sort-Object Name)
  $b=@(Get-ChildItem -LiteralPath (Join-Path $right 'data') -Filter 'Part_????.bi4' -File|Sort-Object Name)
  if($a.Count -ne $b.Count -or $a.Count -lt 2){throw 'Native saved-frame coverage mismatch'}
  $checks=@()
  for($i=0;$i -lt $a.Count;$i++){
    if($a[$i].Name -ne $b[$i].Name){throw 'Native frame names mismatch'}
    $part=[int]$a[$i].BaseName.Substring(5)
    $name=$label+"_p$part";$check=Join-Path $logs ($name+'.check.json')
    Execute $exe @('--compare',(Join-Path $left 'data'),(Join-Path $right 'data'),"$part",$check) $name
    $checks+=Entry $check
  }
  NewJson (Join-Path $logs ($label+'.check.json')) ([ordered]@{passed=$true;actual_native_samples=$a.Count;all15_original_arrays_ID_aligned_0ULP=$true;saved_clock_step_dterror_exact=$true;receipts=$checks;physical_acceptance=$false})
}
$runtimeArgs=@('-cpu','-ompthreads:1','-stable','-mdbc',$seed)
if($Mode -eq 'Baseline' -or $Mode -eq 'BaselineOpen'){
  $open=$Mode -eq 'BaselineOpen';$tag=if($open){'open_'}else{''}
  if($open){$runtimeArgs=@('-cpu','-ompthreads:1','-stable','-mdbc',$openSeed)}
  if(!(Test-Path -LiteralPath ($seed+'.xml'))){throw 'Prepare the bounded inputs first'}
  foreach($c in @('DebugCPU','ReleaseCPU')){
    $file=if($c -eq 'DebugCPU'){'DualSPHysics5.2CPU_win64_debug.exe'}else{'DualSPHysics5.2CPU_win64.exe'}
    $exe=Join-Path $tests "outputs\upl_p2_base_r1\runtime\$file"
    $name="upl_p2_before_${tag}$c";$out=Join-Path $tests "outputs\$name"
    if(Test-Path -LiteralPath $out){throw 'Pre-edit baseline output exists'}
    Execute $exe ($runtimeArgs+@($out,'-dirdataout','data','-svres','-svextraparts:1','-nsteps:128')) $name
  }
  exit 0
}
$buildName="upl_p2_${Configuration}_$Label"
$buildOut=Join-Path $tests "outputs\$buildName"
$harness=Join-Path $PSScriptRoot 'upl_p2_harness_r1.cpp'
$exe=Join-Path $buildOut 'upl_p2_harness_r1.exe'
if($Mode -eq 'Build'){
  if(!$ProductionBuildConfirmed){throw 'Complete the matching authoritative CPU MSBuild first'}
  if(Test-Path -LiteralPath $buildOut){throw 'Build output already exists; use a new label'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment setup failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj';[xml]$xml=Get-Content -LiteralPath $project -Raw
  $objects=@();$sourceFiles=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false
    foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq "'`$(Configuration)|`$(Platform)'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){$objects+=Join-Path $source "VS\Intermediate\DualSPHysics_${Configuration}_x64\$stem.obj";$sourceFiles+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))}
  }
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($project,$harness,$PSCommandPath,(Join-Path $PSScriptRoot 'bv_pair_cpu_r1.cpp'))+$objects+$sourceFiles+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  New-Item -ItemType Directory -Path $buildOut|Out-Null
  $obj=Join-Path $buildOut 'upl_p2_harness_r1.obj';$log=Join-Path $logs ($buildName+'.build.log')
  $flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$buildOut\compile.pdb",'/sourceDependencies',(Join-Path $buildOut 'compile.dependencies.json'))+$flags+@($harness)
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log|Out-Host;if($LASTEXITCODE){throw 'P2 compile failed; preserve log'}
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs
  if($debug){$link+=@('/DEBUG',"/PDB:$buildOut\link.pdb")}
  & link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;if($LASTEXITCODE){throw 'P2 link failed; preserve log'}
  foreach($item in $inputs){if((Entry $item.path).sha256 -ne $item.sha256){throw 'Build input changed'}}
  foreach($dll in Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File){Copy-Item -LiteralPath $dll.FullName -Destination $buildOut}
  Copy-Item -LiteralPath (Join-Path $repo 'bin\windows\DsphConfig.xml') -Destination $buildOut
  NewJson (Join-Path $logs ($buildName+'.build.json')) ([ordered]@{status='built_not_run';configuration=$Configuration;git_head=(& git -C $repo rev-parse HEAD);inputs=$inputs;compile=$compile;link=$link;program=(Entry $exe);log=(Entry $log);runtime=@(Get-ChildItem -LiteralPath $buildOut -File|Where-Object {$_.Extension -eq '.dll' -or $_.Name -eq 'DsphConfig.xml'}|ForEach-Object {Entry $_.FullName})})
  exit 0
}
if($Mode -eq 'Run' -or $Mode -eq 'RunOpen'){
  if(!(Test-Path -LiteralPath $exe)){throw 'Build the harness first'}
  $runName=$buildName;$stepList=@(8,128)
  if($Mode -eq 'RunOpen'){$runName=$buildName+'_open';$runtimeArgs=@('-cpu','-ompthreads:1','-stable','-mdbc',$openSeed);$stepList=@(128)}
  else{
    $name=$buildName+'_pair';Execute $exe @('--pair',(Join-Path $tests "outputs\$name")) $name
    $stateArgs=@('-cpu','-ompthreads:1','-stable','-mdbc',$stateSeed)
    $name=$buildName+'_state';Execute $exe (@('--state')+$stateArgs+@((Join-Path $tests "outputs\$name"),'-dirdataout','data','-svres')) $name
  }
  foreach($steps in $stepList){
    foreach($observe in @(0,1)){
      $name=$runName+"_s${steps}_o$observe";$out=Join-Path $tests "outputs\$name"
      Execute $exe (@('--solver',"$observe")+$runtimeArgs+@($out,'-dirdataout','data','-svres','-svextraparts:1',"-nsteps:$steps")) $name
    }
    $off=Join-Path $tests "outputs\${runName}_s${steps}_o0";$on=Join-Path $tests "outputs\${runName}_s${steps}_o1"
    CompareFolders $exe $off $on ($runName+"_s${steps}_observer")
    $parts=@(Get-ChildItem -LiteralPath (Join-Path $on 'data') -Filter 'Part_????.bi4' -File|Sort-Object Name)
    foreach($part in $parts){
      $index=[int]$part.BaseName.Substring(5);$native=Join-Path $on ($part.BaseName+'_poro.csv')
      Execute $exe @('--read-poro',(Join-Path $on 'data'),"$index",$native) ($runName+"_s${steps}_poro_p$index")
    }
    $final=Join-Path $on ($parts[-1].BaseName+'_poro.csv')
    if((Entry $final).sha256 -ne (Entry (Join-Path $on 'observer_final.csv')).sha256){throw 'Final native J/n/theta differ from actual in-memory export'}
    NewJson (Join-Path $logs ($runName+"_s${steps}_native_poro.check.json")) ([ordered]@{passed=$true;frames=$parts.Count;all_three_double_fields_checked=$true;final_native_and_memory_csv_bit_identical=$true;physical_acceptance=$false})
  }
  $tag=if($Mode -eq 'RunOpen'){'open_'}else{''}
  $before=Join-Path $tests "outputs\upl_p2_before_${tag}$Configuration"
  CompareFolders $exe $before (Join-Path $tests "outputs\${runName}_s128_o0") ($runName+'_default_OFF')
  Write-Output 'P2 observer implementation diagnostics passed; no coupled dynamic-model or physical acceptance.'
  exit 0
}
