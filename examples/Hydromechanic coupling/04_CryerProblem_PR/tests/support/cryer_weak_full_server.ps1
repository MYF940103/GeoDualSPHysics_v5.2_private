param([ValidateSet('full','smoke','check')][string]$Mode='full')
$ErrorActionPreference='Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath 'manifest.json' | ConvertFrom-Json
    foreach ($entry in $manifest.files) {
        $item = Get-Item -LiteralPath $entry.name
        if ($item.Length -ne $entry.bytes -or (Get-FileHash -Algorithm SHA256 -LiteralPath $item.FullName).Hash -ne $entry.sha256) {
            throw "Package integrity failure: $($entry.name)"
        }
    }
    if ($Mode -eq 'check') { Write-Host 'All package files verified'; exit 0 }
    $out = "cryer_weak_${Mode}_out"
    if (Test-Path -LiteralPath $out) { throw "Preserve the existing output. Extract a fresh copy of the package for another run: $out" }
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $hardware = @(nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv)
    if ($LASTEXITCODE -ne 0) { throw 'NVIDIA driver/device query failed' }
    Write-Host ($hardware -join [Environment]::NewLine)
    & '.\weak_full.exe' $Mode $out
    $rc=$LASTEXITCODE
    if ($rc -ne 0) { throw "GPU runner stopped (exit $rc); preserve partial output and actual_clock.csv." }
    $raw = @(Get-ChildItem -File -LiteralPath $out | Sort-Object Name | ForEach-Object {
        [ordered]@{name=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash}
    })
    $receipt=[ordered]@{mode=$Mode;package=(Get-FileHash -Algorithm SHA256 -LiteralPath 'manifest.json').Hash;
      gpu_inventory=$hardware;cuda_visible_devices=$env:CUDA_VISIBLE_DEVICES;utc_finished=[DateTime]::UtcNow.ToString('o');elapsed_seconds=$timer.Elapsed.TotalSeconds;files=$raw}
    $receipt | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 -LiteralPath (Join-Path $out 'server_run.json')
    Write-Host "Verified $($raw.Count) output files. Return the whole $out folder."
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally { Pop-Location }
