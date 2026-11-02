param([switch]$ExecutionAuthorized)
# One authoritative isolated ReleaseCPU Build only. No helper, help, solver or installation.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Root full recipe review and explicit ReleaseCPU build-only authorization required'}
$testPath=Split-Path -Parent $PSScriptRoot
$repoPath=(Get-Item -LiteralPath $testPath).Parent.Parent.Parent.Parent.FullName
$srcPath=Join-Path $repoPath 'src';$tag='upl_column_public_ReleaseCPU_r1'
$outPath=Join-Path $testPath "outputs\$tag";$intPath=Join-Path $srcPath "VS\Intermediate\$tag"
$logPath=Join-Path $testPath "logs\$tag.log";$binlogPath=Join-Path $testPath "logs\$tag.binlog"
$recordPath=Join-Path $testPath "logs\$tag.build.json"
$debugPath=Join-Path $testPath 'logs\upl_column_public_default_DebugCPU_r1.build.json'
$notePath=Join-Path $testPath 'notes\upl_column_public_cpu_release_r1.json'
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function Fresh($paths){foreach($path in $paths){if(Test-Path -LiteralPath $path){throw "Retained build path protected: $path"}}}
Fresh @($outPath,$intPath,$logPath,$binlogPath,$recordPath)
$debugIdentity=Entry $debugPath
$debug=[IO.File]::ReadAllText($debugPath)|ConvertFrom-Json
if(!$debug.passed -or $debug.stage -cne 'upl_column_public_default_cpu_r1' -or $debug.configuration -cne 'DebugCPU' -or $debug.platform -cne 'x64' -or !$debug.default_CPU_solution_build_with_isolated_outputs -or !$debug.direct_native_call -or !$debug.typed_LASTEXITCODE_captured_immediately -or !$debug.owned_call_exited -or $debug.exit_code -ne 0 -or !$debug.canonical_programs_unchanged -or $debug.solver_started -ne $false -or $debug.canonical_program_installed -ne $false -or @($debug.source_snapshot).Count -ne 265 -or @($debug.compile_sources).Count -ne 86 -or @($debug.objects).Count -ne 86 -or @($debug.canonical_programs_before).Count -ne 7){throw 'Passed actual isolated DebugCPU r2 build with265 source pairs/86 units/seven protected programs required'}
$msbuild=$debug.tools[0];$solution=$debug.tools[1];$project=$debug.tools[2]
if([IO.Path]::GetFileName($msbuild.path) -ine 'MSBuild.exe' -or $solution.path -ine (Join-Path $srcPath 'VS\DualSPHysics5ReCpu_vs2022.sln') -or $project.path -ine (Join-Path $srcPath 'VS\DualSPHysics5ReCpu.vcxproj')){throw 'The authoritative VS2022 CPU solution/project and recorded MSBuild are required'}
$authors=@(Entry $PSCommandPath;Entry $notePath)
$tools=@($msbuild,$solution,$project)+$authors
$sourcePairs=@($debug.source_snapshot);$compileSources=@($debug.compile_sources);$canonical=@($debug.canonical_programs_before)
# ReleaseCPU's only project PostBuild command conditionally moves this old generated header.
# Refuse an existing source instead of modifying the authoritative event or moving retained data.
$postBuildHeaderPaths=@((Join-Path $srcPath 'VS\cg_variables.h'),(Join-Path $srcPath 'cg_variables.h'))
function VerifySources{
  Verify @($debugIdentity,$debug.program,$debug.log,$debug.binlog,$debug.documentation_snapshot.original,$debug.documentation_snapshot.snapshot);Verify $debug.runtime_before;Verify $tools;Verify $compileSources
  foreach($pair in $sourcePairs){Verify @($pair.original,$pair.snapshot);if($pair.original.bytes -ne $pair.snapshot.bytes -or $pair.original.sha256 -ine $pair.snapshot.sha256){throw 'Adopted current/snapshot bytes differ'}}
  $current=@(Get-ChildItem -LiteralPath (Join-Path $srcPath 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|ForEach-Object{$_.FullName})
  if($current.Count -ne 265 -or @(Compare-Object ($current|Sort-Object) (@($sourcePairs|ForEach-Object{$_.original.path})|Sort-Object)).Count){throw 'Current265 C++/CUDA code/header membership changed'}
  foreach($path in $postBuildHeaderPaths){if(Test-Path -LiteralPath $path){throw "Conditional project PostBuild header present; stop for root review: $path"}}
}
VerifySources;Verify $canonical
[xml]$projectXml=[IO.File]::ReadAllText($project.path)
$releaseCondition="'`$(Configuration)|`$(Platform)'=='ReleaseCPU|x64'";$releaseSources=@()
foreach($node in $projectXml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
  $excluded=$false
  foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -ceq $releaseCondition){$excluded=($e.InnerText.Trim() -ceq 'true')}}
  if(!$excluded){$releaseSources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project.path) $node.GetAttribute('Include')))}
}
$expectedNames=@($compileSources|ForEach-Object{[IO.Path]::GetFileNameWithoutExtension($_.path)+'.obj'})
if($releaseSources.Count -ne 86 -or @($expectedNames|Sort-Object -Unique).Count -ne 86 -or @($expectedNames|Where-Object{$_ -ieq 'main.obj'}).Count -ne 1 -or @(Compare-Object ($releaseSources|Sort-Object) ($compileSources.path|Sort-Object)).Count){throw 'ReleaseCPU authoritative86 translation units differ from the accepted common CPU source set'}
# A forward-slash-terminated native property avoids the prior space/backslash quoting failure.
$outNative=$outPath.Replace('\','/')+'/';$intNative=$intPath.Replace('\','/')+'/'
$arguments=@($solution.path,'/m','/t:Build','/p:Configuration=ReleaseCPU','/p:Platform=x64',"/p:OutDir=$outNative","/p:IntDir=$intNative",'/v:minimal',"/bl:$binlogPath")
[void](New-Item -ItemType Directory -Path $outPath)
[IO.File]::WriteAllBytes($logPath,[byte[]]@())
$started=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$oldPreference=$ErrorActionPreference
Push-Location $srcPath
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $msbuild.path @arguments 2>&1|Tee-Object -FilePath $logPath -Append|Out-Host;$code=$LASTEXITCODE}
catch{$failure=$_.Exception.Message}
finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$ended=[DateTime]::UtcNow.ToString('o');$sourceUnchanged=$true;$canonicalUnchanged=$true;$postcheckFailures=@()
try{VerifySources}catch{$sourceUnchanged=$false;$postcheckFailures+=@($_.Exception.Message)}
try{Verify $canonical}catch{$canonicalUnchanged=$false;$postcheckFailures+=@($_.Exception.Message)}
$programPath=Join-Path $outPath 'DualSPHysics5.2CPU_win64.exe'
$program=if(Test-Path -LiteralPath $programPath){Entry $programPath}else{$null}
$objects=@(Get-ChildItem -LiteralPath $intPath -File -Filter '*.obj' -ErrorAction SilentlyContinue|Sort-Object Name|ForEach-Object{Entry $_.FullName})
$actualNames=@($objects|ForEach-Object{[IO.Path]::GetFileName($_.path)})
$objectClosure=($objects.Count -eq 86 -and @($actualNames|Sort-Object -Unique).Count -eq 86 -and @(Compare-Object ($actualNames|Sort-Object) ($expectedNames|Sort-Object)).Count -eq 0)
$binlog=if(Test-Path -LiteralPath $binlogPath){Entry $binlogPath}else{$null}
$passed=($code -is [int] -and $code -eq 0 -and $null -eq $failure -and $sourceUnchanged -and $canonicalUnchanged -and $null -ne $program -and $null -ne $binlog -and $objectClosure)
$result=[ordered]@{stage='upl_column_public_cpu_release_r1';passed=$passed;configuration='ReleaseCPU';platform='x64';default_CPU_solution_build_with_isolated_outputs=$true;adopted_Debug_source_build=$debugIdentity;build_tool=$msbuild;program=$program;arguments=$arguments;working_directory=$srcPath;isolated_OutDir=$outPath;fresh_IntDir=$intPath;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;postcheck_failures=$postcheckFailures;tools=$tools;author_files=$authors;compile_sources=$compileSources;source_snapshot=$sourcePairs;source_code_header_count=265;source_bindings_unchanged=$sourceUnchanged;new_source_snapshots_copied=0;objects=$objects;active_CPU_translation_units=86;non_main_CPU_objects=85;exact_object_basename_closure=$objectClosure;old_Debug_objects_reused=$false;canonical_programs_before=$canonical;canonical_program_count=7;canonical_programs_unchanged=$canonicalUnchanged;conditional_postbuild_header_paths_checked=$postBuildHeaderPaths;log=(Entry $logPath);binlog=$binlog;helper_built=$false;help_invoked=$false;solver_started=$false;canonical_program_installed=$false;runtime_prepared_by_this_script=$false;physical_acceptance=$false}
Fresh @($recordPath)
[IO.File]::WriteAllText($recordPath,($result|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "ReleaseCPU build failed; retain partial artifacts and inspect $recordPath"}
Write-Output "ReleaseCPU isolated build passed; no program run: $recordPath"
