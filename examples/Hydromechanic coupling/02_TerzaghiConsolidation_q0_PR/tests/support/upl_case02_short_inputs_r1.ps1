param([switch]$PrepareAuthorized)
# Prepare two private candidate inputs only. Never start GenCase, a solver, a reader or a build.
$ErrorActionPreference='Stop'
if(!$PrepareAuthorized){throw 'Root full review and explicit input-only preparation authorization required'}
$testPath=Split-Path -Parent $PSScriptRoot
$repoPath=(Get-Item -LiteralPath $testPath).Parent.Parent.Parent.Parent.FullName
$sourcePrefix=Join-Path $testPath 'outputs\symc_1d_short_r1_cpu_old\symc_1d_short_r1_cpu_old'
$targetPath=Join-Path $testPath 'outputs\upl_case02_short_r1_seed'
$recordPath=Join-Path $testPath 'logs\upl_case02_short_r1.inputs.json'
$notePath=Join-Path $testPath 'notes\upl_case02_short_inputs_r1.json'
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Input changed: $($r.path)"}}}
function Fresh($paths){foreach($path in $paths){if(Test-Path -LiteralPath $path){throw "Retained path protected: $path"}}}
$windows=@(
    [ordered]@{name='coarse';dt='0.0000025';steps=5000},
    [ordered]@{name='half';dt='0.00000125';steps=10000}
)
$configs=@($windows|ForEach-Object{Join-Path $testPath ('configs\upl_case02_short_'+$_.name+'_r1.xml')})
Fresh (@($targetPath,$recordPath)+$configs)
$expected=[ordered]@{
    '.xml'='06ea556c3555ad86d53491984897120119596bc90f209c0545196a4f3beced9c';
    '.bi4'='f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac';
    '_Normals.nbi4'='0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97'
}
$sources=@();foreach($suffix in $expected.Keys){$e=Entry ($sourcePrefix+$suffix);if($e.sha256 -cne $expected[$suffix]){throw "Retained seed differs: $suffix"};$sources+=@($e)}
$scheduleSources=@(Entry (Join-Path $repoPath 'src\source\JDsOutputTime.cpp');Entry (Join-Path $repoPath 'src\source\JSphCpuSingle.cpp'))
if($scheduleSources[0].sha256 -cne 'b26c1b87f090b28bdc72c28d6ed7dfeee0ad7a0bcd28eb428f1ae72716d0c72f' -or $scheduleSources[1].sha256 -cne '1b2aa2741338c2046380727a680420a8df3bc1d2fedc071f8e3b2bfeaf41f394'){throw 'Reviewed native output scheduling source differs'}
$authorEntries=@(Entry $PSCommandPath;Entry $notePath)
$segments=@(
    [ordered]@{time='0';timeout='0.0000249999999'},
    [ordered]@{time='0.0099749999';timeout='0.00000249999999'},
    [ordered]@{time='0.0100249999';timeout='0.0000249999999'}
)
# Offline binary64 transcription of GetNextTime and the ordinary Run save predicate; not integration.
function PredictSaves([double]$dt,[int]$steps){
    [double[]]$base=@(0,0.0099749999,0.0100249999);[double[]]$cad=@(0.0000249999999,0.00000249999999,0.0000249999999)
    [int]$index=0;[double]$time=0
    function NextTime([double]$now,[double[]]$base,[double[]]$cad,[ref]$index){
        while($index.Value+1 -lt $base.Length -and $now -ge $base[$index.Value+1]){$index.Value++}
        [double]$tb=$base[$index.Value];[double]$tnext=if($index.Value+1 -lt $base.Length){$base[$index.Value+1]}else{[double]::MaxValue}
        if($now -lt $tb){return $tb}
        [uint32]$nt=[math]::Truncate(($now-$tb)/$cad[$index.Value]);[double]$next=$tb+$cad[$index.Value]*$nt
        while($next -le $now){$next=$tb+$cad[$index.Value]*$nt;$nt++}
        if($next -gt $tnext){$next=$tnext};return [double]$next
    }
    $rows=[Collections.Generic.List[object]]::new();$rows.Add([ordered]@{step=0;time=0.0})
    [double]$next=NextTime $time $base $cad ([ref]$index)
    for($step=1;$step -le $steps;$step++){
        [double]$time=$time+$dt
        if($time -ge $next -or $time -ge 0.0125 -or $step -ge $steps){$rows.Add([ordered]@{step=$step;time=$time});[double]$next=NextTime $time $base $cad ([ref]$index)}
    }
    return ,$rows
}
$coarse=PredictSaves 0.0000025 5000;$half=PredictSaves 0.00000125 10000
$declaredCoarse=@(0..399|ForEach-Object{10*$_})+@(3991..4010)+@(402..500|ForEach-Object{10*$_})
if($coarse.Count -ne 519 -or $half.Count -ne 519 -or $declaredCoarse.Count -ne 519){throw 'Declared sample count differs'}
[double]$maxTimeDifference=0
for($i=0;$i -lt 519;$i++){
    if($coarse[$i].step -ne $declaredCoarse[$i] -or $half[$i].step -ne 2*$declaredCoarse[$i]){throw 'Actual Run output predicate does not select the declared paired steps'}
    $maxTimeDifference=[math]::Max($maxTimeDifference,[math]::Abs($coarse[$i].time-$half[$i].time))
}
if($maxTimeDifference -gt 1e-14){throw 'Predicted native c/h clock difference exceeds the unchanged matching tolerance'}
$prepared=@();$utf8=New-Object Text.UTF8Encoding($false)
foreach($w in $windows){
    $xml=New-Object Xml.XmlDocument;$xml.PreserveWhitespace=$false;$xml.Load($sourcePrefix+'.xml');$originalDom=$xml.DocumentElement.OuterXml
    $values=[ordered]@{
        SlipMode=@('3','Private CPU column: fixed FreeSlip bottom; not formal SlipMode1');
        Visco=@('0','Private candidate artificial viscosity OFF; not formal alpha=0.1');
        SoilHourglassXi=@('0','Private candidate HG OFF; not the formal HG setting');
        SoilBoundaryDerivativeSPR=@('0','Private dynamic wall owns its derivative closure; legacy SPR OFF');
        SoilDamping=@('0','Private candidate soil damping OFF; not the formal damped case');
        DtIni=@($w.dt,'Private candidate initial locked step; actual current-state bound remains mandatory');
        DtFixed=@($w.dt,'Private constant-k short candidate fixed step; no clipping or numerical admission implied');
        TimeMax=@('0.0125','Private load/drain candidate window only; not formal or admitted');
        TimeOut=@('0.0000249999999','Required default cadence; the three-segment special timeout adds the dense drainage bracket')
    }
    $changes=@()
    foreach($key in $values.Keys){
        $nodes=$xml.SelectNodes("/case/execution/parameters/parameter[@key='$key']");if($nodes.Count -ne 1){throw "Expected one retained parameter: $key"}
        $node=$nodes[0];$changes+=@([ordered]@{key=$key;old=$node.GetAttribute('value');value=[string]$values[$key][0];had_comment=$node.HasAttribute('comment');old_comment=$node.GetAttribute('comment');comment=[string]$values[$key][1]})
        $node.SetAttribute('value',[string]$values[$key][0]);$node.SetAttribute('comment',[string]$values[$key][1])
    }
    $special=$xml.SelectSingleNode('/case/execution/special');$hydro=$xml.SelectSingleNode('/case/execution/special/hydromechanics')
    if(!$special -or !$hydro -or $special.SelectNodes('timeout').Count){throw 'Expected retained hydromechanics and no old special timeout'}
    $added=@('HydroMechDynamicSeepage','HydroMechConductivityModel','HydroMechConductivityCk','PoreDarcySymmetricCorr')
    foreach($key in $added){
        if($hydro.SelectNodes($key).Count){throw "Unexpected retained explicit key: $key"}
        $node=$xml.CreateElement($key);$node.SetAttribute('value','0')
        $node.SetAttribute('comment',$(if($key -eq 'PoreDarcySymmetricCorr'){'Legacy option OFF; the private complete rate retains its existing pair-symmetric baseline'}else{'Explicit public default OFF; only the reviewed private CPU wrapper activates the candidate'}))
        [void]$hydro.AppendChild($node)
    }
    $timeout=$xml.CreateElement('timeout');$timeout.SetAttribute('active','true');$timeout.SetAttribute('comment','Output-only bias selects paired native steps without snapping TimeStep; dense bracket covers drainage')
    foreach($segment in $segments){$node=$xml.CreateElement('tout');$node.SetAttribute('time',$segment.time);$node.SetAttribute('timeout',$segment.timeout);[void]$timeout.AppendChild($node)}
    [void]$special.AppendChild($timeout)
    $settings=New-Object Xml.XmlWriterSettings;$settings.Encoding=$utf8;$settings.Indent=$true;$settings.IndentChars='    ';$settings.NewLineChars="`r`n";$settings.NewLineHandling=[Xml.NewLineHandling]::Replace
    $stream=New-Object IO.MemoryStream;$writer=[Xml.XmlWriter]::Create($stream,$settings)
    try{$xml.Save($writer);$writer.Flush();[byte[]]$bytes=$stream.ToArray()}finally{$writer.Dispose();$stream.Dispose()}
    $text=$utf8.GetString($bytes)
    if([regex]::IsMatch($text,"(?<!`r)`n|`r(?!`n)")){throw 'Generated XML must use CRLF only'}
    foreach($line in $text -split "`r`n"){if($line -match '^([ \t]+)' -and ($matches[1].Contains("`t") -or $matches[1].Length%4 -ne 0)){throw 'Generated XML indentation must be four-space levels'}}
    $inverse=New-Object Xml.XmlDocument;$inverse.PreserveWhitespace=$false;$inverse.LoadXml($text)
    foreach($change in $changes){$node=$inverse.SelectSingleNode("/case/execution/parameters/parameter[@key='$($change.key)']");$node.SetAttribute('value',$change.old);if($change.had_comment){$node.SetAttribute('comment',$change.old_comment)}else{$node.RemoveAttribute('comment')}}
    $inverseHydro=$inverse.SelectSingleNode('/case/execution/special/hydromechanics');foreach($key in $added){[void]$inverseHydro.RemoveChild($inverseHydro.SelectSingleNode($key))}
    [void]$inverse.SelectSingleNode('/case/execution/special').RemoveChild($inverse.SelectSingleNode('/case/execution/special/timeout'))
    if($inverse.DocumentElement.OuterXml -cne $originalDom){throw 'Inverse DOM proof failed: an undeclared physical/header field changed'}
    $config=Join-Path $testPath ('configs\upl_case02_short_'+$w.name+'_r1.xml');$prefix=Join-Path $targetPath ('upl_case02_short_'+$w.name+'_r1')
    $prepared+=@([ordered]@{window=$w.name;dt=[double]$w.dt;steps=$w.steps;config=$config;prefix=$prefix;bytes=$bytes;changes=$changes})
}
Verify $sources;Verify $scheduleSources;Verify $authorEntries
[void](New-Item -ItemType Directory -Path $targetPath);$jobs=@()
foreach($w in $prepared){
    [IO.File]::WriteAllBytes($w.config,$w.bytes);[IO.File]::WriteAllBytes(($w.prefix+'.xml'),$w.bytes)
    foreach($suffix in @('.bi4','_Normals.nbi4')){Copy-Item -LiteralPath ($sourcePrefix+$suffix) -Destination ($w.prefix+$suffix);if((Entry ($w.prefix+$suffix)).sha256 -cne $expected[$suffix]){throw 'Copied geometry/normal seed differs'}}
    $jobs+=@([ordered]@{window=$w.window;configuration=(Entry $w.config);runtime=(Entry ($w.prefix+'.xml'));initial_BI4=(Entry ($w.prefix+'.bi4'));normals=(Entry ($w.prefix+'_Normals.nbi4'));parameter_changes=$w.changes;added_hydro_keys=$added;special_timeout=$segments;dt_s=$w.dt;end_s=0.0125;steps=$w.steps;expected_samples=519;required_CLI=@('-cpu','-ompthreads:1','-stable','-mdbc_freeslip',('-nsteps:'+ $w.steps));inverse_DOM_equal=$true;four_space_CRLF=$true})
}
Verify $sources;Verify $scheduleSources;Verify $authorEntries
$result=[ordered]@{stage='upl_case02_short_inputs_r1';prepared=$true;source_seed=$sources;authors=$authorEntries;scheduling_source=$scheduleSources;jobs=$jobs;predicted_samples_each=519;predicted_coarse_save_steps='0:10:3990;3991:1:4010;4020:10:5000';predicted_half_save_steps='0:20:7980;7982:2:8020;8040:20:10000';native_Step_metadata='0 at initial,otherwise completed_step-1';predicted_max_actual_time_pair_difference_s=$maxTimeDifference;predicted_coarse_final_s=$coarse[518].time;predicted_half_final_s=$half[518].time;pre_open_completed_steps=@(4000,8000);next_paired_post_open_completed_steps=@(4001,8002);time_snap_or_interpolation=$false;geometry_or_particle_fields_modified=$false;new_GenCase_run=$false;original_soil=1000;original_fixed=40;public_master=0;conductivity_model=0;private_constant_k_candidate=$true;stabilizers_OFF_not_formal=$true;smoke_or_Release_prerequisites_asserted_by_this_preparer=$false;short_or_half_job_admitted=$false;solver_started=$false;physical_acceptance=$false}
Fresh @($recordPath);[IO.File]::WriteAllText($recordPath,($result|ConvertTo-Json -Depth 12)+[Environment]::NewLine,$utf8)
Write-Output "Prepared two candidate inputs only: $recordPath"
