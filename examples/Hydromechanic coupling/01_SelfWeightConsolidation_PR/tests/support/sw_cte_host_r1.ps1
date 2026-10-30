# Standalone CUDA argument reproduction only; no solver or production edits.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$out=Join-Path $tests 'outputs\sw_cte_host_r1'
$log=Join-Path $tests 'logs\sw_cte_host_r1.build.log'
$runlog=Join-Path $tests 'logs\sw_cte_host_r1.run.log'
$check=Join-Path $tests 'logs\sw_cte_host_r1.check.json'
$cu=Join-Path $PSScriptRoot 'sw_cte_host_r1.cu'
if((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $log) -or (Test-Path -LiteralPath $runlog) -or (Test-Path -LiteralPath $check)){throw 'Retained probe evidence exists'}
$null=New-Item -ItemType Directory -Path $out
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$nvcc='C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\bin\nvcc.exe'
$exe=Join-Path $out 'sw_cte_host_r1.exe'
$sourceHash=(Get-FileHash -LiteralPath $cu).Hash
$args=@('-arch=sm_86','-O2','-std=c++14','-ccbin','D:\Program Files\VS2022\VC\Tools\MSVC\14.36.32532\bin\Hostx64\x64','-o',$exe,$cu)
Push-Location $out
try{& $nvcc @args 2>&1 | Tee-Object -FilePath $log; $buildExit=$LASTEXITCODE}finally{Pop-Location}
$runExit=$null
if($buildExit -eq 0){& $exe 2>&1 | Tee-Object -FilePath $runlog; $runExit=$LASTEXITCODE}
if((Get-FileHash -LiteralPath $cu).Hash -ne $sourceHash){throw 'Probe source changed'}
function BindFile($p){[ordered]@{path=$p;bytes=(Get-Item -LiteralPath $p).Length;sha256=(Get-FileHash -LiteralPath $p).Hash}}
$artifacts=@(BindFile $log)
if(Test-Path -LiteralPath $exe){$artifacts+=BindFile $exe}
if(Test-Path -LiteralPath $runlog){$artifacts+=BindFile $runlog}
[ordered]@{build_exit=$buildExit;run_exit=$runExit;source=(BindFile $cu);recipe=(BindFile $PSCommandPath);compiler=(BindFile $nvcc);arguments=$args;artifacts=$artifacts;solver_started=$false;physical_acceptance=$false}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $check -Encoding UTF8
if($buildExit -ne 0 -or $runExit -ne 0){throw 'Probe failed; retain evidence and diagnose'}
