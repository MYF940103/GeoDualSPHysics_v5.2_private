$ErrorActionPreference = "Stop"

$caseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cases = @(
  "CaseStaticDrySoilColumn2D_Feng2021_dp010_xi002_ddt2",
  "CaseStaticDrySoilColumn2D_Feng2021_dp005_xi002_ddt2",
  "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi000_ddt2",
  "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi001_ddt2",
  "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi005_ddt2",
  "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi002_ddt0",
  "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi002_ddt1",
  "CaseStaticDrySoilColumn2D_Feng2021_dp002_xi002_ddt3"
)

$logDir = Join-Path $caseDir "runlogs"
New-Item -ItemType Directory -Force $logDir | Out-Null

Push-Location $caseDir
try {
  foreach($name in $cases) {
    $bat = "x${name}_win64_CPU.bat"
    $log = Join-Path $logDir "$name.log"
    Write-Host "Running $name ..."
    cmd /c "$bat -force" 2>&1 | Tee-Object -FilePath $log
    if($LASTEXITCODE -ne 0) {
      throw "Case failed: $name"
    }
  }
}
finally {
  Pop-Location
}
