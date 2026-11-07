param(
    [Parameter(Mandatory=$true)][string]$SourceOut,
    [ValidateRange(1,9223372036854775807)][long]$ExpectedSteps=4000000,
    [ValidateRange(1,9223372036854775807)][long]$ExpectedPartFiles=1001,
    [ValidateRange(0,9223372036854775807)][long]$ExpectedPartsOut=0,
    [ValidatePattern('^Part_[0-9]{4,}\.bi4$')][string]$ExpectedPrePart='Part_1000.bi4'
)
# Read-only scheduling check. The receiving native loader certifies the PRE state.
$ErrorActionPreference='Stop'
try {
    $csv=Join-Path $SourceOut 'Run.csv'
    $pre=Join-Path (Join-Path $SourceOut 'data') $ExpectedPrePart
    if(!(Test-Path -LiteralPath $csv -PathType Leaf)){throw "Run.csv not found: $csv"}
    if(!(Test-Path -LiteralPath $pre -PathType Leaf)){throw "Scheduled PRE file not found: $pre"}
    $text=[IO.File]::ReadAllText((Get-Item -LiteralPath $csv).FullName)
    $first=($text -split '\r?\n',2)[0]
    if($first -notmatch '^(#?RunName)([;,])'){throw 'Unsupported Run.csv first header: expected #RunName; or RunName; (comma also accepted).'}
    $delimiter=[char]$Matches[2]
    if($first.StartsWith('#')){$text=$text.Substring(1)}
    # Import-Csv treats the leading # header as a comment. Strip that single #
    # before ConvertFrom-Csv; do not reinterpret the first numeric row as headers.
    $rows=@(ConvertFrom-Csv -InputObject $text -Delimiter $delimiter)
    if($rows.Count -ne 1){throw "Expected one Run.csv record; observed $($rows.Count)."}
    $row=$rows[0]
    foreach($name in @('Steps','PartFiles','PartsOut')){
        if(@($row.PSObject.Properties.Name | Where-Object {$_ -ceq $name}).Count -ne 1){throw "Required Run.csv column missing or duplicated: $name"}
        if([string]$row.$name -notmatch '^[0-9]+$'){throw "Noninteger Run.csv $name value: $($row.$name)"}
    }
    if([long]$row.Steps -ne $ExpectedSteps -or [long]$row.PartFiles -ne $ExpectedPartFiles -or [long]$row.PartsOut -ne $ExpectedPartsOut){
        throw "Source schedule differs: Steps=$($row.Steps), PartFiles=$($row.PartFiles), PartsOut=$($row.PartsOut); expected $ExpectedSteps/$ExpectedPartFiles/$ExpectedPartsOut."
    }
    Write-Host "PASS scheduling only: $SourceOut; Steps=$($row.Steps), PartFiles=$($row.PartFiles), PartsOut=$($row.PartsOut), data/$ExpectedPrePart exists."
    Write-Host 'Native PRE certification and physical equilibrium are not established by this CSV/file check.'
    exit 0
} catch {
    [Console]::Error.WriteLine('FAIL scheduling check: '+$_.Exception.Message)
    exit 1
}
