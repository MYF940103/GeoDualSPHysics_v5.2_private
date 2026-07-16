param(
    [Parameter(Mandatory = $true)]
    [string]$Variant,

    [double]$DtFixed = 0.00005,
    [double]$TimeMax = 3.0,
    [double]$TimeOut = 0.05,
    [double]$PoreDtSafety = 0.1,
    [string]$PostTargets = "0.5,1.0,3.0"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$testsDir = Split-Path -Parent $scriptDir
$caseDir = Split-Path -Parent $testsDir
$repoRoot = (Resolve-Path (Join-Path $caseDir "..\..\..")).Path
$binDir = Join-Path $repoRoot "bin\windows"

$configsDir = Join-Path $testsDir "configs"
$outputsDir = Join-Path $testsDir "outputs"
$logsDir = Join-Path $testsDir "logs"
New-Item -ItemType Directory -Force -Path $configsDir, $outputsDir, $logsDir | Out-Null

$case = "CaseLianFlexibleStrip2D_PR"
$baseXml = Join-Path $caseDir "${case}_Def.xml"
$variantXmlStem = "${case}_${Variant}_Def"
$variantXml = Join-Path $configsDir "${variantXmlStem}.xml"
$dirOut = Join-Path $outputsDir "${case}_${Variant}_out"
$dirData = Join-Path $dirOut "data"
$vtkDir = Join-Path $dirOut "particles"

$genCase = Join-Path $binDir "GenCase_win64.exe"
$solver = Join-Path $binDir "DualSPHysics5.2_GEO_win64.exe"
if (!(Test-Path -LiteralPath $solver)) {
    $solver = Join-Path $binDir "DualSPHysics5.2_win64_debug.exe"
}
$partVtk = Join-Path $binDir "PartVTK_win64.exe"
$postprocess = Join-Path $scriptDir "postprocess_lian_flexible_strip.py"

$vars = "+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace"
$logPrefix = Join-Path $logsDir "run_${Variant}"

function Set-ParameterValue([xml]$Doc, [string]$Key, [string]$Value) {
    $node = $Doc.SelectSingleNode("//parameter[@key='$Key']")
    if ($null -eq $node) {
        throw "Missing XML parameter: $Key"
    }
    $node.SetAttribute("value", $Value)
}

function Set-SpecialValue([xml]$Doc, [string]$Name, [string]$Value) {
    $node = $Doc.SelectSingleNode("//*[@value and local-name()='$Name']")
    if ($null -eq $node) {
        throw "Missing XML special element: $Name"
    }
    $node.SetAttribute("value", $Value)
}

function Format-Invariant([double]$Value) {
    return [string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:g}", $Value)
}

[xml]$doc = Get-Content -LiteralPath $baseXml
Set-SpecialValue $doc "PoreDtSafety" (Format-Invariant $PoreDtSafety)
Set-ParameterValue $doc "DtIni" (Format-Invariant $DtFixed)
Set-ParameterValue $doc "DtFixed" (Format-Invariant $DtFixed)
Set-ParameterValue $doc "TimeMax" (Format-Invariant $TimeMax)
Set-ParameterValue $doc "TimeOut" (Format-Invariant $TimeOut)
$doc.Save($variantXml)

if (Test-Path -LiteralPath $dirOut) {
    Remove-Item -LiteralPath $dirOut -Recurse -Force
}

Push-Location $caseDir
try {
    & $genCase "tests\configs\$variantXmlStem" "tests\outputs\${case}_${Variant}_out\$case" -save:all *> "${logPrefix}_gencase.log"
    if ($LASTEXITCODE -ne 0) { throw "GenCase failed for $Variant" }

    & $solver -gpu -mdbc_freeslip "tests\outputs\${case}_${Variant}_out\$case" "tests\outputs\${case}_${Variant}_out" -dirdataout data -svres -svextraparts:1 -tmax:$TimeMax -tout:$TimeOut *> "${logPrefix}_solver.log"
    if ($LASTEXITCODE -ne 0) { throw "DualSPHysics GPU failed for $Variant" }

    & $partVtk -dirin $dirData -savevtk "$vtkDir\PartBound" -onlytype:-all,bound -vars:$vars *> "${logPrefix}_partvtk_bound.log"
    if ($LASTEXITCODE -ne 0) { throw "PartVTK bound failed for $Variant" }

    & $partVtk -dirin $dirData -savevtk "$vtkDir\PartFluid" -onlytype:-all,fluid -vars:$vars *> "${logPrefix}_partvtk.log"
    if ($LASTEXITCODE -ne 0) { throw "PartVTK fluid failed for $Variant" }

    & py -3 $postprocess --run-dir $dirOut --out-dir (Join-Path $dirOut "figures") --targets $PostTargets *> "${logPrefix}_postprocess.log"
    if ($LASTEXITCODE -ne 0) { throw "Lian postprocess failed for $Variant" }
}
finally {
    Pop-Location
}

Write-Output "Lian 2023 flexible strip GPU variant done: $Variant"
Write-Output $dirOut
