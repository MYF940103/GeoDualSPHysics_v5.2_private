[CmdletBinding()]
param(
    [string]$SourceHead = '',
    [string]$VcRedistDirectory = 'D:\Program Files\VS2022\VC\Redist\MSVC\14.36.32532\x64\Microsoft.VC143.CRT',
    [switch]$RequireInstalledVcRuntime
)

# Packages existing verified programs and inputs only. Never builds or runs a case.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$caseRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$repoRoot = (Get-Item -LiteralPath $caseRoot).Parent.Parent.Parent.FullName
$frozen = Join-Path $caseRoot 'tests\outputs\lian_hg_np_build_r1'
$bin = Join-Path $PSScriptRoot 'bin'
$manifestPath = Join-Path $PSScriptRoot 'server_manifest.json'
$zipPath = Join-Path $caseRoot 'Lian_HGSPR_Windows_RTXA6000.zip'
if ((Test-Path -LiteralPath $zipPath) -or (Test-Path -LiteralPath $manifestPath)) {
    throw 'Package or manifest already exists; retained artifacts are never overwritten.'
}
if ($SourceHead -and $SourceHead -notmatch '^[0-9a-fA-F]{40}$') {
    throw 'SourceHead must be an explicitly supplied full Git commit ID, or empty.'
}

# An explicit whitelist: no tests, raw results, CPU/Debug programs or wildcard copy.
$payload = [System.Collections.Generic.List[object]]::new()
$inputs = @(
    @{ Path = (Join-Path $caseRoot 'CaseLianFlexibleStrip2D_PR_release_Def.xml'); Entry = 'CaseLianFlexibleStrip2D_PR_release_Def.xml' },
    @{ Path = (Join-Path $caseRoot 'xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat'); Entry = 'xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat' },
    @{ Path = (Join-Path $caseRoot 'README.md'); Entry = 'README.md' },
    @{ Path = (Join-Path $PSScriptRoot 'README_server.md'); Entry = 'support/README_server.md' },
    @{ Path = (Join-Path $PSScriptRoot 'paper_observables.json'); Entry = 'support/paper_observables.json' },
    @{ Path = $PSCommandPath; Entry = 'support/pack_lian_server.ps1' },
    @{ Path = (Join-Path $repoRoot 'LICENSE'); Entry = 'LICENSE' }
)
foreach ($file in $inputs) {
    if (-not (Test-Path -LiteralPath $file.Path -PathType Leaf)) { throw "Missing package input: $($file.Path)" }
}
$dependencies = [ordered]@{
    'DualSPHysics5.2_GEO_win64.exe' = '260c3d4c845db380f93257f96fba77034b1c6e2047d6780702b2483b974c933c'
    'GenCase_win64.exe' = 'f2f4cd8ed3e6cea4a1922d64f916369aade0a15df4168344edfe66c6efd66c14'
    'dsphchrono.dll' = 'c605befbc02991dd9d36266f2ce28e1e0bd675c115cab79e1f10fc873c6ff8fe'
    'ChronoEngine.dll' = '246d6c92824c55e2ab469e6e9567516fe4cecd84b617fc64cf6d2382fd7fbbe5'
    'vcomp140.dll' = '1d480d651414304bddd0928b1c1563b4fb7f89b1c6ac30650c884150de0ec540'
    'DsphConfig.xml' = 'a2bc1f88c6ea95347187a64a991ebada177c6314de5c35ab078b06d78235eece'
}
foreach ($name in $dependencies.Keys) {
    $source = Join-Path $frozen $name
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $dependencies[$name]) {
        throw "Frozen binary hash mismatch: $name"
    }
}

function Add-PayloadFile([string]$Path, [string]$Entry, [string]$Origin) {
    $file = Get-Item -LiteralPath $Path
    $payload.Add([pscustomobject][ordered]@{
        entry = $Entry
        bytes = $file.Length
        sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        path = $file.FullName
        origin = $Origin
    })
}
function Copy-VerifiedBinary([string]$Source, [string]$Name, [string]$ExpectedHash) {
    $target = Join-Path $bin $Name
    if (Test-Path -LiteralPath $target) {
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $ExpectedHash) {
            throw "Existing support/bin file differs; not overwriting: $Name"
        }
    } else {
        Copy-Item -LiteralPath $Source -Destination $target
    }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $ExpectedHash) {
        throw "Copied binary hash mismatch: $Name"
    }
    Add-PayloadFile $target ('support/bin/' + $Name) $Source
}

# App-local CRTs are accepted only from a VS redistributable directory and with
# valid Microsoft signatures. Otherwise require the official x64 installer.
$runtime = [ordered]@{
    mode = 'official_x64_runtime_must_be_preinstalled'
    minimum_build_tools_version = '14.36'
    ucrt = 'Windows system prerequisite; system DLLs are not copied.'
    license_and_download = 'https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170'
    files = @()
}
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
            $crt += [pscustomobject]@{
                source = $source; name = $name; version = $version
                sha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
                signer = $signature.SignerCertificate.Subject
                signature_status = [string]$signature.Status
            }
        }
    }
}

