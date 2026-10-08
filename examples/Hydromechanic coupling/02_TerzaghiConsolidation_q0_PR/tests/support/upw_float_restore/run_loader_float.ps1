param([ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='loader_debug')
# Isolated real-loader test. Invoke from the configured MSVC x64 environment.
$ErrorActionPreference='Stop'
$caseRoot=(Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$repository=(Get-Item -LiteralPath $caseRoot).Parent
while ($repository -and !(Test-Path -LiteralPath (Join-Path $repository.FullName 'src\VS\DualSPHysics5ReCpu_vs2022.sln'))) {
  $repository=$repository.Parent
}
if (!$repository) { throw 'Cannot locate the authoritative CPU solution.' }
$sourceRoot=Join-Path $repository.FullName 'src\source'
$output=Join-Path $caseRoot "tests\outputs\upw_float_restore\$Label"
$logs=Join-Path $caseRoot 'tests\logs\upw_float_restore'
$buildLog=Join-Path $logs "$Label.build.log"
$runLog=Join-Path $logs "$Label.run.log"
$json=Join-Path $logs "$Label.json"
$manifest=Join-Path $logs "$Label.build.json"
foreach ($path in @($output,$buildLog,$runLog,$json,$manifest)) {
  if (Test-Path -LiteralPath $path) { throw "Refusing to overwrite $path" }
}
New-Item -ItemType Directory -Path $output,$logs -Force | Out-Null
$compiler=(Get-Command cl.exe).Source
$names=@('JPartsLoad4','JPartDataBi4','JPartDataHead','JBinaryData','JRadixSort','JObject','JException','Functions')
$sources=@($names | ForEach-Object { Join-Path $sourceRoot "$_.cpp" })
$harness=Join-Path $PSScriptRoot 'loader_float_harness.cpp'
$inputs=@($sources)+@($names | ForEach-Object { Join-Path $sourceRoot "$_.h" })+@($harness,$PSCommandPath)
$hashes=@($inputs | ForEach-Object { [ordered]@{path=$_;sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash} })
$exe=Join-Path $output 'loader_float_harness.exe'
$flags=@('/nologo','/EHsc','/W3','/Od','/MTd','/Zi','/RTC1','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS',"/I$sourceRoot",'/Fo.\','/Fdloader_float_harness.pdb')
Push-Location $output
try {
  # Production sources retain C++14 to avoid the legacy global byte/C++17 clash.
  & $compiler @flags /std:c++14 /c @sources 2>&1 | Tee-Object -FilePath $buildLog
  if ($LASTEXITCODE -ne 0) { throw 'Loader compilation failed.' }
  $objects=@($names | ForEach-Object { "$_.obj" })
  & $compiler @flags /std:c++17 /Feloader_float_harness.exe $harness @objects 2>&1 | Tee-Object -FilePath $buildLog -Append
  if ($LASTEXITCODE -ne 0) { throw 'Loader Debug harness compilation/link failed.' }
  foreach ($entry in $hashes) {
    if ((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256) { throw "Input changed during build: $($entry.path)" }
  }
  [ordered]@{
    compiler=$compiler
    compiler_version=(Get-Item -LiteralPath $compiler).VersionInfo.FileVersion
    common_flags=$flags
    production_standard='C++14'
    harness_standard='C++17'
    source_inputs=$hashes
    executable=$exe
    executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifest -Encoding UTF8
  & $exe (Join-Path $output 'fixtures') $json 2>&1 | Tee-Object -FilePath $runLog
  if ($LASTEXITCODE -ne 0) { throw 'Loader acceptance failed; inspect JSON and log.' }
}
finally { Pop-Location }
Write-Output "Acceptance result: $json"
