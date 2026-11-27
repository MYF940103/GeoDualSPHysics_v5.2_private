param([Parameter(Mandatory=$true)][string]$Definition, [string]$OutFile, [switch]$Portable,
      [string]$Option1='opt=', [string]$Option2='opt=')
# Windows PowerShell 5.1 and the inbox .NET Framework. Shared by all frozen package launchers.
$ErrorActionPreference = 'Stop'
$launchOptions = @(@($Option1,$Option2) | Where-Object {$_ -ne 'opt='} | ForEach-Object {
    if (!$_.StartsWith('opt=')) {throw 'Malformed package option'}
    $_.Substring(4)
})
$root = Split-Path -Parent $PSScriptRoot
$plan = (Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $PSScriptRoot 'hydro_frozen_plan_r2.json') | ConvertFrom-Json).PSObject.Properties[$Definition]
$utf8 = New-Object Text.UTF8Encoding($false)
$inv = [Globalization.CultureInfo]::InvariantCulture

function Require($ok, [string]$why) { if (!$ok) { throw $why } }
function Hash-Bytes([byte[]]$payload) {
    $h=[Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($h.ComputeHash($payload)).Replace('-','').ToLowerInvariant() } finally { $h.Dispose() }
}
function Read-Xml([byte[]]$raw) {
    $xml=New-Object Xml.XmlDocument
    $xml.XmlResolver=$null
    $settings=New-Object Xml.XmlReaderSettings
    $settings.DtdProcessing='Prohibit'
    $memory=[IO.MemoryStream]::new($raw)
    $reader=[Xml.XmlReader]::Create($memory,$settings)
    try { $xml.Load($reader) } finally { $reader.Dispose();$memory.Dispose() }
    return ,$xml
}
function Children($node) { return @($node.ChildNodes | Where-Object {$_.NodeType -eq 'Element'}) }
function Attribute-Value($node,$name,$otherwise) {
    if ($null -ne $node -and $node.HasAttribute($name)) {return $node.GetAttribute($name)}
    return $otherwise
}
function Selection($doc,$xpath,$name,$attrs) {
    $chosen=@($doc.SelectNodes($xpath))
    Require ($chosen.Count -le 1 -and $chosen.Count -eq $doc.GetElementsByTagName($name).Count) "Duplicate or misplaced $name"
    if (!$chosen.Count) { return $null }
    $node=$chosen[0]
    Require (@(Children $node).Count -eq 0) "Unexpected child of $name"
    foreach($att in $node.Attributes) {Require ($attrs -ccontains $att.Name) "Unrepresentable attribute $name/$($att.Name)"}
    return ,$node
}
function Number($s) {
    $val=[double]::Parse($s,[Globalization.NumberStyles]::Float,$inv)
    Require (!([double]::IsNaN($val) -or [double]::IsInfinity($val)) -and $val -ge 0) "Expected finite nonnegative value: $s"
    return $val
}
function Byte-Copy($content,$destination) {
    $f=[IO.File]::Open($destination,'CreateNew','Write','None')
    try { $f.Write($content,0,$content.Length) } finally {$f.Dispose()}
}
function Export-Legacy($spec,$raw,$unchanged) {
    Require ((Hash-Bytes $raw) -eq $spec.template_sha256) 'Registered original definition changed'
    if ($unchanged) { Byte-Copy $raw $OutFile; return }
    Require $spec.editable 'Frozen release: use a separately verified publication for edited input.'
    $live=Read-Xml ([IO.File]::ReadAllBytes((Join-Path $root $Definition)))
    $archived=Read-Xml $raw
    $special='/case/execution/special'
    $water="$special/hydromechanics"
    Require ($live.SelectNodes($water).Count -eq 1) 'Missing or duplicate hydromechanics'
    $hyd=$live.SelectSingleNode($water)
    $oldHyd=$archived.SelectSingleNode($water)
    $model=Selection $live "$water/HydroMechModel" 'HydroMechModel' @('value')
    $load=Selection $live "$special/externalload" 'externalload' @('mode','q0','ramptime')
    $drain=Selection $live "$special/drainage" 'drainage' @('mode','start','clock')
    Require ((Attribute-Value $model 'value' '0') -ceq [string]$spec.model) 'Original program cannot represent this HydroMechModel (TPI requires its own runtime).'
    foreach($field in $spec.legacy_keys) {Require ($live.GetElementsByTagName($field).Count -eq 0) "Mixed legacy key $field"}
    $actualNames=@(Children $hyd | ForEach-Object {$_.Name} | Where-Object {$_ -cne 'HydroMechModel'} | Sort-Object)
    Require (($actualNames -join '|') -ceq (@($spec.material_keys | Sort-Object) -join '|')) 'Changed, missing or duplicate material property'
    $specialNode=$live.SelectSingleNode($special)
    $specialNames=@(Children $specialNode | ForEach-Object {$_.LocalName} | Where-Object {$_ -cnotin @('drainage','externalload')} | Sort-Object)
    Require (($specialNames -join '|') -ceq (@($spec.special_keys | Sort-Object) -join '|')) 'Unknown or changed special-block layout for this archived program'
    $m=Attribute-Value $load 'mode' '0'
    $modes=@('None','TopVertical','FlexibleConfinement','TopStripVertical','LianFlexibleStrip','TopKernelBand')
    $idx=[array]::IndexOf(@($modes | ForEach-Object {$_.ToLowerInvariant()}),$m.ToLowerInvariant())
    if ($idx -lt 0) {Require ($m -cmatch '^[0-5]$') "Unknown externalload mode $m";$idx=[int]$m}
    $q=Attribute-Value $load 'q0' '0'
    $r=Attribute-Value $load 'ramptime' '0'
    $qValue=Number $q
    $rValue=Number $r
    Require (($idx -eq 0 -and $qValue -eq 0 -and $rValue -eq 0) -or ($idx -ne 0 -and $qValue -gt 0)) 'Inconsistent load mode, q0 or ramptime'
    $dm=(Attribute-Value $drain 'mode' 'drained').ToLowerInvariant()
    $clock=(Attribute-Value $drain 'clock' 'time').ToLowerInvariant()
    $start=Attribute-Value $drain 'start' '0'
    $null=Number $start
    Require ($dm -in @('drained','freeseepage','off') -and $clock -in @('time','fixedstep')) 'Unsupported drainage mode or clock'
    Require ($dm -eq 'drained' -or (!$drain.HasAttribute('start') -and !$drain.HasAttribute('clock'))) 'Drainage clock/start only belong to drained boundaries'
    $values=@{HydroMechTopLoadMode=[string]$idx;HydroMechTopLoadQ0=$q;HydroMechTopLoadRampTime=$r;
      HydroMechDrainage=[string][int]($dm -eq 'drained');HydroMechDrainageStartTime=$start;
      HydroMechDrainageFixedGrid=[string][int]($clock -eq 'fixedstep');HydroMechFreeSeepage=[string][int]($dm -eq 'freeseepage')}
    foreach($node in @($model,$load,$drain)) {if ($null -ne $node) {[void]$node.ParentNode.RemoveChild($node)}}
    foreach($field in $spec.legacy_keys) {
        $old=$oldHyd.SelectSingleNode($field)
        $changed=$values.ContainsKey($field) -and (Number $values[$field]) -ne (Number $spec.defaults.$field)
        if ($null -eq $old) {Require (!$changed) "Frozen program has no qualified representation of $field";continue}
        $new=$live.ImportNode($old,$true)
        if ($changed) {$new.SetAttribute('value',$values[$field])}
        [void]$hyd.AppendChild($new)
    }
    $f=[IO.File]::Open($OutFile,'CreateNew','Write','None')
    try {$live.Save($f)} finally {$f.Dispose()}
}
function Invoke-Portable($spec, $unchanged) {
    Require $unchanged 'Frozen release: a changed seed or configuration needs an independently verified publication.'
    $stem=$Definition.Substring(0,$Definition.Length-8)
    $archiveDefinition=if ($spec.archive_definition) {[string]$spec.archive_definition} else {$Definition}
    Require ([IO.Path]::GetFileName($archiveDefinition) -ceq $archiveDefinition -and $archiveDefinition.EndsWith('_Def.xml')) 'Invalid frozen definition filename'
    $archiveStem=$archiveDefinition.Substring(0,$archiveDefinition.Length-8)
    $renamed=($archiveStem -cne $stem)
    $allowed=@('--prepare-only','--unattended')
    if ($spec.mode -eq 'p3') {$allowed+='--check-only'}
    if ($spec.mode -eq 'gen') {$allowed+='--smoke'}
    foreach($argument in $launchOptions) {Require ($allowed -contains $argument) "Unsupported option $argument"}
    $prep=('--prepare-only' -in $launchOptions -or '--check-only' -in $launchOptions)
    Require (!$prep -or $launchOptions.Count -eq 1) 'Use the preparation option alone'
    $suffix=if ($spec.mode -in @('p3','seed')) {'_GPU_out'} elseif ('--smoke' -in $launchOptions) {'_smoke_out'} else {'_out'}
    $existing=Join-Path $root ($stem+$suffix)
    Require ($prep -or !(Test-Path -LiteralPath $existing)) "Existing result protected: $existing"
    $zip=Join-Path $root $spec.archive
    Require ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -eq $spec.archive_sha256) "Changed frozen package $zip"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    Require ([IO.Path]::GetFileName($spec.workspace) -ceq $spec.workspace) 'Invalid reproduction directory name'
    $work=Join-Path $root $spec.workspace
    $archiveOutput=Join-Path $work ($archiveStem+$suffix)
    Require ($prep -or !$renamed -or !(Test-Path -LiteralPath $archiveOutput)) "Frozen workspace result protected: $archiveOutput"
    if (!(Test-Path -LiteralPath $work)) {
        # Exclusive directory creation. Existing or interrupted folders are only read/verified.
        $null=New-Item -ItemType Directory -Path $work -ErrorAction Stop
        [IO.Compression.ZipFile]::ExtractToDirectory($zip,$work)
    }
    Require (!((Get-Item -LiteralPath $work).Attributes -band [IO.FileAttributes]::ReparsePoint)) 'Reproduction directory is redirected'
    $bundle=[IO.Compression.ZipFile]::OpenRead($zip)
    try {
        foreach($member in $bundle.Entries) {
            if (!$member.Name) {continue}
            $target=Join-Path $work $member.FullName
            $f=Get-Item -LiteralPath $target
            Require ($f.Length -eq $member.Length) "Changed frozen component $target"
            $ms=$member.Open()
            try {$hash=(Get-FileHash -InputStream $ms -Algorithm SHA256).Hash} finally {$ms.Dispose()}
            Require ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $hash) "Changed frozen component $target"
        }
    } finally {$bundle.Dispose()}
    $original=Join-Path $work ('x'+$archiveStem+'_win64_GPU.bat')
    Write-Host "Original release working directory: $work"
    Push-Location -LiteralPath $work
    try {
        if (!$prep) {
            if (!$renamed) { & $original @launchOptions | Out-Host; return $LASTEXITCODE }
            $lockPath=$archiveOutput+'.lock'
            $lock=[IO.File]::Open($lockPath,'CreateNew','Write','None')
            try {
                Require (!(Test-Path -LiteralPath $existing) -and !(Test-Path -LiteralPath $archiveOutput)) 'A canonical or frozen-workspace result already exists'
                $arguments=$launchOptions
                if ('--unattended' -notin $arguments) {$arguments += '--unattended'}
                & $original @arguments | Out-Host
                $rc=$LASTEXITCODE
                if (Test-Path -LiteralPath $archiveOutput) {
                    $produced=Get-Item -LiteralPath $archiveOutput
                    Require ($produced.PSIsContainer -and $produced.Parent.FullName -ieq $work -and !($produced.Attributes -band [IO.FileAttributes]::ReparsePoint)) "Unsafe output directory after frozen BAT exit $rc : $archiveOutput"
                    Require (!(Test-Path -LiteralPath $existing)) "Output appeared after frozen BAT exit $rc ; archive result retained at $archiveOutput"
                    [IO.Directory]::Move($produced.FullName,$existing)
                    Write-Host "Result directory: $existing"
                }
                return $rc
            } finally {
                $lock.Dispose()
                [IO.File]::Delete($lockPath)
            }
        }
        if ($spec.mode -eq 'p3') { & $original --check-only | Out-Host; return $LASTEXITCODE }
        $out=Join-Path $work ('prepare\'+$stem)
        Require (!(Test-Path -LiteralPath $out)) "Output already exists: $out"
        [void][IO.Directory]::CreateDirectory($out)
        if ($spec.mode -eq 'seed') {
            foreach($ext in @('.xml','.bi4')) {
                [IO.File]::Copy((Join-Path $work ('support\upl_seed_nu030_r1\'+$archiveStem+$ext)),(Join-Path $out ('Case'+$ext)))
            }
        } else {
            & (Join-Path $work 'support\bin\GenCase_win64.exe') ($archiveStem+'_Def') ('prepare\'+$stem+'\Case') '-save:all' | Out-Host
            Require ($LASTEXITCODE -eq 0) "GenCase failed with $LASTEXITCODE"
        }
        Require ((Test-Path -LiteralPath "$out\Case.xml") -and (Test-Path -LiteralPath "$out\Case.bi4")) 'Missing generated input'
        return 0
    } finally {Pop-Location}
}
try {
    Require ($null -ne $plan -and [IO.Path]::GetFileName($Definition) -ceq $Definition) 'Unregistered frozen root definition'
    $spec=$plan.Value
    # Default public LF/CRLF and optional UTF-8 BOM are interchangeable; the archive keeps its exact original bytes.
    $present=[IO.File]::ReadAllText((Join-Path $root $Definition)).Replace(([string][char]13+[char]10),[string][char]10)
    $unchanged=(Hash-Bytes $utf8.GetBytes($present)) -eq $spec.public_sha256
    if ($Portable) {
        Require ($spec.mode -and !$OutFile) 'Unexpected portable case or output override'
        $rc=Invoke-Portable $spec $unchanged
        exit $rc
    }
    Require ($OutFile -and !$launchOptions.Count -and !$spec.mode) 'Expected one legacy output filename'
    $original=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot ('frozen_xml\'+$Definition)))
    Export-Legacy $spec $original $unchanged
    exit 0
} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }

