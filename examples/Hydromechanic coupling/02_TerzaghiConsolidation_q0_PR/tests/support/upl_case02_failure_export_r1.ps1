# Offline conversion of the retained rejected trajectory, not a solver or acceptance check.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$runPath=Join-Path $tests 'logs\upl_case02_short_coarse_r1.run.json'
$tag='upl_case02_short_failure_r1'
$folder=Join-Path $tests ('outputs\'+$tag+'_export')
$log=Join-Path $tests ('logs\'+$tag+'.export.log')
$record=Join-Path $tests ('logs\'+$tag+'.export.json')
$program=Join-Path $repo 'bin\windows\PartVTK_win64.exe'
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($item in $items){$now=Entry $item.path;if($now.bytes -ne $item.bytes -or $now.sha256 -ine $item.sha256){throw "Retained evidence changed: $($item.path)"}}}
foreach($path in @($folder,$log,$record)){if(Test-Path -LiteralPath $path){throw "Retained export protected: $path"}}
$run=Get-Content -Encoding UTF8 -Raw -LiteralPath $runPath|ConvertFrom-Json
if($run.passed -ne $false -or $run.exit_code -ne 1 -or !$run.owned_call_exited -or $run.native_frames -ne 76 -or $run.completion){throw 'Expected sealed interrupted coarse trajectory only'}
$bindings=@((Entry $PSCommandPath),(Entry $runPath),(Entry $program),(Entry (Join-Path $repo 'bin\windows\DsphConfig.xml')))+@($run.files)
Verify $bindings
[void](New-Item -ItemType Directory -Path $folder)
$data=Join-Path $tests 'outputs\upl_case02_short_coarse_r1\data'
$argv=@('-dirin',$data,'-first:0','-last:75','-savecsv',(Join-Path $folder 'native.csv'),'-csvsep:1','-onlytype:+all','-vars:-all,+idp,+vel,+rhop,+PorePress,+PoroVolumeRatio,+PoroPorosity,+PoroThetaLastStage,+SigmaState_kk,+SigmaState_ij,+Kplastic,+FSType,+HydroMechLoadAce')
$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location (Split-Path -Parent $program)
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $program @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}
catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$unchanged=$false;try{Verify $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$files=@(Get-ChildItem -LiteralPath $folder -File|ForEach-Object{Entry $_.FullName})
$csv=@($files|Where-Object{[IO.Path]::GetExtension($_.path) -ieq '.csv'})
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $csv.Count -eq 76)
$result=[ordered]@{stage=$tag;passed=$passed;scope='Diagnostic CSV conversion of all76 retained native frames only; not bit-exact typed validation or a completed trajectory';solver_run=(Entry $runPath);program=(Entry $program);arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;bindings=$bindings;bindings_unchanged=$unchanged;files=$files;CSV_frames=$csv.Count;log=$(if(Test-Path -LiteralPath $log){Entry $log}else{$null});solver_started=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Offline export rejected; inspect $record without rerunning solver"}
Write-Output "Retained partial CSVs exported: $record"
