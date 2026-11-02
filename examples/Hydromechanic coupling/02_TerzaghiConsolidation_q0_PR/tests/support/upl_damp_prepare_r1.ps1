param([switch]$ExecutionAuthorized)
# Input copies only: change two damping parameters, never clocks, particles or formal inputs.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$seed=Join-Path $tests 'outputs\upl_damp_seed_r1'
$record=Join-Path $tests 'logs\upl_damp_r1.inputs.json'
function E([string]$p){$f=Get-Item -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=[long]$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function J([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Need([bool]$ok,[string]$why){if(!$ok){throw $why}}
function V($e){$a=E $e.path;Need ($a.bytes -eq $e.bytes -and $a.sha256 -ieq $e.sha256) ('Changed input: '+$e.path)}
function Fresh([string]$p){Need (!(Test-Path -LiteralPath $p)) ('Retained path protected: '+$p)}
Need $ExecutionAuthorized.IsPresent 'Explicit preparation authorization required'
Fresh $seed;Fresh $record
$ring=Join-Path $tests 'logs\upl_column_ringdown_r1.inputs.json'
$public=Join-Path $tests 'logs\upl_column_public_r1.inputs.json'
$jobs=@();$inputs=@((E $PSCommandPath),(E (Join-Path $tests 'notes\upl_damp_plan_r1.json')),(E $ring),(E $public))
$plans=@();foreach($window in @('smoke','coarse','half','eta0')){
  $manifest=if($window -ceq 'eta0'){$public}else{$ring};$m=J $manifest
  Need ($m.passed -and $m.prepared) 'Retained prepared inputs required'
  $wanted=if($window -ceq 'eta0'){'coarse'}else{$window}
  $rows=@($m.jobs|Where-Object {$_.window -ceq $wanted});Need ($rows.Count -eq 1) 'Unique source input required';$old=$rows[0]
  foreach($e in @($old.configuration,$old.runtime,$old.initial_BI4,$old.normals)){V $e;$inputs+=@($e)}
  Need ($old.master_value -eq 1 -and $old.conductivity_model -eq 0 -and $old.initial_BI4.sha256 -ceq 'f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac' -and $old.normals.sha256 -ceq '0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97') 'Original constant-k seed/master differs'
  $config=Join-Path $tests ('configs\upl_damp_'+$window+'_r1.xml');Fresh $config
  $plans+=@{window=$window;old=$old;manifest=(E $manifest);configuration=$config}
}
[void](New-Item -ItemType Directory -Path $seed)
foreach($plan in $plans){
  $o=$plan.old;$x=New-Object Xml.XmlDocument;$x.PreserveWhitespace=$false;$x.Load($o.runtime.path);$before=$x.OuterXml;$oldNodes=@()
  $coef=if($plan.window -ceq 'eta0'){'0'}else{'0.02'}
  foreach($item in @(@{key='SoilDamping';value='1'},@{key='SoilDampingCoef';value=$coef})){
    $nodes=$x.SelectNodes('/case/execution/parameters/parameter[@key="'+$item.key+'"]');Need ($nodes.Count -eq 1) 'Unique damping parameter required';$n=$nodes[0];$oldNodes+=@{key=$item.key;node=$n.CloneNode($true)}
    $n.SetAttribute('value',$item.value);$n.SetAttribute('comment',$(if($plan.window -ceq 'eta0'){'Dynamic zero-damping compatibility; not a physical candidate'}else{'Bounded intrinsic-solid-density elastic damping candidate; not formal release'}))
  }
  $declaration=$x.FirstChild.OuterXml;$settings=New-Object Xml.XmlWriterSettings;$settings.OmitXmlDeclaration=$true;$settings.Indent=$true;$settings.IndentChars='    ';$settings.NewLineChars="`n";$body=New-Object Text.StringBuilder;$writer=[Xml.XmlWriter]::Create($body,$settings)
  try{$x.Save($writer)}finally{$writer.Dispose()};[IO.File]::WriteAllText($plan.configuration,($declaration+"`n"+$body.ToString()),(New-Object Text.UTF8Encoding($false)))
  $inverse=New-Object Xml.XmlDocument;$inverse.PreserveWhitespace=$false;$inverse.Load($plan.configuration)
  foreach($v in $oldNodes){$n=$inverse.SelectSingleNode('/case/execution/parameters/parameter[@key="'+$v.key+'"]');[void]$n.ParentNode.ReplaceChild($inverse.ImportNode($v.node,$true),$n)}
  Need ($inverse.OuterXml -ceq $before) 'Changes outside the two declared damping nodes'
  $prefix=Join-Path $seed ('upl_damp_'+$plan.window+'_r1')
  Copy-Item -LiteralPath $plan.configuration -Destination ($prefix+'.xml');Copy-Item -LiteralPath $o.initial_BI4.path -Destination ($prefix+'.bi4');Copy-Item -LiteralPath $o.normals.path -Destination ($prefix+'_Normals.nbi4')
  $bi4=E ($prefix+'.bi4');$normals=E ($prefix+'_Normals.nbi4');Need ($bi4.sha256 -ceq $o.initial_BI4.sha256 -and $normals.sha256 -ceq $o.normals.sha256) 'Seed copy differs'
  $jobs+=@{window=$plan.window;configuration=(E $plan.configuration);runtime=(E ($prefix+'.xml'));initial_BI4=$bi4;normals=$normals;input_prefix=$prefix;dt_s=$o.dt_s;end_s=$o.end_s;steps=$o.steps;expected_samples=$o.expected_samples;damping=1;damping_coef=[double]$coef;source_manifest=$plan.manifest;source_runtime=$o.runtime;inverse_DOM_exact=$true;saved_clock_table=$o.saved_clock_table;physics_changed_only_in_declared_damping_nodes=$true}
}
foreach($e in $inputs){V $e}
$result=[ordered]@{stage='upl_damp_prepare_r1';passed=$true;prepared=$true;jobs=$jobs;inputs=$inputs;seed_directory=$seed;solver_reader_or_build_invoked=$false;formal_files_changed=$false;physical_acceptance=$false}
[IO.File]::WriteAllText($record,($result|ConvertTo-Json -Depth 16)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Write-Output "Prepared four damping-only inputs, no solver: $record"