if (-not (Test-Path -LiteralPath $bin)) { New-Item -ItemType Directory -Path $bin | Out-Null }
foreach ($file in $inputs) { Add-PayloadFile $file.Path $file.Entry $file.Path }
foreach ($name in $dependencies.Keys) {
    Copy-VerifiedBinary (Join-Path $frozen $name) $name $dependencies[$name]
}
if ($crt.Count -eq 3) {
    foreach ($file in $crt) { Copy-VerifiedBinary $file.source $file.name $file.sha256 }
    $runtime.mode = 'signed_MSVC_14_app_local_from_Visual_Studio_redist'
    $runtime.files = $crt
} else {
    Write-Warning 'No verified app-local CRT set selected. Install the official x64 VC++ runtime on the server first.'
}
# Include vendor notices only when the case maintainer has supplied them.
foreach ($name in @('LICENSE_Chrono.txt', 'LICENSE_MSVC.txt')) {
    $notice = Join-Path $PSScriptRoot $name
    if (Test-Path -LiteralPath $notice -PathType Leaf) { Add-PayloadFile $notice ('support/' + $name) $notice }
}
$sourceHashes = @()
foreach ($relative in @(
    'src/source/JSphHourglassCpu.h', 'src/source/JSphHourglassCpu.cpp',
    'src/source/JSphHourglassGpu_ker.h', 'src/source/JSphHourglassGpu.cpp',
    'src/source/JSphHourglassGpu_ker.cu', 'src/source/JSphCpuSingle.cpp',
    'src/source/JSphGpuSingle.cpp', 'src/VS/DualSPHysics5Re.vcxproj'
)) {
    $sourceHashes += [ordered]@{ path = $relative; sha256 = (Get-FileHash -LiteralPath (Join-Path $repoRoot $relative) -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$manifest = [ordered]@{
    format = 'Lian_HGSPR_server_bundle_v1'
    created_utc = [DateTime]::UtcNow.ToString('o')
    source_head_supplied_by_packager = $SourceHead
    source_hashes_at_packaging = $sourceHashes
    target = 'Windows x64, NVIDIA RTX A6000 (compute capability 8.6)'
    gpu_binary = 'Validated frozen Release: sm_86 SASS and compute_86 PTX7.7, CUDA11.7 static runtime.'
    gpu_driver = 'Install an NVIDIA driver supporting RTX A6000 and CUDA11.7; CUDA11.7 GA Windows toolkit driver baseline is516.01. Confirm actual server driver; no driver/system DLL is bundled.'
    nvidia_reference = 'https://docs.nvidia.com/cuda/archive/11.7.0/cuda-toolkit-release-notes/index.html'
    runtime = $runtime
    project_license = 'LICENSE (project LGPL2.1); preserve existing project notices.'
    chrono_project_reference = 'https://projectchrono.org/'
    vendor_notice = 'No missing third-party license text is invented; Microsoft CRT source/signatures and official license link are recorded.'
    formal_input = 'CaseLianFlexibleStrip2D_PR_release_Def.xml'
    formal_bat = 'xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat'
    new_output = 'CaseLianFlexibleStrip2D_PR_release_HGSPR_out'
    execution = 'Packaging only. Formal100s is for the user server; no solver is launched here. Half3s was cancelled, not accepted.'
    files = $payload.ToArray()
    manifest_entry = 'support/server_manifest.json'
    manifest_self_hash = 'Intentionally omitted to avoid self-reference; ZIP extraction is checked against this manifest.'
}
$encoding = [System.Text.UTF8Encoding]::new($false)
$manifestBytes = $encoding.GetBytes(($manifest | ConvertTo-Json -Depth 10) + "`n")
$stream = [System.IO.File]::Open($manifestPath, [System.IO.FileMode]::CreateNew)
try { $stream.Write($manifestBytes, 0, $manifestBytes.Length) } finally { $stream.Dispose() }

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipStream = [System.IO.File]::Open($zipPath, [System.IO.FileMode]::CreateNew)
$archive = [System.IO.Compression.ZipArchive]::new($zipStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
try {
    foreach ($file in $payload) {
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.path, $file.entry,
            [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $manifestPath,
        'support/server_manifest.json', [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
} finally { $archive.Dispose(); $zipStream.Dispose() }

# Verify every entry by streaming it back; do not extract, invoke tools or run BATs.
$archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    if ($archive.Entries.Count -ne $payload.Count + 1) { throw 'Unexpected ZIP entry count.' }
    $checks = @($payload.ToArray()) + @([pscustomobject]@{
        entry = 'support/server_manifest.json'; sha256 = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash
    })
    foreach ($file in $checks) {
        $entry = $archive.GetEntry($file.entry)
        if ($null -eq $entry) { throw "Missing ZIP entry: $($file.entry)" }
        $entryStream = $entry.Open(); $sha = [System.Security.Cryptography.SHA256]::Create()
        try { $actual = ([BitConverter]::ToString($sha.ComputeHash($entryStream))).Replace('-', '') }
        finally { $sha.Dispose(); $entryStream.Dispose() }
        if ($actual -ne $file.sha256) { throw "ZIP entry hash mismatch: $($file.entry)" }
    }
} finally { $archive.Dispose() }
[pscustomobject]@{
    zip = $zipPath; zip_sha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    manifest = $manifestPath; payload_files = $payload.Count; runtime_mode = $runtime.mode
    solver_executed = $false
}
