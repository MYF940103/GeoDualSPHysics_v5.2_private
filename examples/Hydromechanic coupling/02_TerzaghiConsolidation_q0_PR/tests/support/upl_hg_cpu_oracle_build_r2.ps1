param([Parameter(Mandatory=$true)][ValidateSet('DebugCPU','ReleaseCPU')][string]$Configuration,[switch]$ExecutionAuthorized)
# Build the actual-class oracle against the authoritative project objects; do not run it.
$ErrorActionPreference='Stop';if(!$ExecutionAuthorized){throw 'Root review required before this build'}
$Configuration=if($Configuration -ieq 'DebugCPU'){'DebugCPU'}else{'ReleaseCPU'}
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$src=Join-Path $repo 'src'
$tag='upl_hg_cpu_oracle_'+$Configuration+'_r2';$logs=Join-Path $tests 'logs';$out=Join-Path $tests ('outputs\'+$tag)
$record=Join-Path $logs ($tag+'.helper.json');$cpp=Join-Path $PSScriptRoot 'upl_hg_cpu_oracle_r2.cpp'
$obj=Join-Path $out 'oracle.obj';$exe=Join-Path $out 'upl_hg_cpu_oracle_r2.exe';$dep=Join-Path $out 'compile.dependencies.json'
function Need([bool]$b,[string]$why){if(!$b){throw $why}}
function E([string]$p){$f=Get-Item -LiteralPath $p;return [ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){return ([IO.File]::ReadAllText($p)|ConvertFrom-Json)}
function V($entries){foreach($e in @($entries)){$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed bound artifact: '+$e.path)}}
function Fresh($paths){foreach($p in @($paths)){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}}
function Save([string]$p,$v){Fresh @($p);[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
function PassedCall($e){V @($e);$c=J $e.path;Need ($c.direct_native_call -and $c.typed_LASTEXITCODE_captured_immediately -and $c.owned_call_exited -and $c.exit_code -is [int] -and $c.exit_code -eq 0 -and !$c.invocation_failure) 'Actual typed tool exit0 required';V @($c.program);if($c.log){V @($c.log)};return $c}
function Owned($tool,[string[]]$argv,[string]$kind){
  $p=Join-Path $logs ($tag+'_'+$kind+'.call.json');$log=Join-Path $logs ($tag+'_'+$kind+'.log');Fresh @($p,$log)
  $start=[DateTime]::UtcNow.ToString('o');$code=$null;$why=$null;$prior=$ErrorActionPreference;Push-Location $src
  try{$ErrorActionPreference='Continue';$global:LASTEXITCODE=$null;& $tool.path @argv 2>&1|Tee-Object -FilePath $log|Out-Host;$code=$LASTEXITCODE}catch{$why=$_.Exception.Message}finally{Pop-Location;$ErrorActionPreference=$prior}
  Save $p ([ordered]@{program=$tool;arguments=$argv;working_directory=$src;started_utc=$start;ended_utc=[DateTime]::UtcNow.ToString('o');direct_native_call=$true;typed_LASTEXITCODE_captured_immediately=($code -is [int]);owned_call_exited=($code -is [int]);exit_code=$code;invocation_failure=$why;log=(E $log);solver_run=$false});return (E $p)
}
Fresh @($out,$record)
$buildE=E (Join-Path $logs ('upl_hg_'+$Configuration+'_r1.build.json'));$b=J $buildE.path
Need ($b.passed -and $b.stage -ceq 'upl_hg_build_r1' -and $b.configuration -ceq $Configuration -and $b.exact_object_basename_closure -and @($b.objects).Count -eq 86 -and @($b.source_snapshot).Count -eq 265 -and $b.canonical_programs_unchanged -and $b.runtime_unchanged) 'Passed current authoritative CPU build required'
[void](PassedCall $b.project_call)
$recipeE=E (Join-Path $logs $(if($Configuration -ceq 'DebugCPU'){'upl_case02_flux_affine_DebugCPU_r1.helper.json'}else{'upl_case02_flux_operator_ReleaseCPU_r1.helper.json'}));$h=J $recipeE.path
Need ($h.passed -and $h.configuration -ceq $Configuration -and $h.exact_link_closure_verified -and @($h.objects).Count -eq 85 -and @($h.libraries).Count -eq 17) 'Retained same-configuration cl/link recipe required'
$cc=PassedCall $h.compile_call;$lc=PassedCall $h.link_call
Need ([IO.Path]::GetFileName($cc.program.path) -ieq 'cl.exe' -and [IO.Path]::GetFileName($lc.program.path) -ieq 'link.exe') 'Actual MSVC tools required'
$oldCpp=Join-Path $PSScriptRoot $(if($Configuration -ceq 'DebugCPU'){'upl_case02_flux_affine_r1.cpp'}else{'upl_case02_operator_r1.cpp'})
$objects=@($b.objects|Where-Object{[IO.Path]::GetFileName($_.path) -ine 'main.obj'});Need ($objects.Count -eq 85) 'Exactly85 non-main project objects required'
$byName=@{};foreach($e in $objects){$key=[IO.Path]::GetFileName($e.path).ToLowerInvariant();Need (!$byName.ContainsKey($key)) 'Duplicate project object';$byName[$key]=$e}
$authors=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_hg_cpu_oracle_build_r2.json')),(E $cpp),(E (Join-Path $tests 'notes\upl_hg_cpu_oracle_r2.json')))
$bindings=@($buildE,$b.project_call,$b.log,$b.binlog,$b.program,$recipeE,$h.compile_call,$h.link_call,$h.environment_source,$cc.program,$lc.program,$cc.log,$lc.log)+$authors+@($b.inputs)+@($b.objects)+@($h.tools)+@($h.libraries)+@($h.environment.tools)
foreach($pair in @($b.source_snapshot)+@($b.documentation_snapshot,$b.case_readme_snapshot)){$bindings+=@($pair.original,$pair.snapshot)}
foreach($pair in $b.runtime){$bindings+=@($pair.original,$pair.copy)}
$bindings+=@($b.canonical_programs_before);V $bindings
$ca=@();$sources=0;$fo=0;$fd=0;$deps=0
foreach($a in $cc.arguments){if($a -ieq $oldCpp){$ca+=$cpp;$sources++}elseif($a.StartsWith('/Fo',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fo'+$obj;$fo++}elseif($a.StartsWith('/Fd',[StringComparison]::OrdinalIgnoreCase)){$ca+='/Fd'+(Join-Path $out 'compile.pdb');$fd++}elseif($a -ieq $h.compiler_dependency_record.path){$ca+=$dep;$deps++}else{$ca+=$a}}
Need ($sources -eq 1 -and $fo -eq 1 -and $fd -eq 1 -and $deps -eq 1 -and $ca -ccontains '/std:c++17' -and $ca -ccontains '/fp:precise') 'Only source/Fo/Fd/dependency path remaps allowed'
$la=@();$helpers=0;$outs=0;$mapped=0
foreach($a in $lc.arguments){if($a -ieq $h.helper_object.path){$la+=$obj;$helpers++}elseif($a.StartsWith('/OUT:',[StringComparison]::OrdinalIgnoreCase)){$la+='/OUT:'+$exe;$outs++}elseif($a.StartsWith('/PDB:',[StringComparison]::OrdinalIgnoreCase)){$la+='/PDB:'+(Join-Path $out 'link.pdb')}elseif($a.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)){$key=[IO.Path]::GetFileName($a).ToLowerInvariant();Need ($byName.ContainsKey($key)) 'Unexpected linked object';$la+=$byName[$key].path;$mapped++}else{$la+=$a}}
$linked=@($la|Where-Object{$_.EndsWith('.obj',[StringComparison]::OrdinalIgnoreCase)})
Need ($helpers -eq 1 -and $outs -eq 1 -and $mapped -eq 85 -and $linked.Count -eq 86 -and @($linked|Sort-Object -Unique).Count -eq 86) 'Exact85 project objects plus oracle required'
foreach($key in @('INCLUDE','LIB','VCToolsInstallDir','WindowsSdkDir','WindowsSDKVersion')){$v=[string]$h.environment.selected.$key;Need (![string]::IsNullOrWhiteSpace($v)) 'Missing selected VS environment';[Environment]::SetEnvironmentVariable($key,$v,'Process')}
$env:PATH=([IO.Path]::GetDirectoryName($cc.program.path))+';'+$env:PATH
[void](New-Item -ItemType Directory -Path $out);$compile=$null;$link=$null;$program=$null;$runtime=@();$includes=@();$failure=$null
try{
  $compile=Owned $cc.program $ca 'Compile';[void](PassedCall $compile);$d=J $dep;Need ($d.Data.Source -ieq $cpp) 'Source dependency identity differs'
  $includes=@($d.Data.Includes|Sort-Object -Unique|ForEach-Object{E $_});V $bindings
  $link=Owned $lc.program $la 'Link';[void](PassedCall $link);$program=E $exe
  foreach($pair in $b.runtime){$to=Join-Path $out ([IO.Path]::GetFileName($pair.copy.path));Fresh @($to);Copy-Item -LiteralPath $pair.copy.path -Destination $to;$copy=E $to;Need ($copy.bytes -eq $pair.copy.bytes -and $copy.sha256 -ieq $pair.copy.sha256) 'Runtime copy differs';$runtime+=@{original=$pair.copy;copy=$copy}}
}catch{$failure=$_.Exception.Message}
$unchanged=$false;try{V $bindings;V $includes;foreach($pair in $runtime){V @($pair.original,$pair.copy)};$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$passed=(!$failure -and $unchanged -and $null -ne $program -and $runtime.Count -eq 4)
Save $record ([ordered]@{stage='upl_hg_cpu_oracle_build_r2';passed=$passed;configuration=$Configuration;source_build=$buildE;inputs=$bindings;project_objects=$objects;object_count=85;helper_object=$(if(Test-Path -LiteralPath $obj){E $obj}else{$null});compile_call=$compile;link_call=$link;compiler_dependency_record=$(if(Test-Path -LiteralPath $dep){E $dep}else{$null});actual_includes=$includes;program=$program;runtime=$runtime;frozen_inputs_unchanged=$unchanged;failure=$failure;actual_project_classes_no_stubs=$true;canonical_program_installed=$false;program_run=$false;solver_run=$false;physical_acceptance=$false})
if(!$passed){throw ('Build failed; inspect fresh retained record: '+$record)};Write-Output ('Actual CPU oracle linked, not run: '+$record)
