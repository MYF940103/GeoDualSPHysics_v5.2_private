param([switch]$ExecutionAuthorized)
# One pure-reader compile/link action only; never rebuild or run any main.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Explicit -ExecutionAuthorized required'}
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src'
$tag='upl_column_public_reader_ReleaseCPU_r1';$folder=Join-Path $tests "outputs\$tag";$record=Join-Path $tests "logs\$tag.helper.json"
$buildPath=Join-Path $tests 'logs\upl_column_public_ReleaseCPU_r1.build.json';$recipePath=Join-Path $tests 'logs\upl_case02_flux_window25_reader_ReleaseCPU_r1.helper.json'
$cpp=Join-Path $tests 'support\upl_column_public_native_r1.cpp';$include=Join-Path $tests 'support\upl_cpu_public_native_r1.cpp';$note=Join-Path $tests 'notes\upl_column_public_reader_build_r1.json'
function E([string]$path){$f=Get-Item -LiteralPath $path -Force;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function V($rows){foreach($r in $rows){if(!$r.path -or $null -eq $r.bytes -or !$r.sha256){throw 'Missing bound artifact'};$a=E $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed bound artifact: $($r.path)"}}}
function J([string]$path){[IO.File]::ReadAllText($path)|ConvertFrom-Json}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained artifact protected: $p"}}}
function Save([string]$path,$value){Fresh @($path);[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 20)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($entry){V @($entry);$c=J $entry.path;if(!$c.direct_native_call -or !$c.typed_LASTEXITCODE_captured_immediately -or !$c.owned_call_exited -or $c.exit_code -isnot [int] -or $c.exit_code -ne 0 -or $c.invocation_failure){throw 'Owned typed compiler/link exit0 required'};V @($c.program,$c.log);return $c}
function Owned($tool,[string[]]$argv,[string]$suffix){
  $log=Join-Path $tests "logs\${tag}_${suffix}.log";$path=Join-Path $tests "logs\${tag}_${suffix}.call.json";Fresh @($log,$path);V @($tool);[IO.File]::WriteAllBytes($log,[byte[]]@())
  $started=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$prior=$ErrorActionPreference;Push-Location $src
  try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
  Save $path ([ordered]@{program=$tool;arguments=$argv;working_directory=$src;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;log=(E $log);build_tool_only=$true;program_run=$false;physical_acceptance=$false});return (E $path)
}
Fresh @($folder,$record,(Join-Path $tests "logs\${tag}_Compile.log"),(Join-Path $tests "logs\${tag}_Compile.call.json"),(Join-Path $tests "logs\${tag}_Link.log"),(Join-Path $tests "logs\${tag}_Link.call.json"))
$build=E $buildPath;$b=J $buildPath;$recipe=E $recipePath;$h=J $recipePath
if($recipe.bytes -ne 360875 -or $recipe.sha256 -ine '7c634281307d13e8c06e04565e357b07362fbac28b1087ba4bd8ec0ba093e31f' -or !$h.passed -or $h.kind -cne 'reader' -or $h.configuration -cne 'ReleaseCPU' -or !$h.exact_link_closure_verified -or @($h.objects).Count -ne 85 -or @($h.libraries).Count -ne 17){throw 'Sealed successful window25 reader recipe required'}
if(!$b.passed -or $b.stage -cne 'upl_column_public_cpu_release_r1' -or $b.configuration -cne 'ReleaseCPU' -or !$b.typed_LASTEXITCODE_captured_immediately -or !$b.owned_call_exited -or $b.exit_code -isnot [int] -or $b.exit_code -ne 0 -or !$b.source_bindings_unchanged -or !$b.exact_object_basename_closure -or @($b.objects).Count -ne 86 -or $b.non_main_CPU_objects -ne 85){throw 'Current public ReleaseCPU authoritative build85+main required'}
$source=$b.adopted_Debug_source_build;V @($source);$d=J $source.path
if(!$d.passed -or $d.stage -cne 'upl_column_public_default_cpu_r1' -or !$d.source_bindings_unchanged -or !$d.canonical_programs_unchanged -or !$d.runtime_unchanged -or @($d.source_snapshot).Count -ne 265 -or @($d.canonical_programs_before).Count -ne 7 -or @($d.runtime_before).Count -ne 4){throw 'Current adopted Debug265/doc/seven-canonical/four-runtime freeze required'}
$cc=Call $h.compile_call;$lc=Call $h.link_call;if([IO.Path]::GetFileName($cc.program.path) -ine 'cl.exe' -or [IO.Path]::GetFileName($lc.program.path) -ine 'link.exe'){throw 'Recorded MSVC tools required'}
$authors=@($PSCommandPath,$note,$cpp,(Join-Path $tests 'notes\upl_column_public_native_r1.json'),$include,(Join-Path $tests 'notes\upl_cpu_public_native_r1.json'))|ForEach-Object{E $_}
$expected=@{($cpp)='977c851b840285906c66e0e2e0da6df2a79239c76edc9ea2dbbebea7808c870b';($include)='9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38'}
foreach($p in $expected.Keys){if((E $p).sha256 -ine $expected[$p]){throw "Reviewed reader/include changed: $p"}}
$objects=@($b.objects|Where-Object{[IO.Path]::GetFileName($_.path) -ine 'main.obj'});$byName=@{};foreach($o in $objects){$n=[IO.Path]::GetFileName($o.path);if($byName.ContainsKey($n)){throw 'Duplicate current object basename'};$byName[$n]=$o.path}
$map=@{};foreach($o in $h.objects){$n=[IO.Path]::GetFileName($o.path);if(!$byName.ContainsKey($n) -or $map.ContainsKey($o.path)){throw 'Old/current non-main object membership differs'};$map[$o.path]=$byName[$n]}
if($objects.Count -ne 85 -or $byName.Count -ne 85 -or $map.Count -ne 85){throw 'Exact85 basename substitutions required'}
$runtime=@($d.runtime_before);$runtimeNames=@('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll')
if(@(Compare-Object ($runtimeNames|Sort-Object) (@($runtime|ForEach-Object{[IO.Path]::GetFileName($_.path)})|Sort-Object)).Count){throw 'Four canonical runtime leaves differ'}
foreach($r in $runtime){$old=@($h.runtime|Where-Object{[IO.Path]::GetFileName($_.copy.path) -ieq [IO.Path]::GetFileName($r.path)});if($old.Count -ne 1 -or $old[0].copy.sha256 -ine $r.sha256 -or $old[0].copy.bytes -ne $r.bytes){throw 'Runtime identity differs from the sealed recipe'}}
function VerifyAll{
  V @($build,$source,$recipe,$h.environment_source,$h.compile_call,$h.link_call,$h.compiler_dependency_record,$b.program,$b.log,$b.binlog);V $authors;V $h.tools;V $h.environment.tools;V $h.libraries;V $objects;V $b.tools;V $d.tools;V $b.compile_sources;V $d.canonical_programs_before;V $runtime;V @($cc.program,$cc.log,$lc.program,$lc.log)
  foreach($r in $d.source_snapshot){V @($r.original,$r.snapshot);if($r.original.sha256 -ine $r.snapshot.sha256 -or $r.original.bytes -ne $r.snapshot.bytes){throw 'Current source/snapshot differs'}};V @($d.documentation_snapshot.original,$d.documentation_snapshot.snapshot)
  if(@($b.source_snapshot).Count -ne 265 -or @($b.compile_sources).Count -ne 86){throw 'Release source declaration differs'}
  foreach($r in $b.source_snapshot){$s=@($d.source_snapshot|Where-Object{$_.original.path -ieq $r.original.path});if($s.Count -ne 1 -or $s[0].original.sha256 -ine $r.original.sha256 -or $s[0].original.bytes -ne $r.original.bytes -or $s[0].snapshot.path -ine $r.snapshot.path -or $s[0].snapshot.sha256 -ine $r.snapshot.sha256){throw 'Release/adopted source identity differs'}}
  $paths=@(Get-ChildItem -LiteralPath (Join-Path $src 'source') -File|Where-Object{$_.Extension -in @('.cpp','.h','.cu','.cuh')}|ForEach-Object{$_.FullName});if($paths.Count -ne 265 -or @(Compare-Object ($paths|Sort-Object) ($d.source_snapshot.original.path|Sort-Object)).Count){throw 'Current265 source membership differs'}
}
VerifyAll
foreach($key in @('INCLUDE','LIB','VCToolsInstallDir','WindowsSdkDir','WindowsSDKVersion')){$value=[string]$h.environment.selected.$key;if([string]::IsNullOrWhiteSpace($value)){throw "Missing selected environment: $key"};[Environment]::SetEnvironmentVariable($key,$value,'Process')};$env:PATH=[IO.Path]::GetDirectoryName($cc.program.path)+';'+$env:PATH
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder 'upl_column_public_native_r1.exe';$deps=Join-Path $folder 'compile.dependencies.json';$oldCpp=Join-Path $tests 'support\upl_case02_flux_window25_native_r1.cpp'
$compile=@();$cs=0;$fo=0;$fd=0;$de=0;foreach($a in $cc.arguments){if($a -ieq $oldCpp){$compile+=$cpp;$cs++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$compile+='/Fd'+(Join-Path $folder 'compile.pdb');$fd++}elseif($a -ieq $h.compiler_dependency_record.path){$compile+=$deps;$de++}else{$compile+=$a}}
if($cs -ne 1 -or $fo -ne 1 -or $fd -ne 1 -or $de -ne 1 -or $compile -notcontains '/MT' -or $compile -notcontains '/fp:precise' -or $compile -notcontains '/std:c++17'){throw 'Only source/Fo/Fd/deps remaps permitted'}
$link=@();$hh=0;$oo=0;$mo=0;foreach($a in $lc.arguments){if($a -ieq $h.helper_object.path){$link+=$obj;$hh++}elseif($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$link+='/OUT:'+$exe;$oo++}elseif($map.ContainsKey($a)){$link+=$map[$a];$mo++}else{$link+=$a}}
$linked=@($link|Where-Object{$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)});$kept=@($linked|Where-Object{$_ -ine $obj})
if($hh -ne 1 -or $oo -ne 1 -or $mo -ne 85 -or $linked.Count -ne 86 -or @($linked|Sort-Object -Unique).Count -ne 86 -or @(Compare-Object ($kept|Sort-Object) ($objects.path|Sort-Object)).Count -or @($link|Where-Object{$_.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)}).Count){throw 'Exact85 current+one helper link closure required; no Release link PDB remap'}
[void](New-Item -ItemType Directory -Path $folder);$compileCall=$null;$linkCall=$null;$program=$null;$helperObject=$null;$dependency=$null;$copied=@();$failure=$null
try{
  $compileCall=Owned $cc.program $compile 'Compile';[void](Call $compileCall);VerifyAll;$helperObject=E $obj;$dependency=E $deps;$dep=J $deps
  $local=@($dep.Data.Includes|Where-Object{$_.StartsWith($PSScriptRoot+'\',[StringComparison]::OrdinalIgnoreCase)})
  if($dep.Data.Source -ine $cpp -or $local.Count -ne 1 -or $local[0] -ine $include){throw 'Actual dependency source/single neutral include differs'}
  $linkCall=Owned $lc.program $link 'Link';[void](Call $linkCall);$program=E $exe
  foreach($r in $runtime){$dest=Join-Path $folder ([IO.Path]::GetFileName($r.path));Fresh @($dest);Copy-Item -LiteralPath $r.path -Destination $dest;$copy=E $dest;if($copy.bytes -ne $r.bytes -or $copy.sha256 -ine $r.sha256){throw 'Runtime copy mismatch'};$copied+=@{original=$r;copy=$copy}}
  V @($helperObject,$dependency,$program);foreach($r in $copied){V @($r.original,$r.copy)}
}catch{$failure=$_.Exception.Message}
$unchanged=$false;try{VerifyAll;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}};$passed=($null -eq $failure -and $unchanged -and $null -ne $program -and $copied.Count -eq 4)
Save $record ([ordered]@{stage='upl_column_public_reader_build_r1';passed=$passed;status=$(if($passed){'current_public_column_CPU_reader_linked_not_run'}else{'public_column_reader_build_failed_retained'});kind='reader';configuration='ReleaseCPU';source_build=$build;source_freeze=$source;adopted_Debug_source_build=$source;retained_compiler_recipe=$recipe;environment_source=$h.environment_source;environment=$h.environment;tools=@($cc.program,$lc.program);libraries=$h.libraries;author_files=$authors;source_code_header_count=265;source_snapshot_stored_in=$source;documentation_snapshot=$d.documentation_snapshot;objects=$objects;CPU_non_main_objects=85;CPU_object_path_substitutions=85;helper_object=$helperObject;link_object_count=86;exact_link_closure_verified=$true;canonical_programs_before=$d.canonical_programs_before;canonical_runtime_before=$runtime;compile_call=$compileCall;link_call=$linkCall;compiler_dependency_record=$dependency;runtime=$copied;program=$program;inputs=@($build,$source,$recipe,$h.environment_source,$h.compile_call,$h.link_call);failure=$failure;build_and_source_bindings_unchanged=$unchanged;historical_private_source_originals_used_as_current=$false;production_build_executed=$false;program_run=$false;help_invoked=$false;solver_started=$false;canonical_program_installed=$false;physical_acceptance=$false})
if(!$passed){throw "Reader build failed; retain all evidence: $record"};Write-Output "Public column pure reader linked, not run: $record"

