$ErrorActionPreference='Stop'
$caseDir='D:\MYF\SPH\GeoDualSPHysics_v5.2\examples\myf\08_CohesiveGranularCollapse'
$binDir='D:\MYF\SPH\GeoDualSPHysics_v5.2\bin\windows'
$logDir=Join-Path $caseDir 'runlogs_2d_gpu'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$cases=@('CaseCohesiveGranCollapse2D_ASOff','CaseCohesiveGranCollapse2D_ASCoef03','CaseCohesiveGranCollapse2D_ASCoef05','CaseCohesiveGranCollapse2D_ASCoef07')
function Write-Status([string]$Name,[string]$Message){
  $stamp=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  Add-Content -LiteralPath (Join-Path $logDir ($Name + '.status.txt')) -Value ($stamp + ' ' + $Message)
}
function Check-Code([string]$Name,[string]$Label,[int]$Code){
  Write-Status $Name ('END ' + $Label + ' exit=' + $Code)
  if($Code -ne 0){ throw ($Name + ' ' + $Label + ' failed with exit code ' + $Code) }
}
Set-Location -LiteralPath $caseDir
$resolvedCase=(Resolve-Path -LiteralPath $caseDir).Path
foreach($Name in $cases){
  Remove-Item -LiteralPath (Join-Path $logDir ($Name + '.status.txt')) -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath (Join-Path $logDir ($Name + '.exit.txt')) -Force -ErrorAction SilentlyContinue
  try{
    $dirout=$Name + '_out'
    $diroutdata=Join-Path $dirout 'data'
    $outPath=Join-Path $caseDir $dirout
    if(Test-Path -LiteralPath $outPath){
      $resolvedOut=(Resolve-Path -LiteralPath $outPath).Path
      if(-not $resolvedOut.StartsWith($resolvedCase)){ throw ('Unexpected output path: ' + $resolvedOut) }
      Write-Status $Name ('REMOVE ' + $dirout)
      Remove-Item -LiteralPath $outPath -Recurse -Force
    }
    $gencase=Join-Path $binDir 'GenCase_win64.exe'
    $solver=Join-Path $binDir 'DualSPHysics5.2_GEO_win64.exe'
    $partvtk=Join-Path $binDir 'PartVTK_win64.exe'
    Write-Status $Name 'START gencase'
    & $gencase ($Name + '_Def') ($dirout + '/' + $Name) '-save:all' *> (Join-Path $logDir ($Name + '_gencase.log'))
    Check-Code $Name 'gencase' $LASTEXITCODE
    Write-Status $Name 'START solver_gpu'
    & $solver '-gpu' ($dirout + '/' + $Name) $dirout '-dirdataout' 'data' '-svres' *> (Join-Path $logDir ($Name + '_solver_gpu.log'))
    Check-Code $Name 'solver_gpu' $LASTEXITCODE
    $particles=Join-Path $dirout 'particles'
    Write-Status $Name 'START partvtk_fluid'
    & $partvtk '-dirin' $diroutdata '-savevtk' ($particles + '/PartFluid') '-onlytype:-all,fluid' '-vars:+idp,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic' *> (Join-Path $logDir ($Name + '_partvtk_fluid.log'))
    Check-Code $Name 'partvtk_fluid' $LASTEXITCODE
    Write-Status $Name 'START partvtk_bound'
    & $partvtk '-dirin' $diroutdata '-savevtk' ($particles + '/PartBound') '-onlytype:-all,bound' '-vars:+idp,+vel,+rhop,+sigma_kk' *> (Join-Path $logDir ($Name + '_partvtk_bound.log'))
    Check-Code $Name 'partvtk_bound' $LASTEXITCODE
    Write-Status $Name 'DONE'
    Set-Content -LiteralPath (Join-Path $logDir ($Name + '.exit.txt')) -Value '0'
  }
  catch{
    Write-Status $Name ('FAILED ' + $_.Exception.Message)
    Set-Content -LiteralPath (Join-Path $logDir ($Name + '.exit.txt')) -Value '1'
    throw
  }
}