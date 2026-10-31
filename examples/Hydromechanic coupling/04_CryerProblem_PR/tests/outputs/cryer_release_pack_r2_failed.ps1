[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{40}$')][string]$PackagingHead)
$ErrorActionPreference = 'Stop'
$caseRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$repoRoot = [IO.Path]::GetFullPath((Join-Path $caseRoot '..\..\..'))
$manifestPath = Join-Path $caseRoot 'support\cryer_server_manifest_r2.json'
$zipPath = Join-Path $caseRoot 'Cryer_release_r2_Windows_RTXA6000.zip'
$checkPath = Join-Path $caseRoot 'tests\logs\cryer_release_package_r2.check.json'
$programSHA = '652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096'
foreach ($p in @($manifestPath,$zipPath,$checkPath)) { if (Test-Path -LiteralPath $p) { throw "Refusing retained artifact: $p" } }

function Binding([string]$path) {
    $f = Get-Item -LiteralPath $path
    if ($f.PSIsContainer) { throw "Expected file: $path" }
    return [ordered]@{path=$f.FullName; bytes=$f.Length; sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Verify($expected) {
    $actual = Binding $expected.path
    if ($actual.bytes -ne $expected.bytes -or $actual.sha256 -ne $expected.sha256) { throw "Changed evidence: $($expected.path)" }
    return $actual
}
function Read-Json([string]$path) { return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json }
function Save-New([string]$path, $value) {
    $stream = [IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
    try { $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($value | ConvertTo-Json -Depth 16)); $stream.Write($bytes,0,$bytes.Length) }
    finally { $stream.Dispose() }
}
function Payload-Path([string]$entry) {
    if ([IO.Path]::IsPathRooted($entry)) { throw "Absolute ZIP entry: $entry" }
    $p = [IO.Path]::GetFullPath((Join-Path $caseRoot $entry))
    if (!$p.StartsWith($caseRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw "Escaping ZIP entry: $entry" }
    return $p
}

$oldPath = Join-Path $caseRoot 'support\cryer_server_manifest_r1.json'
$old = Read-Json $oldPath
$evidence = @((Binding $oldPath),(Verify $old.accepted_release_build),(Verify $old.accepted_native_inputs),(Verify $old.implementation_review))
$build = Read-Json $old.accepted_release_build.path
$review = Read-Json $old.implementation_review.path
$nativeInputs = Read-Json $old.accepted_native_inputs.path
if ($build.exit_code -ne 0 -or !$build.owned_exited -or $build.program.sha256 -ne $programSHA -or !$review.implementation_regression_passed) { throw 'Old Release/build/native bridge is not the accepted program.' }
$names = @('cryer_darcy_switch_build_r2.inputs.json','cryer_darcy_switch_build_review_r1.check.json','cryer_darcy_switch_native_r1.check.json','cryer_darcy_native_sources_r1.json')
foreach ($name in $names) {
    $matches = @(@($review.source_links)+@($nativeInputs.inputs) | Where-Object {(Split-Path -Leaf $_.path) -eq $name})
    if (!$matches.Count -or @($matches.sha256 | Select-Object -Unique).Count -ne 1) { throw "Missing/conflicting provenance: $name" }
    $evidence += Verify $matches[0]
}
$sourceRecord = Read-Json (Join-Path $caseRoot 'tests\logs\cryer_darcy_native_sources_r1.json')
$sourceCopies = @()
foreach ($file in $sourceRecord.files) {
    $expected = @($old.source_hashes_at_packaging | Where-Object {(Split-Path -Leaf $_.path) -eq $file.name})
    if ($expected.Count -ne 1 -or $expected[0].sha256 -ne $file.sha256) { throw "Source capture differs: $($file.name)" }
    $sourceCopies += Verify ([pscustomobject]@{path=(Join-Path $sourceRecord.snapshot_directory $file.name);bytes=$file.bytes;sha256=$file.sha256})
}
if ($sourceCopies.Count -ne 6) { throw 'Expected the six preserved compiled-source files, not current worktree source.' }
foreach ($name in @('cryer_full_review_r1.check.json','cryer_state_budget_r1.check.json')) {
    $p = Join-Path $caseRoot ('tests\logs\'+$name); $j = Read-Json $p
    if (!$j.analysis_checks_passed) { throw "Unreviewed offline evidence: $name" }
    $evidence += Binding $p
}
$runtime = @($old.files | Where-Object {$_.entry.StartsWith('support/bin/')})
if ($runtime.Count -ne 9) { throw 'Expected the nine old verified executable/runtime payloads.' }
foreach ($file in $runtime) { Verify $file | Out-Null }
$solver = @($runtime | Where-Object {$_.entry -eq 'support/bin/DualSPHysics5.2_GEO_win64.exe'})
if ($solver.Count -ne 1 -or $solver[0].sha256 -ne $programSHA) { throw 'Wrong packaged GPU program.' }
$entries = @('CaseCryerProblem_PR_release_r2_Def.xml','xCaseCryerProblem_PR_release_r2_win64_GPU.bat','support/run_cryer_release_r2.ps1','support/README_cryer_release_r2.md') + @($runtime.entry) + @('LICENSE')
$licenseSource = Binding (Join-Path $repoRoot 'LICENSE')
$licenseTarget = Join-Path $caseRoot 'LICENSE'
if (!(Test-Path -LiteralPath $licenseTarget)) {
    $from = [IO.File]::OpenRead($licenseSource.path); $to = [IO.File]::Open($licenseTarget,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
    try { $from.CopyTo($to) } finally { $from.Dispose(); $to.Dispose() }
}
if ((Binding $licenseTarget).sha256 -ne $licenseSource.sha256) { throw 'Existing case LICENSE differs; no overwrite allowed.' }
$payload = @($entries | ForEach-Object {$b=Binding (Payload-Path $_); [ordered]@{entry=$_;bytes=$b.bytes;sha256=$b.sha256}})
[xml]$xml = Get-Content -LiteralPath (Payload-Path $entries[0]) -Raw -Encoding UTF8
$dt = [double]::Parse($xml.SelectSingleNode(".//parameter[@key='DtFixed']").value,[Globalization.CultureInfo]::InvariantCulture)
$end = [double]::Parse($xml.SelectSingleNode(".//parameter[@key='TimeMax']").value,[Globalization.CultureInfo]::InvariantCulture)
if ($dt -ne [Math]::Pow(2,-20) -or $end/$dt -ne 963370) { throw 'Unexpected selected baseline clock.' }
$manifest = [ordered]@{format='Cryer_release_r2_windows_bundle';created_utc=[DateTime]::UtcNow.ToString('o');packaging_checkpoint_supplied=$PackagingHead.ToLowerInvariant();
    packaging_checkpoint_scope='Package-making checkpoint only; not a claim that the retained program was rebuilt from this HEAD.';
    r1_checkpoint_supplied_not_full_source_proof=$old.source_head_supplied_by_packager;verified_program_sha256=$programSHA;compiled_source_copies=$sourceCopies;provenance=$evidence;
    compiled_scope='Reused historical Release plus six byte-preserved compiler source snapshots and authoritative build/native receipts. Not a complete system-header/third-party lock or proof of old server execution bytes.';
    target='Windows x64 / NVIDIA RTX A6000; CUDA11.7 sm86 SASS and compute86 PTX; system driver/UCRT required';runtime_source='The same nine executable/runtime entries bound by the preserved r1 manifest';
    license_source=$licenseSource;fixed_dt_s='0.00000095367431640625';time_max_s='0.9187412261962890625';steps=963370;smoke_steps=128;smoke_end_s='0.0001220703125';expected_native_frames=1065;
    reference='FiniteKw,nu0.3,fixed18 initialr/a.05,tau=t-2^-7; legacyTv endpoint approximately1, not2';peak_amplitude_error_percent=-1.03427;peak_timing_error_percent=3.97893;
    limits='Selected approximately-one-percent peak-amplitude baseline, not strict1percent,all-field accuracy,full-half convergence,density repair or general material/boundary acceptance. New execution receipt must bind actual server bytes.';
    files=$payload;manifest_self_hash='Excluded to avoid self-reference; external package check binds the manifest and ZIP';solver_started=$false;physical_acceptance=$false;full_cycle_acceptance=$false}
Save-New $manifestPath $manifest
$items = @($payload)+@([ordered]@{entry='support/cryer_server_manifest_r2.json';bytes=(Get-Item -LiteralPath $manifestPath).Length;sha256=(Binding $manifestPath).sha256})
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipStream = [IO.File]::Open($zipPath,[IO.FileMode]::CreateNew)
$archive = [IO.Compression.ZipArchive]::new($zipStream,[IO.Compression.ZipArchiveMode]::Create,$false)
try {
    foreach ($file in $items) {
        $entry = $archive.CreateEntry($file.entry,[IO.Compression.CompressionLevel]::Optimal)
        $inputStream = [IO.File]::OpenRead((Payload-Path $file.entry)); $dest = $entry.Open()
        try { $inputStream.CopyTo($dest) } finally { $inputStream.Dispose(); $dest.Dispose() }
    }
} finally { $archive.Dispose(); $zipStream.Dispose() }
$archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    if ($archive.Entries.Count -ne $items.Count) { throw 'ZIP entry count mismatch.' }
    foreach ($file in $items) {
        $entry = $archive.GetEntry($file.entry)
        if ($null -eq $entry -or $entry.Length -ne $file.bytes) { throw "ZIP entry missing/size mismatch: $($file.entry)" }
        $s = $entry.Open(); $sha = [Security.Cryptography.SHA256]::Create()
        try { $actual=[BitConverter]::ToString($sha.ComputeHash($s)).Replace('-','').ToLowerInvariant() }
        finally { $sha.Dispose(); $s.Dispose() }
        if ($actual -ne $file.sha256) { throw "ZIP entry hash mismatch: $($file.entry)" }
    }
} finally { $archive.Dispose() }
$receipt = [ordered]@{package_consistency_passed=$true;created_utc=[DateTime]::UtcNow.ToString('o');packer=(Binding $PSCommandPath);manifest=(Binding $manifestPath);zip=(Binding $zipPath);verified_zip_entries=$items.Count;
    license_source=$licenseSource;license_case_copy=(Binding $licenseTarget);old_program_reused=$true;programs_executed=$false;solver_started=$false;portable_smoke_passed=$false;physical_acceptance=$false;full_cycle_acceptance=$false}
Save-New $checkPath $receipt
Write-Host ('Package created and every entry SHA verified: '+$zipPath)
Write-Host ('ZIP SHA256: '+$receipt.zip.sha256)
Write-Host 'Packaging only. Extract to a fresh directory and run an independent smoke before any separately requested full run.'
