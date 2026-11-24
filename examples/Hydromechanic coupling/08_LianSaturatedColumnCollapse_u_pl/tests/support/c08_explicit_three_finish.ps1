param(
    [Parameter(Mandatory=$true)][int]$OwnerId,
    [Parameter(Mandatory=$true)][long]$OwnerFileTime,
    [Parameter(Mandatory=$true)][string]$RootThread,
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [Parameter(Mandatory=$true)][string]$CodexExe
)
$ErrorActionPreference = 'Stop'
$casePath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $casePath
$prefix = Join-Path $casePath 'tests/logs/c08_explicit_three_finish_20261124'
$attempt = "$prefix.queue_attempt.json"
$term = "$prefix.terminal.json"
if ($RootThread -ne $env:CODEX_THREAD_ID -or (Test-Path -LiteralPath "$prefix.start.json")) {throw 'This delivery is already owned or the thread differs'}
$owner = Get-Process -Id $OwnerId
$handle = $owner.Handle
if ($owner.StartTime.ToUniversalTime().ToFileTimeUtc() -ne $OwnerFileTime -or $owner.ProcessName -ne 'powershell') {throw 'The original launch owner has changed'}
$ownerCommand = (Get-CimInstance Win32_Process -Filter "ProcessId=$OwnerId").CommandLine
if ($ownerCommand -notlike '*c08_explicit_three_20261124.ps1*' -or $ownerCommand -notlike "*$casePath*") {throw 'The launch command differs'}
function Write-Receipt($file,$record) {
    $body=$record | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText($file,$body,(New-Object Text.UTF8Encoding($false)))
}
function Run-Release([string[]]$stageArgs) {
    Write-Output ("{0:o} Starting {1}" -f (Get-Date),($stageArgs -join ' '))
    & $PythonExe -B -X utf8 support/run_lian_release.py @stageArgs
    if ($LASTEXITCODE -ne 0) {throw ("Release command failed with exit {0}: {1}" -f $LASTEXITCODE,($stageArgs -join ' '))}
}
Write-Receipt "$prefix.start.json" @{worker_pid=$PID; original_solver_owner=$OwnerId; creation_filetime=$OwnerFileTime; argv=$ownerCommand; utc=(Get-Date).ToUniversalTime().ToString('o')}
$step='wait_positive_release'
$rc=1
try {
    $positive=Join-Path $casePath 'CaseLianCollapse_psi2p5_GPU_out/provenance.json'
    while (-not $owner.HasExited) {
        if ((Test-Path -LiteralPath $positive) -and (Get-Content -Raw -LiteralPath $positive | ConvertFrom-Json).state -eq 'completed') {break}
        Start-Sleep -Seconds 30
    }
    $step='positive_particles_figures'
    Run-Release @('--group','psi2p5','--postprocess-only')
    $step='wait_negative_preload'
    $owner.WaitForExit()
    if ($owner.ExitCode -ne 0) {throw "Original sequence exited $($owner.ExitCode); see its console log and both provenance records"}
    $step='negative_preload_native_review'
    Run-Release @('--group','psim5','--stage','preload','--postprocess-only')
    $step='negative_release_and_figures'
    Run-Release @('--group','psim5','--stage','collapse')
    $step='all_three_paper_comparison'
    Run-Release @('--group','all','--postprocess-only')
    $step='completed_pending_final_review'
    $rc=0
} catch {
    $why=$_.Exception.Message
    Write-Output $why
} finally {
    Write-Receipt $term @{utc=(Get-Date).ToUniversalTime().ToString('o'); exit_code=$rc; stage=$step; error=$why; case_root=$casePath}
    if (-not (Test-Path -LiteralPath $attempt)) {
        Write-Receipt $attempt @{utc=(Get-Date).ToUniversalTime().ToString('o'); thread=$RootThread; cli=$CodexExe; terminal=$term; timeout_s=45}
        $message="用户已授权的同线程 C08 三组无 HG 显式 u-pl 验证续办。阶段=$step，退出=$rc。请读 $term 和该标签 stdout/stderr，以及各组 provenance、validation_post、figures/validation_explicit 中的原始时钟/数据。审核独立 Fluid/Bound、表图及 Lian 图14–17，完成选择性 Git 本地/远端备份，中文汇报实际数值。若失败保留原始状态，仅派生失败则离线修复；不要重复已完成的求解或重发通知。"
        $p=New-Object Diagnostics.Process
        $p.StartInfo.FileName=$CodexExe
        $p.StartInfo.Arguments='queue --thread "'+$RootThread+'" --message "'+$message+'"'
        $p.StartInfo.UseShellExecute=$false
        $p.StartInfo.CreateNoWindow=$true
        [void]$p.Start()
        if($p.WaitForExit(45000)){Write-Receipt "$prefix.queue_result.json" @{exit_code=$p.ExitCode}} else {
            try {$p.Kill()} catch {}
            Write-Receipt "$prefix.queue_result.json" @{status='timeout_delivery_unknown'}
        }
    }
}
exit $rc
