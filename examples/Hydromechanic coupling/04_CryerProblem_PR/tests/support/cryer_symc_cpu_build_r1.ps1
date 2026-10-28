# Build only: two isolated DebugCPU objects plus read-only authoritative objects.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$src=Join-Path $repo 'src'
$out=Join-Path $tests 'outputs\cryer_symc_cpu_build_r1'
$log=Join-Path $tests 'logs\cryer_symc_cpu_r1.build.log'
$manifest=Join-Path $tests 'logs\cryer_symc_cpu_r1.build.json'
$notes=Join-Path $tests 'notes\cryer_symc_cpu_r1.json'
$candidate=Join-Path $out 'JSphCpu.cpp'
$harness=Join-Path $PSScriptRoot 'cryer_symc_cpu_r1.cpp'
$cpuobj=Join-Path $out 'JSphCpu_symc.obj'
$harnessobj=Join-Path $out 'cryer_symc_cpu_r1.obj'
$exe=Join-Path $out 'cryer_symc_cpu_r1.exe'
$canonical=Join-Path $src 'source\JSphCpu.cpp'
$recipePath=Join-Path $tests 'logs\cryer_radial_force_r1.build.json'
$tlog=Join-Path $src 'VS\Intermediate\DualSPHysics_DebugCPU_x64\DualSPHysics.tlog\CL.command.1.tlog'
foreach($p in @($log,$manifest,$cpuobj,$harnessobj,$exe)){
 if(Test-Path -LiteralPath $p){throw "Retained build exists: $p"}
}
if(!(Test-Path -LiteralPath $candidate)){throw 'Prepare the isolated source with apply_patch first'}
$canonicalText=[IO.File]::ReadAllText($canonical).Replace("`r`n","`n")
$candidateText=[IO.File]::ReadAllText($candidate).Replace("`r`n","`n")
$old=@'
                  const double lapw=vol2*(double(pwp1)-pwp2seep)*pdotgrad/double(prr2+Eta2);
                  const double lapz=vol2*pdrz*pdotgrad/double(prr2+Eta2);
'@
$new=@'
                  //-Isolated Cryer probe: symmetric soil-soil Darcy contraction only.
                  double lapdotgrad=pdotgrad;
                  if(!boundp2 && corrmat && CODE_IsFluid(code[p2])){
                    const tmatrix3d cj=corrmat[p2];
                    const double jfrx=cj.a11*pfrx+cj.a12*pfry+cj.a13*pfrz;
                    const double jfry=cj.a21*pfrx+cj.a22*pfry+cj.a23*pfrz;
                    const double jfrz=cj.a31*pfrx+cj.a32*pfry+cj.a33*pfrz;
                    lapdotgrad=.5*(pdotgrad+pdrx*jfrx+pdry*jfry+pdrz*jfrz);
                  }
                  const double lapw=vol2*(double(pwp1)-pwp2seep)*lapdotgrad/double(prr2+Eta2);
                  const double lapz=vol2*pdrz*lapdotgrad/double(prr2+Eta2);
'@
if(([regex]::Matches($canonicalText,[regex]::Escape($old))).Count -ne 1){throw 'Darcy source anchor changed'}
if($candidateText -cne $canonicalText.Replace($old,$new)){throw 'Candidate contains changes outside the Darcy contraction'}
$recipe=Get-Content -LiteralPath $recipePath -Raw -Encoding UTF8 | ConvertFrom-Json
if($recipe.configuration -ne 'DebugCPU'){throw 'Expected the sealed DebugCPU object recipe'}
function HashFiles($paths){
 @($paths | Sort-Object -Unique | ForEach-Object {
  [ordered]@{path=$_;bytes=(Get-Item -LiteralPath $_).Length;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash}
 })
}
foreach($entry in @($recipe.inputs)+@($recipe.runtime)){
 if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256){throw "Authoritative frozen input changed: $($entry.path)"}
}
$env:VSCMD_SKIP_SENDTELEMETRY='1'
$lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
if($LASTEXITCODE){throw 'VS environment failed'}
foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
$compiler=(Get-Command cl.exe).Source;$linker=(Get-Command link.exe).Source
$commands=Get-Content -LiteralPath $tlog -Encoding Unicode
$indexes=@(0..($commands.Length-1) | Where-Object {$commands[$_] -match '(?i)^\^.*\\JSPHCPU\.CPP$'})
if($indexes.Count -ne 1){throw 'Missing/ambiguous authoritative CPU compile command'}
$actualCommand=$commands[$indexes[0]+1]
$tokens=@([regex]::Matches($actualCommand,'(?:[^\s"]|"[^"]*")+') | ForEach-Object {$_.Value.Replace('"','')})
$cpuCompile=@($tokens | Where-Object {$_ -notlike '/Fo*' -and $_ -notlike '/Fd*' -and $_ -notmatch '(?i)\\JSphCpu\.cpp$'})
$cpuCompile+=@("/Fo$cpuobj","/Fd$out\cpu_compile.pdb","/I$src\source",'/sourceDependencies',"$out\cpu.dependencies.json",$candidate)
$oldOut=Join-Path $tests 'outputs\cryer_radial_force_r1_dbg'
function Translate($arg){$arg.Replace($oldOut,$out).Replace('cryer_radial_force_r1','cryer_symc_cpu_r1')}
$harnessCompile=@($recipe.compile | ForEach-Object {Translate $_})
$link=@($recipe.link | ForEach-Object {Translate $_})
$originalCpuObj=Join-Path $src 'VS\Intermediate\DualSPHysics_DebugCPU_x64\JSphCpu.obj'
if(@($link | Where-Object {$_ -eq $originalCpuObj}).Count -ne 1){throw 'CPU object replacement is not unique'}
$link=@($link | ForEach-Object {if($_ -eq $originalCpuObj){$cpuobj}else{$_}})
$canonicalPrograms=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -File |
 Where-Object {$_.Name -like 'DualSPHysics*.exe' -or $_.Extension -eq '.dll' -or $_.Name -eq 'DsphConfig.xml'} |
 ForEach-Object {$_.FullName})
