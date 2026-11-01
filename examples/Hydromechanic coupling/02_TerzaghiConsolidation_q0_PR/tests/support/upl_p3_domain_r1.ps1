param([switch]$ExecuteReviewedRecipe)
$ErrorActionPreference='Stop'
if(!$ExecuteReviewedRecipe){throw 'Read the prospective declaration before executing this offline algebra audit.'}
$tests=Split-Path -Parent $PSScriptRoot
$script=Join-Path $PSScriptRoot 'upl_p3_domain_r1.py'
$note=Join-Path $tests 'notes\upl_p3_domain_r1.json'
$xml=Join-Path $tests 'outputs\upl_p3_wave_seed_r1_c\CaseUplWave_c.xml'
$out=Join-Path $tests 'outputs\upl_p3_wave_DebugCPU_r3_k1_c_actual\Run.out'
$completion=Join-Path $tests 'outputs\upl_p3_wave_DebugCPU_r3_k1_c_actual\complete.json'
$receipt=Join-Path $tests 'logs\upl_p3_wave_DebugCPU_r3_k1_c_actual.run.json'
$final=Join-Path $tests 'logs\upl_p3_wave_DebugCPU_r3.check.json'
$log=Join-Path $tests 'logs\upl_p3_domain_r1.log'
$check=Join-Path $tests 'logs\upl_p3_domain_r1.check.json'
$python='D:\Anaconda3\python.exe'
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($entries){foreach($a in $entries){$b=Entry $a.path;if($a.bytes -ne $b.bytes -or $a.sha256 -ne $b.sha256){throw "Frozen audit input changed: $($a.path)"}}}
foreach($p in @($log,$check)){if(Test-Path -LiteralPath $p){throw 'Retained domain audit protected; no retry or overwrite.'}}
if(!(Get-Content -LiteralPath $final -Raw|ConvertFrom-Json).passed){throw 'Completed current-wave evidence is not admitted'}
$inputs=@(@($script,$note,$PSCommandPath,$xml,$out,$completion,$receipt,$final)|ForEach-Object {Entry $_})
$program=Entry $python
$arguments=@('-B',$script,'--xml',$xml,'--run-out',$out,'--completion',$completion,'--run-receipt',$receipt,'--declaration',$note)
$started=[DateTime]::UtcNow.ToString('o')
$prior=$ErrorActionPreference;$ErrorActionPreference='Continue'
$output=@(& $python @arguments 2>&1|ForEach-Object {"$_"});$exitCode=$LASTEXITCODE
$ErrorActionPreference=$prior
[IO.File]::WriteAllLines($log,$output,(New-Object Text.UTF8Encoding($false)))
Verify $inputs;Verify @($program)
$result=if($exitCode -eq 0){($output -join [Environment]::NewLine)|ConvertFrom-Json}else{$null}
$passed=($exitCode -eq 0 -and $result.passed -and $result.positive_k_samples -eq 6 -and $result.k0_samples -eq 2 -and !$result.new_solver_started -and !$result.production_guard_implemented -and !$result.physical_acceptance)
$record=[ordered]@{passed=$passed;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');owned_python_exit=$exitCode;program=$program;arguments=$arguments;inputs=$inputs;log=(Entry $log);result=$result;new_solver_started=$false;production_guard_implemented=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($check,($record|ConvertTo-Json -Depth 15)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw 'Offline domain audit rejected; preserve log/check and diagnose without automatic retry.'}
Write-Output "PASSED offline continuous-domain audit; no production/physical admission: $check"
