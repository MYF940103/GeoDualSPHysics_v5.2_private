[CmdletBinding()]
param(
    [string[]]$Name,
    [string]$Destination,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
if (!$Destination) { $Destination = Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$manifest = Get-Content -Encoding UTF8 -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw | ConvertFrom-Json
$root = (Get-Item -LiteralPath $Destination).FullName
$zipPath = Join-Path $PSScriptRoot 'launchers.zip'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash -ne $manifest.archive_sha256) {
    throw 'The archived launcher ZIP differs from the manifest.'
}
$rows = @($manifest.launchers)
foreach ($requested in $Name) {
    if ($requested -notin $rows.name) { throw "Unknown archived launcher: $requested" }
}
$archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
$digest = [Security.Cryptography.SHA256]::Create()
try {
    if ($archive.Entries.Count -ne $rows.Count) { throw 'Archive entry count differs.' }
    $missing = @()
    foreach ($row in $rows) {
        $file = [string]$row.name
        if ($file -cnotmatch '^xCaseLianSaturatedColumnCollapse_(?:(?:psi0|psi2p5|psim5)_shared_r[345]|shared_preload_r3)_win64_(?:CPU|GPU)\.bat$') {
            throw "Invalid archived filename: $file"
        }
        $entry = $archive.GetEntry($file)
        if (!$entry -or $entry.Length -ne $row.bytes) { throw "Missing or incomplete entry: $file" }
        $inputStream = $entry.Open()
        try { $hash = [BitConverter]::ToString($digest.ComputeHash($inputStream)).Replace('-', '') }
        finally { $inputStream.Dispose() }
        if ($hash -ne $row.sha256) { throw "Archive entry differs: $file" }
        if ($Name -and $file -notin $Name) { continue }
        $path = Join-Path $root $file
        if (Test-Path -LiteralPath $path) {
            if (!(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileHash -LiteralPath $path).Hash -ne $row.sha256) {
                throw "A different file already exists: $path"
            }
        } else { $missing += $row }
    }
    if ($CheckOnly) { Write-Output "Archive verified. Missing requested launchers: $($missing.Count)"; return }
    foreach ($row in $missing) {
        $path = Join-Path $root $row.name
        $entry = $archive.GetEntry($row.name)
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $path, $false)
        [IO.File]::SetLastWriteTimeUtc($path, [DateTimeOffset]::Parse($row.mtime_utc).UtcDateTime)
        if ((Get-FileHash -LiteralPath $path).Hash -ne $row.sha256) { throw "Restore check failed: $path" }
    }
    Write-Output "Restored $($missing.Count) launchers to $root"
} finally {
    $digest.Dispose()
    $archive.Dispose()
}
