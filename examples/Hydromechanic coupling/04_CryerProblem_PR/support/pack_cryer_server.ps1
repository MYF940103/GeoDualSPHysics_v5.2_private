[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$SourceHead,
    [string]$VcRedistDirectory = 'D:\Program Files\VS2022\VC\Redist\MSVC\14.36.32532\x64\Microsoft.VC143.CRT',
    [switch]$RequireInstalledVcRuntime
)

# Packages frozen inputs/programs only. Never builds, launches a program or runs a case.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$caseRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$repoRoot = (Get-Item -LiteralPath $caseRoot).Parent.Parent.Parent.FullName
$logs = Join-Path $caseRoot 'tests\logs'
$bin = Join-Path $PSScriptRoot 'bin'
$manifestPath = Join-Path $PSScriptRoot 'cryer_server_manifest_r1.json'
$zipPath = Join-Path $caseRoot 'Cryer_symC_nu030_Windows_RTXA6000_r1.zip'
$reviewPath = Join-Path $logs 'cryer_darcy_switch_native_review_r1.check.json'
$buildPath = Join-Path $logs 'cryer_darcy_switch_build_r2_Release.build.json'
$preparedPath = Join-Path $logs 'cryer_darcy_switch_native_r1.inputs.json'
if ((Test-Path -LiteralPath $manifestPath) -or (Test-Path -LiteralPath $zipPath)) {
    throw 'Retained manifest/ZIP exists; never overwrite or repackage this label.'
}

