[CmdletBinding()]
param([switch]$Smoke)
$ErrorActionPreference = 'Stop'
$caseRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$name = 'CaseCryerProblem_PR_release_r2'
$manifestPath = Join-Path $PSScriptRoot 'cryer_server_manifest_r2.json'
$output = Join-Path $caseRoot ($name + $(if ($Smoke) {'_smoke_out'} else {'_out'}))
$receiptPath = Join-Path $output 'execution_receipt_r2.json'
$state = $null
$result = 1

function Payload-Path([string]$entry) {
    if ([IO.Path]::IsPathRooted($entry)) { throw "Absolute payload path: $entry" }
    $path = [IO.Path]::GetFullPath((Join-Path $caseRoot $entry))
    if (!$path.StartsWith($caseRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Payload escapes case: $entry" }
    return $path
}
function Binding([string]$path) {
    $file = Get-Item -LiteralPath $path
    if ($file.PSIsContainer) { throw "Expected file: $path" }
    return [ordered]@{path=$file.FullName; bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Save-Receipt {
    $temp = $receiptPath + '.tmp'
    [IO.File]::WriteAllText($temp, ($script:state | ConvertTo-Json -Depth 14), (New-Object Text.UTF8Encoding($false)))
    if (Test-Path -LiteralPath $receiptPath) { [IO.File]::Replace($temp, $receiptPath, $null) }
    else { [IO.File]::Move($temp, $receiptPath) }
}
function Invoke-Stage([string]$stage, [string]$program, [string[]]$arguments) {
    $log = Join-Path $output ($stage + '.console.log')
    $item = [ordered]@{stage=$stage; status='starting'; started_utc=[DateTime]::UtcNow.ToString('o'); executable_before=(Binding $program); argv=@($program)+$arguments; console_log=$log; exit_code=$null}
    $script:state.stages += $item
    Save-Receipt
    $savedPreference = $ErrorActionPreference
    try {
        # PS5 converts native stderr to ErrorRecords: keep diagnostics visible without
        # mistaking ordinary stderr for a nonzero native exit code.
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = $null
        & $program @arguments 2>&1 | Tee-Object -FilePath $log | Out-Host
        $nativeExit = $global:LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
    $item.exit_code = $nativeExit
    $item.status = 'exited'
    $item.ended_utc = [DateTime]::UtcNow.ToString('o')
    $item.executable_after = Binding $program
    if (Test-Path -LiteralPath $log) { $item.console_log_binding = Binding $log }
    Save-Receipt
    if ($null -eq $nativeExit -or $nativeExit -ne 0) { throw "$stage did not exit zero (code=$nativeExit); partial output is retained." }
}

try {
    if (Test-Path -LiteralPath $output) { throw "Output already exists: $output. No overwrite or PART restart." }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.format -ne 'Cryer_release_r2_windows_bundle') { throw 'Unexpected release manifest.' }
    $required = @(($name+'_Def.xml'),('x'+$name+'_win64_GPU.bat'),'support/run_cryer_release_r2.ps1','support/README_cryer_release_r2.md','LICENSE')
    $required += @('DualSPHysics5.2_GEO_win64.exe','GenCase_win64.exe','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','DsphConfig.xml','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll') | ForEach-Object {'support/bin/'+$_}
    if (@($manifest.files).Count -ne $required.Count) { throw 'Incomplete/duplicate payload manifest.' }
    foreach ($entry in $required) { if ($entry -notin @($manifest.files.entry)) { throw "Required payload missing: $entry" } }
    $actualPayload = @()
    foreach ($file in $manifest.files) {
        $actual = Binding (Payload-Path $file.entry)
        if ($actual.bytes -ne $file.bytes -or $actual.sha256 -ne $file.sha256) { throw "Payload hash/size mismatch: $($file.entry)" }
        $actualPayload += [ordered]@{entry=$file.entry; actual_file=$actual}
    }
    $solver = Payload-Path 'support/bin/DualSPHysics5.2_GEO_win64.exe'
    $gencase = Payload-Path 'support/bin/GenCase_win64.exe'
    if ((Binding $solver).sha256 -ne '652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096') { throw 'Wrong verified Cryer program.' }
    New-Item -ItemType Directory -Path $output | Out-Null
    $state = [ordered]@{format='Cryer_release_r2_actual_execution'; status='preflight_passed'; started_utc=[DateTime]::UtcNow.ToString('o'); mode=$(if ($Smoke) {'smoke'} else {'full'}); working_directory=$caseRoot;
        output=$output; manifest=(Binding $manifestPath); actual_payload_at_launch=$actualPayload; stages=@(); restart_used=$false; solver_exited_zero=$false; native_completion_verified=$false; physical_acceptance=$false;
        expected_dt_s='0.00000095367431640625'; expected_steps=$(if ($Smoke) {128} else {963370}); effective_tmax_s=$(if ($Smoke) {'0.0001220703125'} else {'0.9187412261962890625'});
        gpu_inventory=[ordered]@{status='not_observed'; expected_target='NVIDIA RTX A6000'; expected_model_verified=$false}}
    Save-Receipt
    try {
        $query = Get-Command nvidia-smi.exe -CommandType Application -ErrorAction Stop
        $savedPreference = $ErrorActionPreference
        try { $ErrorActionPreference='Continue'; $global:LASTEXITCODE=$null; $gpuLines=@(& $query.Source --query-gpu=index,name,uuid,driver_version --format=csv,noheader 2>&1 | ForEach-Object {$_.ToString()}); $gpuExit=$global:LASTEXITCODE }
        finally { $ErrorActionPreference=$savedPreference }
        $state.gpu_inventory = [ordered]@{status=$(if ($gpuExit -eq 0) {'inventory_observed'} else {'query_failed'}); executable=(Binding $query.Source); argv=@('--query-gpu=index,name,uuid,driver_version','--format=csv,noheader'); exit_code=$gpuExit; raw_lines=$gpuLines;
            scope='Available GPU inventory, not proof of which device the solver selected. Preserve Run.out for actual device selection.'; expected_model_verified=$false}
    } catch { $state.gpu_inventory=[ordered]@{status='query_unavailable'; error=$_.Exception.Message; expected_model_verified=$false} }
    Save-Receipt
    Set-Location -LiteralPath $caseRoot
    $inputStem = Join-Path $output $name
    Invoke-Stage 'gencase' $gencase @((Join-Path $caseRoot ($name+'_Def')), $inputStem, '-save:all')
    $state.generated_xml = Binding ($inputStem+'.xml')
    $state.generated_initial_bi4 = Binding ($inputStem+'.bi4')
    [xml]$generated = Get-Content -LiteralPath ($inputStem+'.xml') -Raw -Encoding UTF8
    $observedDt = $generated.SelectSingleNode(".//parameter[@key='DtFixed']").value
    $observedEnd = $generated.SelectSingleNode(".//parameter[@key='TimeMax']").value
    $state.generated_configuration_observed = [ordered]@{DtFixed_s=$observedDt;TimeMax_s=$observedEnd;scope='Actual generated XML values. Smoke separately overrides the effective end using the recorded solver command.'}
    if ([double]::Parse($observedDt,[Globalization.CultureInfo]::InvariantCulture) -ne [Math]::Pow(2,-20) -or [double]::Parse($observedEnd,[Globalization.CultureInfo]::InvariantCulture) -ne [double]::Parse('0.9187412261962890625',[Globalization.CultureInfo]::InvariantCulture)) { throw 'Generated XML does not match the selected baseline clock.' }
    $state.status = 'initial_data_generated'
    Save-Receipt
    $solverArgs = @('-gpu','-stable')
    if ($Smoke) { $solverArgs += '-tmax:0.0001220703125' }
    $solverArgs += @($inputStem,$output,'-dirdataout','data','-svres','-svextraparts:1')
    $state.actual_runtime_before_solver = @($manifest.files | Where-Object {$_.entry.StartsWith('support/bin/')} | ForEach-Object {Binding (Payload-Path $_.entry)})
    $state.status = 'solver_starting'
    Save-Receipt
    Invoke-Stage 'solver' $solver $solverArgs
    $state.actual_runtime_after_solver = @($manifest.files | Where-Object {$_.entry.StartsWith('support/bin/')} | ForEach-Object {Binding (Payload-Path $_.entry)})
    $state.run_log = Binding (Join-Path $output 'Run.out')
    $state.status = 'solver_exited_zero_pending_native_review'
    $state.solver_exited_zero = $true
    $result = 0
    Write-Host 'Solver exited zero. Copy the entire output directory and execution receipt for native review.'
    Write-Host 'Smoke does not start a full run. Normal exit is not physical/full-cycle acceptance.'
} catch {
    if ($null -ne $state) { $state.status='failed_or_interrupted_partial_retained'; $state.error=$_.Exception.Message }
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
} finally {
    if ($null -ne $state) { $state.ended_utc=[DateTime]::UtcNow.ToString('o'); Save-Receipt }
}
exit $result
