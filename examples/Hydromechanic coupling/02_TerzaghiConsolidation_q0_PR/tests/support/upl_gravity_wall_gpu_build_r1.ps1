param([Parameter(Mandatory=$true)][ValidateSet('Debug','Release')][string]$Configuration)
# Build only: replay the accepted wall helper recipe with the current authoritative GPU objects.
$ErrorActionPreference='Stop'
$t=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs';$name='upl_gravity_wall_gpu_'+$Configuration+'_r1'
$folder=Join-Path $t ('outputs\'+$name+'_helper');$record=Join-Path $logs ($name+'.helper.json')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes-ne$r.bytes-or$a.sha256-cne$r.sha256){throw "Changed frozen file: $($r.path)"}}}
function Save($p,$v){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,$label){
 $log=Join-Path $logs ($label+'.log');$receipt=Join-Path $logs ($label+'.call.json')
 if((Test-Path -LiteralPath $log)-or(Test-Path -LiteralPath $receipt)){throw 'Retained native call protected'}
 [IO.File]::WriteAllBytes($log,[byte[]]@());$start=[DateTime]::UtcNow.ToString('o');$failure=$null;$code=$null;$saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
 Push-Location (Join-Path $repo 'src')
 try{$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$failure=[string]$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
 Save $receipt ([ordered]@{program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');owned_call_exited=($code-is[int]);typed_LASTEXITCODE_captured_immediately=($code-is[int]);exit_code=$code;invocation_failure=$failure;log=(E $log);build_only=$true;physical_acceptance=$false})
 if($code-isnot[int]-or$code-ne0-or$failure){throw "Compile/link rejected: $label"};E $receipt
}
if((Test-Path -LiteralPath $folder)-or(Test-Path -LiteralPath $record)){throw 'Fresh build label required'}
$oldp=Join-Path $logs ('upl_gpu_wall_wall_actual_'+$Configuration+'_r2.helper.json');$old=J $oldp
$currentp=Join-Path $logs ('upl_gpu_gravity_init_probe_'+$Configuration+'_r1.helper.json');$current=J $currentp;$s=J $current.source_freeze.path
if($old.status-ne'actual_authoritative_GPU_objects_helper_linked_not_run'-or$old.fixture-ne'WallActual'-or!$old.exact_link_closure_verified-or$old.link_object_count-ne111){throw 'Original accepted wall build recipe required'}
if($current.status-ne'init_guard_probe_linked_not_run'-or$current.configuration-ne$Configuration-or@($current.objects).Count-ne110){throw 'Current authoritative gravity object closure required'}
$cpp=Join-Path $t 'support\upl_gravity_wall_gpu_r1.cpp';$inc=Join-Path $t 'support\upl_gpu_observer_native_r1.cpp'
$authors=@(E $PSCommandPath;E (Join-Path $t 'notes\upl_gravity_wall_gpu_build_r1.json');E $cpp;E (Join-Path $t 'notes\upl_gravity_wall_gpu_r1.json');E $inc)
$inputs=@(E $oldp;E $currentp;$current.source_build;$current.source_freeze)+$authors
function Verify{V $inputs;V $s.source;V $s.canonical_GPU_six_and_CPU_two;V $current.objects;V $old.tools;V $old.libraries;V @($old.compile_call,$old.link_call);foreach($r in $current.runtime){V @($r.original,$r.copy)}}
Verify
$cc=J $old.compile_call.path;$lc=J $old.link_call.path
foreach($c in @($cc,$lc)){if($c.exit_code-isnot[int]-or$c.exit_code-ne0-or!$c.owned_call_exited){throw 'Original compile/link exit missing'}}
$byName=@{};foreach($o in $current.objects){$base=[IO.Path]::GetFileName($o.path).ToLowerInvariant();if($byName.ContainsKey($base)){throw 'Duplicate authoritative object basename'};$byName[$base]=$o}
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder 'upl_gravity_wall_gpu_r1.exe';$oldCpp=Join-Path $t 'support\upl_gpu_wall_actual_r1.cpp'
$src=0;$fo=0;$fd=0;$ca=@(foreach($a in $cc.arguments){if($a-ieq$oldCpp){$cpp;$src++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){'/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){'/Fd'+(Join-Path $folder 'compile.pdb');$fd++}else{$a}})
$on=0;$pn=0;$hn=0;$maps=@();$la=@(foreach($a in $lc.arguments){
 if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){'/OUT:'+$exe;$on++}
 elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){'/PDB:'+(Join-Path $folder 'link.pdb');$pn++}
 elseif($a-ieq$old.helper_object.path){$obj;$hn++}
 elseif($a.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)){$base=[IO.Path]::GetFileName($a).ToLowerInvariant();if(!$byName.ContainsKey($base)){throw "No authoritative replacement: $a"};$replacement=$byName[$base];$maps+=@{old_recipe_object=$a;current=$replacement};$replacement.path}
 else{$a}
})
if($src-ne1-or$fo-ne1-or$fd-ne1-or$on-ne1-or$hn-ne1-or$maps.Count-ne110-or$pn-ne$(if($Configuration-eq'Debug'){1}else{0})){throw 'Only declared source/object/output remaps allowed'}
$wanted=@($current.objects.path)+@($obj);$actual=@($la|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)})
if($actual.Count-ne111-or@(Compare-Object ($actual|Sort-Object) ($wanted|Sort-Object)).Count){throw 'Exact 110 current objects + one new helper required'}
$bcrypt=@($old.libraries|Where-Object {[IO.Path]::GetFileName($_.path)-ieq'bcrypt.lib'});if($bcrypt.Count-ne1-or$la-notcontains$bcrypt[0].path){throw 'Original exact SDK bcrypt library required'}
$vs=E 'D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat';$cmd=E $env:ComSpec;$env:VSCMD_SKIP_SENDTELEMETRY='1';$global:LASTEXITCODE=$null
$lines=& $cmd.path /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
$envCode=$LASTEXITCODE;if($envCode-isnot[int]-or$envCode-ne0){throw 'VS environment acquisition failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i-gt0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder)
$compile=Call $cc.program $ca ($name+'_compile');$link=Call $lc.program $la ($name+'_link')
$runtime=@(foreach($r in $current.runtime){$to=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $to;$e=E $to;if($e.sha256-cne$r.copy.sha256){throw 'Runtime copy mismatch'};[ordered]@{original=$r.copy;copy=$e}})
Verify
Save $record ([ordered]@{status='gravity_wall_helper_linked_not_run';fixture='GravityWallActual';configuration=$Configuration;inputs=$inputs;author_files=$authors;source_build=$current.source_build;source_freeze=$current.source_freeze;objects=$current.objects;link_object_count=111;exact_link_closure_verified=$true;helper_object=(E $obj);tools=$old.tools;libraries=$old.libraries;runtime=$runtime;program=(E $exe);compile_call=$compile;link_call=$link;object_substitutions=$maps;environment_acquisition=@{script=$vs;program=$cmd;typed_exit_code=$envCode};canonical_unchanged=$true;historical_production_paths_revalidated_as_current=$false;solver_or_helper_run=$false;wall_trajectory_admitted=$false;physical_acceptance=$false})
