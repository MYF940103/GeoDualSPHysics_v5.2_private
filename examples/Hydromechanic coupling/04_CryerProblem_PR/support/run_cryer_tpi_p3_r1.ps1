[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('peak','full')][string]$Stage,[switch]$CheckOnly)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$stem = "CaseCryer_TPI_P3_nu030_$($Stage)_r1"
$out = Join-Path $root ($stem + '_GPU_out')
$def = Join-Path $root ($stem + '_Def.xml')
$seed = Join-Path $PSScriptRoot 'upl_seed_nu030_r1\CaseCryerProblem_u_pl_nu030_r1'
$solver = Join-Path $PSScriptRoot 'bin_cryer_tpi_p3_r1\DualSPHysics5.2_GEO_win64.exe'
$manifestPath = Join-Path $PSScriptRoot 'cryer_tpi_p3_package_r1.json'
$steps = if($Stage -eq 'peak'){36864}else{481685}
$frames = if($Stage -eq 'peak'){577}else{265}
$prefix = Join-Path $out $stem
$solverArgs = @('-gpu','-stable',$prefix,$out,'-dirdataout','data','-svres',"-nsteps:$steps")
$ownedOut = $false
$rec = [ordered]@{profile=$Stage; solver=$solver; arguments=$solverArgs; started_utc=$null; ended_utc=$null
    solver_exit=$null; elapsed_s=$null; hardware=$null; steps=$null; part_files=$null; reported_end_s=$null
    status='preflight'; error=$null}
