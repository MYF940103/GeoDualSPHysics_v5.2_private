param(
    [Parameter(Mandatory = $true)]
    [string]$Variant,

    [double]$DampingCoef = 0.02,
    [int]$DensityDT = 0,
    [double]$DensityDTValue = 0.1,
    [int]$PoreShepardRegularization = 0,
    [double]$TimeMax = 10.0,
    [double]$TimeOut = 0.05
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$testsDir = Split-Path -Parent $scriptDir
if ((Split-Path -Leaf $scriptDir) -ne "scripts") {
    $testsDir = $scriptDir
}
$caseDir = Split-Path -Parent $testsDir
$repoRoot = (Resolve-Path (Join-Path $caseDir "..\..\..")).Path
$binDir = Join-Path $repoRoot "bin\windows"
$configsDir = Join-Path $testsDir "configs"
$outputsDir = Join-Path $testsDir "outputs"
$logsDir = Join-Path $testsDir "logs"
New-Item -ItemType Directory -Force -Path $configsDir, $outputsDir, $logsDir | Out-Null

$case = "CaseYao2DConsolidation_PR"
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
$postprocess = Join-Path $scriptDir "postprocess_yao2d_ab_normalized_epwp.py"

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

[xml]$doc = Get-Content -LiteralPath $baseXml
Set-SpecialValue $doc "PoreShepardRegularization" ([string]$PoreShepardRegularization)
Set-ParameterValue $doc "SlipMode" "3"
Set-ParameterValue $doc "SoilDamping" "1"
Set-ParameterValue $doc "SoilDampingCoef" ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:g}", $DampingCoef))
Set-ParameterValue $doc "DensityDT" ([string]$DensityDT)
Set-ParameterValue $doc "DensityDTvalue" ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:g}", $DensityDTValue))
Set-ParameterValue $doc "TimeMax" ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:g}", $TimeMax))
Set-ParameterValue $doc "TimeOut" ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:g}", $TimeOut))
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

    & py -3 $postprocess --case-dir $dirOut *> "${logPrefix}_ab_postprocess.log"
    if ($LASTEXITCODE -ne 0) { throw "A/B postprocess failed for $Variant" }
}
finally {
    Pop-Location
}

Write-Output "Yao 2025 2-D variant run done: $Variant"
Write-Output $dirOut
