# Authoritative CPU builds only. Execute only after root finishes/freezes source; no solver or GenCase here.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$receipt=Join-Path $tests 'logs\upl_p3_perm_build_r2.json'
$snapshot=Join-Path $tests 'outputs\upl_p3_perm_source_r2'
$prior=Join-Path $tests 'outputs\upl_p3_perm_prebuild_r2'
foreach($p in @($receipt,$snapshot,$prior)){if(Test-Path -LiteralPath $p){throw 'Fresh build artifacts required'}}
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
New-Item -ItemType Directory -Path $snapshot,$prior|Out-Null
$sources=@()
foreach($name in @('JSphCpu.h','JSphCpu.cpp','JSphCpuSingle.cpp')){
  $path=Join-Path $repo "src\source\$name";$before=Entry $path;$dest=Join-Path $snapshot $name
  Copy-Item -LiteralPath $path -Destination $dest;$copy=Entry $dest
  if($copy.sha256 -ne $before.sha256){throw 'Source snapshot mismatch'}
  $sources+=@{original=$before;snapshot=$copy}
}
$programNames=@('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2CPU_win64.exe')
$oldPrograms=@(foreach($name in $programNames){
  $p=Join-Path $repo "bin\windows\$name";$before=Entry $p;$dest=Join-Path $prior $name
  Copy-Item -LiteralPath $p -Destination $dest;$copy=Entry $dest
  if($copy.sha256 -ne $before.sha256){throw 'Prior program copy mismatch'}
  @{original=$before;snapshot=$copy}
})
$msbuild='D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe'
$solution=Join-Path $repo 'src\VS\DualSPHysics5ReCpu_vs2022.sln'
$project=Join-Path $repo 'src\VS\DualSPHysics5ReCpu.vcxproj'
$inputs=@(Entry $PSCommandPath;Entry $msbuild;Entry $solution;Entry $project)
$codes=@{};$buildLogs=@();$start=[DateTime]::UtcNow.ToString('o')
foreach($config in @('DebugCPU','ReleaseCPU')){
  $log=Join-Path $tests "logs\upl_p3_perm_$($config)_build_r2.log"
  if(Test-Path -LiteralPath $log){throw 'Build log retained'}
  $old=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $msbuild $solution /m /t:Rebuild "/p:Configuration=$config" /p:Platform=x64 /v:minimal *> $log
  $codes[$config]=$LASTEXITCODE;$ErrorActionPreference=$old;$buildLogs+=Entry $log
  Write-Output "MSBUILD $config exit=$($codes[$config])"
  if($codes[$config]){Get-Content -LiteralPath $log -Tail 30;break}
}
foreach($s in $sources){if((Entry $s.original.path).sha256 -ne $s.snapshot.sha256){throw 'Source changed during build'}}
$passed=$codes.DebugCPU -eq 0 -and $codes.ContainsKey('ReleaseCPU') -and $codes.ReleaseCPU -eq 0
$result=[ordered]@{status=if($passed){'DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'}else{'build_failed_retained'};started_utc=$start;utc=[DateTime]::UtcNow.ToString('o');git_base=(& git -C $repo rev-parse HEAD);source=$sources;inputs=$inputs;prior_programs=$oldPrograms;logs=$buildLogs;programs=@($programNames|ForEach-Object {Entry (Join-Path $repo "bin\windows\$_")});msbuild_exit_codes=$codes;scope='Private CPU smooth k(J) candidate after bounded constant-k wall checkpoint; default OFF unchanged, no public XML/GPU or general sufficient stability claim';solver_started=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($receipt,($result|ConvertTo-Json -Depth 10)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
if(!$passed){throw 'Authoritative build failed; retain snapshot and logs'}
Write-Output "SEALED $receipt"
