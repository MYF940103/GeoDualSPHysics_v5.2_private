param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration='DebugCPU',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [switch]$ProductionBuildConfirmed
)
# Actual CPU component only, never invokes a physical solver or modifies production.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src';$logs=Join-Path $tests 'logs'
$name="upl_p3_actual_${Configuration}_$Label"
$buildOut=Join-Path $tests "outputs\$name"
$harness=Join-Path $PSScriptRoot 'upl_p3_actual_r3.cpp'
$r1Harness=Join-Path $PSScriptRoot 'upl_p3_actual_r1.cpp'
$r2Harness=Join-Path $PSScriptRoot 'upl_p3_actual_r2.cpp'
$base=Join-Path $PSScriptRoot 'upl_p2_feedback_harness_r1.cpp'
$notes=Join-Path $tests 'notes\upl_p3_actual_r1.json'
$addendum=Join-Path $tests 'notes\upl_p3_actual_r2.json'
$failedSeal=Join-Path $logs 'upl_p3_actual_DebugCPU_r1.failure_seal.json'
$secondSeal=Join-Path $logs 'upl_p3_actual_DebugCPU_r2.failure_seal.json'
$repairNote=Join-Path $tests 'notes\upl_p3_actual_r3.json'
$authoritative=Join-Path $logs 'upl_p3_actual_build_r2.json'
$exe=Join-Path $buildOut 'upl_p3_actual_r3.exe'
$buildReceipt=Join-Path $logs ($name+'.build.json')
function Entry([string]$path){$a=Get-Item -LiteralPath $path;[ordered]@{path=$a.FullName;bytes=$a.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function NewJson([string]$path,$value){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Verify($entries){foreach($a in $entries){$b=Entry $a.path;if($a.sha256 -ne $b.sha256 -or $a.bytes -ne $b.bytes){throw "Frozen artifact changed: $($a.path)"}}}
if(!$ProductionBuildConfirmed){throw 'Root must confirm completed authoritative builds and source freeze.'}
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $buildOut) -or (Test-Path -LiteralPath $buildReceipt)){throw 'Fresh build label required'}
  $auth=Get-Content -LiteralPath $authoritative -Raw|ConvertFrom-Json
  if($auth.status -ne 'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'){throw 'Authoritative build not admitted'}
  foreach($a in $auth.source){Verify @($a.original,$a.snapshot)}
  $oldSource=(Get-Content -LiteralPath $r2Harness -Raw).Replace("`r`n","`n").TrimEnd([char[]]"`r`n")
  $expected=$oldSource.Replace('code=DCEL_GetCode(2,2,2)','code=DCEL_GetCode(27,2,2)').Replace('Dcellc[p]=DCEL_Cell(code,cx,cy,cz);',"Dcellc[p]=DCEL_Cell(code,cx,cy,cz);`n      Require(DCEL_Cellx(code,Dcellc[p])==cx&&DCEL_Celly(code,Dcellc[p])==cy&&DCEL_Cellz(code,Dcellc[p])==cz,`"Static packed cell round-trip failed`");")
  $newSource=(Get-Content -LiteralPath $harness -Raw).Replace("`r`n","`n").TrimEnd([char[]]"`r`n")
  if($newSource -cne $expected){throw 'R3 fixture must differ only by declared cell packing and round-trip assertion'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'VS environment failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $project=Join-Path $source 'VS\DualSPHysics5ReCpu.vcxproj';[xml]$xml=Get-Content -LiteralPath $project -Raw
  $objects=@();$sources=@()
  foreach($node in $xml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
    $excluded=$false
    foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -eq "'`$(Configuration)|`$(Platform)'=='$Configuration|x64'"){$excluded=$e.InnerText.Trim() -eq 'true'}}
    $stem=[IO.Path]::GetFileNameWithoutExtension($node.GetAttribute('Include'))
    if(!$excluded -and $stem -ne 'main'){$objects+=Join-Path $source "VS\Intermediate\DualSPHysics_${Configuration}_x64\$stem.obj";$sources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include')))}
  }
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -Recurse -File|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $controlOut=Join-Path $tests "outputs\upl_p2_feedback_${Configuration}_r2_run"
  $controlFiles=@('ledger.csv','momentum.csv','history.csv','halves.csv','guards.csv','complete.json')
  $controls=@($controlFiles|ForEach-Object {Entry (Join-Path $controlOut $_)})
  $inputs=@(@($project,$harness,$r1Harness,$r2Harness,$base,$PSCommandPath,$notes,$addendum,$repairNote,$failedSeal,$secondSeal,$authoritative)+$objects+$sources+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  $debug=$Configuration -eq 'DebugCPU';$suffix=if($debug){'Debug'}else{'Release'}
  $libs=@('dsphchrono.lib',"LibJVtkLib_x64_v143_$suffix.lib","LibJNumexLib_x64_v143_$suffix.lib","LibJWaveGen_x64_v143_$suffix.lib","LibDSphMoorDyn_x64_v143_$suffix.lib",'kernel32.lib','user32.lib','gdi32.lib','winspool.lib','comdlg32.lib','advapi32.lib','shell32.lib','ole32.lib','oleaut32.lib','uuid.lib','odbc32.lib','odbccp32.lib')
  $libraries=@($libs[0..4]|ForEach-Object {Entry (Join-Path $source "lib\vs2022\$_")})
  New-Item -ItemType Directory -Path $buildOut|Out-Null;$snapshots=@()
  foreach($path in @($harness,$r1Harness,$r2Harness,$base,$PSCommandPath,$notes,$addendum,$repairNote,$failedSeal,$secondSeal)){$dest=Join-Path $buildOut ([IO.Path]::GetFileName($path));Copy-Item -LiteralPath $path -Destination $dest;if((Entry $path).sha256 -ne (Entry $dest).sha256){throw 'Recipe snapshot mismatch'};$snapshots+=Entry $dest}
  $obj=Join-Path $buildOut 'upl_p3_actual_r3.obj';$log=Join-Path $logs ($name+'.build.log');[IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($debug){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$source\source","/Fo$obj","/Fd$buildOut\compile.pdb",'/sourceDependencies',(Join-Path $buildOut 'compile.dependencies.json'))+$flags+@($harness)
  $link=@('/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE',"/OUT:$exe","/LIBPATH:$source\lib\vs2022",$obj)+$objects+$libs;if($debug){$link+=@('/DEBUG',"/PDB:$buildOut\link.pdb")}
  $started=[DateTime]::UtcNow.ToString('o');$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$ce=$LASTEXITCODE;$le=$null
  if($ce -eq 0){& link.exe @link 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$le=$LASTEXITCODE};$ErrorActionPreference=$old
  Verify $inputs;Verify $libraries;Verify $controls;Verify $snapshots;$runtime=@()
  if($ce -eq 0 -and $le -eq 0){foreach($path in (@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File|ForEach-Object {$_.FullName})+@(Join-Path $repo 'bin\windows\DsphConfig.xml'))){$a=Entry $path;$dest=Join-Path $buildOut ([IO.Path]::GetFileName($path));Copy-Item -LiteralPath $path -Destination $dest;$b=Entry $dest;if($a.sha256 -ne $b.sha256){throw 'Runtime copy changed'};$runtime+=@{original=$a;copy=$b}}}
  NewJson $buildReceipt ([ordered]@{status=if($ce -eq 0 -and $le -eq 0){'built_not_run'}else{'build_failed_retained'};configuration=$Configuration;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');compile_exit=$ce;link_exit=$le;inputs=$inputs;libraries=$libraries;snapshots=$snapshots;controls=$controls;compile=$compile;link=$link;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};runtime=$runtime;log=(Entry $log);physical_acceptance=$false})
  if($ce -ne 0 -or $le -ne 0){throw 'Companion build failed; preserve label'};Write-Output "BUILT $exe";exit 0
}
$build=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
if($build.status -ne 'built_not_run'){throw 'No accepted companion build'}
function VerifyAll{Verify $build.inputs;Verify $build.libraries;Verify $build.snapshots;Verify $build.controls;Verify @($build.program);foreach($a in $build.runtime){Verify @($a.copy)}}
VerifyAll
$runName=$name+'_run';$out=Join-Path $tests "outputs\$runName";$control=Join-Path $tests "outputs\${name}_feedback_control"
$receipt=Join-Path $logs ($runName+'.run.json');$check=Join-Path $logs ($runName+'.check.json');$log=Join-Path $logs ($runName+'.log')
foreach($p in @($out,$control,$receipt,$check,$log)){if(Test-Path -LiteralPath $p){throw "Fresh run required: $p"}}
$started=[DateTime]::UtcNow.ToString('o');[IO.File]::WriteAllBytes($log,[byte[]]@());$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
& $exe '--out' $out 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$actualExit=$LASTEXITCODE;$controlExit=$null
if($actualExit -eq 0){& $exe '--feedback-control' $control 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$controlExit=$LASTEXITCODE};$ErrorActionPreference=$old
NewJson $receipt ([ordered]@{started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');actual_exit=$actualExit;control_exit=$controlExit;owned_calls_exited=$true;program=(Entry $exe);build_receipt=(Entry $buildReceipt);log=(Entry $log);physical_acceptance=$false})
if($actualExit -ne 0 -or $controlExit -ne 0){throw 'Component/control rejected; preserve output and diagnose'}
VerifyAll
$done=Get-Content -LiteralPath (Join-Path $out 'complete.json') -Raw|ConvertFrom-Json
if(!$done.passed -or $done.cases -ne 40 -or $done.rate_checks -ne 744 -or $done.ct_sentinel_checks -ne 144 -or $done.periodic_C_proofs -ne 12 -or !$done.actual_private_helper -or $done.physical_acceptance){throw 'Actual component coverage mismatch'}
$comparisons=@()
foreach($a in $build.controls){$b=Entry (Join-Path $control ([IO.Path]::GetFileName($a.path)));if($a.sha256 -ne $b.sha256 -or $a.bytes -ne $b.bytes){throw "Unchanged P2 default-OFF control changed: $($a.path)"};$comparisons+=@{retained=$a;current=$b;byte_identical=$true}}
$files=@(@($out,$control)|ForEach-Object {Get-ChildItem -LiteralPath $_ -File -Recurse}|Sort-Object FullName|ForEach-Object {Entry $_.FullName});Verify $files
NewJson $check ([ordered]@{passed=$true;configuration=$Configuration;scope='actual private CPU helper component, not a physical trajectory';completion=$done;retained_P2_default_OFF_byte_comparisons=$comparisons;run_receipt=(Entry $receipt);build_receipt=(Entry $buildReceipt);files=$files;output_manifest_posthoc=$true;pre_run_output_attestation=$false;physical_acceptance=$false})
Write-Output "PASSED $check"
