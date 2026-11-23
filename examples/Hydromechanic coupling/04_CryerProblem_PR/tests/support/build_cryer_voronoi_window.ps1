param([string]$Architecture = 'sm_86')
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'cryer_voronoi_window.cu')).Path
$folder = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../outputs/cryer_voronoi_window_build_r1'))
if (Test-Path -LiteralPath $folder) { throw "Use a fresh Voronoi build directory: $folder" }
if ($Architecture -notmatch '^sm_[0-9]{2,3}$' -or -not $env:INCLUDE -or -not $env:LIB) {
    throw 'An x64 MSVC native environment and valid CUDA architecture are required.'
}
$nvcc = (Get-Command nvcc.exe -CommandType Application | Select-Object -First 1).Source
$cl = (Get-Command cl.exe -CommandType Application | Select-Object -First 1).Source
$null = [IO.Directory]::CreateDirectory($folder)
$dll = Join-Path $folder 'cryer_voronoi_window.dll'
$options = @('--shared','-O3','-std=c++17',"-arch=$Architecture",'--cudart','static',
             '-ccbin',(Split-Path $cl),'-Xcompiler','/MD','-o',$dll,$source)
Push-Location -LiteralPath $folder
try {
    $ErrorActionPreference = 'Continue'
    & $nvcc @options *> (Join-Path $folder 'build.log')
    $rc = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $ok = $rc -eq 0 -and (Test-Path -LiteralPath $dll -PathType Leaf)
    [ordered]@{source=$source;compiler=$nvcc;hostCompiler=$cl;options=$options;exit=$rc;
        passed=$ok;dll=$dll;buildTimeUtc=[DateTime]::UtcNow.ToString('o')} |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $folder 'build.json') -Encoding utf8
    if (-not $ok) { Get-Content -LiteralPath (Join-Path $folder 'build.log') -Tail 30; throw "nvcc failed ($rc)" }
    Write-Output $dll
} finally { Pop-Location }
