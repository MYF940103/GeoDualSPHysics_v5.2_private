param([switch]$ExecutionAuthorized)
# Preserve the pre-compiler r1 failure; adopt unchanged snapshots and use slash-ended MSBuild paths.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Explicit build authorization required'}
$testPath=Split-Path -Parent $PSScriptRoot
$repoPath=(Get-Item -LiteralPath $testPath).Parent.Parent.Parent.Parent.FullName
$srcPath=Join-Path $repoPath 'src'
$tag='upl_case02_cpu_DebugCPU_r2'
$outPath=Join-Path $testPath "outputs\$tag"
$snapshotPath=Join-Path $testPath "outputs\${tag}_source"
$intPath=Join-Path $srcPath "VS\Intermediate\$tag"
$logPath=Join-Path $testPath "logs\$tag.log"
$binlogPath=Join-Path $testPath "logs\$tag.binlog"
$recordPath=Join-Path $testPath "logs\$tag.build.json"
$priorPath=Join-Path $testPath 'logs\upl_case02_cpu_DebugCPU_r1.build.json'
foreach($path in @($outPath,$snapshotPath,$intPath,$logPath,$binlogPath,$recordPath)){
  if(Test-Path -LiteralPath $path){throw "Preserve retained build: $path"}
}
function Entry([string]$path){
  $file=Get-Item -LiteralPath $path
  [ordered]@{path=$file.FullName;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Verify($entries){
  foreach($entry in $entries){$actual=Entry $entry.path;if($actual.bytes -ne $entry.bytes -or $actual.sha256 -cne $entry.sha256){throw "Changed input: $($entry.path)"}}
}
$prior=Get-Content -LiteralPath $priorPath -Raw | ConvertFrom-Json
if($prior.passed -ne $false -or $prior.exit_code -ne 1 -or $prior.program -or @($prior.objects).Count -ne 0 -or
  !(Select-String -LiteralPath $prior.log.path -Pattern 'MSB1008' -Quiet)){
  throw 'Expected sealed pre-compiler r1 parameter failure'
}
Verify $prior.tools;Verify $prior.canonical_programs_before;Verify @($prior.log)
$tools=@($prior.tools)+@(Entry $PSCommandPath;Entry $priorPath)
New-Item -ItemType Directory -Path $outPath,$snapshotPath | Out-Null
$targetPath=Join-Path $srcPath 'source\JSphCpu.cpp'
$sourcePairs=@()
foreach($pair in $prior.source_snapshot){
  Verify @($pair.snapshot)
  if($pair.original.path -ieq $targetPath){
    $original=Entry $targetPath
    $copyPath=Join-Path $snapshotPath 'JSphCpu.cpp'
    Copy-Item -LiteralPath $targetPath -Destination $copyPath
    $copy=Entry $copyPath
    if($original.sha256 -cne $copy.sha256 -or $original.bytes -ne $copy.bytes){throw 'Updated CPU source snapshot mismatch'}
    $sourcePairs+=@{original=$original;snapshot=$copy}
  }else{Verify @($pair.original);$sourcePairs+=@{original=$pair.original;snapshot=$pair.snapshot}}
}
$compileSources=@($prior.compile_sources | ForEach-Object {if($_.path -ieq $targetPath){Entry $targetPath}else{Verify @($_);$_}})
if($compileSources.Count -ne 86 -or @($sourcePairs|Where-Object {$_.original.path -ieq $targetPath}).Count -ne 1){throw 'CPU source inventory mismatch'}
$msbuild=$prior.tools[0].path
$arguments=@($prior.arguments[0],'/m','/t:Build','/p:Configuration=DebugCPU','/p:Platform=x64',
  "/p:OutDir=$outPath/", "/p:IntDir=$intPath/",'/v:minimal',"/bl:$binlogPath")
$started=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$oldPreference=$ErrorActionPreference
try{Push-Location $srcPath;$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;
  & $msbuild @arguments 2>&1 | Tee-Object -FilePath $logPath | Out-Host;$code=$LASTEXITCODE
}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$unchanged=$true
try{Verify $prior.canonical_programs_before;Verify $tools;foreach($pair in $sourcePairs){Verify @($pair.original,$pair.snapshot)}}catch{$unchanged=$false;$failure=$_.Exception.Message}
$programPath=Join-Path $outPath 'DualSPHysics5.2CPU_win64_debug.exe'
$program=if(Test-Path -LiteralPath $programPath){Entry $programPath}else{$null}
$objects=@(Get-ChildItem -LiteralPath $intPath -Filter '*.obj' -File -ErrorAction SilentlyContinue | ForEach-Object {Entry $_.FullName})
$passed=($code -is [int] -and $code -eq 0 -and $unchanged -and $null -ne $program -and $objects.Count -eq 86)
$result=[ordered]@{stage='upl_case02_cpu_build_r2';passed=$passed;configuration='DebugCPU';platform='x64';
  default_CPU_solution_build_with_isolated_outputs=$true;program=$program;arguments=$arguments;working_directory=$srcPath;
  adopted_failed_r1_record=(Entry $priorPath);updated_source='JSphCpu.cpp predictor uses valid PosPrec, not unfilled Posc';
  started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;
  typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;
  tools=$tools;compile_sources=$compileSources;source_snapshot=$sourcePairs;objects=$objects;
  canonical_programs_before=$prior.canonical_programs_before;canonical_programs_unchanged=$unchanged;log=(Entry $logPath);
  binlog=$(if(Test-Path -LiteralPath $binlogPath){Entry $binlogPath}else{$null});solver_started=$false;
  canonical_program_installed=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($recordPath,($result|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "CPU Debug build failed; inspect $recordPath"}
Write-Output "CPU Debug build passed: $recordPath"
