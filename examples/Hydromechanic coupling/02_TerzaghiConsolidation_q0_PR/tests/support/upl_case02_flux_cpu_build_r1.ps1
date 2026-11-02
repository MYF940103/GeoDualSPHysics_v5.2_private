param([Parameter(Mandatory=$true)][ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration)
# Root-reviewed candidate build only; one authoritative CPU solution invocation, never a program run.
$ErrorActionPreference='Stop';$Configuration=if($Configuration -ieq 'DebugCPU'){'DebugCPU'}else{'ReleaseCPU'}
$testPath=Split-Path -Parent $PSScriptRoot;$repoPath=(Get-Item -LiteralPath $testPath).Parent.Parent.Parent.Parent.FullName;$srcPath=Join-Path $repoPath 'src'
$tag="upl_case02_flux_cpu_${Configuration}_r1";$outPath=Join-Path $testPath "outputs\$tag";$snapshotPath=Join-Path $testPath "outputs\${tag}_source";$intPath=Join-Path $srcPath "VS\Intermediate\$tag"
$logPath=Join-Path $testPath "logs\$tag.log";$binlogPath=Join-Path $testPath "logs\$tag.binlog";$recordPath=Join-Path $testPath "logs\$tag.build.json"
$baselineTag=if($Configuration -ceq 'DebugCPU'){'upl_case02_cpu_DebugCPU_r2'}else{'upl_case02_cpu_ReleaseCPU_r1'};$baselinePath=Join-Path $testPath "logs\$baselineTag.build.json"
$notePath=Join-Path $testPath 'notes\upl_case02_flux_cpu_build_r1.json';$targetPath=Join-Path $srcPath 'source\JSphCpu.cpp';$docPath=Join-Path $repoPath 'doc\xml_format\_FmtXML_ElastoplasticSoil.xml'
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function Fresh($paths){foreach($path in $paths){if(Test-Path -LiteralPath $path){throw "Retained build path protected: $path"}}}
Fresh @($outPath,$snapshotPath,$intPath,$logPath,$binlogPath,$recordPath)
$baselineIdentity=Entry $baselinePath;$known=if($Configuration -ceq 'DebugCPU'){@{bytes=340628;sha256='928527205bcdee13c49d0317ef4f1ff186f6fb6e480145a405d61f2ebe6bb5db'}}else{@{bytes=342696;sha256='85e754287a4057598c11e63e0d326e28dee16efb87624ca1bd7ceeed9c3ab09e'}}
if($baselineIdentity.bytes -ne $known.bytes -or $baselineIdentity.sha256 -ine $known.sha256){throw 'Reviewed prechange configuration build identity differs'}
$b=[IO.File]::ReadAllText($baselinePath)|ConvertFrom-Json
if(!$b.passed -or $b.configuration -cne $Configuration -or $b.platform -cne 'x64' -or !$b.default_CPU_solution_build_with_isolated_outputs -or !$b.direct_native_call -or !$b.typed_LASTEXITCODE_captured_immediately -or !$b.owned_call_exited -or $b.exit_code -ne 0 -or !$b.canonical_programs_unchanged -or $b.solver_started -ne $false -or $b.canonical_program_installed -ne $false -or @($b.source_snapshot).Count -ne 265 -or @($b.compile_sources).Count -ne 86 -or @($b.objects).Count -ne 86 -or @($b.canonical_programs_before).Count -ne 7){throw 'Passed actual prechange build with265 source pairs/86 units/seven protected programs required'}
$msbuild=$b.tools[0];$solution=$b.tools[1];$project=$b.tools[2]
if([IO.Path]::GetFileName($msbuild.path) -ine 'MSBuild.exe' -or $solution.path -ine (Join-Path $srcPath 'VS\DualSPHysics5ReCpu_vs2022.sln') -or $project.path -ine (Join-Path $srcPath 'VS\DualSPHysics5ReCpu.vcxproj')){throw 'Authoritative VS2022 CPU solution/project and recorded MSBuild required'}
$authors=@(Entry $PSCommandPath;Entry $notePath);$tools=@($msbuild,$solution,$project)+$authors;$canonical=@($b.canonical_programs_before)
Verify @($baselineIdentity,$b.program,$b.log,$b.binlog);Verify $tools;Verify $canonical
$current=@(Get-ChildItem -LiteralPath (Join-Path $srcPath 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|Sort-Object Name|ForEach-Object{Entry $_.FullName})
if($current.Count -ne 265 -or @(Compare-Object ($current.path|Sort-Object) (@($b.source_snapshot|ForEach-Object{$_.original.path})|Sort-Object)).Count){throw 'Current265 code/header membership differs from the prechange build'}
$currentByPath=@{};foreach($e in $current){if($currentByPath.ContainsKey($e.path)){throw 'Duplicate current source path'};$currentByPath[$e.path]=$e}
$oldCpu=$null;$unchangedCode=0
foreach($pair in $b.source_snapshot){
  Verify @($pair.snapshot);if($pair.original.bytes -ne $pair.snapshot.bytes -or $pair.original.sha256 -ine $pair.snapshot.sha256){throw 'Retained prechange source/snapshot pair differs'}
  if($pair.original.path -ieq $targetPath){if($oldCpu){throw 'Duplicate baseline CPU entry'};$oldCpu=$pair.original}else{Verify @($pair.original);$unchangedCode++}
}
if(!$oldCpu -or $unchangedCode -ne 264 -or $oldCpu.bytes -ne 264709 -or $oldCpu.sha256 -ine '3fed0edf70aff9735a498c26edc921dd8436deb76f03afc11f43e213d5c9a08e'){throw 'Only the retained3fed CPU source may differ;264 other code files must be unchanged'}
$newCpu=$currentByPath[$targetPath];if($newCpu.sha256 -ieq $oldCpu.sha256){throw 'Expected the root-reviewed CPU candidate, not the unchanged prechange source'}
$compileSources=@($b.compile_sources|ForEach-Object{$e=$currentByPath[$_.path];if(!$e){throw 'Compile source outside current265 inventory'};$e})
[xml]$projectXml=[IO.File]::ReadAllText($project.path);$condition="'`$(Configuration)|`$(Platform)'=='${Configuration}|x64'";$activeSources=@()
foreach($node in $projectXml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
  $excluded=$false;foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -ceq $condition){$excluded=($e.InnerText.Trim() -ceq 'true')}}
  if(!$excluded){$activeSources+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project.path) $node.GetAttribute('Include')))}
}
$expectedNames=@($compileSources|ForEach-Object{[IO.Path]::GetFileNameWithoutExtension($_.path)+'.obj'})
if($activeSources.Count -ne 86 -or @($expectedNames|Sort-Object -Unique).Count -ne 86 -or @($expectedNames|Where-Object{$_ -ieq 'main.obj'}).Count -ne 1 -or @(Compare-Object ($activeSources|Sort-Object) ($compileSources.path|Sort-Object)).Count){throw 'Authoritative selected CPU configuration must compile the exact86 common units'}
# Refuse the source of the project's conditional header-move event, without changing that event.
$postBuildHeaderPaths=@((Join-Path $srcPath 'VS\cg_variables.h'),(Join-Path $srcPath 'cg_variables.h'))
foreach($path in $postBuildHeaderPaths){if(Test-Path -LiteralPath $path){throw "Conditional project PostBuild header present: $path"}}
$doc=Entry $docPath;[void](New-Item -ItemType Directory -Path $outPath,$snapshotPath);$sourcePairs=@()
foreach($e in $current){$dest=Join-Path $snapshotPath ([IO.Path]::GetFileName($e.path));Fresh @($dest);Copy-Item -LiteralPath $e.path -Destination $dest;$copy=Entry $dest;if($copy.bytes -ne $e.bytes -or $copy.sha256 -ine $e.sha256){throw 'New source snapshot mismatch'};$sourcePairs+=@{original=$e;snapshot=$copy}}
$docCopyPath=Join-Path $snapshotPath '_FmtXML_ElastoplasticSoil.xml';Fresh @($docCopyPath);Copy-Item -LiteralPath $docPath -Destination $docCopyPath;$documentation=@{original=$doc;snapshot=(Entry $docCopyPath)}
if($documentation.original.bytes -ne $documentation.snapshot.bytes -or $documentation.original.sha256 -ine $documentation.snapshot.sha256){throw 'Documentation snapshot mismatch'}
function VerifySources{
  Verify @($baselineIdentity,$b.program,$b.log,$b.binlog);Verify $tools;Verify $compileSources
  foreach($pair in $sourcePairs){Verify @($pair.original,$pair.snapshot)};Verify @($documentation.original,$documentation.snapshot)
  foreach($pair in $b.source_snapshot){Verify @($pair.snapshot);if($pair.original.path -ine $targetPath){Verify @($pair.original)}}
  $paths=@(Get-ChildItem -LiteralPath (Join-Path $srcPath 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|ForEach-Object{$_.FullName})
  if($paths.Count -ne 265 -or @(Compare-Object ($paths|Sort-Object) ($current.path|Sort-Object)).Count){throw 'Current265 source/header membership changed during build'}
  foreach($path in $postBuildHeaderPaths){if(Test-Path -LiteralPath $path){throw "Conditional project PostBuild header present: $path"}}
}
VerifySources;Verify $canonical
$outNative=$outPath.Replace('\','/')+'/';$intNative=$intPath.Replace('\','/')+'/'
$arguments=@($solution.path,'/m','/t:Build',"/p:Configuration=$Configuration",'/p:Platform=x64',"/p:OutDir=$outNative","/p:IntDir=$intNative",'/v:minimal',"/bl:$binlogPath")
[IO.File]::WriteAllBytes($logPath,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$oldPreference=$ErrorActionPreference
Push-Location $srcPath
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $msbuild.path @arguments 2>&1|Tee-Object -FilePath $logPath -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$ended=[DateTime]::UtcNow.ToString('o');$sourceUnchanged=$true;$canonicalUnchanged=$true;$postcheckFailures=@()
try{VerifySources}catch{$sourceUnchanged=$false;$postcheckFailures+=@($_.Exception.Message)}
try{Verify $canonical}catch{$canonicalUnchanged=$false;$postcheckFailures+=@($_.Exception.Message)}
$programName=if($Configuration -ceq 'DebugCPU'){'DualSPHysics5.2CPU_win64_debug.exe'}else{'DualSPHysics5.2CPU_win64.exe'};$programPath=Join-Path $outPath $programName
$program=if(Test-Path -LiteralPath $programPath){Entry $programPath}else{$null}
$objects=@(Get-ChildItem -LiteralPath $intPath -File -Filter '*.obj' -ErrorAction SilentlyContinue|Sort-Object Name|ForEach-Object{Entry $_.FullName});$actualNames=@($objects|ForEach-Object{[IO.Path]::GetFileName($_.path)})
$objectClosure=($objects.Count -eq 86 -and @($actualNames|Sort-Object -Unique).Count -eq 86 -and @(Compare-Object ($actualNames|Sort-Object) ($expectedNames|Sort-Object)).Count -eq 0)
$binlog=if(Test-Path -LiteralPath $binlogPath){Entry $binlogPath}else{$null};$passed=($code -is [int] -and $code -eq 0 -and $null -eq $failure -and $sourceUnchanged -and $canonicalUnchanged -and $null -ne $program -and $null -ne $binlog -and $objectClosure)
$result=[ordered]@{stage='upl_case02_flux_cpu_build_r1';passed=$passed;configuration=$Configuration;platform='x64';label='r1';default_CPU_solution_build_with_isolated_outputs=$true;prechange_source_build=$baselineIdentity;allowed_changed_code_path=$targetPath;unchanged_prechange_code_files=264;candidate_CPU_source=@{before=$oldCpu;after=$newCpu};documentation_snapshot=$documentation;build_tool=$msbuild;program=$program;arguments=$arguments;working_directory=$srcPath;isolated_OutDir=$outPath;fresh_IntDir=$intPath;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;failure=$failure;postcheck_failures=$postcheckFailures;tools=$tools;author_files=$authors;compile_sources=$compileSources;source_snapshot=$sourcePairs;source_code_header_count=265;source_bindings_unchanged=$sourceUnchanged;new_source_snapshots_copied=265;objects=$objects;active_CPU_translation_units=86;non_main_CPU_objects=85;exact_object_basename_closure=$objectClosure;old_objects_reused=$false;canonical_programs_before=$canonical;canonical_program_count=7;canonical_programs_unchanged=$canonicalUnchanged;conditional_postbuild_header_paths_checked=$postBuildHeaderPaths;log=(Entry $logPath);binlog=$binlog;helper_built=$false;help_invoked=$false;solver_started=$false;canonical_program_installed=$false;runtime_prepared_by_this_script=$false;physical_acceptance=$false}
Fresh @($recordPath);[IO.File]::WriteAllText($recordPath,($result|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw "Candidate CPU build failed; retain partial artifacts and inspect $recordPath"}
Write-Output "Candidate CPU isolated build passed; no program run: $recordPath"
