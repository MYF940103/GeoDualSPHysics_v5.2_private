param([Parameter(Mandatory=$true)][string]$Name)
$ErrorActionPreference='Stop'
$caseDir='D:\MYF\SPH\GeoDualSPHysics_v5.2\examples\myf\08_CohesiveGranularCollapse'
$binDir='D:\MYF\SPH\GeoDualSPHysics_v5.2\bin\windows'
$logDir=Join-Path $caseDir 'runlogs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$status=Join-Path $logDir ($Name + '.status.txt')
$exitfile=Join-Path $logDir ($Name + '.exit.txt')
Remove-Item -LiteralPath $status -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $exitfile -Force -ErrorAction SilentlyContinue
function Write-Status([string]$Message){
  $stamp=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  Add-Content -LiteralPath $status -Value ($stamp + ' ' + $Message)
}
function Check-Code([string]$Label,[int]$Code){
  Write-Status ('END ' + $Label + ' exit=' + $Code)
  if($Code -ne 0){ throw ($Label + ' failed with exit code ' + $Code) }
}
try{
  Set-Location -LiteralPath $caseDir
  $dirout=$Name + '_out'
  $diroutdata=Join-Path $dirout 'data'
  $resolvedCase=(Resolve-Path -LiteralPath $caseDir).Path
  $outPath=Join-Path $caseDir $dirout
  if(Test-Path -LiteralPath $outPath){
    $resolvedOut=(Resolve-Path -LiteralPath $outPath).Path
    if(-not $resolvedOut.StartsWith($resolvedCase)){ throw ('Unexpected output path: ' + $resolvedOut) }
    Write-Status ('REMOVE ' + $dirout)
    Remove-Item -LiteralPath $outPath -Recurse -Force
  }
  $gencase=Join-Path $binDir 'GenCase_win64.exe'
  $solver=Join-Path $binDir 'DualSPHysics5.2_GEO_win64.exe'
  $partvtk=Join-Path $binDir 'PartVTK_win64.exe'
  Write-Status 'START gencase'
  & $gencase ($Name + '_Def') ($dirout + '/' + $Name) '-save:all' *> (Join-Path $logDir ($Name + '_gencase.log'))
  Check-Code 'gencase' $LASTEXITCODE
  Write-Status 'START solver_gpu'
  & $solver '-gpu' ($dirout + '/' + $Name) $dirout '-dirdataout' 'data' '-svres' *> (Join-Path $logDir ($Name + '_solver_gpu.log'))
  Check-Code 'solver_gpu' $LASTEXITCODE
  $particles=Join-Path $dirout 'particles'
  Write-Status 'START partvtk_fluid'
  & $partvtk '-dirin' $diroutdata '-savevtk' ($particles + '/PartFluid') '-onlytype:-all,fluid' '-vars:+idp,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic' *> (Join-Path $logDir ($Name + '_partvtk_fluid.log'))
  Check-Code 'partvtk_fluid' $LASTEXITCODE
  Write-Status 'START partvtk_bound'
  & $partvtk '-dirin' $diroutdata '-savevtk' ($particles + '/PartBound') '-onlytype:-all,bound' '-vars:+idp,+vel,+rhop,+sigma_kk' *> (Join-Path $logDir ($Name + '_partvtk_bound.log'))
  Check-Code 'partvtk_bound' $LASTEXITCODE
  Write-Status 'DONE'
  Set-Content -LiteralPath $exitfile -Value '0'
  exit 0
}
catch{
  Write-Status ('FAILED ' + $_.Exception.Message)
  Set-Content -LiteralPath $exitfile -Value '1'
  exit 1
}