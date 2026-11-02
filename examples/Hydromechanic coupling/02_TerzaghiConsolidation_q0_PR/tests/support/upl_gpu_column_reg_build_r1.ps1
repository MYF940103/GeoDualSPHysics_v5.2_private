param([Parameter(Mandatory=$true)][ValidateSet('periodic','wall','gravity')][string]$Case)
# One selected old helper, freshly linked to current Release objects; no helper/solver execution.
$ErrorActionPreference='Stop';$Case=$Case.ToLowerInvariant();$Configuration='Release'
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$logs=Join-Path $tests 'logs';$tag='upl_gpu_column_reg_'+$Case+'_Release_r1'
$folder=Join-Path $tests ('outputs\'+$tag);$record=Join-Path $logs ($tag+'.helper.json')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Need([bool]$ok,[string]$why){if(!$ok){throw $why}}
function V($rows){foreach($r in $rows){Need (![string]::IsNullOrEmpty($r.path)) 'Missing bound Entry';$a=E $r.path;Need ($a.bytes -eq $r.bytes -and $a.sha256 -ieq $r.sha256) ('Changed artifact: '+$r.path)}}
function Fresh($paths){foreach($p in $paths){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$value){Fresh @($p);[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Owned($tool,[string[]]$argv,[string]$label){
  $log=Join-Path $logs ($label+'.log');$call=Join-Path $logs ($label+'.call.json');Fresh @($log,$call);V @($tool);[IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$code=$null;$failure=$null;$saved=$ErrorActionPreference
  Push-Location (Join-Path $repo 'src');try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log -Append|Out-Host;$code=$LASTEXITCODE}catch{$failure=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
  Save $call ([ordered]@{program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$failure;log=(E $log);helper_or_solver_run=$false});return (E $call)
}
$fixtures=@{
  periodic=@{stem='upl_gpu_perm_actual_r1';cpp='b410dc4b62b18366a2c669678bed5027cd7dd115beccb98d83b9287e41140abf';note='23ebe5bf4f56822cea1ddb80e139d504e8c1efc1ba6280035a745ff9c9dba1aa'}
  wall=@{stem='upl_gpu_wall_actual_r1';cpp='8dcd7ece2011c03eba190bec883997cebf4fa95e8f88680c10d7bbf2623bcea4';note='4c0c80ba21c0cd0978b7bbf2e4645f4641e4fa9ebce310ed56636bcee62433b1'}
  gravity=@{stem='upl_gravity_wall_gpu_r1';cpp='b00656d3fc35b7f33724d75691f59941a360156982d925c89f02e7884c9e5d38';note='bdb51ece0b34b3ca33f2d3722e485edb6ce1f07a20114f1d62def30c9fb73aae'}
};$selected=$fixtures[$Case];$cpp=Join-Path $tests ('support\'+$selected.stem+'.cpp');$note=Join-Path $tests ('notes\'+$selected.stem+'.json');$cppEntry=E $cpp;$noteEntry=E $note
Need ($cppEntry.sha256 -ceq $selected.cpp -and $noteEntry.sha256 -ceq $selected.note) 'Selected immutable helper author identity changed'
$neutral=E (Join-Path $tests 'support\upl_gpu_observer_native_r1.cpp');$neutralNote=E (Join-Path $tests 'notes\upl_gpu_observer_native_r1.json')
Need ($neutral.sha256 -ceq 'b112f7e78651dde136c2438a02f326522ef4cb35b5603fa1eb17ee24d3437857' -and $neutralNote.sha256 -ceq '26dafa6246e7ba38798cc7e3542bb10d9b3926c8303ae17c54dcd35bd499344d') 'Immutable neutral include changed'
# Each selected CPP includes only this support CPP; the remaining headers are covered by current source265/tools.
$localIncludes=@([regex]::Matches([IO.File]::ReadAllText($cpp),'(?m)^#include\s+"(upl_[^"\r\n]+)"')|ForEach-Object{$_.Groups[1].Value});Need ($localIncludes.Count -eq 1 -and $localIncludes[0] -ceq 'upl_gpu_observer_native_r1.cpp') 'Unexpected support include closure'
$oldPath=Join-Path $logs 'upl_gpu_wall_wall_actual_Release_r2.helper.json';$currentPath=Join-Path $logs 'upl_gpu_column_Release_r1.build.json';$old=J $oldPath;$current=J $currentPath;$source=J $current.source_freeze.path
Need ($old.status -ceq 'actual_authoritative_GPU_objects_helper_linked_not_run' -and $old.fixture -ceq 'WallActual' -and $old.configuration -ceq 'Release' -and $old.exact_link_closure_verified -and $old.link_object_count -eq 111) 'Accepted real Release wall compile/link recipe required'
Need ($current.passed -and $current.status -ceq 'full_authoritative_GPU_Rebuild_passed_no_helper_or_program_run' -and $current.configuration -ceq 'Release' -and $current.objects_exclude_main -and @($current.objects).Count -eq 110 -and @($current.runtime).Count -eq 4 -and $current.source_and_protected_artifacts_unchanged -and @($source.source).Count -eq 265 -and @($source.current_source_snapshot).Count -eq 265 -and @($source.canonical_programs_before).Count -eq 7 -and @($source.runtime_before).Count -eq 4) 'Current authoritative source265/Release110/canonical7/runtime4 required'
$compileRecipe=J $old.compile_call.path;$linkRecipe=J $old.link_call.path
foreach($c in @($compileRecipe,$linkRecipe)){Need ($c.owned_call_exited -and $c.exit_code -is [int] -and $c.exit_code -eq 0) 'Real old compiler/linker exits required; no invented historical typed flag'}
$authors=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_gpu_column_reg_build_r1.json')),$cppEntry,$noteEntry,$neutral,$neutralNote)
$bindings=@((E $oldPath),(E $currentPath),$current.source_freeze,$old.compile_call,$old.link_call,$compileRecipe.program,$linkRecipe.program,$compileRecipe.log,$linkRecipe.log)+$authors+@($old.tools)+@($old.libraries)+@($current.tools)+@($current.libraries)+@($current.objects)+@($source.source)+@($source.canonical_programs_before)+@($source.runtime_before)+@($source.documentation_snapshot.original,$source.documentation_snapshot.snapshot,$current.project_call,$current.project_main_object,$current.isolated_GPU_program)
foreach($p in $source.current_source_snapshot){$bindings+=@($p.original,$p.snapshot)};foreach($r in $current.runtime){$bindings+=@($r.original,$r.copy)}
$byName=@{};foreach($o in $current.objects){$base=[IO.Path]::GetFileName($o.path).ToLowerInvariant();Need (!$byName.ContainsKey($base)) 'Duplicate current object basename';$byName[$base]=$o}
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder ($tag+'.exe');$oldCpp=Join-Path $tests 'support\upl_gpu_wall_actual_r1.cpp';$srcCount=0;$fo=0;$fd=0
$ca=@(foreach($a in $compileRecipe.arguments){if($a -ieq $oldCpp){$cpp;$srcCount++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){'/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){'/Fd'+(Join-Path $folder 'compile.pdb');$fd++}else{$a}})
$outCount=0;$pdbCount=0;$helperCount=0;$maps=@();$la=@(foreach($a in $linkRecipe.arguments){
  if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){'/OUT:'+$exe;$outCount++}
  elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){'/PDB:'+(Join-Path $folder 'link.pdb');$pdbCount++}
  elseif($a -ieq $old.helper_object.path){$obj;$helperCount++}
  elseif($a.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)){$base=[IO.Path]::GetFileName($a).ToLowerInvariant();Need ($byName.ContainsKey($base)) ('Missing current object: '+$a);$maps+=@{old_recipe_object=$a;current=$byName[$base]};$byName[$base].path}
  else{$a}
})
Need ($srcCount -eq 1 -and $fo -eq 1 -and $fd -eq 1 -and $outCount -eq 1 -and $helperCount -eq 1 -and $maps.Count -eq 110 -and $pdbCount -eq 0) 'Only selected source/object/output remaps allowed'
$wanted=@($current.objects.path)+@($obj);$actual=@($la|Where-Object{$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)})
Need ($actual.Count -eq 111 -and !(Compare-Object ($actual|Sort-Object) ($wanted|Sort-Object)) -and !@($actual|Where-Object{[IO.Path]::GetFileName($_) -ieq 'main.obj'}).Count) 'Exact current110 non-main plus selected helper required'
$bcrypt=@($old.libraries|Where-Object{[IO.Path]::GetFileName($_.path) -ieq 'bcrypt.lib'});Need ($bcrypt.Count -eq 1 -and @($la|Where-Object{$_ -ieq $bcrypt[0].path}).Count -eq 1) 'Retain exact archived Windows SDK bcrypt library'
Fresh @($folder,$record,(Join-Path $logs ($tag+'_compile.log')),(Join-Path $logs ($tag+'_compile.call.json')),(Join-Path $logs ($tag+'_link.log')),(Join-Path $logs ($tag+'_link.call.json')));V $bindings
$vs=E 'D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat';$cmd=E $env:ComSpec;$env:VSCMD_SKIP_SENDTELEMETRY='1';$global:LASTEXITCODE=$null
$lines=& $cmd.path /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set';$envCode=$LASTEXITCODE;Need ($envCode -is [int] -and $envCode -eq 0) 'VS environment acquisition failed'
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$selectedEnvironment=[ordered]@{};foreach($key in @('PATH','INCLUDE','LIB','LIBPATH','VCToolsInstallDir')){$value=[Environment]::GetEnvironmentVariable($key,'Process');Need (![string]::IsNullOrEmpty($value)) ('Missing VS environment: '+$key);$selectedEnvironment[$key]=$value}
[void](New-Item -ItemType Directory -Path $folder);$compile=$null;$link=$null;$program=$null;$failure=$null;$runtime=@()
try{
  V $bindings;$compile=Owned $compileRecipe.program $ca ($tag+'_compile');$c=J $compile.path;Need ($c.exit_code -is [int] -and $c.exit_code -eq 0 -and !$c.invocation_failure) 'Selected helper compilation failed'
  V $bindings;$link=Owned $linkRecipe.program $la ($tag+'_link');$l=J $link.path;Need ($l.exit_code -is [int] -and $l.exit_code -eq 0 -and !$l.invocation_failure) 'Selected helper linking failed';$program=E $exe
  foreach($r in $current.runtime){$to=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Fresh @($to);Copy-Item -LiteralPath $r.copy.path -Destination $to;$e=E $to;Need ($e.bytes -eq $r.copy.bytes -and $e.sha256 -ieq $r.copy.sha256) 'Runtime copy differs';$runtime+=@{original=$r.copy;copy=$e}}
}catch{$failure=$_.Exception.Message}
$unchanged=$false;try{V $bindings;V @($vs,$cmd);foreach($r in $runtime){V @($r.original,$r.copy)};$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$passed=(!$failure -and $unchanged -and $null -ne $program -and $runtime.Count -eq 4)
Save $record ([ordered]@{stage='upl_gpu_column_reg_build_r1';passed=[bool]$passed;status=$(if($passed){'current_column_GPU_regression_helper_linked_not_run'}else{'column_GPU_regression_helper_failed_retained'});case=$Case;configuration=$Configuration;source_build=(E $currentPath);source_freeze=$current.source_freeze;recipe_source=(E $oldPath);inputs=$bindings;author_files=$authors;neutral_include=$neutral;tools=$old.tools;libraries=$old.libraries;objects=$current.objects;exact_link_closure_verified=$true;link_object_count=111;helper_object=$(if(Test-Path -LiteralPath $obj){E $obj}else{$null});program=$program;compile_call=$compile;link_call=$link;runtime=$runtime;object_substitutions=$maps;environment=@{program=$cmd;script=$vs;typed_exit_code=$envCode;selected=$selectedEnvironment};source_and_protected_artifacts_unchanged=$unchanged;historical_source_originals_revalidated_as_current=$false;failure=$failure;project_rebuilt=$false;program_run=$false;solver_started=$false;physical_acceptance=$false})
if(!$passed){throw "Regression helper build failed; retain $record"};Write-Output "One selected regression helper linked, not run: $record"
