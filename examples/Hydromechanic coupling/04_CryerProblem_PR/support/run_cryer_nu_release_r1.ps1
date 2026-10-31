[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('010','020','045')][string]$Nu, [switch]$Smoke)
$ErrorActionPreference = 'Stop'
$caseRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$name = 'CaseCryerProblem_PR_release_nu' + $Nu + '_r1'
$manifestPath = Join-Path $PSScriptRoot 'cryer_nu_server_manifest_r1.json'
$output = Join-Path $caseRoot ($name + $(if ($Smoke) {'_smoke_out'} else {'_out'}))
$receiptPath = Join-Path $output 'execution_receipt_nu_r1.json'
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
    if (Test-Path -LiteralPath $receiptPath) { [IO.File]::Replace($temp, $receiptPath, ($receiptPath + '.previous')) }
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
    if ($manifest.format -ne 'Cryer_nu_release_r1_windows_bundle') { throw 'Unexpected release manifest.' }
    $tags = @('010','020','045')
    if (@($manifest.variants).Count -ne 3) { throw 'Expected three independent Poisson-ratio variants.' }
    $required = @('support/run_cryer_nu_release_r1.ps1','support/README_cryer_nu_release_r1.md','LICENSE')
    foreach ($tag in $tags) {
        if (@($manifest.variants | Where-Object {$_.nu_tag -eq $tag}).Count -ne 1) { throw "Missing/duplicate variant: $tag" }
        $stem = 'CaseCryerProblem_PR_release_nu' + $tag + '_r1'
        $required += @(($stem+'_Def.xml'),('x'+$stem+'_win64_GPU.bat'))
    }
    $variant = @($manifest.variants | Where-Object {$_.nu_tag -eq $Nu})[0]
    $culture = [Globalization.CultureInfo]::InvariantCulture
    $expectedNu = [Convert]::ToDouble($variant.nu,$culture)
    $expectedDt = [Convert]::ToDouble($variant.dt_s,$culture)
    $expectedEnd = [Convert]::ToDouble($variant.end_s,$culture)
    $expectedInterval = [Convert]::ToDouble($variant.output_interval_s,$culture)
    $expectedSteps = [Convert]::ToInt64($variant.steps,$culture)
    $expectedFrames = [Convert]::ToInt32($variant.expected_frames,$culture)
    if ($expectedNu -ne ([int]$Nu / 100.0) -or $expectedDt -ne [Math]::Pow(2,-20) -or $expectedEnd/$expectedDt -ne $expectedSteps -or $expectedSteps -le 128 -or $expectedInterval -le 0 -or $expectedFrames -lt 2) { throw 'Invalid selected variant clock/Poisson ratio.' }
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
    $state = [ordered]@{format='Cryer_nu_release_r1_actual_execution'; status='preflight_passed'; started_utc=[DateTime]::UtcNow.ToString('o'); mode=$(if ($Smoke) {'smoke'} else {'full'}); working_directory=$caseRoot;
        output=$output; manifest=(Binding $manifestPath); actual_payload_at_launch=$actualPayload; stages=@(); restart_used=$false; solver_exited_zero=$false; native_completion_verified=$false; physical_acceptance=$false;
        nu_tag=$Nu; selected_variant=$variant; expected_dt_s=$variant.dt_s; expected_steps=$(if ($Smoke) {128} else {$expectedSteps});
        expected_native_frames=$(if ($Smoke) {2} else {$expectedFrames}); effective_tmax_s=$(if ($Smoke) {'0.0001220703125'} else {$variant.end_s});
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
    $observedNu = $generated.SelectSingleNode('.//PRvs').value
    $observedDt = $generated.SelectSingleNode(".//parameter[@key='DtFixed']").value
    $observedEnd = $generated.SelectSingleNode(".//parameter[@key='TimeMax']").value
    $observedInterval = $generated.SelectSingleNode(".//parameter[@key='TimeOut']").value
    $state.generated_configuration_observed = [ordered]@{PRvs=$observedNu;DtFixed_s=$observedDt;TimeMax_s=$observedEnd;TimeOut_s=$observedInterval;scope='Actual generated XML values. Smoke separately overrides the effective end using the recorded solver command.'}
    if ([double]::Parse($observedNu,$culture) -ne $expectedNu -or [double]::Parse($observedDt,$culture) -ne $expectedDt -or [double]::Parse($observedEnd,$culture) -ne $expectedEnd -or [double]::Parse($observedInterval,$culture) -ne $expectedInterval) { throw 'Generated XML does not match the selected variant.' }
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
