param(
  [Parameter(Mandatory=$true)][ValidateSet('actual','operator','reader')][string]$Kind,
  [Parameter(Mandatory=$true)][ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration
)
# Single compile/link only. No main build, helper/help/reader/solver invocation.
$ErrorActionPreference='Stop';$Kind=$Kind.ToLowerInvariant();$Configuration=if($Configuration -ieq 'DebugCPU'){'DebugCPU'}else{'ReleaseCPU'};$testPath=Split-Path -Parent $PSScriptRoot
$repoPath=(Get-Item -LiteralPath $testPath).Parent.Parent.Parent.Parent.FullName;$srcPath=Join-Path $repoPath 'src';$logs=Join-Path $testPath 'logs'
$tag="upl_case02_flux_${Kind}_${Configuration}_r1";$folder=Join-Path $testPath "outputs\$tag";$resultPath=Join-Path $logs ($tag+'.helper.json')
$stem=switch($Kind){'reader'{'upl_case02_native_r1'}'actual'{'upl_case02_actual_r1'}'operator'{'upl_case02_operator_r1'}}
$cpp=Join-Path $testPath "support\$stem.cpp";$cppNote=Join-Path $testPath "notes\$stem.json";$note=Join-Path $testPath 'notes\upl_case02_flux_helper_build_r1.json'
$include=Join-Path $testPath 'support\upl_cpu_public_native_r1.cpp';$buildTag="upl_case02_flux_cpu_${Configuration}_r1"
$buildPath=Join-Path $logs ($buildTag+'.build.json');$recipePath=Join-Path $logs "upl_gravity_wall_cpu_${Configuration}_r2.helper.json"
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ReadJson([string]$path){[IO.File]::ReadAllText($path)|ConvertFrom-Json}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Frozen artifact changed: $($r.path)"}}}
function Fresh($paths){foreach($path in $paths){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"}}}
function Save([string]$path,$value){Fresh @($path);[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function PassedCall($ref){Verify @($ref);$c=ReadJson $ref.path;if(!$c.typed_LASTEXITCODE_captured_immediately -or !$c.owned_call_exited -or $c.exit_code -ne 0 -or $c.invocation_failure){throw 'Successful owned typed compiler/link receipt required'};Verify @($c.program,$c.log);return $c}
function Owned($tool,[string[]]$argv,[string]$suffix){
  $stdout=Join-Path $logs ($tag+'_'+$suffix+'.log');$receipt=Join-Path $logs ($tag+'_'+$suffix+'.call.json');Fresh @($stdout,$receipt);Verify @($tool);[IO.File]::WriteAllBytes($stdout,[byte[]]@())
  $started=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$oldPreference=$ErrorActionPreference;Push-Location $srcPath
  try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $stdout -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$oldPreference}
  Save $receipt ([ordered]@{program=$tool;arguments=$argv;working_directory=$srcPath;direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');log=(Entry $stdout);build_tool_only=$true;program_run=$false;physical_acceptance=$false});return (Entry $receipt)
}
Fresh @($folder,$resultPath,(Join-Path $logs ($tag+'_Compile.log')),(Join-Path $logs ($tag+'_Compile.call.json')),(Join-Path $logs ($tag+'_Link.log')),(Join-Path $logs ($tag+'_Link.call.json')))
# New main-build identity is deliberately late-bound, never the old case02 source proof.
$buildIdentity=Entry $buildPath;$recipeIdentity=Entry $recipePath
$knownRecipe=if($Configuration -ceq 'DebugCPU'){@{bytes=55152;sha256='83de3d2da0198e62d09ff67b5034cecedffd1d8e0c07becec794985a468c18b0'}}else{@{bytes=55363;sha256='47aa0e8c3b02a97cd539c2b533c7bff8402df70e179a88dfd4be1e4aa230e3ba'}}
if($recipeIdentity.bytes -ne $knownRecipe.bytes -or $recipeIdentity.sha256 -ine $knownRecipe.sha256){throw 'Reviewed successful same-configuration wall r2 argument recipe differs'}
$b=ReadJson $buildPath;$h=ReadJson $recipePath
if(!$b.passed -or $b.configuration -cne $Configuration -or $b.platform -cne 'x64' -or !$b.default_CPU_solution_build_with_isolated_outputs -or !$b.direct_native_call -or !$b.typed_LASTEXITCODE_captured_immediately -or !$b.owned_call_exited -or $b.exit_code -ne 0 -or $b.solver_started -ne $false -or $b.canonical_program_installed -ne $false -or !$b.canonical_programs_unchanged -or @($b.objects).Count -ne 86 -or @($b.compile_sources).Count -ne 86 -or @($b.source_snapshot).Count -ne 265 -or @($b.canonical_programs_before).Count -ne 7){throw 'Passed new flux configuration build with86 objects/265 code pairs/seven protected programs required'}
if(!$h.passed -or $h.status -cne 'actual_authoritative_CPU_objects_wall_helper_linked_not_run' -or $h.configuration -cne $Configuration -or $h.label -cne 'r2' -or $h.CPU_non_main_objects -ne 85 -or $h.link_object_count -ne 86 -or !$h.exact_link_closure_verified -or $h.program_run -ne $false -or @($h.libraries).Count -ne 17){throw 'Actually passed wall r2 compiler/link/environment recipe required'}
$cc=PassedCall $h.compile_call;$lc=PassedCall $h.link_call
if([IO.Path]::GetFileName($cc.program.path) -ine 'cl.exe' -or [IO.Path]::GetFileName($lc.program.path) -ine 'link.exe'){throw 'Only recorded CPU compiler/linker tools admitted'}
Verify @($h.environment_source);$environmentIdentity=Entry $h.environment_source.path;$environmentRecord=ReadJson $h.environment_source.path
if(!$environmentRecord.passed -or $environmentRecord.configuration -cne $Configuration -or $environmentRecord.environment.exit_code -ne 0 -or $h.environment.exit_code -ne 0){throw 'Successful sealed same-configuration developer environment required'}
foreach($key in @('INCLUDE','LIB','VCToolsInstallDir','WindowsSdkDir','WindowsSDKVersion')){$value=[string]$h.environment.selected.$key;if([string]::IsNullOrWhiteSpace($value) -or $value -cne [string]$environmentRecord.environment.selected.$key){throw "Recorded environment differs: $key"};[Environment]::SetEnvironmentVariable($key,$value,'Process')};$env:PATH=([IO.Path]::GetDirectoryName($cc.program.path))+';'+$env:PATH
$byName=@{};$objectDirectory=Join-Path $srcPath "VS\Intermediate\$buildTag"
foreach($r in $b.objects){$name=[IO.Path]::GetFileName($r.path);if($byName.ContainsKey($name) -or [IO.Path]::GetDirectoryName($r.path) -ine $objectDirectory){throw 'New flux object name/directory differs'};$byName[$name]=$r}
$objects=@($b.objects|Where-Object{[IO.Path]::GetFileName($_.path) -ine 'main.obj'});$compileNames=@($b.compile_sources|ForEach-Object{[IO.Path]::GetFileNameWithoutExtension($_.path)+'.obj'})
if(!$byName.ContainsKey('main.obj') -or $objects.Count -ne 85 -or @($compileNames|Sort-Object -Unique).Count -ne 86 -or @(Compare-Object ($compileNames|Sort-Object) ($byName.Keys|Sort-Object)).Count){throw 'New main plus exact85 unique CPU non-main basenames required'}
$runtimeNames=@('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll');$runtimeSources=@();$canonicalRuntime=@()
if(@($h.runtime).Count -ne 4 -or @(Compare-Object ($runtimeNames|Sort-Object) (@($h.runtime|ForEach-Object{[IO.Path]::GetFileName($_.copy.path)})|Sort-Object)).Count){throw 'Four actual configuration/Chrono/OpenMP runtime copies required'}
foreach($r in $h.runtime){Verify @($r.copy);$current=Entry (Join-Path (Join-Path $repoPath 'bin\windows') ([IO.Path]::GetFileName($r.copy.path)));if($current.bytes -ne $r.copy.bytes -or $current.sha256 -ine $r.copy.sha256){throw 'Recorded and current canonical runtime differ'};$runtimeSources+=@($r.copy);$canonicalRuntime+=@($current)}
$knownFixture=switch($Kind){'actual'{@{cpp='0b1cfa12c0420aadba6c6a5b73d0bd4e62de662ef5d7e114f9238c8242c08784';note='8974789d127a1ac5a0f2ab1a280da3428bea2831a64d999a4b6bf98e09631f4c'}}'reader'{@{cpp='bcb59a2fc986bdd620dba02ae2021e50e8c970f865ca80bb142efa191c27d825';note='7453c3bd16de9183eff26c70bc782c6f025a0f8bbee7d74a4c543b49c026eae1'}}'operator'{@{cpp='95650f5304d73ffeb949dc878321b6cf519119585e36af5b8c36361658b0cc30';note='ab513ed6f0ce7dfa79997f11249a9fb51f057241e1f8cc7955888835cafd3648'}}}
$authors=@($PSCommandPath,$note,$cpp,$cppNote,$include,(Join-Path $testPath 'notes\upl_cpu_public_native_r1.json'))|ForEach-Object{Entry $_}
$chosenCpp=Entry $cpp;$chosenNote=Entry $cppNote;$included=Entry $include
if($chosenCpp.sha256 -ine $knownFixture.cpp -or $chosenNote.sha256 -ine $knownFixture.note -or $included.bytes -ne 22469 -or $included.sha256 -ine '9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38'){throw 'An existing frozen fixture/note/neutral include changed'}
function VerifyBase{
  Verify @($buildIdentity,$recipeIdentity,$environmentIdentity,$h.compile_call,$h.link_call,$b.program,$b.log,$b.binlog);Verify $authors;Verify $b.tools;Verify $b.compile_sources;Verify $b.objects;Verify $b.canonical_programs_before
  foreach($pair in $b.source_snapshot){Verify @($pair.original,$pair.snapshot);if($pair.original.bytes -ne $pair.snapshot.bytes -or $pair.original.sha256 -ine $pair.snapshot.sha256){throw 'New flux current-source/snapshot pair differs'}}
  if($b.documentation_snapshot){foreach($pair in @($b.documentation_snapshot)){Verify @($pair.original,$pair.snapshot);if($pair.original.bytes -ne $pair.snapshot.bytes -or $pair.original.sha256 -ine $pair.snapshot.sha256){throw 'Flux documentation snapshot differs'}}}
  Verify $h.tools;Verify $h.environment.tools;Verify $h.libraries;Verify @($cc.program,$cc.log,$lc.program,$lc.log);Verify $runtimeSources;Verify $canonicalRuntime
  $current=@(Get-ChildItem -LiteralPath (Join-Path $srcPath 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|ForEach-Object{$_.FullName})
  if($current.Count -ne 265 -or @(Compare-Object ($current|Sort-Object) (@($b.source_snapshot|ForEach-Object{$_.original.path})|Sort-Object)).Count){throw 'Current265 code/header membership differs'}
}
VerifyBase
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder ($stem+'.exe');$dependencies=Join-Path $folder 'compile.dependencies.json';$oldCpp=Join-Path $testPath 'support\upl_gravity_wall_cpu_r1.cpp';$oldDir=Split-Path -Parent $h.program.path
$compile=@();$sourceCount=0;$fo=0;$fd=0;$deps=0
foreach($a in $cc.arguments){if($a -ieq $oldCpp){$compile+=$cpp;$sourceCount++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq (Join-Path $oldDir 'compile.dependencies.json')){$compile+=$dependencies;$deps++}else{$compile+=$a}}
$runtimeFlag=if($Configuration -ceq 'DebugCPU'){'/MTd'}else{'/MT'}
if($sourceCount -ne 1 -or $fo -ne 1 -or $fd -ne 1 -or $deps -ne 1 -or $compile -notcontains '/std:c++17' -or $compile -notcontains '/fp:precise' -or $compile -notcontains $runtimeFlag){throw 'Exact source/Fo/Fd/dependency remaps and unchanged compiler flags required'}
$link=@();$seen=@{};$helperCount=0;$outCount=0;$pdbCount=0
foreach($a in $lc.arguments){if($a -ieq $h.helper_object.path){$link+=$obj;$helperCount++}elseif($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$link+='/OUT:'+$exe;$outCount++}elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$link+='/PDB:'+(Join-Path $folder 'link.pdb');$pdbCount++}elseif($a.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)){$name=[IO.Path]::GetFileName($a);if($name -ieq 'main.obj' -or !$byName.ContainsKey($name) -or $seen.ContainsKey($name)){throw 'Old vector contains unexpected/duplicate/main object'};$link+=$byName[$name].path;$seen[$name]=$true}else{$link+=$a}}
$linked=@($link|Where-Object{$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)});$nonMain=@($linked|Where-Object{$_ -ine $obj});$expectedPdb=if($Configuration -ceq 'DebugCPU'){1}else{0}
if($helperCount -ne 1 -or $outCount -ne 1 -or $pdbCount -ne $expectedPdb -or $seen.Count -ne 85 -or $linked.Count -ne 86 -or @(Compare-Object ($nonMain|Sort-Object) ($objects.path|Sort-Object)).Count){throw 'Exact new flux85 plus one selected helper link closure required'}
[void](New-Item -ItemType Directory -Path $folder);$compileCall=Owned $cc.program $compile 'Compile';$compileDone=ReadJson $compileCall.path
$linkCall=$null;$failure=$null;$runtime=@();$depsIdentity=$null;$helperObject=$null;$program=$null
try{
  if(!$compileDone.typed_LASTEXITCODE_captured_immediately -or $compileDone.exit_code -ne 0 -or $compileDone.invocation_failure){throw 'Compilation failed; preserve output and do not link/run'}
  VerifyBase;$helperObject=Entry $obj;$depsIdentity=Entry $dependencies;$dependencyData=ReadJson $dependencies
  if($dependencyData.Data.Source -ine $cpp){throw 'Compiler dependency source differs from selected fixture'}
  $supportIncludes=@($dependencyData.Data.Includes|Where-Object{$_.StartsWith($PSScriptRoot+'\',[StringComparison]::OrdinalIgnoreCase)})
  if($supportIncludes.Count -ne 1 -or $supportIncludes[0] -ine $include){throw 'Only the captured immutable local declaration include is admitted'}
  $linkCall=Owned $lc.program $link 'Link';$linkDone=ReadJson $linkCall.path
  if(!$linkDone.typed_LASTEXITCODE_captured_immediately -or $linkDone.exit_code -ne 0 -or $linkDone.invocation_failure){throw 'Link failed; preserve output and do not run'}
  $program=Entry $exe
  foreach($source in $runtimeSources){$dest=Join-Path $folder ([IO.Path]::GetFileName($source.path));Fresh @($dest);Copy-Item -LiteralPath $source.path -Destination $dest;$copy=Entry $dest;if($copy.bytes -ne $source.bytes -or $copy.sha256 -ine $source.sha256){throw 'Isolated runtime copy differs'};$runtime+=@{original=$source;copy=$copy}}
  Verify @($helperObject,$depsIdentity,$program);foreach($r in $runtime){Verify @($r.original,$r.copy)}
}catch{$failure=$_.Exception.Message}
$bindingsUnchanged=$false;try{VerifyBase;$bindingsUnchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$passed=($null -eq $failure -and $bindingsUnchanged -and $null -ne $program -and $runtime.Count -eq 4)
Save $resultPath ([ordered]@{stage='upl_case02_flux_helper_build_r1';passed=$passed;status=$(if($passed){'current_CPU_flux_helper_linked_not_run'}else{'flux_helper_build_failed_retained'});kind=$Kind;configuration=$Configuration;label='r1';source_build=$buildIdentity;retained_compiler_recipe=$recipeIdentity;environment_source=$environmentIdentity;environment=$h.environment;tools=@($cc.program,$lc.program);libraries=$h.libraries;author_files=$authors;source_snapshot=$b.source_snapshot;documentation_snapshot=$b.documentation_snapshot;source_code_header_count=265;compile_sources=$b.compile_sources;objects=$objects;CPU_non_main_objects=85;CPU_object_substitutions=85;historical_recipe_objects_reused=$false;helper_object=$helperObject;link_object_count=86;exact_link_closure_verified=$true;canonical_programs_before=$b.canonical_programs_before;canonical_program_count=7;canonical_runtime_before=$canonicalRuntime;compile_call=$compileCall;link_call=$linkCall;compiler_dependency_record=$depsIdentity;runtime=$runtime;program=$program;failure=$failure;build_and_source_bindings_unchanged=$bindingsUnchanged;production_build_executed=$false;program_run=$false;help_invoked=$false;solver_started=$false;canonical_program_installed=$false;physical_acceptance=$false})
if(!$passed){throw "Flux helper build failed; retain artifacts and inspect $resultPath"}
Write-Output "Selected flux helper compiled/linked, not run: $resultPath"
