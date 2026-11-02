param([switch]$ExecutionAuthorized)
# One isolated default CPU Debug build only; no solver or canonical installation.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Explicit build authorization required'}
$testPath=Split-Path -Parent $PSScriptRoot
$repoPath=(Get-Item -LiteralPath $testPath).Parent.Parent.Parent.Parent.FullName
$srcPath=Join-Path $repoPath 'src'
$tag='upl_case02_cpu_DebugCPU_r1'
$outPath=Join-Path $testPath "outputs\$tag"
$snapshotPath=Join-Path $testPath "outputs\${tag}_source"
$intPath=Join-Path $srcPath "VS\Intermediate\$tag"
$logPath=Join-Path $testPath "logs\$tag.log"
$binlogPath=Join-Path $testPath "logs\$tag.binlog"
$recordPath=Join-Path $testPath "logs\$tag.build.json"
$msbuild='D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe'
$solution=Join-Path $srcPath 'VS\DualSPHysics5ReCpu_vs2022.sln'
$project=Join-Path $srcPath 'VS\DualSPHysics5ReCpu.vcxproj'
foreach($freshPath in @($outPath,$snapshotPath,$intPath,$logPath,$binlogPath,$recordPath)){
  if(Test-Path -LiteralPath $freshPath){throw "Preserve existing build artifact: $freshPath"}
}
function Entry([string]$path){
  $file=Get-Item -LiteralPath $path
  [ordered]@{path=$file.FullName;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Verify($entries){
  foreach($entry in $entries){
    $actual=Entry $entry.path
    if($actual.bytes -ne $entry.bytes -or $actual.sha256 -cne $entry.sha256){throw "Build input changed: $($entry.path)"}
  }
}
$protected=@(Get-ChildItem -LiteralPath (Join-Path $repoPath 'bin\windows') -File |
  Where-Object {$_.Name -match '^DualSPHysics.*\.exe$'} | ForEach-Object {Entry $_.FullName})
$tools=@(Entry $msbuild;Entry $solution;Entry $project;Entry $PSCommandPath)
[xml]$projectXml=Get-Content -LiteralPath $project -Raw
$compileSources=@()
foreach($node in $projectXml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
  $excluded=$false
  foreach($condition in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){
    if(!$condition.GetAttribute('Condition') -or $condition.GetAttribute('Condition') -ceq "'`$(Configuration)|`$(Platform)'=='DebugCPU|x64'"){
      $excluded=$condition.InnerText.Trim() -ceq 'true'
    }
  }
  if(!$excluded){$compileSources+=Entry ([IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project) $node.GetAttribute('Include'))))}
}
if($compileSources.Count -ne 86){throw 'Authoritative CPU compile inventory changed'}
New-Item -ItemType Directory -Path $outPath,$snapshotPath | Out-Null
$sourcePairs=@()
foreach($file in (Get-ChildItem -LiteralPath (Join-Path $srcPath 'source') -File -Recurse | Where-Object {$_.Extension -in '.cpp','.h','.cu','.cuh'})){
  $relative=$file.FullName.Substring((Join-Path $srcPath 'source').Length+1)
  $copyPath=Join-Path $snapshotPath $relative
  $copyParent=Split-Path -Parent $copyPath
  if(!(Test-Path -LiteralPath $copyParent)){New-Item -ItemType Directory -Path $copyParent | Out-Null}
  $original=Entry $file.FullName
  Copy-Item -LiteralPath $file.FullName -Destination $copyPath
  $copy=Entry $copyPath
  if($original.bytes -ne $copy.bytes -or $original.sha256 -cne $copy.sha256){throw 'Source snapshot differs'}
  $sourcePairs+=@{original=$original;snapshot=$copy}
}
$arguments=@($solution,'/m','/t:Build','/p:Configuration=DebugCPU','/p:Platform=x64',
  "/p:OutDir=$outPath\", "/p:IntDir=$intPath\",'/v:minimal',"/bl:$binlogPath")
$started=[DateTime]::UtcNow.ToString('o')
$code=$null;$failure=$null;$oldPreference=$ErrorActionPreference
try{
  Push-Location $srcPath
  $ErrorActionPreference='Continue'
  $global:LASTEXITCODE=$null
  & $msbuild @arguments 2>&1 | Tee-Object -FilePath $logPath | Out-Host
  $code=$LASTEXITCODE
}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$unchanged=$true
try{Verify $protected;Verify $tools;foreach($pair in $sourcePairs){Verify @($pair.original,$pair.snapshot)}}catch{$unchanged=$false;$failure=$_.Exception.Message}
$programPath=Join-Path $outPath 'DualSPHysics5.2CPU_win64_debug.exe'
$objects=@(Get-ChildItem -LiteralPath $intPath -Filter '*.obj' -File -ErrorAction SilentlyContinue | ForEach-Object {Entry $_.FullName})
$program=if(Test-Path -LiteralPath $programPath){Entry $programPath}else{$null}
$passed=($code -is [int] -and $code -eq 0 -and $unchanged -and $null -ne $program -and $objects.Count -eq 86)
$result=[ordered]@{stage='upl_case02_cpu_build_r1';passed=$passed;configuration='DebugCPU';platform='x64';
  default_CPU_solution_build_with_isolated_outputs=$true;program=$program;arguments=$arguments;working_directory=$srcPath;
  started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;
  typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;
  tools=$tools;compile_sources=$compileSources;source_snapshot=$sourcePairs;objects=$objects;
  canonical_programs_before=$protected;canonical_programs_unchanged=$unchanged;log=(Entry $logPath);
  binlog=$(if(Test-Path -LiteralPath $binlogPath){Entry $binlogPath}else{$null});
  solver_started=$false;canonical_program_installed=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($recordPath,($result|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "CPU Debug build did not pass; inspect $recordPath"}
Write-Output "CPU Debug build passed: $recordPath"
