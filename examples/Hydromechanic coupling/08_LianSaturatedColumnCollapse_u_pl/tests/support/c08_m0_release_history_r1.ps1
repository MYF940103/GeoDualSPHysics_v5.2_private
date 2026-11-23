param([switch]$Build,[string]$ShortData,[uint32]$Part=42,[uint32]$Step=42,
      [double]$Dt=0.000005,[uint32]$PreviousPart=41)
$ErrorActionPreference = 'Stop'
$tag = 'c08_m0_release_history_r1'
$tests = (Get-Item -LiteralPath $PSScriptRoot).Parent
$hydro = $tests.Parent.Parent
$src = Join-Path $hydro.Parent.Parent.FullName 'src/source'
$out = Join-Path $tests.FullName "outputs/$tag"
$exe = Join-Path $out 'ReadPressureHistory.exe'
if ($Build) {
    if (Test-Path -LiteralPath $exe) { throw 'Existing reader. Omit -Build to use it.' }
    [void][IO.Directory]::CreateDirectory($out)
    $vswhere = Join-Path (${env:ProgramFiles(x86)}) 'Microsoft Visual Studio/Installer/vswhere.exe'
    $vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if (!$vs) { throw 'Visual Studio C++ toolchain was not found.' }
    $vcvars = Join-Path $vs 'VC/Auxiliary/Build/vcvars64.bat'
    $settings = & $env:ComSpec /d /s /c ('call "'+$vcvars+'" >nul && set')
    if ($LASTEXITCODE) { throw 'vcvars failed' }
    foreach ($line in $settings) {
        $split=$line.IndexOf('=')
        if ($split -gt 0) {
            [Environment]::SetEnvironmentVariable($line.Substring(0,$split),$line.Substring($split+1),'Process')
        }
    }
    $units = @('Functions','JObject','JException','JBinaryData','JPartDataHead','JPartDataBi4') |
             ForEach-Object { Join-Path $src ($_.ToString()+'.cpp') }
    Push-Location -LiteralPath $out
    try {
        & cl.exe /nologo /EHsc /std:c++17 /Gy /O2 /fp:precise /MT /DWIN32 /D_HAS_STD_BYTE=0 "/I$src" (Join-Path $PSScriptRoot "$tag.cpp") @units /link /OPT:REF "/OUT:$exe" > build.log
        if ($LASTEXITCODE) { Get-Content -Tail 18 build.log; throw 'C++ build failed' }
    } finally {Pop-Location}
}
if (!(Test-Path -LiteralPath $exe)) { throw 'Compile the reader with -Build first.' }
if ($ShortData) {
    $dtText=$Dt.ToString('R',[Globalization.CultureInfo]::InvariantCulture)
    $json=& $exe short (Resolve-Path -LiteralPath $ShortData).Path $Part $Step $dtText $PreviousPart $hydro.FullName
    $label="M0_part$Part"
} else {
    $json=& $exe retained $hydro.FullName
    $label='retained'
}
if ($LASTEXITCODE) { throw "Readback failed (exit $LASTEXITCODE)." }
$null=$json | ConvertFrom-Json
$record=Join-Path $tests.FullName "logs/$tag.$label.json"
if (!(Test-Path -LiteralPath $record)) { [IO.File]::WriteAllText($record,$json+[Environment]::NewLine) }
elseif (([IO.File]::ReadAllText($record)).Trim() -cne $json) {throw 'Stored receipt differs'}
$json
