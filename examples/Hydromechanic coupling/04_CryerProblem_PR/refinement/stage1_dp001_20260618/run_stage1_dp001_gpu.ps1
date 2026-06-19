$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$caseRoot = Resolve-Path (Join-Path $root "..\..")
$binRoot = Resolve-Path (Join-Path $caseRoot "..\..\..\bin\windows")
$template = Join-Path $caseRoot "CaseCryerProblem_PR_Stage1_Def.xml"

$gencase = Join-Path $binRoot "GenCase_win64.exe"
$solver = Join-Path $binRoot "DualSPHysics5.2_GEO_win64.exe"
$partvtk = Join-Path $binRoot "PartVTK_win64.exe"

$outRoot = Join-Path $root "out"
$analysisRoot = Join-Path $root "analysis"
$runlogRoot = Join-Path $outRoot "runlogs"
New-Item -ItemType Directory -Force $analysisRoot | Out-Null
if(Test-Path $outRoot){ Remove-Item -LiteralPath $outRoot -Recurse -Force }
New-Item -ItemType Directory -Force $outRoot | Out-Null
New-Item -ItemType Directory -Force $runlogRoot | Out-Null

$caseName = "CaseCryerStage1_dp001_l1"
$xmlPath = Join-Path $root "$($caseName)_Def.xml"
$caseOut = Join-Path $outRoot "dp001_l1"
$casePrefix = Join-Path $caseOut $caseName
$dataDir = Join-Path $caseOut "data"
$vtkDir = Join-Path $caseOut "particles_final"
$vars = "+idp,+mk,+vel,+rhop,+press,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace"

function Invoke-Logged {
  param(
    [string]$Exe,
    [string[]]$CmdArgs,
    [string]$Log
  )
  & $Exe @CmdArgs *> $Log
  if($LASTEXITCODE -ne 0){
    Get-Content $Log -Tail 100
    throw "Command failed with exit code $LASTEXITCODE`: $Exe $($CmdArgs -join ' ')"
  }
}

New-Item -ItemType Directory -Force $caseOut | Out-Null
New-Item -ItemType Directory -Force $vtkDir | Out-Null

$xml = Get-Content $template -Raw
$xml = [regex]::Replace($xml, '<newvarcte Dp="[^"]+"', '<newvarcte Dp="0.001"')
$xml = [regex]::Replace($xml, '<HydroMechDrainage value="[^"]+"[^>]*/>', '<HydroMechDrainage value="0" comment="Stage 1 is explicitly undrained; no pore-pressure drainage boundary is enforced" />')
$xml = [regex]::Replace($xml, '<HydroMechDrainageStartTime value="[^"]+"[^>]*/>', '<HydroMechDrainageStartTime value="0.0" comment="Ignored while HydroMechDrainage=0" units_comment="seconds" />')
$xml = [regex]::Replace($xml, '<parameter key="SoilDampingCoef" value="[^"]+"', '<parameter key="SoilDampingCoef" value="0.02"')
$xml = [regex]::Replace($xml, '<parameter key="DtIni" value="[^"]+"', '<parameter key="DtIni" value="1e-6"')
$xml = [regex]::Replace($xml, '<parameter key="DtFixed" value="[^"]+"', '<parameter key="DtFixed" value="1e-6"')
$xml = [regex]::Replace($xml, '<parameter key="TimeMax" value="[^"]+"', '<parameter key="TimeMax" value="0.006"')
$xml = [regex]::Replace($xml, '<parameter key="TimeOut" value="[^"]+"', '<parameter key="TimeOut" value="0.006"')
Set-Content -LiteralPath $xmlPath -Value $xml -Encoding UTF8

Invoke-Logged -Exe $gencase -CmdArgs @("$($caseName)_Def", $casePrefix, "-save:all") -Log (Join-Path $runlogRoot "dp001_l1_gencase.log")
Invoke-Logged -Exe $solver -CmdArgs @("-gpu", $casePrefix, $caseOut, "-dirdataout", "data", "-svres:1", "-svextraparts:1", "-tmax:0.006", "-tout:0.006") -Log (Join-Path $runlogRoot "dp001_l1_solver.log")

$lastPart = Get-ChildItem -LiteralPath $dataDir -Filter "Part_*.bi4" | Sort-Object Name | Select-Object -Last 1
if(-not $lastPart){ throw "No Part_*.bi4 output found in $dataDir" }
$lastIndex = [int]([regex]::Match($lastPart.BaseName, '\d+$').Value)
Invoke-Logged -Exe $partvtk -CmdArgs @("-dirin", $dataDir, "-files:$lastIndex", "-savevtk", (Join-Path $vtkDir "PartFluid"), "-onlytype:-bound", "-vars:$vars") -Log (Join-Path $runlogRoot "dp001_l1_partvtk_vtk.log")

Write-Host "dp001_l1 Stage1 run completed."
