param([switch]$PrepareAuthorized)
# Copy two authored inputs only. No GenCase, build, solve, reader or automatic next action.
$ErrorActionPreference='Stop';if(!$PrepareAuthorized){throw 'Root full review and explicit input-only preparation authorization required'}
$tests=Split-Path -Parent $PSScriptRoot;$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName;$tag='upl_case02_flux_window25_r1'
$target=Join-Path $tests "outputs\${tag}_seed";$record=Join-Path $tests "logs\$tag.inputs.json";$parentPath=Join-Path $tests 'logs\upl_case02_short_r1.inputs.json';$note=Join-Path $tests 'notes\upl_case02_flux_window25_prepare_r2.json'
function Entry([string]$path){$f=Get-Item -Force -LiteralPath $path;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($rows){foreach($r in $rows){if(!$r.path -or $null -eq $r.bytes -or !$r.sha256){throw 'Missing input binding'};$e=Entry $r.path;if($e.bytes -ne $r.bytes -or $e.sha256 -ine $r.sha256){throw "Changed input: $($r.path)"}}}
foreach($p in @($target,$record)){if(Test-Path -LiteralPath $p){throw "Retained preparation protected: $p"}}
$parent=[IO.File]::ReadAllText($parentPath)|ConvertFrom-Json
if(!$parent.prepared -or $parent.stage -cne 'upl_case02_short_inputs_r1' -or @($parent.jobs).Count -ne 2 -or $parent.predicted_samples_each -ne 519){throw 'Sealed original short inputs required'}
$scheduling=@((Entry (Join-Path $repo 'src\source\JDsOutputTime.cpp')),(Entry (Join-Path $repo 'src\source\JSphCpuSingle.cpp')))
if($scheduling[0].sha256 -cne 'b26c1b87f090b28bdc72c28d6ed7dfeee0ad7a0bcd28eb428f1ae72716d0c72f' -or $scheduling[1].sha256 -cne '1b2aa2741338c2046380727a680420a8df3bc1d2fedc071f8e3b2bfeaf41f394'){throw 'Reviewed save-predicate source changed'}
$segments=@(@{time='0';timeout='0.0000249999999'},@{time='0.0099749999';timeout='0.00000249999999'},@{time='0.0100249999';timeout='0.0000249999999'},@{time='0.0124999999';timeout='0.0000499999999'})
# Same binary64 GetNextTime/ordinary Run transcription as the sealed short preparer.
function PredictSaves([double]$dt,[int]$steps){
  [double[]]$base=@(0,.0099749999,.0100249999,.0124999999);[double[]]$cad=@(.0000249999999,.00000249999999,.0000249999999,.0000499999999);[int]$index=0;[double]$time=0
  function NextTime([double]$now,[double[]]$base,[double[]]$cad,[ref]$index){
    while($index.Value+1 -lt $base.Length -and $now -ge $base[$index.Value+1]){$index.Value++}
    [double]$tb=$base[$index.Value];[double]$tnext=if($index.Value+1 -lt $base.Length){$base[$index.Value+1]}else{[double]::MaxValue}
    if($now -lt $tb){return $tb}
    [uint32]$nt=[math]::Truncate(($now-$tb)/$cad[$index.Value]);[double]$next=$tb+$cad[$index.Value]*$nt
    while($next -le $now){$next=$tb+$cad[$index.Value]*$nt;$nt++};if($next -gt $tnext){$next=$tnext};return [double]$next
  }
  $rows=[Collections.Generic.List[object]]::new();$rows.Add([ordered]@{step=0;time=0.0});[double]$next=NextTime $time $base $cad ([ref]$index)
  for($step=1;$step -le $steps;$step++){[double]$time=$time+$dt;if($time -ge $next -or $time -ge .025 -or $step -ge $steps){$rows.Add([ordered]@{step=$step;time=$time});[double]$next=NextTime $time $base $cad ([ref]$index)}};return ,$rows
}
$coarse=PredictSaves .0000025 10000;$half=PredictSaves .00000125 20000
$oldSteps=@(0..399|ForEach-Object{10*$_})+@(3991..4010)+@(402..500|ForEach-Object{10*$_});$steps=$oldSteps+@(251..500|ForEach-Object{20*$_})
if($oldSteps.Count -ne 519 -or $steps.Count -ne 769 -or $coarse.Count -ne 769 -or $half.Count -ne 769){throw 'Predeclared769 paired samples not selected'}
[double]$maxTimeDifference=0
for($i=0;$i -lt 769;$i++){if($coarse[$i].step -ne $steps[$i] -or $half[$i].step -ne 2*$steps[$i]){throw 'Native-save step selection differs'};$maxTimeDifference=[math]::Max($maxTimeDifference,[math]::Abs($coarse[$i].time-$half[$i].time))}
if($maxTimeDifference -gt 1e-14){throw 'Predicted c/h clock mismatch exceeds unchanged1e-14 limit'}
$bindings=@((Entry $PSCommandPath),(Entry $note),(Entry $parentPath))+$scheduling;$prepared=@()
foreach($window in @('coarse','half')){
  $old=@($parent.jobs|Where-Object{$_.window -ceq $window});if($old.Count -ne 1){throw 'Unique old runtime required'};$old=$old[0]
  Verify @($old.configuration,$old.runtime,$old.initial_BI4,$old.normals)
  $expectedXml=if($window -ceq 'coarse'){'d9703a85543e56557697b5e084f96a7d20cd98ca1f0c78f74d55d93ae87772b8'}else{'df95326f88b71738fe119dc33c3dc727b7a3882861e0f90b968dd0ab504b7765'}
  if($old.runtime.sha256 -cne $expectedXml -or $old.initial_BI4.sha256 -cne 'f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac' -or $old.normals.sha256 -cne '0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97'){throw 'Reviewed template/geometry identity differs'}
  $config=Join-Path $tests "configs\upl_case02_flux_window25_${window}_r1.xml";$text=[IO.File]::ReadAllText($config);$before=New-Object Xml.XmlDocument;$before.PreserveWhitespace=$false;$before.Load($old.runtime.path);$x=New-Object Xml.XmlDocument;$x.PreserveWhitespace=$false;$x.LoadXml($text)
  if([regex]::IsMatch($text,"(?<!\r)\n|\r(?!\n)")){throw 'Authored XML must retain CRLF'};foreach($line in $text -split "\r\n"){if($line -match '^([ \t]+)' -and ($matches[1].Contains([char]9) -or $matches[1].Length%4)){throw 'Four-space XML levels required'}}
  $timeMax=$x.SelectSingleNode('/case/execution/parameters/parameter[@key="TimeMax"]');$timeOutParameter=$x.SelectSingleNode('/case/execution/parameters/parameter[@key="TimeOut"]');$timeout=$x.SelectSingleNode('/case/execution/special/timeout');$list=$timeout.SelectNodes('tout')
  $dt=if($window -ceq 'coarse'){.0000025}else{.00000125};$count=if($window -ceq 'coarse'){10000}else{20000}
  if($timeMax.GetAttribute('value') -cne '0.025' -or $list.Count -ne 4 -or $timeOutParameter.GetAttribute('value') -cne '0.0000249999999'){throw 'Declared window/default timeout differs'}
  for($i=0;$i -lt 4;$i++){if($list[$i].GetAttribute('time') -cne $segments[$i].time -or $list[$i].GetAttribute('timeout') -cne $segments[$i].timeout){throw 'Four timeout segments differ'}}
  foreach($key in @('DtIni','DtFixed')){if([double]$x.SelectSingleNode("/case/execution/parameters/parameter[@key='$key']").GetAttribute('value') -ne $dt){throw 'Paired fixed dt changed'}}
  $timeMax.SetAttribute('value',$before.SelectSingleNode('/case/execution/parameters/parameter[@key="TimeMax"]').GetAttribute('value'));$timeOutParameter.SetAttribute('comment',$before.SelectSingleNode('/case/execution/parameters/parameter[@key="TimeOut"]').GetAttribute('comment'));[void]$timeout.RemoveChild($list[3])
  if($x.DocumentElement.OuterXml -cne $before.DocumentElement.OuterXml){throw 'Reverse DOM proof failed: undeclared input change'}
  $configEntry=Entry $config;$bindings+=@($old.configuration,$old.runtime,$old.initial_BI4,$old.normals,$configEntry);$prepared+=@{window=$window;old=$old;config=$configEntry;prefix=(Join-Path $target "upl_case02_flux_window25_${window}_r1");dt=$dt;steps=$count}
}
Verify $bindings;[void](New-Item -ItemType Directory -Path $target);$jobs=@()
foreach($w in $prepared){
  Copy-Item -LiteralPath $w.config.path -Destination ($w.prefix+'.xml');Copy-Item -LiteralPath $w.old.initial_BI4.path -Destination ($w.prefix+'.bi4');Copy-Item -LiteralPath $w.old.normals.path -Destination ($w.prefix+'_Normals.nbi4')
  $runtime=Entry ($w.prefix+'.xml');$bi4=Entry ($w.prefix+'.bi4');$normals=Entry ($w.prefix+'_Normals.nbi4')
  foreach($pair in @(@($w.config,$runtime),@($w.old.initial_BI4,$bi4),@($w.old.normals,$normals))){if($pair[0].bytes -ne $pair[1].bytes -or $pair[0].sha256 -ine $pair[1].sha256){throw 'Prepared copy differs'}}
  $jobs+=@([ordered]@{window=$w.window;configuration=$w.config;runtime=$runtime;initial_BI4=$bi4;normals=$normals;source_runtime=$w.old.runtime;dt_s=$w.dt;end_s=.025;steps=$w.steps;expected_samples=769;required_CLI=@('-cpu','-ompthreads:1','-stable','-mdbc_freeslip',('-nsteps:'+$w.steps));parameter_changes=@{TimeMax=@{old='0.0125';value='0.025'};TimeOut_comment_only=$true};special_timeout=$segments;inverse_DOM_equal=$true;four_space_CRLF=$true})
}
Verify $bindings
$result=[ordered]@{stage='upl_case02_flux_window25_r1';prepared=$true;parent=(Entry $parentPath);bindings=$bindings;jobs=$jobs;predicted_samples_each=769;old519_step_prefix_preserved=$true;predicted_coarse_save_steps='0:10:3990;3991:1:4010;4020:10:5000;5020:20:10000';predicted_half_save_steps='0:20:7980;7982:2:8020;8040:20:10000;10040:40:20000';native_Step_metadata='0 initially; otherwise completed_step-1';predicted_max_actual_time_pair_difference_s=$maxTimeDifference;predicted_coarse_final_s=$coarse[768].time;predicted_half_final_s=$half[768].time;pre_open_completed_steps=@(4000,8000);next_paired_post_open_completed_steps=@(4001,8002);time_snap_or_interpolation=$false;geometry_or_particle_fields_modified=$false;new_GenCase_run=$false;public_master=0;conductivity_model=0;original_soil=1000;original_fixed=40;runtime_prepared_only=$true;Run_Reader_Build_started=$false;window25_admitted=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 15)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)));Write-Output "Prepared window25 inputs only: $record"
