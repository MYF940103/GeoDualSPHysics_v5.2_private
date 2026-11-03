param([Parameter(Mandatory=$true)][ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration,[switch]$ExecutionAuthorized)
# Compile two actual-class fixture translation units and link; never run them.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root full review required before this build'}
$Configuration=if($Configuration -ieq 'DebugCPU'){'DebugCPU'}else{'ReleaseCPU'}
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src'
$tag='upl_hg_cpu_legacy_'+$Configuration+'_r1';$logs=Join-Path $tests 'logs';$out=Join-Path $tests ('outputs\'+$tag)
$record=Join-Path $logs ($tag+'.helper.json');$exe=Join-Path $out 'upl_hg_cpu_legacy_r1.exe'
$units=@(
  [ordered]@{name='Fixture';cpp=(Join-Path $PSScriptRoot 'upl_hg_cpu_legacy_r1.cpp');obj=(Join-Path $out 'legacy.obj');dep=(Join-Path $out 'legacy.dependencies.json');pdb=(Join-Path $out 'legacy.pdb')},
  [ordered]@{name='Reference';cpp=(Join-Path $PSScriptRoot 'upl_hg_cpu_legacy_reference_r1.cpp');obj=(Join-Path $out 'legacy_reference.obj');dep=(Join-Path $out 'legacy_reference.dependencies.json');pdb=(Join-Path $out 'legacy_reference.pdb')}
)
function Need([bool]$b,[string]$why){if(!$b){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function V($entries){foreach($e in @($entries)){Need ($e.path -and $e.sha256 -and $null -ne $e.bytes) 'Missing bound identity';$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed bound artifact: '+$e.path)}}
function Fresh($paths){foreach($p in @($paths)){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function PassedCall($e){V @($e);$c=J $e.path;Need ($c.direct_native_call -and $c.typed_LASTEXITCODE_captured_immediately -and $c.owned_call_exited -and $c.exit_code -is [int] -and $c.exit_code -eq 0 -and !$c.invocation_failure) 'Actual typed tool exit0 required';V @($c.program);if($c.log){V @($c.log)};return $c}
function Owned($tool,[string[]]$argv,[string]$kind){
  $p=Join-Path $logs ($tag+'_'+$kind+'.call.json');$log=Join-Path $logs ($tag+'_'+$kind+'.log');Fresh @($p,$log)
  [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$why=$null;$prior=$ErrorActionPreference;Push-Location $src
  try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$why=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
  Save $p ([ordered]@{program=$tool;arguments=$argv;working_directory=$src;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$why;log=(E $log);build_tool_only=$true;program_run=$false;solver_run=$false});return (E $p)
}
Fresh @($out,$record)
foreach($kind in @('CompileFixture','CompileReference','Link')){Fresh @((Join-Path $logs ($tag+'_'+$kind+'.call.json')),(Join-Path $logs ($tag+'_'+$kind+'.log')))}
$buildE=E (Join-Path $logs ('upl_hg_'+$Configuration+'_r1.build.json'));$b=J $buildE.path
Need ($b.passed -and $b.stage -ceq 'upl_hg_build_r1' -and $b.configuration -ceq $Configuration -and $b.source_bindings_unchanged -and $b.exact_object_basename_closure -and $b.objects_include_project_main -and @($b.objects).Count -eq 86 -and @($b.source_snapshot).Count -eq 265 -and @($b.canonical_programs_before).Count -eq 7 -and @($b.runtime).Count -eq 4 -and $b.canonical_programs_unchanged -and $b.runtime_unchanged) 'Passed current authoritative CPU build86/source265/runtime4/canonical7 required'
[void](PassedCall $b.project_call)
$recipeE=E (Join-Path $logs $(if($Configuration -ceq 'DebugCPU'){'upl_case02_flux_affine_DebugCPU_r1.helper.json'}else{'upl_case02_flux_operator_ReleaseCPU_r1.helper.json'}));$h=J $recipeE.path
Need ($h.passed -and $h.configuration -ceq $Configuration -and $h.exact_link_closure_verified -and @($h.objects).Count -eq 85 -and @($h.libraries).Count -eq 17) 'Retained same-configuration cl/link recipe required'
$cc=PassedCall $h.compile_call;$lc=PassedCall $h.link_call
Need ([IO.Path]::GetFileName($cc.program.path) -ieq 'cl.exe' -and [IO.Path]::GetFileName($lc.program.path) -ieq 'link.exe') 'Actual MSVC tools required'
$oldCpp=Join-Path $PSScriptRoot $(if($Configuration -ceq 'DebugCPU'){'upl_case02_flux_affine_r1.cpp'}else{'upl_case02_operator_r1.cpp'})
$objects=@($b.objects|Where-Object{[IO.Path]::GetFileName($_.path) -ine 'main.obj'});Need ($objects.Count -eq 85) 'Exactly85 non-main project objects required'
$byName=@{};foreach($e in $objects){$key=[IO.Path]::GetFileName($e.path).ToLowerInvariant();Need (!$byName.ContainsKey($key)) 'Duplicate project object';$byName[$key]=$e}
Need ($byName.ContainsKey('jsphhourglasscpu.obj') -and $byName.ContainsKey('jobject.obj') -and $byName.ContainsKey('jexception.obj') -and $byName.ContainsKey('functions.obj') -and $byName.ContainsKey('jappinfo.obj')) 'Actual HG/JObject/JException/Functions/JAppInfo objects required'
$frozenE=E (Join-Path $logs 'hg_release_base.json');$frozen=J $frozenE.path;$snapshot=Join-Path $tests 'outputs\hg_release_base'
Need ($frozen.source_and_copy_hashes_verified -and [IO.Path]::GetFullPath($frozen.snapshot) -ieq [IO.Path]::GetFullPath($snapshot)) 'Frozen reference manifest/snapshot differs from fixture include'
$reference=@();foreach($relative in @('source\JSphHourglassCpu.h','source\JSphHourglassCpu.cpp')){
  $rows=@($frozen.entries|Where-Object{$_.relative -ceq $relative});Need ($rows.Count -eq 1) ('One frozen manifest entry required: '+$relative)
  $copy=E (Join-Path $snapshot $relative);Need ($copy.bytes -eq $rows[0].bytes -and $copy.sha256 -ieq $rows[0].sha256) ('Frozen HG source differs from manifest: '+$relative);$reference+=@($copy)
}
$authors=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_hg_cpu_legacy_build_r1.json')),(E $units[0].cpp),(E $units[1].cpp),(E (Join-Path $tests 'notes\upl_hg_cpu_legacy_r1.json')))
$bindings=@($buildE,$b.project_call,$b.log,$b.binlog,$b.program,$recipeE,$h.compile_call,$h.link_call,$h.environment_source,$cc.program,$lc.program,$cc.log,$lc.log,$frozenE)+$reference+$authors+@($b.inputs)+@($b.objects)+@($h.tools)+@($h.libraries)+@($h.environment.tools)
foreach($pair in @($b.source_snapshot)+@($b.documentation_snapshot,$b.case_readme_snapshot)){$bindings+=@($pair.original,$pair.snapshot)}
foreach($pair in $b.runtime){$bindings+=@($pair.original,$pair.copy)};$bindings+=@($b.canonical_programs_before)
if($Configuration -ceq 'ReleaseCPU'){
  $debugE=E (Join-Path $logs 'upl_hg_cpu_legacy_DebugCPU_r1.helper.json');$debug=J $debugE.path
  Need ($debug.passed -and $debug.stage -ceq 'upl_hg_cpu_legacy_build_r1' -and $debug.configuration -ceq 'DebugCPU' -and $debug.exact_link_object_closure_verified -and $debug.link_object_count -eq 87 -and $debug.actual_project_classes_no_stubs -and $debug.frozen_inputs_unchanged -and !$debug.program_run -and !$debug.solver_run) 'Build the actual DebugCPU legacy fixture successfully before ReleaseCPU'
  V @($debug.program);$bindings+=@($debugE,$debug.program)
}
V $bindings
$commands=@();foreach($unit in $units){
  $ca=@();$sources=0;$fo=0;$fd=0;$deps=0
  foreach($a in $cc.arguments){if($a -ieq $oldCpp){$ca+=$unit.cpp;$sources++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$unit.obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+$unit.pdb;$fd++}elseif($a -ieq $h.compiler_dependency_record.path){$ca+=$unit.dep;$deps++}else{$ca+=$a}}
  Need ($sources -eq 1 -and $fo -eq 1 -and $fd -eq 1 -and $deps -eq 1 -and $ca -ccontains '/std:c++17' -and $ca -ccontains '/fp:precise' -and $ca -cnotcontains '/GL') 'Only source/Fo/Fd/dependency remaps; separate non-LTCG translation units required'
  Need ($ca -ccontains $(if($Configuration -ceq 'DebugCPU'){'/MTd'}else{'/MT'})) 'Same-configuration static runtime flag required'
  $commands+=@([ordered]@{unit=$unit;arguments=$ca})
}
$la=@();$helpers=0;$outs=0;$mapped=0;$seen=@{}
foreach($a in $lc.arguments){
  if($a -ieq $h.helper_object.path){$la+=@($units[0].obj,$units[1].obj);$helpers++}
  elseif($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$outs++}
  elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $out 'link.pdb')}
  elseif($a.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)){$key=[IO.Path]::GetFileName($a).ToLowerInvariant();Need ($byName.ContainsKey($key) -and !$seen.ContainsKey($key)) 'Unexpected/duplicate linked project object';$la+=$byName[$key].path;$seen[$key]=$true;$mapped++}
  else{$la+=$a}
}
$linked=@($la|Where-Object{$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)});$projectLinked=@($linked|Where-Object{$_ -ine $units[0].obj -and $_ -ine $units[1].obj})
Need ($helpers -eq 1 -and $outs -eq 1 -and $mapped -eq 85 -and $seen.Count -eq 85 -and $linked.Count -eq 87 -and @($linked|Sort-Object -Unique).Count -eq 87 -and !(Compare-Object ($projectLinked|Sort-Object) ($objects.path|Sort-Object)) -and !(@($la|Where-Object{$_ -match '^/LTCG(?::|$)'}).Count)) 'Exactly85 current project objects plus two separate new fixture objects required'
foreach($key in @('INCLUDE','LIB','VCToolsInstallDir','WindowsSdkDir','WindowsSDKVersion')){$v=[string]$h.environment.selected.$key;Need (![string]::IsNullOrWhiteSpace($v)) 'Missing selected VS environment';[Environment]::SetEnvironmentVariable($key,$v,'Process')}
$env:PATH=([IO.Path]::GetDirectoryName($cc.program.path))+';'+$env:PATH
[void](New-Item -ItemType Directory -Path $out);$compileCalls=@();$link=$null;$program=$null;$runtime=@();$includes=@();$builtObjects=@();$dependencies=@();$failure=$null
try{
  foreach($command in $commands){
    V $bindings;$call=Owned $cc.program $command.arguments ('Compile'+$command.unit.name);$compileCalls+=@($call);[void](PassedCall $call)
    $d=J $command.unit.dep;Need ($d.Data.Source -ieq $command.unit.cpp) 'Source dependency identity differs'
    $unitIncludes=@($d.Data.Includes|Sort-Object -Unique);Need ($unitIncludes -icontains $reference[0].path) 'Actual frozen reference header must be a recorded dependency'
    if($command.unit.name -ceq 'Reference'){Need ($unitIncludes -icontains $reference[1].path) 'Separate reference TU must include the actual frozen CPP'}
    $includes+=@($unitIncludes|ForEach-Object{E $_});$builtObjects+=@(E $command.unit.obj);$dependencies+=@(E $command.unit.dep);V $bindings
  }
  $link=Owned $lc.program $la 'Link';[void](PassedCall $link);$program=E $exe
  foreach($pair in $b.runtime){$to=Join-Path $out ([IO.Path]::GetFileName($pair.copy.path));Fresh @($to);Copy-Item -LiteralPath $pair.copy.path -Destination $to;$copy=E $to;Need ($copy.bytes -eq $pair.copy.bytes -and $copy.sha256 -ieq $pair.copy.sha256) 'Runtime copy differs';$runtime+=@{original=$pair.copy;copy=$copy}}
}catch{$failure=$_.Exception.Message}
$unchanged=$false;try{V $bindings;V $includes;V $builtObjects;V $dependencies;if($program){V @($program)};foreach($pair in $runtime){V @($pair.original,$pair.copy)};$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$passed=(!$failure -and $unchanged -and $compileCalls.Count -eq 2 -and $builtObjects.Count -eq 2 -and $null -ne $program -and $runtime.Count -eq 4)
Save $record ([ordered]@{stage='upl_hg_cpu_legacy_build_r1';passed=$passed;configuration=$Configuration;source_build=$buildE;retained_invocation_recipe=$recipeE;inputs=$bindings;author_files=$authors;frozen_reference_manifest=$frozenE;frozen_reference_files=$reference;historical_original_source_paths_verified_as_current=$false;project_objects=$objects;CPU_non_main_objects=85;object_count=85;helper_objects=$builtObjects;link_object_count=87;exact_link_object_closure_verified=$true;separate_fixture_reference_translation_units=$true;current_HG_extra_translation_unit=$false;compile_commands=$commands;link_arguments=$la;compile_calls=$compileCalls;link_call=$link;compiler_dependency_records=$dependencies;actual_includes=$includes;program=$program;runtime=$runtime;frozen_inputs_unchanged=$unchanged;failure=$failure;actual_project_classes_no_stubs=$true;canonical_program_installed=$false;program_run=$false;solver_run=$false;GPU_build_or_run=$false;physical_acceptance=$false})
if(!$passed){throw ('Build failed; inspect fresh retained record: '+$record)};Write-Output ('Actual CPU legacy fixture linked, not run: '+$record)