function Get-Binding([string]$Path) {
    $item = Get-Item -LiteralPath $Path
    [pscustomobject][ordered]@{ path = $item.FullName; bytes = $item.Length
        sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
}
function Assert-Binding($Binding) {
    $actual = Get-Binding $Binding.path
    if ($actual.bytes -ne $Binding.bytes -or $actual.sha256 -ne $Binding.sha256) {
        throw "Frozen binding changed: $($Binding.path)"
    }
}
function Find-Binding($Records, [string]$Path) {
    $resolved = [IO.Path]::GetFullPath($Path)
    $found = @($Records | Where-Object { [IO.Path]::GetFullPath($_.path) -eq $resolved })
    if ($found.Count -ne 1) { throw "Missing/ambiguous accepted binding: $Path" }
    Assert-Binding $found[0]
    $found[0]
}

$review = Get-Content -LiteralPath $reviewPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($review.implementation_regression_passed -ne $true) { throw 'Native implementation review has not passed.' }
$acceptedBuild = Find-Binding $review.source_links $buildPath
$acceptedPrepared = Find-Binding $review.source_links $preparedPath
$build = Get-Content -LiteralPath $buildPath -Raw -Encoding UTF8 | ConvertFrom-Json
$prepared = Get-Content -LiteralPath $preparedPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($build.configuration -ne 'Release' -or $build.status -ne 'built_not_run' -or
    $build.exit_code -ne 0 -or -not $build.owned_exited -or -not $build.protected_inputs_unchanged) {
    throw 'Accepted GPU Release build receipt is not successful.'
}
$programHash = '652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096'
Assert-Binding $build.program
if ($build.program.sha256 -ne $programHash) { throw 'Unexpected GPU Release program.' }
foreach ($pair in $build.runtime) {
    Assert-Binding $pair.source; Assert-Binding $pair.target
    if ($pair.source.sha256 -ne $pair.target.sha256) { throw 'Accepted runtime copy differs.' }
}

# Explicit whitelist: no tests, existing outputs, CPU/Debug executables or wildcard copy.
$inputName = 'CaseCryerProblem_PR_symc_nu030_Def.xml'
$batName = 'xCaseCryerProblem_PR_symc_nu030_win64_GPU.bat'
$inputs = @(
    @{ Path = (Join-Path $caseRoot $inputName); Entry = $inputName },
    @{ Path = (Join-Path $caseRoot $batName); Entry = $batName },
    @{ Path = (Join-Path $caseRoot 'README.md'); Entry = 'README.md' },
    @{ Path = (Join-Path $PSScriptRoot 'README_server.md'); Entry = 'support/README_server.md' },
    @{ Path = $PSCommandPath; Entry = 'support/pack_cryer_server.ps1' },
    @{ Path = (Join-Path $repoRoot 'LICENSE'); Entry = 'LICENSE' }
)
foreach ($file in $inputs) {
    if (-not (Test-Path -LiteralPath $file.Path -PathType Leaf)) { throw "Missing payload: $($file.Path)" }
}
$canonical = Join-Path $repoRoot 'bin\windows'
$dependencies = [ordered]@{
    'DualSPHysics5.2_GEO_win64.exe' = @{ Source = $build.program.path; Hash = $programHash }
    'GenCase_win64.exe' = @{ Source = (Join-Path $canonical 'GenCase_win64.exe'); Hash = 'f2f4cd8ed3e6cea4a1922d64f916369aade0a15df4168344edfe66c6efd66c14' }
    'ChronoEngine.dll' = @{ Source = (Join-Path $canonical 'ChronoEngine.dll'); Hash = '246d6c92824c55e2ab469e6e9567516fe4cecd84b617fc64cf6d2382fd7fbbe5' }
    'dsphchrono.dll' = @{ Source = (Join-Path $canonical 'dsphchrono.dll'); Hash = 'c605befbc02991dd9d36266f2ce28e1e0bd675c115cab79e1f10fc873c6ff8fe' }
    'vcomp140.dll' = @{ Source = (Join-Path $canonical 'vcomp140.dll'); Hash = '1d480d651414304bddd0928b1c1563b4fb7f89b1c6ac30650c884150de0ec540' }
    'DsphConfig.xml' = @{ Source = (Join-Path $canonical 'DsphConfig.xml'); Hash = 'a2bc1f88c6ea95347187a64a991ebada177c6314de5c35ab078b06d78235eece' }
}
foreach ($name in $dependencies.Keys) {
    $dependency = $dependencies[$name]
    $frozen = Find-Binding $prepared.inputs $dependency.Source
    if ($frozen.sha256 -ne $dependency.Hash) { throw "Unexpected dependency: $name" }
}
$sourceHashes = @()
foreach ($relative in @('src/source/JSph.h', 'src/source/JSph.cpp', 'src/source/JSphCpu.cpp',
    'src/source/JSphGpu_ker.h', 'src/source/JSphGpu_ker.cu', 'src/source/JSphGpu.cpp',
    'src/VS/DualSPHysics5Re.vcxproj')) {
    $binding = Find-Binding $prepared.inputs (Join-Path $repoRoot $relative)
    $sourceHashes += [ordered]@{ path = $relative; bytes = $binding.bytes; sha256 = $binding.sha256 }
}
$documentation = Get-Binding (Join-Path $repoRoot 'doc/xml_format/_FmtXML_ElastoplasticSoil.xml')

$payload = [System.Collections.Generic.List[object]]::new()
function Add-Payload([string]$Path, [string]$Entry, [string]$Origin) {
    $binding = Get-Binding $Path
    $payload.Add([pscustomobject][ordered]@{ entry = $Entry; bytes = $binding.bytes
        sha256 = $binding.sha256; path = $binding.path; origin = $Origin })
}
function Copy-Verified([string]$Source, [string]$Name, [string]$Hash) {
    $target = Join-Path $bin $Name
    if (Test-Path -LiteralPath $target) {
        if ((Get-Binding $target).sha256 -ne $Hash) { throw "Retained support/bin differs: $Name" }
    } else { Copy-Item -LiteralPath $Source -Destination $target }
    if ((Get-Binding $target).sha256 -ne $Hash) { throw "Copy hash mismatch: $Name" }
    Add-Payload $target ('support/bin/' + $Name) $Source
}

# Only the three signed redistributable CRTs are eligible for app-local copying.
$runtime = [ordered]@{ mode = 'official_x64_VC_runtime_must_be_preinstalled'; files = @()
    minimum_build_tools_version = '14.36'; system_ucrt = 'Windows prerequisite; never copied'
    license_and_download = 'https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170' }
$crt = @()
if (-not $RequireInstalledVcRuntime -and (Test-Path -LiteralPath $VcRedistDirectory -PathType Container)) {
    $redist = (Resolve-Path -LiteralPath $VcRedistDirectory).Path
    if ($redist -match '\\VC\\Redist\\MSVC\\' -and (Split-Path -Leaf $redist) -eq 'Microsoft.VC143.CRT') {
        foreach ($name in @('msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')) {
            $source = Join-Path $redist $name
            if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { $crt = @(); break }
            $signature = Get-AuthenticodeSignature -LiteralPath $source
            $version = (Get-Item -LiteralPath $source).VersionInfo.FileVersion
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft' -or
                [version]$version -lt [version]'14.36') { $crt = @(); break }
            $crt += [pscustomobject]@{ source = $source; name = $name; version = $version
                sha256 = (Get-Binding $source).sha256; signer = $signature.SignerCertificate.Subject }
        }
    }
}
if (-not (Test-Path -LiteralPath $bin)) { New-Item -ItemType Directory -Path $bin | Out-Null }
foreach ($file in $inputs) { Add-Payload $file.Path $file.Entry $file.Path }
foreach ($name in $dependencies.Keys) { Copy-Verified $dependencies[$name].Source $name $dependencies[$name].Hash }
if ($crt.Count -eq 3) {
    foreach ($file in $crt) { Copy-Verified $file.source $file.name $file.sha256 }
    $runtime.mode = 'signed_MSVC14_app_local_from_VS_redist'; $runtime.files = $crt
} else { Write-Warning 'Install the official Microsoft x64 VC++ runtime on the server; no unknown CRT DLL is copied.' }
foreach ($name in @('LICENSE_Chrono.txt', 'LICENSE_MSVC.txt')) {
    $notice = Join-Path $PSScriptRoot $name
    if (Test-Path -LiteralPath $notice -PathType Leaf) { Add-Payload $notice ('support/' + $name) $notice }
}

