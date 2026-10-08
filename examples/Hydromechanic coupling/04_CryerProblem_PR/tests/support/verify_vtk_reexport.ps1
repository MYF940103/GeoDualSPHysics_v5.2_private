# Re-export saved BI4 only; this script never runs a solver or deletes old VTK.
# Default: compare the first/middle/last saved frames of four completed tests.
# Full regeneration into a NEW directory, with the same fields:
#   powershell -File tests/support/verify_vtk_reexport.ps1 -Full -Group gpu_releasecheck
# Optional: -OutputDirectory tests/outputs/vtk_restored_new
# The JSON report also gives each group's original-name regeneration arguments.
[CmdletBinding()]
param(
    [ValidateSet('all','batstyle_smoke','cpu_peak','cpu_peak_dp002','gpu_releasecheck')]
    [string]$Group = 'all',
    [switch]$Full,
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
$caseRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$repoRoot = (Resolve-Path (Join-Path $caseRoot '../../..')).Path
$partVtk = Join-Path $repoRoot 'bin/windows/PartVTK_win64.exe'
$runTag = 'vtk_reexport_20261008'
if ($Full) { $runTag += '_full_' + $Group }
if (-not $OutputDirectory) { $OutputDirectory = 'tests/outputs/' + $runTag }
if (-not [IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory = Join-Path $caseRoot $OutputDirectory
}
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$runTag = Split-Path -Leaf $OutputDirectory
if (Test-Path -LiteralPath $OutputDirectory) {
    throw "Choose a new output directory; existing data will not be overwritten: $OutputDirectory"
}
$logDirectory = Join-Path $caseRoot 'tests/logs'
$reportPath = Join-Path $logDirectory ($runTag + '.json')
if (Test-Path -LiteralPath $reportPath) { throw "Report already exists: $reportPath" }

# Field selections were checked against the existing binary VTK headers.
# The small CPU peak export omits Mk; the other three include unsigned-short Mk.
$basic = '-all,+idp,+vel,+rhop,+press,+type,+excessporepress,+fstype,+porepress,+porepress0'
$soil = $basic + ',+mk,+fsnormal,+kplastic,+sigma_ij,+sigma_kk'
$groups = @(
    @{ Id='batstyle_smoke'; Out='tests/outputs/CaseCryerProblem_PR_dp002_rampclosed_nu030_batstyle_smoke_out'; Frames=@(0,1); Vars=$soil+',+hydromechloadace' },
    @{ Id='cpu_peak'; Out='tests/outputs/cpu_release_peak/CaseCryerProblem_PR_cpu_rel_peak_out'; Frames=@(0,31,61); Vars=$basic },
    @{ Id='cpu_peak_dp002'; Out='tests/outputs/cpu_release_peak_dp002/CaseCryerProblem_PR_cpu_rel_peak_dp002_out'; Frames=@(0,31,61); Vars=$soil },
    @{ Id='gpu_releasecheck'; Out='tests/outputs/gpu_releasecheck/CaseCryerProblem_PR_gpu_releasecheck_nu030_out'; Frames=@(0,500,1000); Vars=$soil }
)
if ($Group -ne 'all') { $groups = @($groups | Where-Object { $_.Id -eq $Group }) }
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$results = @()
foreach ($item in $groups) {
    $originalOutput = Join-Path $caseRoot $item.Out
    $dataDirectory = Join-Path $originalOutput 'data'
    $prefix = Join-Path $OutputDirectory ($item.Id + '_PartFluid')
    $arguments = @('-dirin', $dataDirectory, '-savevtk', $prefix,
        '-onlytype:-all,fluid', ('-vars:' + $item.Vars))
    if (-not $Full) { $arguments += '-files:' + ($item.Frames -join ',') }
    $logPath = Join-Path $logDirectory ($runTag + '_' + $item.Id + '.log')
    & $partVtk @arguments 2>&1 | Out-File -LiteralPath $logPath -Encoding utf8
    $exportExitCode = $LASTEXITCODE
    $samples = @()
    foreach ($frame in $item.Frames) {
        $suffix = '_{0:D4}.vtk' -f $frame
        $original = Join-Path (Join-Path $originalOutput 'particles') ('PartFluid' + $suffix)
        $regenerated = $prefix + $suffix
        $same = $null
        $oldSize = $null
        $oldHash = $null
        $originalExists = Test-Path -LiteralPath $original
        if ($originalExists) {
            $oldSize = (Get-Item -LiteralPath $original).Length
            $oldHash = (Get-FileHash -LiteralPath $original -Algorithm SHA256).Hash
        }
        $newSize = $null
        $newHash = $null
        if (Test-Path -LiteralPath $regenerated) {
            $newSize = (Get-Item -LiteralPath $regenerated).Length
            $newHash = (Get-FileHash -LiteralPath $regenerated -Algorithm SHA256).Hash
            if ($originalExists) { $same = ($oldSize -eq $newSize -and $oldHash -eq $newHash) }
        }
        $samples += [ordered]@{ frame=$frame; original=$original; regenerated=$regenerated;
            original_exists=$originalExists;
            original_bytes=$oldSize; regenerated_bytes=$newSize;
            original_sha256=$oldHash; regenerated_sha256=$newHash; byte_identical=$same }
    }
    $failedSamples = @($samples | Where-Object {
        $null -eq $_.regenerated_sha256 -or $_.byte_identical -eq $false -or
        (-not $Full -and -not $_.original_exists)
    })
    $passed = ($exportExitCode -eq 0 -and $failedSamples.Count -eq 0)
    $results += [ordered]@{ group=$item.Id; source_data=$dataDirectory;
        source_partinfo=(Join-Path $dataDirectory 'PartInfo.ibi4');
        tool_arguments=$arguments; export_exit_code=$exportExitCode; log=$logPath;
        full_original_name_arguments=@('-dirin', $dataDirectory, '-savevtk',
            (Join-Path $originalOutput 'particles/PartFluid'), '-onlytype:-all,fluid', ('-vars:' + $item.Vars));
        passed=$passed; samples=$samples }
    Write-Output ($item.Id + ': verification passed = ' + $passed)
}
$allPassed = @($results | Where-Object { -not $_.passed }).Count -eq 0
[ordered]@{ created=(Get-Date).ToString('o'); mode=$(if ($Full) {'full_reexport'} else {'sample_validation'});
    case_root=$caseRoot; output_directory=$OutputDirectory; tool=$partVtk;
    tool_sha256=(Get-FileHash -LiteralPath $partVtk -Algorithm SHA256).Hash;
    tool_version='PartVTK v5.0.206 (12-04-2023)';
    scope='Only four tests/outputs groups; no root release outputs or refinement data';
    deletion_performed=$false; passed=$allPassed;
    all_samples_byte_identical=(@($results.samples | Where-Object { $_.byte_identical -ne $true }).Count -eq 0);
    groups=$results
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output ('Report: ' + $reportPath)
if (-not $allPassed) { exit 1 }
