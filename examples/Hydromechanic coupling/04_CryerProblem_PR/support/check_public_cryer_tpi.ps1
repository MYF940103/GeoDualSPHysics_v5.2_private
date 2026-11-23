param([Parameter(Mandatory=$true)][string]$OutputDirectory,
      [Parameter(Mandatory=$true)][ValidateSet(2,481685)][int]$Steps)
$ErrorActionPreference = 'Stop'
$rows = @(Get-Content -LiteralPath (Join-Path $OutputDirectory 'Run.csv'))
if ($rows.Count -ne 2) { throw 'Run.csv must contain one completed simulation.' }
$names = $rows[0].TrimStart('#').Split(';')
$values = $rows[1].Split(';')
function Field([string]$key) {
    $pos = [Array]::IndexOf($names, $key)
    if ($pos -lt 0) { throw "Missing Run.csv field $key" }
    return $values[$pos]
}
$frames = if ($Steps -eq 2) { 2 } else { 265 }
if ((Field 'Steps') -ne "$Steps" -or (Field 'PartFiles') -ne "$frames" -or
    (Field 'PartsOut') -ne '0' -or (Field 'Np') -ne '37181' -or
    (Field 'Hardware') -notmatch 'GPU') { throw 'Incomplete GPU run or unexpected particle count.' }
foreach ($series in @(@('data','Part_','bi4'),@('particles','PartFluid_','vtk'))) {
    $dir = Join-Path $OutputDirectory $series[0]
    $files = @(Get-ChildItem -LiteralPath $dir -Filter ($series[1]+'*.'+$series[2]) -File | Sort-Object Name)
    if ($files.Count -ne $frames) { throw "Incomplete output series in $dir" }
    for ($i=0; $i -lt $frames; $i++) {
        $name = $series[1]+('{0:D4}' -f $i)+'.'+$series[2]
        if ($files[$i].Name -ne $name -or $files[$i].Length -le 0) { throw "Invalid output file $name" }
    }
}
Write-Output "Verified $frames native frames and $frames Fluid VTK files."
