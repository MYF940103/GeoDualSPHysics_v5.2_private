param()
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$name='upl_p3_spectrum_r1'
$dir=Join-Path $tests "outputs\$name"
$receipt=Join-Path $tests "logs\$name.check.json"
$cpp=Join-Path $PSScriptRoot ($name+'.cpp')
$py=Join-Path $PSScriptRoot ($name+'.py')
$note=Join-Path $tests ("notes\$name.json")
$python='D:\Anaconda3\python.exe'
function Entry([string]$path){$item=Get-Item -LiteralPath $path;[ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function NewJson([string]$path,$value){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 14)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if((Test-Path -LiteralPath $dir) -or (Test-Path -LiteralPath $receipt)){throw 'Fresh offline labels only'}
$wavecheck=Join-Path $tests 'logs\upl_p3_wave_ReleaseCPU_r3.check.json'
$check=Get-Content -LiteralPath $wavecheck -Raw|ConvertFrom-Json
if(!$check.passed){throw 'Retained actual wave gate did not pass'}
foreach($file in @($check.build,$check.seeds)+$check.receipts+$check.files){$actual=Entry $file.path;if($actual.sha256 -ne $file.sha256 -or $actual.bytes -ne $file.bytes){throw "Retained wave artifact changed: $($file.path)"}}
$buildreceipt=Join-Path $tests 'logs\upl_p3_actual_build_r2.json'
$build=Get-Content -LiteralPath $buildreceipt -Raw|ConvertFrom-Json
foreach($pair in $build.source){foreach($file in @($pair.original,$pair.snapshot)){$actual=Entry $file.path;if($actual.sha256 -ne $file.sha256 -or $actual.bytes -ne $file.bytes){throw "Frozen production source changed: $($file.path)"}}}
$seed=Join-Path $tests 'outputs\upl_p2_wave_seed_r2_c\CaseUplWave_c.xml'
[xml]$xml=Get-Content -LiteralPath $seed -Raw
$ct=$xml.case.execution.constants;$h=$ct.h.value;$rho=$ct.rhop0.value;$mass=$ct.massfluid.value
$actualdir=Join-Path $tests 'outputs\upl_p3_wave_ReleaseCPU_r3_k0_c_actual'
$runout=Join-Path $actualdir 'Run.out'
$state=Join-Path $actualdir 'physical.bin'
$complete=Join-Path $actualdir 'complete.json'
$text=Get-Content -LiteralPath $runout -Raw
function Loaded([string]$key){$match=[regex]::Match($text,"(?m)^\s*$([regex]::Escape($key)):\s*([0-9.eE+-]+)\s*$");if(!$match.Success){throw "Missing loaded $key"};$match.Groups[1].Value}
$K=Loaded 'Bulk Modulus';$G=Loaded 'Shear Modulus';$n=Loaded 'Porosity';$rhow=Loaded 'PoreWaterRho'
# Run.out rounds Kw to six significant figures; bound seed keeps exactly representable 2^26.
$kw=$xml.case.execution.special.hydromechanics.PoreWaterBulkModulus.value
$paths=@($PSCommandPath,$cpp,$py,$note,$seed,$runout,$state,$complete,$wavecheck,$buildreceipt,$python,(Join-Path $source 'source\JSph.cpp'))
foreach($pair in $build.source){$paths+=@($pair.original.path,$pair.snapshot.path)}
$paths+=Get-ChildItem -LiteralPath (Join-Path $source 'source') -File|Where-Object {$_.Extension -eq '.h'}|ForEach-Object {$_.FullName}
$inputs=@($paths|Sort-Object -Unique|ForEach-Object {Entry $_})
New-Item -ItemType Directory -Path $dir|Out-Null
foreach($path in @($cpp,$py,$note,$PSCommandPath)){Copy-Item -LiteralPath $path -Destination (Join-Path $dir ([IO.Path]::GetFileName($path)))}
$snapshots=@(Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Entry $_.FullName})
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$envlines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $envlines){$at=$line.IndexOf('=');if($at -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$at),$line.Substring($at+1),'Process')}}
$exe=Join-Path $dir ($name+'.exe');$buildlog=Join-Path $tests "logs\$name.build.log"
$compile=@('/nologo','/std:c++17','/EHsc','/W3','/O2','/MT','/fp:precise',"/I$source\source","/Fo$dir\symbol.obj","/Fe$exe",'/sourceDependencies',"$dir\compile.dependencies.json",$cpp)
$started=[DateTime]::UtcNow.ToString('o');$previous=$ErrorActionPreference;$ErrorActionPreference='Continue'
& cl.exe @compile 2>&1|Tee-Object -FilePath $buildlog|Out-Host
$buildexit=$LASTEXITCODE;$ErrorActionPreference=$previous;$jobs=@();$analysis=$null;$symbol_match=$false
if($buildexit -eq 0){
  $symbols=Join-Path $dir 'symbols.csv'
  $arguments=@($state,$symbols,$h,$K,$G,$kw,$n,$rho,$mass,$rhow)
  & $exe @arguments
  $code=$LASTEXITCODE;$jobs+=@{label='actual_header_symbols';exit_code=$code;arguments=$arguments}
  if($code -eq 0){
    $first=Import-Csv -LiteralPath $symbols|Where-Object {[double]$_.J -eq 1 -and [int]$_.m -eq 1}
    $old=Get-Content -LiteralPath $complete -Raw|ConvertFrom-Json
    $pairs=@(@('Kr','discrete_Kr'),@('Ks','discrete_Ks'),@('Ksig','discrete_Ksig'),@('ell','discrete_ell'))
    foreach($pair in $pairs){$now=[double]$first.($pair[0]);$prior=[double]$old.($pair[1]);if([math]::Abs($now-$prior) -gt 32768*2.2204460492503131e-16*[math]::Max(1,[math]::Abs($prior))){throw "Actual-P3 symbol mismatch $($pair[0]): $now / $prior"}}
    $symbol_match=$true
    $arguments=@('-B',$py,$symbols,(Join-Path $dir 'spectrum.csv'))
    & $python @arguments
    $code=$LASTEXITCODE;$jobs+=@{label='matrix_time_map_audit';exit_code=$code;arguments=$arguments}
    if($code -eq 0){$analysis=Get-Content -LiteralPath (Join-Path $dir 'spectrum.json') -Raw|ConvertFrom-Json}
  }
}
foreach($file in $inputs+$snapshots){$now=Entry $file.path;if($now.sha256 -ne $file.sha256 -or $now.bytes -ne $file.bytes){throw "Frozen offline input changed: $($file.path)"}}
$passed=$buildexit -eq 0 -and $jobs.Count -eq 2 -and @($jobs|Where-Object {$_.exit_code -ne 0}).Count -eq 0 -and $symbol_match -and $analysis.offline_mathematical_checks_passed
NewJson $receipt ([ordered]@{passed=$passed;offline_mathematical_checks_only=$true;physical_acceptance=$false;new_project_solver=$false;production_edits=$false;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');compile=$compile;build_exit=$buildexit;jobs=$jobs;J1_m1_matches_retained_actual_symbols=$symbol_match;inputs=$inputs;snapshots=$snapshots;files=@(Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Entry $_.FullName});build_log=Entry $buildlog})
if(!$passed){throw 'Offline audit failed; preserve and inspect label'}
Write-Output "OFFLINE COMPLETE $receipt"