try {
    if(Test-Path -LiteralPath $out){throw "Output already exists: $out"}
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if($manifest.method -ne 'Cryer P3 Eq40 Rh1' -or $manifest.nu -ne 0.3){throw 'Incompatible package manifest.'}
    foreach($entry in $manifest.files){
        $file = Get-Item -LiteralPath (Join-Path $root $entry.name)
        if($file.Length -ne $entry.bytes){throw "Package size mismatch: $($entry.name)"}
    }
    foreach($file in @($def,$solver,"$seed.xml","$seed.bi4")){
        $rel = $file.Substring($root.Length+1).Replace('\','/')
        $entry = @($manifest.files | Where-Object {$_.name -eq $rel})
        if($entry.Count -ne 1 -or (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $entry[0].sha256){
            throw "Qualified input or program differs from package: $rel"
        }
    }
    $rec.package_id = $manifest.package_id
    $rec.program_sha256 = $manifest.program_sha256
    $rec.peak_input_sha256 = $manifest.peak_input_sha256
    $rec.selectors = $manifest.selectors
    [xml]$definition = [IO.File]::ReadAllText($def)
    [xml]$case = [IO.File]::ReadAllText("$seed.xml")
    foreach($name in @('special','parameters')){
        $xpath = "/case/execution/$name"
        $from = $definition.SelectSingleNode($xpath)
        $to = $case.SelectSingleNode($xpath)
        if(-not $from -or -not $to){throw "Missing $xpath"}
        [void]$to.ParentNode.ReplaceChild($case.ImportNode($from,$true),$to)
    }
    $particles = $case.SelectSingleNode('/case/execution/particles')
    if($particles.GetAttribute('np') -ne '37181' -or $particles.GetAttribute('nb') -ne '8'){throw 'Wrong seed particle counts.'}
    Write-Host "Profile $Stage | $steps steps | $frames planned frames | $out"
    if($CheckOnly){Write-Host 'Inputs and portable runtime passed preflight.'; exit 0}
    if($Stage -eq 'full'){
        $reviewPath = Join-Path $PSScriptRoot 'cryer_tpi_p3_peak_review.json'
        if(-not [IO.File]::Exists($reviewPath)){throw 'Return the peak directory for review. This profile needs support/cryer_tpi_p3_peak_review.json.'}
        $review = Get-Content -LiteralPath $reviewPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if($review.peak_qualified -ne $true -or $review.scheme -ne 'B' -or $review.rounds -ne 3 -or $review.nu -ne 0.30 -or $review.dt_s -ne [Math]::Pow(2,-19) -or $review.package_id -ne $manifest.package_id -or $review.program_sha256 -ne $manifest.program_sha256 -or $review.peak_input_sha256 -ne $manifest.peak_input_sha256){
            throw 'Peak review does not qualify this program and input.'
        }
        $peakOut = Join-Path $root 'CaseCryer_TPI_P3_nu030_peak_r1_GPU_out'
        $native = $review.native
        $ph = $review.physics
        if($native.frames -ne 577 -or $native.end_s -ne 0.0703125 -or $native.post_open_frames -ne 512 -or
           $review.sidecar.pressure_rounds -ne 3 -or $review.sidecar.dt_phases -ne 5 -or $review.sidecar.rows -ne (577*18*3) -or
           $ph.sampling -ne $true -or $ph.amplitude -ne $true -or $ph.amplitude_vs_A -ne $true -or $ph.phase -ne $true){
            throw 'Peak review evidence does not meet this native, method and physical profile.'
        }
        foreach($record in @('Run.csv','server_run.json')){
            $entry = @($review.peak_server_files | Where-Object {$_.name -eq $record})
            if($entry.Count -ne 1 -or (Get-FileHash -LiteralPath (Join-Path $peakOut $record) -Algorithm SHA256).Hash -ne $entry[0].sha256){
                throw "Reviewed peak return record differs: $record"
            }
        }
    }
    foreach($selector in @('UPL_TPI_GPU_R1','UPL_TPI_P3_ROWS_R1','UPL_TPI_M0_DT_R1')){
        [Environment]::SetEnvironmentVariable($selector,$manifest.selectors.$selector,'Process')
    }
    [void](New-Item -ItemType Directory -Path $out -ErrorAction Stop)
    $ownedOut = $true
    $case.Save("$prefix.xml")
    Copy-Item -LiteralPath "$seed.bi4" -Destination "$prefix.bi4"
    $rec.started_utc = [DateTime]::UtcNow.ToString('o')
    $rec.status = 'running'
    $rec | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'launch.json') -Encoding UTF8
    $clock = [Diagnostics.Stopwatch]::StartNew()
    & $solver @solverArgs
    $rec.solver_exit = $LASTEXITCODE
    $rec.elapsed_s = $clock.Elapsed.TotalSeconds
    if($rec.solver_exit -ne 0){throw "GPU solver exit $($rec.solver_exit). Partial output retained."}

    $lines = @(Get-Content -LiteralPath (Join-Path $out 'Run.csv') | Where-Object {$_ -match '\S'})
    if($lines.Count -ne 2){throw 'Unexpected Run.csv shape. Keep the completed output for offline review.'}
    $names = $lines[0].TrimStart('#').Split(';')
    $values = $lines[1].Split(';')
    if($names.Count -ne $values.Count){throw 'Run.csv column counts differ.'}
    $row = @{}
    foreach($key in @('Steps','PartFiles','PartsOut','Hardware','PhysicalTime')){
        $indices = @(for($i=0;$i -lt $names.Count;$i++){if($names[$i].Trim() -eq $key){$i}})
        if($indices.Count -ne 1){throw "Missing or repeated Run.csv field $key."}
        $row[$key] = $values[$indices[0]].Trim()
    }
    $rec.hardware = $row.Hardware
    $rec.steps = [int]$row.Steps
    $rec.part_files = [int]$row.PartFiles
    $rec.reported_end_s = $row.PhysicalTime
    $data = Join-Path $out 'data'
    $files = @(Get-ChildItem -LiteralPath $data -File -Filter 'Part_*.bi4' | Where-Object {$_.Name -match '^Part_\d+\.bi4$'})
    if($rec.steps -ne $steps -or $rec.part_files -ne $frames -or $files.Count -ne $frames -or [int]$row.PartsOut -ne 0){throw 'Saved run counts differ from the plan.'}
    foreach($i in 0..($frames-1)){
        if(-not [IO.File]::Exists((Join-Path $data ('Part_{0:D4}.bi4' -f $i)))){throw "Missing native frame $i."}
    }
    foreach($name in @('UplTpiP3GpuR1.policy.json','UplTpiP3DtR1.policy.json','UplTpiP3DtR1.csv',
                       'UplTpiP3GpuR1.summary.json','UplTpiP3DtR1.summary.json','UplTpiP3GpuR1.body.csv',
                       'UplTpiP3GpuR1.round1.csv','UplTpiP3GpuR1.round2.csv','UplTpiP3GpuR1.round3.csv')){
        if((Get-Item -LiteralPath (Join-Path $out $name)).Length -le 0){throw "Empty solver diagnostic: $name"}
    }
    $rec.status = 'completed_pending_native_physical_review'
    Write-Host "GPU: $($rec.hardware). Return the complete output directory."
} catch {
    $rec.error = $_.Exception.Message
    $rec.status = if($null -eq $rec.solver_exit){'preparation_or_launch_error'}elseif($rec.solver_exit -eq 0){'solver_completed_summary_needs_review'}else{'solver_failed'}
    [Console]::Error.WriteLine($rec.error)
} finally {
    if($ownedOut){
        $rec.ended_utc = [DateTime]::UtcNow.ToString('o')
        $rec | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'server_run.json') -Encoding UTF8
    }
}
if($rec.status -ne 'completed_pending_native_physical_review'){exit 1}
exit 0
