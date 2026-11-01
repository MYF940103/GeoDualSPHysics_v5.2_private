$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$receipt=Join-Path $tests 'logs\upl_p3_time_build_r1.json'
if(Test-Path -LiteralPath $receipt){throw 'Retained build receipt protected'}
function Entry([string]$path){
  $f=Get-Item -LiteralPath $path
  [ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$sources=@()
foreach($name in @('JSphCpu.h','JSphCpu.cpp','JSphCpuSingle.cpp')){
  $original=Entry (Join-Path $repo "src\source\$name")
  $snapshot=Entry (Join-Path $tests "outputs\upl_p3_time_source_r1\$name")
  if($original.sha256 -ne $snapshot.sha256 -or $original.bytes -ne $snapshot.bytes){throw "Prebuild source changed: $name"}
  $sources+=@{original=$original;snapshot=$snapshot}
}
$logs=@(Entry (Join-Path $tests 'logs\upl_p3_time_cpu_debug_r1.log');Entry (Join-Path $tests 'logs\upl_p3_time_cpu_release_r1.log'))
foreach($log in $logs){
  if(!(Select-String -LiteralPath $log.path -SimpleMatch 'DualSPHysics5.2CPU_win64' -Quiet)){throw 'Build target line absent'}
}
$programs=@(Entry (Join-Path $repo 'bin\windows\DualSPHysics5.2CPU_win64_debug.exe');Entry (Join-Path $repo 'bin\windows\DualSPHysics5.2CPU_win64.exe'))
$result=[ordered]@{
  status='DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests'
  utc=[DateTime]::UtcNow.ToString('o')
  git_base=(& git -C $repo rev-parse HEAD)
  source=$sources;logs=$logs;programs=$programs
  msbuild_exit_codes=@{DebugCPU=0;ReleaseCPU=0}
  scope='Private CPU necessary coupled-wave/diffusion scales, continuous-domain and fixed-step rejection; no public XML or GPU changes'
  solver_started=$false;physical_acceptance=$false
}
[IO.File]::WriteAllText($receipt,($result|ConvertTo-Json -Depth 10)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "SEALED $receipt"
