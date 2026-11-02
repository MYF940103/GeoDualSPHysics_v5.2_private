param([Parameter(Mandatory=$true)][ValidateSet('Debug','Release')][string]$Configuration)
# Compile/link one fresh GPU initialization guard probe only. No solver/program invocation.
$ErrorActionPreference='Stop'
$t=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $t).Parent.Parent.Parent.Parent.FullName
$logs=Join-Path $t 'logs'
$name='upl_gpu_gravity_init_probe_'+$Configuration+'_r1'
$folder=Join-Path $t ('outputs\'+$name+'_helper')
$record=Join-Path $logs ($name+'.helper.json')
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){Get-Content -LiteralPath $p -Raw|ConvertFrom-Json}
function V($rows){foreach($r in $rows){$a=E $r.path;if($a.bytes-ne$r.bytes-or$a.sha256-cne$r.sha256){throw "Changed frozen file: $($r.path)"}}}
function Save($p,$v){if(Test-Path -LiteralPath $p){throw "Retained record protected: $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function Call($tool,[string[]]$argv,$label){
 $log=Join-Path $logs ($label+'.log');$receipt=Join-Path $logs ($label+'.call.json')
 if((Test-Path -LiteralPath $log)-or(Test-Path -LiteralPath $receipt)){throw 'Retained native call protected'}
 [IO.File]::WriteAllBytes($log,[byte[]]@())
 $start=[DateTime]::UtcNow.ToString('o');$failure=$null;$code=$null;$saved=$ErrorActionPreference;$ErrorActionPreference='Continue'
 Push-Location (Join-Path $repo 'src')
 try{$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$failure=[string]$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$saved}
 Save $receipt ([ordered]@{program=$tool;arguments=$argv;working_directory=(Join-Path $repo 'src');started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');owned_call_exited=($code-is[int]);typed_LASTEXITCODE_captured_immediately=($code-is[int]);exit_code=$code;invocation_failure=$failure;log=(E $log);build_only=$true;physical_acceptance=$false})
 if($code-isnot[int]-or$code-ne0-or$failure){throw "Compile/link rejected: $label"}
 E $receipt
}
if((Test-Path -LiteralPath $folder)-or(Test-Path -LiteralPath $record)){throw 'Fresh build label required'}
$hp=Join-Path $logs ('upl_gpu_gravity_endpoint_'+$Configuration+'_r1.helper.json')
$h=J $hp;$b=J $h.source_build.path;$s=J $b.source_freeze.path
if($h.status-ne'actual_authoritative_GPU_objects_helper_linked_not_run'-or$h.fixture-ne'GravityPeriodicEndpoint'-or!$h.exact_link_closure_verified-or$h.link_object_count-ne111-or@($h.objects).Count-ne110){throw 'Frozen authoritative object closure missing'}
$cpp=Join-Path $t 'support\upl_gpu_gravity_init_probe_r1.cpp';$inc=Join-Path $t 'support\upl_gpu_observer_native_r1.cpp'
$authors=@(E $PSCommandPath;E (Join-Path $t 'notes\upl_gpu_gravity_init_probe_build_r1.json');E $cpp;E (Join-Path $t 'notes\upl_gpu_gravity_init_probe_r1.json');E $inc)
$inputs=@(E $hp;$h.source_build;$b.source_freeze)+$authors
function Verify{V $inputs;V $s.source;V $s.canonical_GPU_six_and_CPU_two;V $h.objects;V $h.tools;V $h.libraries;V @($h.compile_call,$h.link_call);foreach($r in $h.runtime){V @($r.original,$r.copy)}}
Verify
$cc=J $h.compile_call.path;$lc=J $h.link_call.path
foreach($c in @($cc,$lc)){if($c.exit_code-isnot[int]-or$c.exit_code-ne0-or!$c.owned_call_exited){throw 'Original compile/link exit missing'}}
$obj=Join-Path $folder 'helper.obj';$exe=Join-Path $folder 'upl_gpu_gravity_init_probe_r1.exe'
$oldCpp=Join-Path $t 'support\upl_gpu_gravity_endpoint_r1.cpp'
$src=0;$fo=0;$fd=0;$ca=@(foreach($a in $cc.arguments){if($a-ieq$oldCpp){$cpp;$src++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){'/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){'/Fd'+(Join-Path $folder 'compile.pdb');$fd++}else{$a}})
$on=0;$pn=0;$hn=0;$la=@(foreach($a in $lc.arguments){if($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){'/OUT:'+$exe;$on++}elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){'/PDB:'+(Join-Path $folder 'link.pdb');$pn++}elseif($a-ieq$h.helper_object.path){$obj;$hn++}else{$a}})
if($src-ne1-or$fo-ne1-or$fd-ne1-or$on-ne1-or$hn-ne1-or$pn-ne$(if($Configuration-eq'Debug'){1}else{0})){throw 'Only source/helper/output remaps allowed'}
$wanted=@($h.objects.path)+@($obj);$actual=@($la|Where-Object {$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)})
if($actual.Count-ne111-or@(Compare-Object ($actual|Sort-Object) ($wanted|Sort-Object)).Count){throw 'Exact 110 original objects + Init probe required'}
$vs=E 'D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat';$cmd=E $env:ComSpec
$env:VSCMD_SKIP_SENDTELEMETRY='1';$global:LASTEXITCODE=$null
$lines=& $cmd.path /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
$envCode=$LASTEXITCODE;if($envCode-isnot[int]-or$envCode-ne0){throw 'VS environment acquisition failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i-gt0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
[void](New-Item -ItemType Directory -Path $folder)
$compile=Call $cc.program $ca ($name+'_compile')
$link=Call $lc.program $la ($name+'_link')
$runtime=@(foreach($r in $h.runtime){$to=Join-Path $folder ([IO.Path]::GetFileName($r.copy.path));Copy-Item -LiteralPath $r.copy.path -Destination $to;$e=E $to;if($e.sha256-cne$r.copy.sha256){throw 'Runtime copy mismatch'};[ordered]@{original=$r.copy;copy=$e}})
Verify
Save $record ([ordered]@{status='init_guard_probe_linked_not_run';fixture='GravityInitProbe';configuration=$Configuration;inputs=$inputs;author_files=$authors;source_build=$h.source_build;source_freeze=$b.source_freeze;objects=$h.objects;link_object_count=111;helper_object=(E $obj);tools=$h.tools;libraries=$h.libraries;runtime=$runtime;program=(E $exe);compile_call=$compile;link_call=$link;environment_acquisition=@{script=$vs;program=$cmd;typed_exit_code=$envCode};canonical_unchanged=$true;solver_or_helper_run=$false;physical_acceptance=$false})
