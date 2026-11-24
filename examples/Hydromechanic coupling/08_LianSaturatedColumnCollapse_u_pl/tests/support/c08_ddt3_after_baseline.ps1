param(
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [Parameter(Mandatory=$true)][string]$OldGpuExe,
    [Parameter(Mandatory=$true)][string]$GpuExe,
    [Parameter(Mandatory=$true)][string]$CodexExe,
    [Parameter(Mandatory=$true)][string]$RootThread,
    [long]$BaselineWorkerFileTime=134399891419698771
)
$ErrorActionPreference='Stop'
$casePath=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $casePath
$tag=Join-Path $casePath 'tests/logs/c08_ddt3_after_baseline_r1'
$oldTag=Join-Path $casePath 'tests/logs/c08_explicit_three_finish_20261124'
$smokeCheck=Join-Path $casePath 'tests/logs/c08_ddt3_smoke_GPU_r1.check.json'
$figDir=Join-Path $casePath 'tests/figures/c08_ddt3_psi2p5'

function Write-NewReceipt($path,$data){
    $bytes=[Text.Encoding]::UTF8.GetBytes(($data | ConvertTo-Json -Depth 8))
    $file=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $file.Write($bytes,0,$bytes.Length) } finally { $file.Dispose() }
}
function Read-Receipt($path){ Get-Content -Raw -Encoding UTF8 -LiteralPath $path | ConvertFrom-Json }
function File-Identity($path){
    $f=Get-Item -LiteralPath $path
    [ordered]@{path=$f.FullName;bytes=$f.Length;mtime_utc=$f.LastWriteTimeUtc.ToString('o')}
}
function Wait-Owned($processId,$fileTime,$scriptName){
    $process=Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (!$process){ return @{pid=$processId;observed='already_absent'} }
    try {
        [void]$process.Handle
        if ($process.StartTime.ToUniversalTime().ToFileTimeUtc() -ne $fileTime){
            return @{pid=$processId;observed='original_exited_pid_reused'}
        }
        $w=Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
        if (!$w -and $process.HasExited){return @{pid=$processId;observed='exited';exit_code=$process.ExitCode}}
        if ($process.ProcessName -ne 'powershell' -or $w.CommandLine -notlike "*$scriptName*" -or $w.CommandLine -notlike "*$casePath*"){throw "Baseline owner command differs for PID $processId"}
        $process.WaitForExit()
        return @{pid=$processId;observed='exited';exit_code=$process.ExitCode;argv=$w.CommandLine;creation_filetime=$fileTime}
    } finally {$process.Dispose()}
}
function Wait-GpuSolvers(){
    # Include renamed test solvers with an explicit GPU switch as well as release/debug binaries.
    do {
        $busy=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'DualSPHysics%.exe' OR Name='solver.exe'" |
            Where-Object { $_.Name -notlike '*CPU*' -and ($_.Name -like 'DualSPHysics*' -or $_.CommandLine -match '(?:^|\s)-gpu(?=[:\s]|$)') })
        if ($busy.Count){Write-Output ("Waiting for GPU solver PID(s) "+($busy.ProcessId -join ','));Start-Sleep -Seconds 30}
    } while ($busy.Count)
}
function Run-PythonStage($name,[string[]]$arguments){
    foreach($binding in $boundTools){
        $now=File-Identity $binding.path
        if($now.bytes -ne $binding.bytes -or $now.mtime_utc -ne $binding.mtime_utc){throw "Tool changed while queued: $($binding.path)"}
    }
    $t=(Get-Date).ToUniversalTime().ToString('o')
    & $PythonExe -B -X utf8 @arguments
    $childRc=$LASTEXITCODE
    Write-NewReceipt "$tag.$name.json" @{start_utc=$t;end_utc=(Get-Date).ToUniversalTime().ToString('o');argv=$arguments;exit_code=$childRc}
    if ($childRc -ne 0){throw "$name exited $childRc; see stdout/stderr and the stage's provenance"}
}

