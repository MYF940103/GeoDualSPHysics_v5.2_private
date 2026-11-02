param([Parameter(Mandatory=$true)][ValidateSet('component','actual','native')][string]$Kind,[Parameter(Mandatory=$true)][ValidateSet('Debug','Release')][string]$Configuration)
# One helper compilation/link only. Fresh exact current GPU objects; no program invocation.
$ErrorActionPreference='Stop';$Kind=$Kind.ToLowerInvariant();$Configuration=if($Configuration -ieq 'Debug'){'Debug'}else{'Release'}
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $tests 'logs';$tag='upl_gpu_column_'+$Kind+'_'+$Configuration+'_r1'
$folder=Join-Path $tests ('outputs\'+$tag);$record=Join-Path $logs ($tag+'.helper.json');$cpp=Join-Path $tests ('support\upl_gpu_column_'+$Kind+'_r1.cpp');$note=Join-Path $tests ('notes\upl_gpu_column_'+$Kind+'_r1.json')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Changed artifact: $($r.path)"}}}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained path protected: $p"}}}
function Save([string]$p,$value){Fresh @($p);[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Owned($tool,[string[]]$argv,[string]$label){
  $log=Join-Path $logs ($label+'.log');$call=Join-Path $logs ($label+'.call.json');Fresh @($log,$call);V @($tool);[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$saved=$ErrorActionPreference
  Push-Location (Join-Path $repo 'src');try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
  Save $call ([ordered]@{program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;log=(E $log);program_run=$false});return (E $call)
}
Fresh @($folder,$record)
$oldPath=Join-Path $logs ('upl_gpu_wall_wall_actual_'+$Configuration+'_r2.helper.json');$currentPath=Join-Path $logs ('upl_gpu_column_'+$Configuration+'_r1.build.json');$old=J $oldPath;$current=J $currentPath;$source=J $current.source_freeze.path
if($old.status -cne 'actual_authoritative_GPU_objects_helper_linked_not_run' -or $old.fixture -cne 'WallActual' -or !$old.exact_link_closure_verified -or $old.link_object_count -ne 111){throw 'Passed real wall helper compile/link recipe required'}
if(!$current.passed -or $current.status -cne 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -or $current.configuration -cne $Configuration -or @($current.objects).Count -ne 110 -or !$current.objects_exclude_main -or !$current.source_and_protected_artifacts_unchanged){throw 'Fresh matching authoritative GPU column build required'}
$compileRecipe=J $old.compile_call.path;$linkRecipe=J $old.link_call.path
foreach($c in @($compileRecipe,$linkRecipe)){if($c.exit_code -isnot [int] -or $c.exit_code -ne 0 -or !$c.owned_call_exited){throw 'Owned old compiler/linker exits required'}}
$authors=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_gpu_column_helper_r1.json')),(E $cpp),(E $note))
# Include the already reviewed neutral declarations, not an old actual Run or its old admission gates.
$neutralLeaf=if($Kind -ceq 'native'){'upl_cpu_public_native_r1.cpp'}else{'upl_gpu_observer_native_r1.cpp'}
$neutralSha=if($Kind -ceq 'native'){'9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38'}else{'b112f7e78651dde136c2438a02f326522ef4cb35b5603fa1eb17ee24d3437857'}
$neutral=E (Join-Path $tests ('support\'+$neutralLeaf));if($neutral.sha256 -cne $neutralSha){throw 'Neutral declaration include changed'}
$bindings=@((E $oldPath),(E $currentPath),$current.source_freeze,$old.compile_call,$old.link_call,$compileRecipe.program,$linkRecipe.program,$compileRecipe.log,$linkRecipe.log,$neutral)+$authors+@($old.tools)+@($old.libraries)+@($current.objects)+@($source.source)+@($source.canonical_programs_before)+@($source.runtime_before)+@($source.documentation_snapshot.original,$source.documentation_snapshot.snapshot)
foreach($p in $source.current_source_snapshot){$bindings+=@($p.snapshot)};foreach($r in $current.runtime){$bindings+=@($r.original,$r.copy)}
$byName=@{};foreach($o in $current.objects){$base=[IO.Path]::GetFileName($o.path).ToLowerInvariant();if($byName.ContainsKey($base)){throw 'Duplicate current object basename'};$byName[$base]=$o}
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder ('upl_gpu_column_'+$Kind+'_r1.exe');$oldCpp=Join-Path $tests 'support\upl_gpu_wall_actual_r1.cpp';$srcCount=0;$fo=0;$fd=0
$ca=@(foreach($a in $compileRecipe.arguments){if($a -ieq $oldCpp){$cpp;$srcCount++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){'/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){'/Fd'+(Join-Path $folder 'compile.pdb');$fd++}else{$a}})
$outCount=0;$pdbCount=0;$helperCount=0;$maps=@();$la=@(foreach($a in $linkRecipe.arguments){
  if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){'/OUT:'+$exe;$outCount++}
  elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){'/PDB:'+(Join-Path $folder 'link.pdb');$pdbCount++}
  elseif($a -ieq $old.helper_object.path){$obj;$helperCount++}
  elseif($a.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)){$base=[IO.Path]::GetFileName($a).ToLowerInvariant();if(!$byName.ContainsKey($base)){throw "Missing current object: $a"};$maps+=@{old_recipe_object=$a;current=$byName[$base]};$byName[$base].path}
  else{$a}
})
if($srcCount -ne 1 -or $fo -ne 1 -or $fd -ne 1 -or $outCount -ne 1 -or $helperCount -ne 1 -or $maps.Count -ne 110 -or $pdbCount -ne $(if($Configuration -ceq 'Debug'){1}else{0})){throw 'Only declared helper source/object/output remaps allowed'}
$wanted=@($current.objects.path)+@($obj);$actual=@($la|Where-Object{$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)})
if($actual.Count -ne 111 -or @(Compare-Object ($actual|Sort-Object) ($wanted|Sort-Object)).Count -or @($actual|Where-Object{[IO.Path]::GetFileName($_) -ieq 'main.obj'}).Count){throw 'Exact110 current non-main objects plus new helper required'}
V $bindings
$vs=E 'D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat';$cmd=E $env:ComSpec;$env:VSCMD_SKIP_SENDTELEMETRY='1';$global:LASTEXITCODE=$null
$lines=& $cmd.path /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';$envCode=$LASTEXITCODE
if($envCode -isnot [int] -or $envCode -ne 0){throw 'VS environment acquisition failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder);$compile=$null;$link=$null;$program=$null;$failure=$null;$runtime=@()
try{
  $compile=Owned $compileRecipe.program $ca ($tag+'_compile');$c=J $compile.path;if($c.exit_code -isnot [int] -or $c.exit_code -ne 0 -or $c.invocation_failure){throw 'Helper compilation failed'}
  $link=Owned $linkRecipe.program $la ($tag+'_link');$l=J $link.path;if($l.exit_code -isnot [int] -or $l.exit_code -ne 0 -or $l.invocation_failure){throw 'Helper linking failed'}
  $program=E $exe
  foreach($r in $current.runtime){$to=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Fresh @($to);Copy-Item -LiteralPath $r.copy.path -Destination $to;$e=E $to;if($e.bytes -ne $r.copy.bytes -or $e.sha256 -ine $r.copy.sha256){throw 'Runtime copy differs'};$runtime+=@{original=$r.copy;copy=$e}}
}catch{$failure=$_.Exception.Message}
$unchanged=$false;try{V $bindings;V @($vs,$cmd);foreach($r in $runtime){V @($r.original,$r.copy)};$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$passed=(!$failure -and $unchanged -and $null -ne $program -and $runtime.Count -eq 4)
Save $record ([ordered]@{stage='upl_gpu_column_helper_r1';passed=$passed;status=$(if($passed){'current_column_GPU_helper_linked_not_run'}else{'column_GPU_helper_failed_retained'});kind=$Kind;configuration=$Configuration;source_build=(E $currentPath);source_freeze=$current.source_freeze;inputs=$bindings;author_files=$authors;neutral_include=$neutral;tools=$old.tools;libraries=$old.libraries;objects=$current.objects;exact_link_closure_verified=$true;link_object_count=111;helper_object=$(if(Test-Path -LiteralPath $obj){E $obj}else{$null});program=$program;compile_call=$compile;link_call=$link;runtime=$runtime;object_substitutions=$maps;environment_acquisition=@{program=$cmd;script=$vs;typed_exit_code=$envCode};source_and_protected_artifacts_unchanged=$unchanged;failure=$failure;program_run=$false;solver_started=$false;physical_acceptance=$false})
if(!$passed){throw "Helper build failed; retain $record"};Write-Output "One column helper linked, not run: $record"