[xml]$xml = Get-Content -LiteralPath (Join-Path $caseRoot $inputName) -Raw -Encoding UTF8
$schedule = @($xml.SelectNodes('//timeout/tout') | ForEach-Object { [ordered]@{ time = $_.time; timeout = $_.timeout } })
$manifest = [ordered]@{
    format = 'Cryer_symC_nu030_server_bundle_r1'; created_utc = [DateTime]::UtcNow.ToString('o')
    source_head_supplied_by_packager = $SourceHead.ToLowerInvariant(); source_hashes_at_packaging = $sourceHashes
    documentation_at_packaging = $documentation
    documentation_provenance = 'Guide is not a compiled input and may intentionally differ after delivery-documentation updates. Its old native-input bytes remain archived by tests/logs/cryer_darcy_native_doc_r1.json; no historical binding is rewritten.'
    source_scope = 'Private source checkpoint supplied by packager; explicit current file hashes verified against accepted native inputs. No Git command or claim that every source file equals HEAD.'
    implementation_review = (Get-Binding $reviewPath); accepted_release_build = $acceptedBuild; accepted_native_inputs = $acceptedPrepared
    target = 'Windows x64, NVIDIA RTX A6000 / sm_86; actual server compatibility remains to be checked'
    local_test_device = 'RTX 3050; bounded native OFF/ON regressions and Debug memcheck, not A6000 or full-cycle validation'
    cuda = 'CUDA 11.7 Release, sm_86 SASS plus compute_86 PTX, static cudart; no CUDA Toolkit/Visual Studio/Python required for execution. Older GPU architectures are not accepted.'
    driver = 'Install an NVIDIA driver supporting RTX A6000 and CUDA 11.7; CUDA 11.7 GA Windows toolkit baseline is 516.01. No driver/system DLL bundled.'
    nvidia_reference = 'https://docs.nvidia.com/cuda/archive/11.7.0/cuda-toolkit-release-notes/index.html'
    runtime = $runtime; project_license = 'LICENSE (LGPL); preserve project and third-party notices'
    chrono_project_reference = 'https://github.com/projectchrono/chrono/blob/main/LICENSE'
    formal_input = $inputName; formal_bat = $batName; new_output = 'CaseCryerProblem_PR_symc_nu030_out'
    time_max_s = $xml.SelectSingleNode('//parameter[@key="TimeMax"]').value
    fixed_dt_s = $xml.SelectSingleNode('//parameter[@key="DtFixed"]').value
    default_output_interval_s = $xml.SelectSingleNode('//parameter[@key="TimeOut"]').value
    special_output_schedule = $schedule
    time_origin = 'Absolute run time includes ramp/closed hold; drained theory uses tau=t-2^-7. Target tau=0.9109285714285714 s (LegacyTv=1), final time ceiled to the fixed-step grid.'
    startup_smoke = 'Root BAT --smoke: tmax=2^-13 s, 2 native frames only; --unattended disables final pause. No automatic full run after smoke.'
    return_data = 'Copy the entire new output directory, BI4/extra files and run logs, together with this ZIP and manifest. No Python/postprocessing is bundled.'
    execution = 'Packaging only; no programs/help/solvers launched. Full server simulation and physical/theory acceptance remain pending.'
    implementation_regression_passed = $true; full_cycle_accepted = $false; physical_acceptance = $false
    files = $payload.ToArray(); manifest_entry = 'support/cryer_server_manifest_r1.json'
    manifest_self_hash = 'Omitted to avoid self-reference; ZIP entries are streamed back and checked, with external ZIP SHA256 reported.'
}
$encoding = [Text.UTF8Encoding]::new($false)
$bytes = $encoding.GetBytes(($manifest | ConvertTo-Json -Depth 10) + "`n")
$stream = [IO.File]::Open($manifestPath, [IO.FileMode]::CreateNew)
try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipStream = [IO.File]::Open($zipPath, [IO.FileMode]::CreateNew)
$archive = [IO.Compression.ZipArchive]::new($zipStream, [IO.Compression.ZipArchiveMode]::Create, $false)
try {
    foreach ($file in $payload) {
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.path, $file.entry, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
    [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $manifestPath, 'support/cryer_server_manifest_r1.json', [IO.Compression.CompressionLevel]::Optimal) | Out-Null
} finally { $archive.Dispose(); $zipStream.Dispose() }
$archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    if ($archive.Entries.Count -ne $payload.Count + 1) { throw 'Unexpected ZIP entry count.' }
    $checks = @($payload.ToArray()) + @([pscustomobject]@{ entry = 'support/cryer_server_manifest_r1.json'; sha256 = (Get-Binding $manifestPath).sha256 })
    foreach ($file in $checks) {
        $entry = $archive.GetEntry($file.entry)
        if ($null -eq $entry) { throw "Missing ZIP entry: $($file.entry)" }
        $data = $entry.Open(); $sha = [Security.Cryptography.SHA256]::Create()
        try { $actual = ([BitConverter]::ToString($sha.ComputeHash($data))).Replace('-', '').ToLowerInvariant() }
        finally { $sha.Dispose(); $data.Dispose() }
        if ($actual -ne $file.sha256) { throw "ZIP entry hash mismatch: $($file.entry)" }
    }
} finally { $archive.Dispose() }
[pscustomobject]@{ zip = $zipPath; zip_sha256 = (Get-Binding $zipPath).sha256
    manifest = $manifestPath; payload_files = $payload.Count; runtime_mode = $runtime.mode; solver_executed = $false }