if (!$RootThread -or $RootThread -ne $env:CODEX_THREAD_ID){throw 'Terminal queue must address this thread.'}
$PythonExe=(Resolve-Path -LiteralPath $PythonExe).Path
$OldGpuExe=(Resolve-Path -LiteralPath $OldGpuExe).Path
$GpuExe=(Resolve-Path -LiteralPath $GpuExe).Path
$CodexExe=(Resolve-Path -LiteralPath $CodexExe).Path
if ($OldGpuExe -eq $GpuExe){throw 'The old and candidate GPU programs must be distinct files.'}
$boundTools=@(File-Identity $OldGpuExe; File-Identity $GpuExe)
$original=Read-Receipt "$oldTag.start.json"
if ($original.worker_pid -ne 31032 -or !$original.original_solver_owner -or !$original.creation_filetime){throw 'Unexpected baseline start receipt.'}
Write-NewReceipt "$tag.start.json" @{pid=$PID;start_utc=(Get-Date).ToUniversalTime().ToString('o');thread=$RootThread;baseline_receipt="$oldTag.start.json";worker_filetime=$BaselineWorkerFileTime;tools=$boundTools}
$rc=1; $why=$null; $stage='await_baseline'
try {
    $baseWorker=Wait-Owned $original.worker_pid $BaselineWorkerFileTime 'c08_explicit_three_finish.ps1'
    $baseOwner=Wait-Owned $original.original_solver_owner $original.creation_filetime 'c08_explicit_three_20261124.ps1'
    $baseTerminal=if(Test-Path -LiteralPath "$oldTag.terminal.json"){Read-Receipt "$oldTag.terminal.json"}else{$null}
    Write-NewReceipt "$tag.baseline.json" @{worker=$baseWorker;original_owner=$baseOwner;terminal=$baseTerminal}
    if (!$baseTerminal -or $baseTerminal.exit_code -ne 0){Write-Output "Baseline sequence incomplete; inspecting the independent +2.5-degree control and GPU occupancy."}
    $control=Read-Receipt 'CaseLianCollapse_psi2p5_GPU_out/provenance.json'
    if ($control.state -ne 'completed' -or !(Test-Path -LiteralPath 'figures/validation_explicit/psi2p5/history.csv')){throw 'Completed +2.5-degree DDT0 control unavailable.'}
    $stage='gpu_smoke'
    Wait-GpuSolvers
    if(Test-Path -LiteralPath $smokeCheck){throw 'GPU smoke already has a receipt; retain and inspect before taking any further action.'}
    Run-PythonStage $stage @('tests/support/c08_ddt3_smoke.py','--backend','GPU','--stage','run','--old',$OldGpuExe,'--new',$GpuExe)
    $smoke=Read-Receipt $smokeCheck
    if($smoke.passed -ne $true -or $smoke.backend -ne 'GPU' -or $smoke.steps -ne 40 -or $smoke.native_fields -ne 22 -or !$smoke.off_exact -or !$smoke.on_changed){throw 'GPU smoke acceptance fields differ.'}
    $stage='positive_preload_collapse_and_analysis'
    Wait-GpuSolvers
    Run-PythonStage $stage @('tests/support/c08_ddt3_compare.py','--stage','all','--solver',$GpuExe)
    foreach($file in 'comparison.csv','comparison.png','comparison_material.csv','comparison_pressure.png','comparison_spacing.png'){
        if ((Get-Item -LiteralPath (Join-Path $figDir $file)).Length -le 0){throw "Missing comparison output $file"}
    }
    $stage='completed_pending_physical_review';$rc=0
} catch {
    $why=$_.Exception.Message
    Write-Output "$stage failed: $why"
}
Write-NewReceipt "$tag.terminal.json" @{stage=$stage;exit_code=$rc;error=$why;end_utc=(Get-Date).ToUniversalTime().ToString('o');smoke_check=$smokeCheck;figures=$figDir}
Write-NewReceipt "$tag.queue_attempt.json" @{thread=$RootThread;utc=(Get-Date).ToUniversalTime().ToString('o');terminal="$tag.terminal.json";timeout_seconds=45}
$message="Authorized C08 +2.5-degree DensityDT=3 comparison is terminal, stage=$stage exit=$rc. Review $tag.terminal.json, stage receipts and retained DDT0 vs DDT3 native pressure, motion, spacing, plastic strain and Lian comparison before deciding on the other two angles. Report quantitative findings in Chinese. Preserve partials, never duplicate solvers or resend this notification."
$notify=New-Object Diagnostics.Process
$notify.StartInfo.FileName=$CodexExe
$notify.StartInfo.Arguments='queue --thread "'+$RootThread+'" --message "'+$message+'"'
$notify.StartInfo.UseShellExecute=$false
$notify.StartInfo.CreateNoWindow=$true
try {
    [void]$notify.Start()
    if($notify.WaitForExit(45000)){$result=@{exit_code=$notify.ExitCode}}
    else {try{$notify.Kill()}catch{};$result=@{status='timeout_delivery_unknown'}}
} catch {$result=@{error=$_.Exception.Message}} finally {$notify.Dispose()}
Write-NewReceipt "$tag.queue_result.json" $result
exit $rc
