param(
    [string]$BuildDirectory = (Join-Path $PSScriptRoot '../outputs/cryer_weak_nu_full_build_r1'),
    [string]$FrozenPackage = (Join-Path $PSScriptRoot '../../support/weak_full_r1'),
    [string]$ImportLibrary = (Join-Path $PSScriptRoot '../outputs/cryer_weak_window_build_r1/cryer_weak_window.lib')
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'cryer_weak_nu_full_host.cpp')).Path
$package = (Resolve-Path -LiteralPath $FrozenPackage).Path
$library = (Resolve-Path -LiteralPath $ImportLibrary).Path
$folder = [IO.Path]::GetFullPath($BuildDirectory)
if (Test-Path -LiteralPath $folder) { throw "Use a fresh build directory: $folder" }
$dll = Join-Path $package 'cryer_weak_window.dll'
$originalDll = Join-Path (Split-Path $library) 'cryer_weak_window.dll'
$sealedHash = 'd89fa09263e9ed3af7e15d5e8eedf07b967809e64762a8fa19b2173bfcb14c9c'
if ((Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash -ne $sealedHash -or
    (Get-FileHash -LiteralPath $originalDll -Algorithm SHA256).Hash -ne $sealedHash) {
    throw 'The runtime DLL and original import-library build must match the sealed weak component.'
}
$cl = (Get-Command cl.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
if (-not $env:INCLUDE -or -not $env:LIB) { throw 'Use a Visual Studio x64 native tools environment.' }
$null = [IO.Directory]::CreateDirectory($folder)
$exe = Join-Path $folder 'weak_nu_full.exe'
$object = Join-Path $folder 'cryer_weak_nu_full_host.obj'
$options = @('/nologo', '/EHsc', '/std:c++17', '/O2', '/MT', $source, $library, "/Fo$object", "/Fe$exe")
Push-Location -LiteralPath $folder
try {
    $ErrorActionPreference = 'Continue'
    & $cl @options *> (Join-Path $folder 'build.log')
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $ok = $rc -eq 0 -and (Test-Path -LiteralPath $exe -PathType Leaf)
    $programHash = $null
    if ($ok) {
        foreach ($name in @('cryer_weak_window.dll', 'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')) {
            Copy-Item -LiteralPath (Join-Path $package $name) -Destination (Join-Path $folder $name)
        }
        $programHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    [ordered]@{
        source=$source; sourceSha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash;
        compiler=$cl; options=$options; frozenPackage=$package; importLibrary=$library;
        importLibrarySha256=(Get-FileHash -LiteralPath $library -Algorithm SHA256).Hash;
        runtimeDllSha256=$sealedHash; exit=$rc; returncode=$rc; passed=$ok; executable=$exe;
        program_sha256=$programHash;
        buildTimeUtc=[DateTime]::UtcNow.ToString('o')
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $folder 'build.json') -Encoding utf8
    if (-not $ok) { Get-Content -LiteralPath (Join-Path $folder 'build.log') -Tail 30; throw "MSVC failed ($rc)" }
    Write-Output $exe
    Write-Output "Run from frozen package directory: $package"
} finally { Pop-Location }
