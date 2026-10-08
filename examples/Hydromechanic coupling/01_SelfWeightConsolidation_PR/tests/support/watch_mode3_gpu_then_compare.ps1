param(
  [string]$TestsDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [int]$PollSeconds = 600
)

$ErrorActionPreference = "Stop"

$pidPath = Join-Path $TestsDir "run_scenario2_mode3_gpu_full.pid"
$watchLog = Join-Path $TestsDir "run_scenario2_mode3_gpu_watch.log"
$outDir = Join-Path $TestsDir "outputs\CaseSWScenario2_Mode3_GPU_out"
$dataDir = Join-Path $outDir "data"
$figDir = Join-Path $TestsDir "figures\CaseSWScenario2_Mode3_GPU"
$cpuFigDir = Resolve-Path (Join-Path $TestsDir "..\figures")
$compareDir = Join-Path $TestsDir "figures\mode3_gpu_vs_cpu_compare"
$notePath = Join-Path $TestsDir "notes\self_weight_mode3_gpu_cpu_comparison_20260629.md"

function Write-WatchLog([string]$Message) {
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  Add-Content -Path $watchLog -Value $line -Encoding UTF8
}

Write-WatchLog "Watcher started. TestsDir=$TestsDir PollSeconds=$PollSeconds"

if(!(Test-Path $pidPath)) {
  Write-WatchLog "PID file not found: $pidPath"
  exit 2
}

$runPid = [int](Get-Content $pidPath)
Write-WatchLog "Watching process PID=$runPid"

while($true) {
  $proc = Get-Process -Id $runPid -ErrorAction SilentlyContinue
  $parts = @()
  if(Test-Path $dataDir) {
    $parts = @(Get-ChildItem -LiteralPath $dataDir -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "Part_*.bi4" } | Sort-Object Name)
  }
  $lastPart = if($parts.Count) { $parts[-1].Name } else { "none" }
  $lastWrite = if($parts.Count) { $parts[-1].LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss") } else { "none" }
  if($proc) {
    Write-WatchLog ("RUNNING parts={0} last={1} lastWrite={2}" -f $parts.Count,$lastPart,$lastWrite)
    Start-Sleep -Seconds $PollSeconds
  }
  else {
    Write-WatchLog ("Process ended. parts={0} last={1} lastWrite={2}" -f $parts.Count,$lastPart,$lastWrite)
    break
  }
}

Start-Sleep -Seconds 10

$errLog = Join-Path $TestsDir "run_scenario2_mode3_gpu_full.err.log"
$stdoutLog = Join-Path $TestsDir "run_scenario2_mode3_gpu_full.log"
if(Test-Path $errLog) {
  $errLen = (Get-Item $errLog).Length
  Write-WatchLog "stderr length=$errLen"
}
if(Test-Path $stdoutLog) {
  $tail = Get-Content $stdoutLog -Tail 5 -ErrorAction SilentlyContinue
  Write-WatchLog ("stdout tail: " + ($tail -join " | "))
}

$gpuBottom = Join-Path $figDir "scenario2_bottom_dissipation.csv"
$gpuTargets = Join-Path $figDir "scenario2_target_summary.csv"
if(!(Test-Path $gpuBottom) -or !(Test-Path $gpuTargets)) {
  Write-WatchLog "Postprocessing outputs missing. Expected $gpuBottom and $gpuTargets"
  exit 3
}

$compareScript = Join-Path $PSScriptRoot "compare_mode3_gpu_cpu.py"
Write-WatchLog "Running CPU/GPU comparison."
& py $compareScript --cpu-figdir $cpuFigDir --gpu-figdir $figDir --outdir $compareDir --note $notePath --case CaseSWScenario2_Mode3_GPU 2>&1 | ForEach-Object { Write-WatchLog $_ }
if($LASTEXITCODE -ne 0) {
  Write-WatchLog "Comparison failed with exit code $LASTEXITCODE"
  exit $LASTEXITCODE
}

Write-WatchLog "Watcher finished successfully."
