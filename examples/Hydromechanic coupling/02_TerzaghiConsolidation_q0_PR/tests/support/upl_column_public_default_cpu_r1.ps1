# Author-only until root review: one isolated default CPU Debug Build, never a solver/helper run.
$ErrorActionPreference='Stop';$Configuration='DebugCPU';$tag='upl_column_public_default_DebugCPU_r1'
$testPath=Split-Path -Parent $PSScriptRoot;$repoPath=(Get-Item -LiteralPath $testPath).Parent.Parent.Parent.Parent.FullName;$srcPath=Join-Path $repoPath 'src';$binPath=Join-Path $repoPath 'bin\windows'
$outPath=Join-Path $testPath "outputs\$tag";$snapshotPath=Join-Path $testPath "outputs\${tag}_source";$intPath=Join-Path $srcPath "VS\Intermediate\$tag"
$logPath=Join-Path $testPath "logs\$tag.log";$binlogPath=Join-Path $testPath "logs\$tag.binlog";$callPath=Join-Path $testPath "logs\$tag.msbuild.call.json";$recordPath=Join-Path $testPath "logs\$tag.build.json"
$recipePath=Join-Path $testPath 'logs\upl_case02_flux_cpu_DebugCPU_r1.build.json';$notePath=Join-Path $testPath 'notes\upl_column_public_default_cpu_r1.json';$docPath=Join-Path $repoPath 'doc\xml_format\_FmtXML_ElastoplasticSoil.xml'
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Captured artifact changed: $($r.path)"}}}
function Fresh($paths){foreach($path in $paths){if(Test-Path -LiteralPath $path){throw "Retained build path protected: $path"}}}
function WriteFresh([string]$path,$value){Fresh @($path);[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
$freshPaths=@($outPath,$snapshotPath,$intPath,$logPath,$binlogPath,$callPath,$recordPath);Fresh $freshPaths
$recipeIdentity=Entry $recipePath;$recipe=[IO.File]::ReadAllText($recipePath)|ConvertFrom-Json
if(!$recipe.passed -or $recipe.configuration -cne 'DebugCPU' -or $recipe.platform -cne 'x64' -or !$recipe.default_CPU_solution_build_with_isolated_outputs -or !$recipe.direct_native_call -or !$recipe.typed_LASTEXITCODE_captured_immediately -or !$recipe.owned_call_exited -or $recipe.exit_code -ne 0 -or !$recipe.canonical_programs_unchanged -or @($recipe.source_snapshot).Count -ne 265 -or @($recipe.compile_sources).Count -ne 86 -or @($recipe.objects).Count -ne 86 -or @($recipe.canonical_programs_before).Count -ne 7){throw 'Passed authoritative CPU Debug recipe with265 sources/86 units/seven protected programs required'}
$solutionPath=Join-Path $srcPath 'VS\DualSPHysics5ReCpu_vs2022.sln';$projectPath=Join-Path $srcPath 'VS\DualSPHysics5ReCpu.vcxproj'
if([IO.Path]::GetFileName($recipe.build_tool.path) -ine 'MSBuild.exe' -or $recipe.arguments[0] -ine $solutionPath -or $recipe.arguments -cnotcontains '/m' -or $recipe.arguments -cnotcontains '/t:Build' -or $recipe.arguments -cnotcontains '/p:Configuration=DebugCPU' -or $recipe.arguments -cnotcontains '/p:Platform=x64'){throw 'Reviewed authoritative DebugCPU MSBuild invocation required'}
# Historical recipe supplies identities of paths, not current source/tool/runtime hashes.
$msbuild=Entry $recipe.build_tool.path;$solution=Entry $solutionPath;$project=Entry $projectPath;$authors=@(Entry $PSCommandPath;Entry $notePath);$tools=@($msbuild,$solution,$project)+$authors
$canonicalNames=@('DualSPHysics4.0_LiquidGasCPU_win64.exe','DualSPHysics4.0_LiquidGas_win64.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2_win64.exe','DualSPHysics5.2_win64_debug.exe')
$canonical=@($canonicalNames|ForEach-Object{Entry (Join-Path $binPath $_)});$runtimeNames=@('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll');$runtime=@($runtimeNames|ForEach-Object{Entry (Join-Path $binPath $_)})
if(@(Compare-Object ($canonical.path|Sort-Object) ($recipe.canonical_programs_before.path|Sort-Object)).Count){throw 'Seven canonical protected paths differ from reviewed recipe'}
$current=@(Get-ChildItem -LiteralPath (Join-Path $srcPath 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|Sort-Object Name|ForEach-Object{Entry $_.FullName})
if($current.Count -ne 265 -or @(Compare-Object ($current.path|Sort-Object) (@($recipe.source_snapshot|ForEach-Object{$_.original.path})|Sort-Object)).Count){throw 'Current265 code/header path membership differs from authoritative recipe'}
$currentByPath=@{};foreach($e in $current){if($currentByPath.ContainsKey($e.path)){throw 'Duplicate current source path'};$currentByPath[$e.path]=$e}
[xml]$projectXml=[IO.File]::ReadAllText($project.path);$condition="'`$(Configuration)|`$(Platform)'=='DebugCPU|x64'";$activePaths=@()
foreach($node in $projectXml.SelectNodes("//*[local-name()='ClCompile'][@Include]")){
  $excluded=$false;foreach($e in $node.SelectNodes("*[local-name()='ExcludedFromBuild']")){if(!$e.GetAttribute('Condition') -or $e.GetAttribute('Condition') -ceq $condition){$excluded=($e.InnerText.Trim() -ceq 'true')}}
  if(!$excluded){$activePaths+=[IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $project.path) $node.GetAttribute('Include')))}
}
$compileSources=@($activePaths|ForEach-Object{$e=$currentByPath[$_];if(!$e){throw 'Active CPU source outside current265 inventory'};$e});$expectedNames=@($compileSources|ForEach-Object{[IO.Path]::GetFileNameWithoutExtension($_.path)+'.obj'})
if($activePaths.Count -ne 86 -or @($expectedNames|Sort-Object -Unique).Count -ne 86 -or @($expectedNames|Where-Object{$_ -ieq 'main.obj'}).Count -ne 1 -or @(Compare-Object ($activePaths|Sort-Object) ($recipe.compile_sources.path|Sort-Object)).Count){throw 'Authoritative CPU Debug project must compile the exact86 common units'}
$postBuildHeaderPaths=@((Join-Path $srcPath 'VS\cg_variables.h'),(Join-Path $srcPath 'cg_variables.h'));foreach($path in $postBuildHeaderPaths){if(Test-Path -LiteralPath $path){throw "Conditional project PostBuild header present: $path"}}
$doc=Entry $docPath;[void](New-Item -ItemType Directory -Path $outPath,$snapshotPath);$sourcePairs=@()
foreach($e in $current){$dest=Join-Path $snapshotPath ([IO.Path]::GetFileName($e.path));Fresh @($dest);Copy-Item -LiteralPath $e.path -Destination $dest;$copy=Entry $dest;if($copy.bytes -ne $e.bytes -or $copy.sha256 -ine $e.sha256){throw 'Current source snapshot mismatch'};$sourcePairs+=@{original=$e;snapshot=$copy}}
$docCopyPath=Join-Path $snapshotPath '_FmtXML_ElastoplasticSoil.xml';Fresh @($docCopyPath);Copy-Item -LiteralPath $docPath -Destination $docCopyPath;$documentation=@{original=$doc;snapshot=(Entry $docCopyPath)}
if($documentation.original.bytes -ne $documentation.snapshot.bytes -or $documentation.original.sha256 -ine $documentation.snapshot.sha256){throw 'Current documentation snapshot mismatch'}
function VerifySources{
  Verify @($recipeIdentity);Verify $tools;Verify $compileSources;foreach($pair in $sourcePairs){Verify @($pair.original,$pair.snapshot)};Verify @($documentation.original,$documentation.snapshot)
  $paths=@(Get-ChildItem -LiteralPath (Join-Path $srcPath 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|ForEach-Object{$_.FullName})
  if($paths.Count -ne 265 -or @(Compare-Object ($paths|Sort-Object) ($current.path|Sort-Object)).Count){throw 'Current265 source/header membership changed during build'}
  foreach($path in $postBuildHeaderPaths){if(Test-Path -LiteralPath $path){throw "Conditional project PostBuild header present: $path"}}
}
VerifySources;Verify $canonical;Verify $runtime
$outNative=$outPath.Replace('\','/')+'/';$intNative=$intPath.Replace('\','/')+'/'
$arguments=@($solution.path,'/m','/t:Build','/p:Configuration=DebugCPU','/p:Platform=x64',"/p:OutDir=$outNative","/p:IntDir=$intNative",'/v:minimal',"/bl:$binlogPath")
[IO.File]::WriteAllBytes($logPath,[byte[]]@());$started=[DateTime]::UtcNow.ToString('o');$nativeCode=$null;$failure=$null;$oldPreference=$ErrorActionPreference
Push-Location $srcPath
try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $msbuild.path @arguments 2>&1|Tee-Object -FilePath $logPath -Append|Out-Host;$nativeCode=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
$ended=[DateTime]::UtcNow.ToString('o')
# Seal the owned typed exit before hashing program/log/binlog/object outputs or checking bindings.
$call=[ordered]@{stage='upl_column_public_default_cpu_r1.msbuild';program=$msbuild;arguments=$arguments;working_directory=$srcPath;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($nativeCode -is [int]);owned_call_exited=($nativeCode -is [int]);exit_code=$nativeCode;invocation_failure=$failure};WriteFresh $callPath $call
$sourceUnchanged=$true;$canonicalUnchanged=$true;$runtimeUnchanged=$true;$postcheckFailures=@()
try{VerifySources}catch{$sourceUnchanged=$false;$postcheckFailures+=@($_.Exception.Message)}
try{Verify $canonical}catch{$canonicalUnchanged=$false;$postcheckFailures+=@($_.Exception.Message)}
try{Verify $runtime}catch{$runtimeUnchanged=$false;$postcheckFailures+=@($_.Exception.Message)}
$programPath=Join-Path $outPath 'DualSPHysics5.2CPU_win64_debug.exe';$program=if(Test-Path -LiteralPath $programPath){Entry $programPath}else{$null}
$objects=@(Get-ChildItem -LiteralPath $intPath -File -Filter '*.obj' -ErrorAction SilentlyContinue|Sort-Object Name|ForEach-Object{Entry $_.FullName});$actualNames=@($objects|ForEach-Object{[IO.Path]::GetFileName($_.path)})
$objectClosure=($objects.Count -eq 86 -and @($actualNames|Sort-Object -Unique).Count -eq 86 -and @(Compare-Object ($actualNames|Sort-Object) ($expectedNames|Sort-Object)).Count -eq 0)
$binlog=if(Test-Path -LiteralPath $binlogPath){Entry $binlogPath}else{$null};$passed=($nativeCode -is [int] -and $nativeCode -eq 0 -and $null -eq $failure -and $sourceUnchanged -and $canonicalUnchanged -and $runtimeUnchanged -and $null -ne $program -and $null -ne $binlog -and $objectClosure)
$result=[ordered]@{stage='upl_column_public_default_cpu_r1';passed=$passed;configuration=$Configuration;platform='x64';default_CPU_solution_build_with_isolated_outputs=$true;retained_invocation_recipe=$recipeIdentity;historical_source_hashes_used_as_current=$false;build_tool=$msbuild;program=$program;arguments=$arguments;working_directory=$srcPath;isolated_OutDir=$outPath;fresh_IntDir=$intPath;fresh_paths=$freshPaths;started_utc=$started;ended_utc=$ended;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($nativeCode -is [int]);owned_call_exited=($nativeCode -is [int]);exit_code=$nativeCode;owned_exit_record=(Entry $callPath);failure=$failure;postcheck_failures=$postcheckFailures;tools=$tools;author_files=$authors;compile_sources=$compileSources;source_snapshot=$sourcePairs;documentation_snapshot=$documentation;source_code_header_count=265;source_bindings_unchanged=$sourceUnchanged;new_source_snapshots_copied=265;objects=$objects;active_CPU_translation_units=86;non_main_CPU_objects=85;exact_object_basename_closure=$objectClosure;old_objects_reused=$false;canonical_programs_before=$canonical;canonical_program_count=7;canonical_programs_unchanged=$canonicalUnchanged;runtime_before=$runtime;runtime_count=4;runtime_unchanged=$runtimeUnchanged;runtime_copied_by_this_script=$false;conditional_postbuild_header_paths_checked=$postBuildHeaderPaths;log=(Entry $logPath);binlog=$binlog;helper_built=$false;help_invoked=$false;solver_started=$false;canonical_program_installed=$false;physical_acceptance=$false}
WriteFresh $recordPath $result
if(!$passed){throw "Default CPU isolated build failed; retain owned call and partial artifacts: $recordPath"}
Write-Output "Default CPU Debug isolated Build passed; no program run: $recordPath"
