param([switch]$ExecutionAuthorized)
# DebugCPU wrapper compile/link only. Never invoke MSBuild, help, the solver or the helper.
$ErrorActionPreference='Stop'
if(!$ExecutionAuthorized){throw 'Root review of this recipe and the actual CPP, then explicit DebugCPU build-only authorization required'}
$testPath=Split-Path -Parent $PSScriptRoot
$repoPath=(Get-Item -LiteralPath $testPath).Parent.Parent.Parent.Parent.FullName
$srcPath=Join-Path $repoPath 'src';$logPath=Join-Path $testPath 'logs'
$tag='upl_case02_actual_DebugCPU_r1';$folder=Join-Path $testPath "outputs\$tag"
$resultPath=Join-Path $logPath ($tag+'.helper.json')
$buildPath=Join-Path $logPath 'upl_case02_cpu_DebugCPU_r2.build.json'
$recipePath=Join-Path $logPath 'upl_gravity_wall_cpu_DebugCPU_r2.helper.json'
$cpp=Join-Path $testPath 'support\upl_case02_actual_r1.cpp'
$cppNote=Join-Path $testPath 'notes\upl_case02_actual_r1.json'
$note=Join-Path $testPath 'notes\upl_case02_actual_build_r1.json'
$include=Join-Path $testPath 'support\upl_cpu_public_native_r1.cpp'
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ReadJson([string]$path){[IO.File]::ReadAllText($path)|ConvertFrom-Json}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function Fresh($paths){foreach($path in $paths){if(Test-Path -LiteralPath $path){throw "Retained path protected: $path"}}}
function Save([string]$path,$value){Fresh @($path);[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function PassedCall($entry){Verify @($entry);$c=ReadJson $entry.path;if(!$c.typed_LASTEXITCODE_captured_immediately -or !$c.owned_call_exited -or $c.exit_code -ne 0){throw 'Successful owned typed compiler/link receipt required'};Verify @($c.program,$c.log);return $c}
function Owned($tool,[string[]]$argv,[string]$suffix){
  $stdout=Join-Path $logPath ($tag+'_'+$suffix+'.log');$receipt=Join-Path $logPath ($tag+'_'+$suffix+'.call.json')
  Fresh @($stdout,$receipt);Verify @($tool);[IO.File]::WriteAllBytes($stdout,[byte[]]@())
  $started=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$oldPreference=$ErrorActionPreference
  Push-Location $srcPath
  try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $stdout -Append|Out-Host;$code=$LASTEXITCODE}
  catch{$failure=$_.Exception.Message}
  finally{Pop-Location;$ErrorActionPreference=$oldPreference}
  Save $receipt ([ordered]@{program=$tool;arguments=$argv;working_directory=$srcPath;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $stdout);build_tool_only=$true;solver_started=$false;physical_acceptance=$false})
  return (Entry $receipt)
}
Fresh @($folder,$resultPath,(Join-Path $logPath ($tag+'_Compile.log')),(Join-Path $logPath ($tag+'_Compile.call.json')),(Join-Path $logPath ($tag+'_Link.log')),(Join-Path $logPath ($tag+'_Link.call.json')))
$buildIdentity=Entry $buildPath;$recipeIdentity=Entry $recipePath
if($buildIdentity.bytes -ne 340628 -or $buildIdentity.sha256 -ine '928527205bcdee13c49d0317ef4f1ff186f6fb6e480145a405d61f2ebe6bb5db' -or $recipeIdentity.bytes -ne 55152 -or $recipeIdentity.sha256 -ine '83de3d2da0198e62d09ff67b5034cecedffd1d8e0c07becec794985a468c18b0'){throw 'Reviewed current CPU build or successful historical argument recipe identity differs'}
$b=ReadJson $buildPath;$h=ReadJson $recipePath
if(!$b.passed -or $b.stage -cne 'upl_case02_cpu_build_r2' -or $b.configuration -cne 'DebugCPU' -or $b.platform -cne 'x64' -or !$b.default_CPU_solution_build_with_isolated_outputs -or !$b.direct_native_call -or !$b.typed_LASTEXITCODE_captured_immediately -or !$b.owned_call_exited -or $b.exit_code -ne 0 -or $b.solver_started -ne $false -or $b.canonical_program_installed -ne $false -or !$b.canonical_programs_unchanged -or @($b.objects).Count -ne 86 -or @($b.compile_sources).Count -ne 86 -or @($b.source_snapshot).Count -ne 265 -or @($b.canonical_programs_before).Count -ne 7){throw 'Current isolated DebugCPU r2 actual build/86 objects/265 code snapshots/seven canonical identities required'}
if(!$h.passed -or $h.status -cne 'actual_authoritative_CPU_objects_wall_helper_linked_not_run' -or $h.configuration -cne 'DebugCPU' -or $h.label -cne 'r2' -or $h.CPU_non_main_objects -ne 85 -or $h.link_object_count -ne 86 -or !$h.exact_link_closure_verified -or $h.program_run -ne $false){throw 'The successful wall r2 recipe is required; failed r1 has no link/environment recipe'}
$cc=PassedCall $h.compile_call;$lc=PassedCall $h.link_call
if([IO.Path]::GetFileName($cc.program.path) -ine 'cl.exe' -or [IO.Path]::GetFileName($lc.program.path) -ine 'link.exe'){throw 'Only the recorded native CPU compiler and linker are admitted'}
Verify @($h.environment_source);$environmentIdentity=Entry $h.environment_source.path;$environmentRecord=ReadJson $h.environment_source.path
if(!$environmentRecord.passed -or $environmentRecord.configuration -cne 'DebugCPU' -or $environmentRecord.environment.exit_code -ne 0 -or $h.environment.exit_code -ne 0){throw 'Successful sealed DebugCPU developer environment required'}
foreach($key in @('INCLUDE','LIB','VCToolsInstallDir','WindowsSdkDir','WindowsSDKVersion')){
  $value=[string]$h.environment.selected.$key
  if([string]::IsNullOrWhiteSpace($value) -or $value -cne [string]$environmentRecord.environment.selected.$key){throw "Recorded environment missing/different: $key"}
  [Environment]::SetEnvironmentVariable($key,$value,'Process')
}
$env:PATH=([IO.Path]::GetDirectoryName($cc.program.path))+';'+$env:PATH
$byName=@{};$objectDirectory=Join-Path $srcPath 'VS\Intermediate\upl_case02_cpu_DebugCPU_r2'
foreach($r in $b.objects){$name=[IO.Path]::GetFileName($r.path);if($byName.ContainsKey($name) -or [IO.Path]::GetDirectoryName($r.path) -ine $objectDirectory){throw 'Current object basename/directory differs'};$byName[$name]=$r}
if(!$byName.ContainsKey('main.obj') -or $byName.Count -ne 86){throw 'One current main plus85 uniquely named non-main objects required'}
$objects=@($b.objects|Where-Object{[IO.Path]::GetFileName($_.path) -ine 'main.obj'})
$compileNames=@($b.compile_sources|ForEach-Object{[IO.Path]::GetFileNameWithoutExtension($_.path)+'.obj'})
if(@($compileNames|Sort-Object -Unique).Count -ne 86 -or @(Compare-Object ($compileNames|Sort-Object) ($byName.Keys|Sort-Object)).Count){throw 'Authoritative compile-source/object membership differs'}
$runtimeNames=@('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll');$runtimeSources=@();$canonicalRuntime=@()
if(@($h.runtime).Count -ne 4 -or @(Compare-Object ($runtimeNames|Sort-Object) (@($h.runtime|ForEach-Object{[IO.Path]::GetFileName($_.copy.path)})|Sort-Object)).Count){throw 'Recorded four-file CPU configuration/Chrono/OpenMP runtime required'}
foreach($r in $h.runtime){Verify @($r.copy);$current=Entry (Join-Path (Join-Path $repoPath 'bin\windows') ([IO.Path]::GetFileName($r.copy.path)));if($current.bytes -ne $r.copy.bytes -or $current.sha256 -ine $r.copy.sha256){throw 'Sealed runtime copy and current canonical runtime differ'};$runtimeSources+=@($r.copy);$canonicalRuntime+=@($current)}
# Capture the reviewed wrapper at build time; no CPP SHA was invented before author completion.
$authors=@($PSCommandPath,$note,$cpp,$cppNote,$include,(Join-Path $testPath 'notes\upl_cpu_public_native_r1.json'))|ForEach-Object{Entry $_}
$included=$authors|Where-Object{$_.path -ieq $include}
if($included.bytes -ne 22469 -or $included.sha256 -ine '9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38'){throw 'Immutable declaration include differs'}
function VerifyBase{
  Verify @($buildIdentity,$recipeIdentity,$environmentIdentity,$h.compile_call,$h.link_call,$b.program,$b.log,$b.binlog)
  Verify $authors;Verify $b.tools;Verify $b.compile_sources;Verify $b.objects;Verify $b.canonical_programs_before
  foreach($pair in $b.source_snapshot){Verify @($pair.original,$pair.snapshot);if($pair.original.bytes -ne $pair.snapshot.bytes -or $pair.original.sha256 -ine $pair.snapshot.sha256){throw 'Current code/snapshot pair differs'}}
  Verify $h.tools;Verify $h.environment.tools;Verify $h.libraries;Verify @($cc.program,$cc.log,$lc.program,$lc.log);Verify $runtimeSources;Verify $canonicalRuntime
  $current=@(Get-ChildItem -LiteralPath (Join-Path $srcPath 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|ForEach-Object{$_.FullName})
  if($current.Count -ne 265 -or @(Compare-Object ($current|Sort-Object) (@($b.source_snapshot|ForEach-Object{$_.original.path})|Sort-Object)).Count){throw 'Current265 C++/CUDA code/header membership differs'}
}
VerifyBase
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder 'upl_case02_actual_r1.exe';$dependencies=Join-Path $folder 'compile.dependencies.json'
$oldCpp=Join-Path $testPath 'support\upl_gravity_wall_cpu_r1.cpp';$oldDir=Split-Path -Parent $h.program.path
$compile=@();$sourceCount=0;$fo=0;$fd=0;$deps=0
foreach($a in $cc.arguments){
  if($a -ieq $oldCpp){$compile+=$cpp;$sourceCount++}
  elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fo'+$obj;$fo++}
  elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}
  elseif($a -ieq (Join-Path $oldDir 'compile.dependencies.json')){$compile+=$dependencies;$deps++}
  else{$compile+=$a}
}
if($sourceCount -ne 1 -or $fo -ne 1 -or $fd -ne 1 -or $deps -ne 1 -or $compile -notcontains '/std:c++17' -or $compile -notcontains '/fp:precise' -or $compile -notcontains '/MTd' -or $compile -notcontains '/RTC1'){throw 'One source/Fo/Fd/dependency remap and unchanged actual DebugCPU flags required'}
$link=@();$seen=@{};$helperCount=0;$outCount=0;$pdbCount=0
foreach($a in $lc.arguments){
  if($a -ieq $h.helper_object.path){$link+=$obj;$helperCount++}
  elseif($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$link+='/OUT:'+$exe;$outCount++}
  elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$link+='/PDB:'+(Join-Path $folder 'link.pdb');$pdbCount++}
  elseif($a.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)){$name=[IO.Path]::GetFileName($a);if($name -ieq 'main.obj' -or !$byName.ContainsKey($name) -or $seen.ContainsKey($name)){throw 'Historical link vector has unexpected/duplicate/main object'};$link+=$byName[$name].path;$seen[$name]=$true}
  else{$link+=$a}
}
$linkedObjects=@($link|Where-Object{$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)})
$linkedNonMain=@($linkedObjects|Where-Object{$_ -ine $obj})
if($helperCount -ne 1 -or $outCount -ne 1 -or $pdbCount -ne 1 -or $seen.Count -ne 85 -or $linkedObjects.Count -ne 86 -or @(Compare-Object ($linkedNonMain|Sort-Object) ($objects.path|Sort-Object)).Count){throw 'Exactly current85 non-main objects plus one new wrapper object required'}
# Explicit output filenames are single native arguments, never a quoted directory ending in backslash.
[void](New-Item -ItemType Directory -Path $folder)
$compileCall=Owned $cc.program $compile 'Compile';$compileDone=ReadJson $compileCall.path
$linkCall=$null;$linkDone=$null;$failure=$null;$runtime=@();$depsIdentity=$null;$helperObject=$null;$program=$null
try{
  if(!$compileDone.typed_LASTEXITCODE_captured_immediately -or $compileDone.exit_code -ne 0 -or $compileDone.invocation_failure){throw 'New wrapper compilation failed; preserve the owned call and do not link/run'}
  VerifyBase;$helperObject=Entry $obj;$depsIdentity=Entry $dependencies
  $dependencyData=ReadJson $dependencies
  if($dependencyData.Data.Source -ine $cpp){throw 'Compiler dependency source is not the actual wrapper'}
  $linkCall=Owned $lc.program $link 'Link';$linkDone=ReadJson $linkCall.path
  if(!$linkDone.typed_LASTEXITCODE_captured_immediately -or $linkDone.exit_code -ne 0 -or $linkDone.invocation_failure){throw 'Wrapper link failed; preserve the owned call and do not run'}
  $program=Entry $exe
  foreach($source in $runtimeSources){$destination=Join-Path $folder ([IO.Path]::GetFileName($source.path));Fresh @($destination);Copy-Item -LiteralPath $source.path -Destination $destination;$copy=Entry $destination;if($copy.bytes -ne $source.bytes -or $copy.sha256 -ine $source.sha256){throw 'New isolated helper runtime copy differs'};$runtime+=@{original=$source;copy=$copy}}
  VerifyBase;Verify @($helperObject,$depsIdentity,$program);foreach($r in $runtime){Verify @($r.original,$r.copy)}
}catch{$failure=$_.Exception.Message}
$passed=($null -eq $failure -and $null -ne $program -and $runtime.Count -eq 4)
Save $resultPath ([ordered]@{stage='upl_case02_actual_build_r1';passed=$passed;status=$(if($passed){'current_CPU_Debug_wrapper_linked_not_run'}else{'wrapper_build_failed_retained'});configuration='DebugCPU';label='r1';source_build=$buildIdentity;retained_compiler_recipe=$recipeIdentity;environment_source=$environmentIdentity;environment=$h.environment;tools=@($cc.program,$lc.program);libraries=$h.libraries;author_files=$authors;source_snapshot=$b.source_snapshot;source_code_header_count=265;compile_sources=$b.compile_sources;objects=$objects;CPU_non_main_objects=85;historical_recipe_objects_reused=$false;CPU_object_substitutions=85;helper_object=$helperObject;link_object_count=86;exact_link_object_closure_verified=$true;canonical_programs_before=$b.canonical_programs_before;canonical_program_count=7;canonical_runtime_before=$canonicalRuntime;compile_call=$compileCall;link_call=$linkCall;compiler_dependency_record=$depsIdentity;runtime=$runtime;program=$program;failure=$failure;build_and_source_bindings_unchanged=($null -eq $failure);historical_argument_environment_only=$true;production_build_executed=$false;program_run=$false;solver_started=$false;help_invoked=$false;Release_built=$false;physical_acceptance=$false})
if(!$passed){throw "Actual wrapper build failed; preserve artifacts and inspect $resultPath"}
Write-Output "DebugCPU wrapper linked, not run: $resultPath"
