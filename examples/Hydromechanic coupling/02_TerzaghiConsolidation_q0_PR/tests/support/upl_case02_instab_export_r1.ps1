param([switch]$ExecutionAuthorized)
# One offline official PartVTK call against the already rejected dt-only run.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Root review and explicit -ExecutionAuthorized are required'}
$tests=Split-Path -Parent $PSScriptRoot
$tag='upl_case02_instab_half_r1'
$runPath=Join-Path $tests ('logs\'+$tag+'.run.json')
$priorPath=Join-Path $tests 'logs\upl_case02_short_failure_r1.export.json'
$folder=Join-Path $tests ('outputs\'+$tag+'_export')
$log=Join-Path $tests ('logs\'+$tag+'.export.log')
$record=Join-Path $tests ('logs\'+$tag+'.export.json')
function Entry([string]$path){$f=Get-Item -Force -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($items){foreach($item in $items){$now=Entry $item.path;if($now.bytes -ne $item.bytes -or $now.sha256 -ine $item.sha256){throw "Retained evidence changed: $($item.path)"}}}
foreach($path in @($folder,$log,$record)){if(Test-Path -LiteralPath $path){throw "Retained export protected: $path"}}
$run=Get-Content -Encoding UTF8 -Raw -LiteralPath $runPath|ConvertFrom-Json
if($run.stage -cne $tag -or $run.exit_code -ne 1 -or !$run.owned_call_exited -or !$run.bindings_unchanged -or $run.native_frames -ne 76 -or $run.actual_complete_exists -ne $false -or $run.accepted_half_pair -ne $false -or $run.physical_acceptance -ne $false){throw 'Expected sealed rejected dt-only half diagnostic, not an accepted half'}
Verify @($run.owned_exit_record)
$solver=Get-Content -Encoding UTF8 -Raw -LiteralPath $run.owned_exit_record.path|ConvertFrom-Json
if(!$solver.direct_native_call -or !$solver.typed_LASTEXITCODE_captured_immediately -or !$solver.owned_call_exited -or $solver.exit_code -ne 1 -or $solver.invocation_failure -or !$solver.diagnostic_only){throw 'Missing actual typed rejected solver ownership'}
$data=Join-Path $tests ('outputs\'+$tag+'\data')
if($solver.arguments[0] -cne '--solver' -or $solver.arguments[1] -cne 'half' -or $solver.arguments[7] -cne (Split-Path -Parent $data)){throw 'Rejected solver output attribution differs'}
$parts=@(Get-ChildItem -LiteralPath $data -File|Where-Object{$_.Name -cmatch '^Part_\d{4}\.bi4$'}|Sort-Object Name)
if($parts.Count -ne 76 -or (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $data) 'actual_complete.json'))){throw 'Expected exactly76 retained PART frames and no successful completion'}
for($i=0;$i -lt 76;$i++){if($parts[$i].Name -cne ('Part_{0:D4}.bi4' -f $i)){throw 'PART sequence incomplete'}}
$prior=Get-Content -Encoding UTF8 -Raw -LiteralPath $priorPath|ConvertFrom-Json
if(!$prior.direct_native_call -or !$prior.typed_LASTEXITCODE_captured_immediately -or !$prior.owned_call_exited -or $prior.exit_code -ne 0 -or $prior.failure -or !$prior.bindings_unchanged -or [IO.Path]::GetFileName($prior.program.path) -cne 'PartVTK_win64.exe'){throw 'Prior actual official converter call missing; prior counting failure is not accepted as a whole pass'}
$argv=@($prior.arguments)
if($argv.Count -ne 9 -or $argv[0] -cne '-dirin' -or $argv[2] -cne '-first:0' -or $argv[3] -cne '-last:75' -or $argv[4] -cne '-savecsv' -or $argv[6] -cne '-csvsep:1' -or $argv[7] -cne '-onlytype:+all' -or $argv[8] -cne '-vars:-all,+idp,+vel,+rhop,+PorePress,+PoroVolumeRatio,+PoroPorosity,+PoroThetaLastStage,+SigmaState_kk,+SigmaState_ij,+Kplastic,+FSType,+HydroMechLoadAce'){throw 'Official retained variable/parameter vector differs'}
$argv[1]=$data;$argv[5]=Join-Path $folder 'native.csv'
$config=@($prior.bindings|Where-Object{[IO.Path]::GetFileName($_.path) -ceq 'DsphConfig.xml'})
if($config.Count -ne 1){throw 'Unique retained PartVTK runtime config missing'}
$bindings=@((Entry $PSCommandPath),(Entry (Join-Path $tests 'notes\upl_case02_instab_export_r1.json')),(Entry $runPath),(Entry $priorPath),$run.owned_exit_record,$run.source_build,$run.input_manifest,$run.rejected_control,$solver.program,$prior.program)+$config+@($run.bindings)+@($run.files)
Verify $bindings
[void](New-Item -ItemType Directory -Path $folder)
[IO.File]::WriteAllText($log,'',(New-Object Text.UTF8Encoding($false)))
$code=$null;$failure=$null;$started=[DateTime]::UtcNow.ToString('o');$oldPreference=$ErrorActionPreference
Push-Location (Split-Path -Parent $prior.program.path)
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $prior.program.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}
catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$unchanged=$false;try{Verify $bindings;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$files=@(Get-ChildItem -LiteralPath $folder -File|ForEach-Object{Entry $_.FullName})
$frames=@($files|Where-Object{[IO.Path]::GetFileName($_.path) -cmatch '^native_\d{4}\.csv$'}|Sort-Object path)
$statistics=@($files|Where-Object{[IO.Path]::GetFileName($_.path) -ceq 'native_stats.csv'})
$otherCsv=@($files|Where-Object{[IO.Path]::GetExtension($_.path) -ieq '.csv' -and [IO.Path]::GetFileName($_.path) -cnotmatch '^native_\d{4}\.csv$' -and [IO.Path]::GetFileName($_.path) -cne 'native_stats.csv'})
$sequence=($frames.Count -eq 76)
if($sequence){for($i=0;$i -lt 76;$i++){if([IO.Path]::GetFileName($frames[$i].path) -cne ('native_{0:D4}.csv' -f $i)){$sequence=$false}}}
$passed=($code -is [int] -and $code -eq 0 -and !$failure -and $unchanged -and $sequence -and $statistics.Count -le 1 -and $otherCsv.Count -eq 0)
$result=[ordered]@{stage=$tag+'_export';passed=$passed;scope='Diagnostic official CSV conversion of76 rejected dt-only frames; not completed-half or physical acceptance';solver_run=(Entry $runPath);solver_exit_record=$run.owned_exit_record;prior_converter_call=(Entry $priorPath);prior_whole_export_pass_inherited=$false;program=$prior.program;arguments=$argv;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;bindings=$bindings;bindings_unchanged=$unchanged;files=$files;CSV_frames=$frames.Count;native_frame_sequence_0000_through_0075=$sequence;statistics_CSV_count=$statistics.Count;statistics_files=$statistics;other_CSV_count=$otherCsv.Count;log=(Entry $log);solver_started=$false;half_pair_accepted=$false;bit_exact_typed_native_validation=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Offline conversion rejected; retain outputs and inspect $record without rerunning the solver"}
Write-Output "Rejected diagnostic frames exported: $record"