$lianBin=Join-Path $repo 'examples\Hydromechanic coupling\05_LianFlexibleStrip2D_PR\support\bin'
$lianPrograms=@(Get-ChildItem -LiteralPath $lianBin -File | ForEach-Object {$_.FullName})
$protected=HashFiles (@($recipe.inputs.path)+@($recipe.runtime.path)+$canonicalPrograms+$lianPrograms+@($tlog))
$inputs=HashFiles (@($candidate,$harness,$PSCommandPath,$notes,$recipePath,$compiler,$linker)+@($protected.path))
$stages=@();$failure=$null;$runtime=@();$started=[DateTime]::UtcNow.ToString('o')
Push-Location -LiteralPath $out
try{
 foreach($job in @(@{name='isolated_JSphCpu';arguments=$cpuCompile},@{name='harness';arguments=$harnessCompile})){
  $arguments=@($job.arguments)
  Write-Output "COMPILE_STAGE $($job.name)" | Tee-Object -FilePath $log -Append
  $ErrorActionPreference='Continue'
  & $compiler @arguments 2>&1 | Tee-Object -FilePath $log -Append
  $code=$LASTEXITCODE;$ErrorActionPreference='Stop';$stages+=@{stage=$job.name;exit_code=$code}
  if($code){throw "Compile failed: $($job.name); preserve this attempt"}
 }
 $ErrorActionPreference='Continue'
 & $linker @link 2>&1 | Tee-Object -FilePath $log -Append
 $code=$LASTEXITCODE;$ErrorActionPreference='Stop';$stages+=@{stage='link';exit_code=$code}
 if($code){throw 'Isolated link failed; preserve this attempt'}
 $dlls=@(Get-ChildItem -LiteralPath (Join-Path $repo 'bin\windows') -Filter '*.dll' -File)
 foreach($dll in $dlls){Copy-Item -LiteralPath $dll.FullName -Destination $out}
 $cfg=Join-Path $repo 'bin\windows\DsphConfig.xml'
 if(Test-Path -LiteralPath $cfg){Copy-Item -LiteralPath $cfg -Destination $out}
 $runtime=HashFiles (@($exe)+@(Get-ChildItem -LiteralPath $out -File | Where-Object {$_.Extension -eq '.dll' -or $_.Name -eq 'DsphConfig.xml'} | ForEach-Object {$_.FullName}))
}catch{$failure=$_;$_ | Out-String | Tee-Object -FilePath $log -Append}finally{
 Pop-Location
 $changed=@($protected | Where-Object {(Get-FileHash -LiteralPath $_.path -Algorithm SHA256).Hash -ne $_.sha256})
 $warnings=@();if(Test-Path -LiteralPath $log){$warnings=@(Select-String -LiteralPath $log -Pattern 'warning (C|D|LNK)\d+' | ForEach-Object {$_.Line} | Sort-Object -Unique)}
 [ordered]@{
  status=$(if($failure -or $changed.Count){'build_failed_preserved'}else{'built_not_run'})
  started_utc=$started;finished_utc=[DateTime]::UtcNow.ToString('o');configuration='DebugCPU'
  probe_executed=$false;solver_launched=$false;physical_acceptance=$false
  source_comparison=[ordered]@{canonical=HashFiles @($canonical);candidate=HashFiles @($candidate)
   exact_normalized_source_is_single_Darcy_replacement=$true;candidate_line_endings='LF; canonical historical mixed CRLF/LF untouched'
   removed=$old;inserted=$new;soil_pairs_only=$true;boundary_receiver_C_unchanged=$true}
  authoritative_compile_command=$actualCommand;cpu_compile=$cpuCompile;harness_compile=$harnessCompile;link=$link
  inputs=$inputs;protected_before=$protected;protected_after=HashFiles @($protected.path)
  canonical_and_Lian_sources_programs_objects_unchanged=($changed.Count -eq 0);changed_protected=$changed
  stages=$stages;warnings=$warnings;runtime=$runtime
  error=$(if($failure){$failure.Exception.Message}else{$null})
  log=$(if(Test-Path -LiteralPath $log){HashFiles @($log)}else{@()})
  expected_observation_only_after_explicit_main_agent_run='radial_rates.csv and radial_summary.json in a fresh observation directory'
 } | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath $manifest -Encoding UTF8
}
if($failure){throw $failure}
if($changed.Count){throw 'Protected source/program/object changed; inspect retained build receipt'}
Write-Output "BUILT_NOT_RUN $exe"
