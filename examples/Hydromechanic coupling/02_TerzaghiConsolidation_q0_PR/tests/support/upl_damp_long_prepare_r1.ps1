param([switch]$ExecutionAuthorized)
# Prepare two fresh .5s inputs only; no GenCase, build, reader, solver or follow-on action.
$ErrorActionPreference='Stop';$tests=Split-Path -Parent $PSScriptRoot;$logs=Join-Path $tests 'logs';$seed=Join-Path $tests 'outputs\upl_damp_long_seed_r1';$record=Join-Path $logs 'upl_damp_long_r1.inputs.json';$ci=[Globalization.CultureInfo]::InvariantCulture
function E([string]$p){$f=Get-Item -LiteralPath $p -Force;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Need([bool]$ok,[string]$why){if(!$ok){throw $why}}
function V($rows){foreach($e in $rows){Need ($e.path -and $e.sha256) 'Missing Entry';$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed input: '+$e.path)}}
function Fresh($paths){foreach($p in $paths){Need (!(Test-Path -LiteralPath $p)) ('Retained artifact protected: '+$p)}}
function Dom([string]$p){$x=New-Object Xml.XmlDocument;$x.PreserveWhitespace=$false;$x.Load($p);return $x}
function One($x,[string]$path){$n=$x.SelectNodes($path);Need ($n.Count -eq 1) ('Expected one XML node: '+$path);return $n[0]}
function Number([string]$v){[double]::Parse($v,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture)}
function SaveXml($x,[string]$p){$declaration=$x.FirstChild.OuterXml;$s=New-Object Xml.XmlWriterSettings;$s.OmitXmlDeclaration=$true;$s.Indent=$true;$s.IndentChars='    ';$s.NewLineChars="`n";$s.NewLineHandling=[Xml.NewLineHandling]::Replace;$body=New-Object Text.StringBuilder;$w=[Xml.XmlWriter]::Create($body,$s);try{$x.Save($w)}finally{$w.Dispose()};[IO.File]::WriteAllText($p,($declaration+"`n"+$body.ToString()),(New-Object Text.UTF8Encoding($false)))}
# Literal existing JDsOutputTime::GetNextTime replay, including anchor clamp and duplicate-call cache.
function NextTime([double]$t,$state,$segments){
  if($state.last_input -ge 0 -and $t -eq $state.last_input){return $state.last_output};$state.last_input=$t
  $tb=[double]$segments[$state.base].time;$nextAnchor=[double]::MaxValue;if($state.base+1 -lt $segments.Count){$nextAnchor=[double]$segments[$state.base+1].time}
  while($t -ge $nextAnchor){$state.base++;$tb=[double]$segments[$state.base].time;$nextAnchor=[double]::MaxValue;if($state.base+1 -lt $segments.Count){$nextAnchor=[double]$segments[$state.base+1].time}}
  if($t -lt $tb){$next=$tb}else{$cadence=[double]$segments[$state.base].timeout;$nt=[long][Math]::Floor(($t-$tb)/$cadence);$next=$tb+$cadence*$nt;while($next -le $t){$next=$tb+$cadence*$nt;$nt++};if($next -gt $nextAnchor){$next=$nextAnchor}}
  $state.last_output=[double]$next;return [double]$next
}
function Schedule([bool]$half,$prefix){
  $dc=[Math]::Pow(2,-19);$factor=if($half){2}else{1};$dt=$dc/$factor;$steps=262144*$factor;$expected=New-Object 'Collections.Generic.SortedSet[int]'
  for($k=0;$k -le 65536;$k+=64){[void]$expected.Add($k*$factor)};for($k=5120;$k -le 5376;$k++){[void]$expected.Add($k*$factor)};for($k=66560;$k -le 262144;$k+=1024){[void]$expected.Add($k*$factor)}
  $segments=@(@{time=0.0;timeout=64*$dc},@{time=5120*$dc;timeout=$dc},@{time=5376*$dc;timeout=64*$dc},@{time=65536*$dc;timeout=1024*$dc})
  $state=@{base=0;last_input=-1.0;last_output=0.0};$rows=New-Object 'Collections.Generic.List[object]';[void]$rows.Add([ordered]@{part=0;completed_steps=0;saved_step=0;time_s=0.0});$t=0.0;$next=NextTime 0.0 $state $segments
  for($completed=1;$completed -le $steps;$completed++){$t+=$dt;if($t -ge $next -or $completed -eq $steps){[void]$rows.Add([ordered]@{part=$rows.Count;completed_steps=$completed;saved_step=$completed-1;time_s=[double]$t});$next=NextTime $t $state $segments}}
  $wanted=@($expected);Need ($rows.Count -eq 1469 -and $wanted.Count -eq 1469 -and @($prefix).Count -eq 1277 -and $t -eq 0.5) 'Declared .5s saved set differs'
  for($i=0;$i -lt 1469;$i++){Need ($rows[$i].part -eq $i -and $rows[$i].completed_steps -eq $wanted[$i] -and $rows[$i].saved_step -eq $(if($i){$wanted[$i]-1}else{0}) -and [BitConverter]::DoubleToInt64Bits($rows[$i].time_s) -eq [BitConverter]::DoubleToInt64Bits([double]$wanted[$i]*$dt)) 'Replayed dyadic native schedule differs';if($i -lt 1277){Need ($prefix[$i].part -eq $i -and $prefix[$i].completed_steps -eq $wanted[$i] -and $prefix[$i].saved_step -eq $rows[$i].saved_step) 'Retained1277 integer schedule prefix differs'}}
  Need ($rows[203].completed_steps -eq 5243*$factor -and $rows[1276].time_s -eq 0.125 -and @($rows|Where-Object{$_.completed_steps -gt 5243*$factor}).Count -eq 1265) 'Event/prefix/post-open schedule differs'
  return [ordered]@{table=$rows.ToArray();segments=$segments;dt=$dt;steps=$steps;factor=$factor}
}
Need $ExecutionAuthorized.IsPresent 'Root full read and explicit Prepare authorization required';Fresh @($seed,$record)
$oldEntry=E (Join-Path $logs 'upl_damp_r1.inputs.json');$old=J $oldEntry.path;$scheduler=E (Join-Path (Join-Path $tests '..\..\..\..\src') 'source\JDsOutputTime.cpp')
Need ($old.stage -ceq 'upl_damp_prepare_r1' -and $old.passed -and $old.prepared -and !$old.physical_acceptance -and $scheduler.sha256 -ceq 'b26c1b87f090b28bdc72c28d6ed7dfeee0ad7a0bcd28eb428f1ae72716d0c72f') 'Sealed damping inputs and unchanged literal scheduler required'
$inputs=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_damp_long_r1.json')),$oldEntry,$scheduler);$plans=@();$fresh=@()
foreach($window in @('coarse','half')){
  $selected=@($old.jobs|Where-Object{$_.window -ceq $window});Need ($selected.Count -eq 1) 'Unique retained damping window required';$o=$selected[0];V @($o.configuration,$o.runtime,$o.initial_BI4,$o.normals)
  Need ($o.damping -eq 1 -and $o.damping_coef -eq 0.02 -and $o.end_s -eq 0.125 -and $o.expected_samples -eq 1277 -and $o.dt_s -eq [Math]::Pow(2,$(if($window -ceq 'half'){-20}else{-19})) -and $o.steps -eq $(if($window -ceq 'half'){131072}else{65536}) -and $o.configuration.sha256 -ceq $o.runtime.sha256 -and $o.initial_BI4.sha256 -ceq 'f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac' -and $o.normals.sha256 -ceq '0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97') 'Retained damping/clock/seed differs'
  $configuration=Join-Path $tests ('configs\upl_damp_long_'+$window+'_r1.xml');$prefix=Join-Path $seed ('upl_damp_long_'+$window+'_r1');$fresh+=@($configuration,($prefix+'.xml'),($prefix+'.bi4'),($prefix+'_Normals.nbi4'));$plans+=@{window=$window;old=$o;configuration=$configuration;prefix=$prefix;schedule=(Schedule ($window -ceq 'half') $o.saved_clock_table)};$inputs+=@($o.configuration,$o.runtime,$o.initial_BI4,$o.normals)
}
for($i=0;$i -lt 1469;$i++){Need ($plans[1].schedule.table[$i].completed_steps -eq 2*$plans[0].schedule.table[$i].completed_steps -and [BitConverter]::DoubleToInt64Bits($plans[1].schedule.table[$i].time_s) -eq [BitConverter]::DoubleToInt64Bits($plans[0].schedule.table[$i].time_s)) 'Coarse/half binary clocks differ'}
Fresh $fresh;V $inputs;$jobs=@();$files=@();$failure=$null;$unchanged=$false
try{[void](New-Item -ItemType Directory -Path $seed);foreach($p in $plans){
  $o=$p.old;$x=Dom $o.runtime.path;$before=$x.OuterXml;$h='/case/execution/special/hydromechanics/'
  foreach($item in @(@{path=$h+'HydroMechDynamicSeepage';value=1},@{path=$h+'HydroMechConductivityModel';value=0},@{path=$h+'HydroMechConductivityCk';value=0},@{path=$h+'HydroMechTopLoadRampTime';value=5243*[Math]::Pow(2,-19)},@{path=$h+'HydroMechDrainageStartTime';value=5243*[Math]::Pow(2,-19)},@{path='/case/execution/parameters/parameter[@key="SoilDamping"]';value=1},@{path='/case/execution/parameters/parameter[@key="SoilDampingCoef"]';value=0.02})){Need ((Number ((One $x $item.path).GetAttribute('value'))) -eq $item.value) 'Retained public/damping/event value differs'}
  $endNode=One $x '/case/execution/parameters/parameter[@key="TimeMax"]';Need ((Number $endNode.GetAttribute('value')) -eq 0.125) 'Retained end differs';$oldEnd=$endNode.GetAttribute('value');$endNode.SetAttribute('value','0.5')
  $timeoutNode=One $x '/case/execution/special/timeout';$nodes=$timeoutNode.SelectNodes('tout');Need ($nodes.Count -eq 3) 'Retained three timeout nodes required'
  for($i=0;$i -lt 3;$i++){Need ((Number $nodes[$i].GetAttribute('time')) -eq $p.schedule.segments[$i].time -and (Number $nodes[$i].GetAttribute('timeout')) -eq $p.schedule.segments[$i].timeout) 'Retained prefix timeout differs'}
  $added=$x.CreateElement('tout');$added.SetAttribute('time','0.125');$added.SetAttribute('timeout',(1024*[Math]::Pow(2,-19)).ToString('R',$ci));[void]$timeoutNode.AppendChild($added);SaveXml $x $p.configuration
  $inverse=Dom $p.configuration;(One $inverse '/case/execution/parameters/parameter[@key="TimeMax"]').SetAttribute('value',$oldEnd);$inverseTimeout=One $inverse '/case/execution/special/timeout';Need ($inverseTimeout.SelectNodes('tout').Count -eq 4) 'New timeout count differs';[void]$inverseTimeout.RemoveChild($inverseTimeout.SelectNodes('tout')[3]);Need ($inverse.OuterXml -ceq $before) 'Changes outside TimeMax and appended timeout'
  Copy-Item -LiteralPath $p.configuration -Destination ($p.prefix+'.xml');Copy-Item -LiteralPath $o.initial_BI4.path -Destination ($p.prefix+'.bi4');Copy-Item -LiteralPath $o.normals.path -Destination ($p.prefix+'_Normals.nbi4')
  $ce=E $p.configuration;$re=E ($p.prefix+'.xml');$be=E ($p.prefix+'.bi4');$ne=E ($p.prefix+'_Normals.nbi4');Need ($ce.sha256 -ceq $re.sha256 -and $be.sha256 -ceq $o.initial_BI4.sha256 -and $be.bytes -eq $o.initial_BI4.bytes -and $ne.sha256 -ceq $o.normals.sha256 -and $ne.bytes -eq $o.normals.bytes) 'Fresh runtime/seed copy differs'
  $jobs+=@{window=$p.window;configuration=$ce;runtime=$re;initial_BI4=$be;normals=$ne;input_prefix=$p.prefix;dt_s=$p.schedule.dt;end_s=0.5;steps=$p.schedule.steps;expected_samples=1469;required_CLI=@('-mdbc_freeslip','-svres',('-nsteps:'+$p.schedule.steps));damping=1;damping_coef=0.02;source_manifest=$oldEntry;source_configuration=$o.configuration;source_runtime=$o.runtime;inverse_DOM_exact=$true;physics_and_first_three_timeouts_unchanged=$true;declared_changes=@('TimeMax','appended fourth timeout','new artifact labels and CLI terminal step');saved_clock_table=$p.schedule.table;special_timeout=$p.schedule.segments;retained_prefix_samples=1277;retained_prefix_integer_steps_exact=$true;retained_prefix_binary_times_reconstructed_from_integer_steps=$true;prefix_native_fields_observed=$false;event_completed_step=5243*$p.schedule.factor;ramp_and_drain_event_s=5243*[Math]::Pow(2,-19);post_open_frames=1265;initial_particle_fields_rewritten=$false};$files+=@($ce,$re,$be,$ne)
}}catch{$failure=$_.Exception.Message}
try{V $inputs;V $files;$unchanged=$true}catch{if(!$failure){$failure=$_.Exception.Message}}
$passed=(!$failure -and $unchanged -and $jobs.Count -eq 2 -and $files.Count -eq 8)
$result=[ordered]@{stage='upl_damp_long_prepare_r1';passed=[bool]$passed;prepared=[bool]$passed;jobs=$jobs;inputs=$inputs;files=$files;seed_directory=$seed;source_scheduler=$scheduler;sample_count=1469;retained_prefix_samples=1277;new_late_samples=192;paired_times_bit_exact=$true;deserialized_JSON_rowtime_used_as_clock_truth=$false;input_sources_unchanged=$unchanged;solver_reader_or_build_invoked=$false;formal_files_changed=$false;physical_acceptance=$false;failure=$failure}
Fresh @($record);[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 18)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)));if(!$passed){throw "Long preparation rejected; preserve $record and partials"};Write-Output "Two .5s inputs prepared only: $record"
