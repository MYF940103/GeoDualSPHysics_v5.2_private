param()
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$name='upl_p2_wave_symbol_r2'
$dir=Join-Path $tests "outputs\$name"
$receipt=Join-Path $tests "logs\$name.check.json"
$cpp=Join-Path $PSScriptRoot 'upl_p2_wave_symbol_r2.cpp'
$note=Join-Path $tests 'notes\upl_p2_wave_symbol_r2.json'
function Entry([string]$path){$item=Get-Item -LiteralPath $path;[ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function NewJson([string]$path,$value){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 14)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if((Test-Path -LiteralPath $dir) -or (Test-Path -LiteralPath $receipt)){throw 'Use a fresh label; do not overwrite offline evidence'}
$wavecheck=Join-Path $tests 'logs\upl_p2_wave_ReleaseCPU_r3.check.json'
$check=Get-Content -LiteralPath $wavecheck -Raw|ConvertFrom-Json
if(!$check.passed){throw 'Retained wave implementation gate did not pass'}
foreach($file in @($check.build,$check.seeds)+$check.receipts+$check.files){$actual=Entry $file.path;if($actual.sha256 -ne $file.sha256 -or $actual.bytes -ne $file.bytes){throw "Retained wave artifact changed: $($file.path)"}}
$seed=Join-Path $tests 'outputs\upl_p2_wave_seed_r2_c\CaseUplWave_c.xml'
[xml]$xml=Get-Content -LiteralPath $seed -Raw
$ct=$xml.case.execution.constants;$h=$ct.h.value;$rho=$ct.rhop0.value;$mass=$ct.massfluid.value
$runout=Join-Path $tests 'outputs\upl_p2_wave_ReleaseCPU_r3_c_actual\Run.out'
$text=Get-Content -LiteralPath $runout -Raw
function Loaded([string]$key){$match=[regex]::Match($text,"(?m)^\s*$([regex]::Escape($key)):\s*([0-9.eE+-]+)\s*$");if(!$match.Success){throw "Missing loaded $key"};$match.Groups[1].Value}
$K=Loaded 'Bulk Modulus';$G=Loaded 'Shear Modulus';$n=Loaded 'Porosity'
# Run.out prints Kw with only six significant figures. The bound seed retains
# exact input 2^26, representable in the loaded float; cu_actual cross-checks it.
$kw=$xml.case.execution.special.hydromechanics.PoreWaterBulkModulus.value
$paths=@($PSCommandPath,$cpp,$note,$seed,$runout,$wavecheck)
foreach($which in 'c','h'){$paths+=Join-Path $tests "outputs\upl_p2_wave_ReleaseCPU_r3_${which}_actual\physical.bin";$paths+=Join-Path $tests "outputs\upl_p2_wave_ReleaseCPU_r3_${which}_actual\modes.csv"}
$paths+=Get-ChildItem -LiteralPath (Join-Path $source 'source') -File|Where-Object {$_.Extension -eq '.h'}|ForEach-Object {$_.FullName}
$inputs=@($paths|Sort-Object -Unique|ForEach-Object {Entry $_})
New-Item -ItemType Directory -Path $dir|Out-Null
foreach($path in @($cpp,$note,$PSCommandPath)){Copy-Item -LiteralPath $path -Destination (Join-Path $dir ([IO.Path]::GetFileName($path)))}
$snapshots=@(Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Entry $_.FullName})
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$envlines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $envlines){$at=$line.IndexOf('=');if($at -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$at),$line.Substring($at+1),'Process')}}
$exe=Join-Path $dir ($name+'.exe');$buildlog=Join-Path $tests "logs\$name.build.log"
$compile=@('/nologo','/std:c++17','/EHsc','/W3','/O2','/MT','/fp:precise',"/I$source\source","/Fo$dir\symbol.obj","/Fe$exe",'/sourceDependencies',"$dir\compile.dependencies.json",$cpp)
$started=[DateTime]::UtcNow.ToString('o');$previous=$ErrorActionPreference;$ErrorActionPreference='Continue'
& cl.exe @compile 2>&1|Tee-Object -FilePath $buildlog|Out-Host
$buildexit=$LASTEXITCODE;$ErrorActionPreference=$previous;$jobs=@()
if($buildexit -eq 0){foreach($which in 'c','h'){
  $actual=Join-Path $tests "outputs\upl_p2_wave_ReleaseCPU_r3_${which}_actual"
  $prefix=Join-Path $dir $which
  $arguments=@((Join-Path $actual 'physical.bin'),(Join-Path $actual 'modes.csv'),$prefix,$h,$K,$G,$kw,$n,$rho,$mass,'.125','.0625','.001953125','257')
  & $exe @arguments
  $exit=$LASTEXITCODE;$jobs+=@{label=$which;exit_code=$exit;arguments=$arguments}
  if($exit -ne 0){break}
}}
foreach($file in $inputs+$snapshots){$actual=Entry $file.path;if($actual.sha256 -ne $file.sha256 -or $actual.bytes -ne $file.bytes){throw "Frozen offline input changed: $($file.path)"}}
$passed=$buildexit -eq 0 -and $jobs.Count -eq 2 -and @($jobs|Where-Object {$_.exit_code -ne 0}).Count -eq 0
NewJson $receipt ([ordered]@{offline_completed=$passed;physical_acceptance=$false;new_solver=$false;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');compile=$compile;build_exit=$buildexit;jobs=$jobs;inputs=$inputs;snapshots=$snapshots;files=@(Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Entry $_.FullName});build_log=Entry $buildlog})
if(!$passed){throw 'Offline attribution failed; preserve label and inspect receipt'}
Write-Output "OFFLINE COMPLETE $receipt"
