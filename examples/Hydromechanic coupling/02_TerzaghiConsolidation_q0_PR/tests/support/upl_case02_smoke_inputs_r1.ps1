param([switch]$PrepareAuthorized)
# Mechanical clone of a retained GenCase seed; prepares no formal input and starts no program.
$ErrorActionPreference='Stop'
if(!$PrepareAuthorized){throw 'Explicit input preparation required'}
$testPath=Split-Path -Parent $PSScriptRoot
$sourcePrefix=Join-Path $testPath 'outputs\symc_1d_short_r1_cpu_old\symc_1d_short_r1_cpu_old'
$targetPath=Join-Path $testPath 'outputs\upl_case02_smoke_r1_seed'
$configPath=Join-Path $testPath 'configs\upl_case02_smoke_r1.xml'
$recordPath=Join-Path $testPath 'logs\upl_case02_smoke_r1.inputs.json'
$targetPrefix=Join-Path $targetPath 'upl_case02_smoke_r1'
foreach($path in @($targetPath,$configPath,$recordPath)){if(Test-Path -LiteralPath $path){throw "Preserve retained input: $path"}}
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
$expected=@{
  '.xml'='06ea556c3555ad86d53491984897120119596bc90f209c0545196a4f3beced9c';
  '.bi4'='f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac';
  '_Normals.nbi4'='0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97'
}
$sources=@()
foreach($suffix in $expected.Keys){$item=Entry ($sourcePrefix+$suffix);if($item.sha256 -cne $expected[$suffix]){throw "Seed changed: $suffix"};$sources+=@($item)}
$xml=New-Object Xml.XmlDocument
$xml.PreserveWhitespace=$true
$xml.Load($sourcePrefix+'.xml')
$changes=@()
function SetParameter([string]$key,[string]$value){
  $nodes=$xml.SelectNodes("/case/execution/parameters/parameter[@key='$key']")
  if($nodes.Count -ne 1){throw "Expected one existing parameter: $key"}
  $old=$nodes[0].GetAttribute('value');$nodes[0].SetAttribute('value',$value)
  [ordered]@{key=$key;old=$old;value=$value}
}
$values=[ordered]@{SlipMode='3';Visco='0';SoilHourglassXi='0';SoilBoundaryDerivativeSPR='0';SoilDamping='0';DtIni='0.0000025';DtFixed='0.0000025';TimeMax='0.000005';TimeOut='0.0000025'}
foreach($key in $values.Keys){$changes+=@(SetParameter $key $values[$key])}
$hydro=$xml.SelectSingleNode('/case/execution/special/hydromechanics')
foreach($key in @('HydroMechDynamicSeepage','HydroMechConductivityModel','HydroMechConductivityCk','PoreDarcySymmetricCorr')){
  if($hydro.SelectNodes($key).Count){throw "Seed unexpectedly already declares $key"}
  $element=$xml.CreateElement($key);$element.SetAttribute('value','0');$element.SetAttribute('comment','Explicit public default; private case02 wrapper activates the complete model')
  [void]$hydro.AppendChild($xml.CreateWhitespace('                '));[void]$hydro.AppendChild($element);[void]$hydro.AppendChild($xml.CreateWhitespace("`r`n"))
}
New-Item -ItemType Directory -Path $targetPath | Out-Null
$xml.Save($configPath)
Copy-Item -LiteralPath $configPath -Destination ($targetPrefix+'.xml')
foreach($suffix in @('.bi4','_Normals.nbi4')){
  Copy-Item -LiteralPath ($sourcePrefix+$suffix) -Destination ($targetPrefix+$suffix)
  if((Entry ($targetPrefix+$suffix)).sha256 -cne $expected[$suffix]){throw 'Copied native seed changed'}
}
$result=[ordered]@{stage='upl_case02_smoke_inputs_r1';prepared=$true;source_seed=$sources;script=(Entry $PSCommandPath);
  parameter_changes=$changes;configuration=(Entry $configPath);runtime=(Entry ($targetPrefix+'.xml'));
  initial_BI4=(Entry ($targetPrefix+'.bi4'));normals=(Entry ($targetPrefix+'_Normals.nbi4'));
  required_CLI=@('-cpu','-ompthreads:1','-mdbc_freeslip','-nsteps:2');dt_s=0.0000025;end_s=0.000005;steps=2;expected_frames=3;
  original_soil=1000;original_fixed=40;new_GenCase_run=$false;physical_fields_modified=$false;
  differences_from_formal='FreeSlip3; HG/SPR/artificial viscosity/soil damping OFF; private dynamic closure. This is not the accepted formal setting.';
  full_or_half_job_admitted=$false;solver_started=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($recordPath,($result|ConvertTo-Json -Depth 8)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "Prepared smoke input only: $recordPath"
