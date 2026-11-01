param()
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$name='upl_p3_spatial_symbol_r2'
$dir=Join-Path $tests "outputs\$name"
$receipt=Join-Path $tests "logs\$name.check.json"
$cpp=Join-Path $PSScriptRoot 'upl_p3_spatial_symbol_r1.cpp';$py=Join-Path $PSScriptRoot 'upl_p3_spatial_symbol_r1.py'
$note=Join-Path $tests 'notes\upl_p3_spatial_plan_r1.json'
$python='D:\Anaconda3\python.exe'
function Entry([string]$path){$item=Get-Item -LiteralPath $path;[ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($item in $items){$actual=Entry $item.path;if($actual.sha256-ne$item.sha256-or$actual.bytes-ne$item.bytes){throw "Frozen input changed: $($item.path)"}}}
function NewJson([string]$path,$value){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 15)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
if((Test-Path -LiteralPath $dir)-or(Test-Path -LiteralPath $receipt)){throw 'Fresh offline audit label only'}
$oldcheckPath=Join-Path $tests 'logs\upl_p3_spectrum_r1.check.json'
$oldcheck=Get-Content -Raw -LiteralPath $oldcheckPath|ConvertFrom-Json
if(!$oldcheck.passed){throw 'Sealed original symbol audit missing'}
Verify $oldcheck.files
$oldsymbol=Join-Path $tests 'outputs\upl_p3_spectrum_r1\symbols.csv'
$actual=Join-Path $tests 'outputs\upl_p3_wave_ReleaseCPU_r3_k1_c_actual'
$state=Join-Path $actual 'physical.bin';$runout=Join-Path $actual 'Run.out';$complete=Join-Path $actual 'complete.json'
$oldwave=Get-Content -Raw -LiteralPath (Join-Path $tests 'logs\upl_p3_wave_ReleaseCPU_r3.check.json')|ConvertFrom-Json
if(!$oldwave.passed){throw 'Original actual wave not accepted'}
foreach($path in @($state,$runout,$complete)){$binding=@($oldwave.files|Where-Object {$_.path-eq$path});if($binding.Count-ne1){throw 'Ambiguous retained wave binding'};Verify $binding}
$text=Get-Content -Raw -LiteralPath $runout
function Loaded([string]$key){$m=[regex]::Match($text,"(?m)^\s*$([regex]::Escape($key))\s*[:=]\s*([0-9.eE+-]+)\s*$");if(!$m.Success){throw "Missing loaded $key"};$m.Groups[1].Value}
$K=Loaded 'Bulk Modulus';$G=Loaded 'Shear Modulus';$n=Loaded 'Porosity';$rho=Loaded 'RhopZero';$mass=Loaded 'MassFluid';$rhow=Loaded 'PoreWaterRho'
$seed=Join-Path $tests 'outputs\upl_p3_wave_seed_r1_c\CaseUplWave_c.xml'
[xml]$xml=Get-Content -Raw -LiteralPath $seed
$kw=$xml.case.execution.special.hydromechanics.PoreWaterBulkModulus.value
if([double]$kw-ne67108864-or[double]$xml.case.execution.special.hydromechanics.HydraulicConductivity.value-ne.0001){throw 'Physical material changed'}
$paths=@($PSCommandPath,$cpp,$py,$note,$python,$oldcheckPath,$oldsymbol,$state,$runout,$complete,$seed,(Join-Path $source 'source\JSph.cpp'),(Join-Path $source 'source\JSphCpu.cpp'))
$paths+=Get-ChildItem -LiteralPath (Join-Path $source 'source') -File|Where-Object {$_.Extension-eq'.h'}|ForEach-Object {$_.FullName}
$inputs=@($paths|Sort-Object -Unique|ForEach-Object {Entry $_})
New-Item -ItemType Directory -Path $dir|Out-Null
foreach($path in @($cpp,$py,$note,$PSCommandPath)){Copy-Item -LiteralPath $path -Destination (Join-Path $dir ([IO.Path]::GetFileName($path)))}
$snapshots=@(Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Entry $_.FullName})
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment setup failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i-gt0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$exe=Join-Path $dir ($name+'.exe');$buildlog=Join-Path $tests "logs\$name.build.log"
$compile=@('/nologo','/std:c++17','/EHsc','/W3','/O2','/MT','/fp:precise',"/I$source\source","/Fo$dir\symbol.obj","/Fe$exe",'/sourceDependencies',"$dir\compile.dependencies.json",$cpp)
$started=[DateTime]::UtcNow.ToString('o');$previous=$ErrorActionPreference;$ErrorActionPreference='Continue'
& cl.exe @compile 2>&1|Tee-Object -FilePath $buildlog|Out-Host
$buildexit=$LASTEXITCODE;$ErrorActionPreference=$previous;$jobs=@();$analysis=$null;$symbolMatch=$false
if($buildexit-eq0){
  $symbols=Join-Path $dir 'symbols.csv'
  $arguments=@($state,$symbols,$K,$G,$kw,$n,$rho,$rhow,$mass)
  & $exe @arguments;$code=$LASTEXITCODE;$jobs+=@{label='actual_header_frozen_spatial_symbols';exit_code=$code;arguments=$arguments}
  if($code-eq0){
    $first=@(Import-Csv -LiteralPath $symbols)[0]
    $old=@(Import-Csv -LiteralPath $oldsymbol|Where-Object {[double]$_.J-eq1-and[int]$_.m-eq1})
    if($old.Count-ne1){throw 'Ambiguous old mode1 control'}
    foreach($key in @('Mxx','Cxx','Kr','Ks','Ksig','Ka','ell')){$now=[double]$first.$key;$prior=[double]$old[0].$key;if([math]::Abs($now-$prior)-gt32768*2.2204460492503131e-16*[math]::Max(1,[math]::Abs($prior))){throw "Original16-grid symbol mismatch: $key"}}
    $symbolMatch=$true;$arguments=@('-B',$py,$symbols,(Join-Path $dir 'predictions.csv'))
    & $python @arguments;$code=$LASTEXITCODE;$jobs+=@{label='frozen_continuum_discrete_predictions';exit_code=$code;arguments=$arguments}
    if($code-eq0){$analysis=Get-Content -Raw -LiteralPath (Join-Path $dir 'predictions.json')|ConvertFrom-Json}
  }
}
Verify ($inputs+$snapshots)
$passed=$buildexit-eq0-and$jobs.Count-eq2-and@($jobs|Where-Object {$_.exit_code-ne0}).Count-eq0-and$symbolMatch-and$analysis.offline_mathematical_checks_passed
NewJson $receipt ([ordered]@{passed=$passed;offline_only=$true;production_edits=$false;project_solver_started=$false;actual_wave_or_gencase_run=$false;actual_execution_authorized=$false;physical_acceptance=$false;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');build_exit=$buildexit;compile=$compile;jobs=$jobs;original16_grid_symbols_match=$symbolMatch;inputs=$inputs;snapshots=$snapshots;files=@(Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Entry $_.FullName});build_log=Entry $buildlog})
if(!$passed){throw 'Offline spatial audit failed; preserve output and use a fresh repair label'}
Write-Output "OFFLINE SPATIAL COMPLETE $receipt"


