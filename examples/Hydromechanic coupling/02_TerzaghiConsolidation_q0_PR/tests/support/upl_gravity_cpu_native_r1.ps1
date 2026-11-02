param(
  [Parameter(Mandatory=$true)][ValidateSet('Prepare')][string]$Mode,
  [switch]$ExecutionAuthorized
)
# Prepare-only: emits exact future main/reader commands, NEVER invokes them.
# Six heterogeneous native contracts are retained rather than relabelled as one.
$ErrorActionPreference='Stop'
$t=Split-Path -Parent $PSScriptRoot
$cases=(Get-Item -LiteralPath $t).Parent.Parent.FullName
$s=Join-Path $cases '01_SelfWeightConsolidation_PR\tests'
$note=Join-Path $t 'notes\upl_gravity_cpu_native_r1.json'
$manifest=Join-Path $t 'logs\upl_gravity_cpu_native_r1.inputs.json'
$buildPath=Join-Path $t 'logs\upl_gravity_cpu_ReleaseCPU_r2.build.json'
function Entry([string]$p){$f=Get-Item -Force -LiteralPath $p;[ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}}
function ReadJson([string]$p){[IO.File]::ReadAllText($p)|ConvertFrom-Json}
function Verify($rows){foreach($r in $rows){$a=Entry $r.path;if($null -eq $r.bytes -or !$r.sha256 -or $a.bytes -ne $r.bytes -or $a.sha256 -ine $r.sha256){throw "Frozen file changed: $($r.path)"}}}
function PathAt([string]$root,[string]$relative){[IO.Path]::GetFullPath((Join-Path $root $relative))}
function Fresh($paths){foreach($p in $paths){if(Test-Path -LiteralPath $p){throw "Retained output protected: $p"}}}
if(!$ExecutionAuthorized){throw 'Root full-read and explicit manifest-preparation authorization required'}
Fresh @($manifest)
$declaration=ReadJson $note
if($declaration.stage -cne 'upl_gravity_cpu_native_r1' -or @($declaration.jobs).Count -ne 6){throw 'Six predeclared jobs required'}
$build=ReadJson $buildPath
if(!$build.passed -or $build.status -cne 'authoritative_CPU_Rebuild_passed_no_program_run' -or $build.configuration -cne 'ReleaseCPU' -or $build.label -cne 'r2' -or $build.non_main_CPU_objects -ne 85){throw 'Future candidate isolated ReleaseCPU r2 Rebuild required'}
$expectedMain=Join-Path $t 'outputs\upl_gravity_cpu_ReleaseCPU_r2_main\DualSPHysics5.2CPU_win64.exe'
if($build.program.path -ine $expectedMain){throw 'Only candidate actual main (not a helper or old program) may be selected'}
$proof=@(Entry $PSCommandPath;Entry $note;Entry $buildPath)+@($build.program)+@($build.source)+@($build.inputs)+@($build.protected_canonical_GPU_six_and_CPU_two)
foreach($r in $build.current_source_snapshot){$proof+=@($r.original,$r.snapshot)}
foreach($r in $build.runtime){$proof+=@($r.original,$r.copy)}
Verify $proof
$jobs=@()
foreach($spec in $declaration.jobs){
  $root=if($spec.case -eq '01'){$s}else{$t}
  $inputPrefix=PathAt $root $spec.input_prefix
  $inputRows=@(Entry ($inputPrefix+'.xml');Entry ($inputPrefix+'.bi4'))
  if($spec.normals){$inputRows+=Entry ($inputPrefix+'_Normals.nbi4')}
  if($inputRows[0].sha256 -ine $spec.xml_sha256 -or $inputRows[1].sha256 -ine $spec.bi4_sha256){throw 'Retained runtime XML / GenCase geometry input differs from predeclared bytes'}
  $oldRunPath=PathAt $root $spec.old_run
  $oldCheckPath=PathAt $root $spec.old_check
  $oldRun=ReadJson $oldRunPath;$oldCheck=ReadJson $oldCheckPath
  if(!$oldCheck.passed){throw 'Accepted retained native control required'}
  $oldOutput=PathAt $root $spec.old_output
  $newOutput=Join-Path $t ('outputs\upl_gravity_cpu_native_r1_'+$spec.job)
  $newReview=Join-Path $t ('outputs\upl_gravity_cpu_native_r1_'+$spec.job+'_review')
  Fresh @($newOutput,$newReview)
  $records=@(Entry $oldRunPath;Entry $oldCheckPath)
  if($spec.contract -eq 'selfweight38'){
    if($oldRun.exit_code -ne 0 -or !$oldRun.owned_exited -or !$oldRun.solver_finished -or @($oldRun.surviving_owned).Count){throw 'Retained nonzero-g actual main owned exit proof missing'}
    $raw=@($oldRun.outputs);$oldProgram=$oldRun.program
    $solverArguments=@('-cpu','-ompthreads:8','-stable','-mdbc',$inputPrefix,$newOutput,'-dirdataout','data','-svres','-svextraparts:1','-nsteps:2000')
    $readerBuildPath=PathAt $root 'logs\sw_native_r1.build.json';$rb=ReadJson $readerBuildPath
    if($rb.exit_code -ne 0 -or $rb.production_modified){throw 'Original pure selfweight native reader build required'}
    $reader=$rb.program;$records+=Entry $readerBuildPath
    $readerCommands=@();for($part=0;$part -lt 5;$part++){$readerCommands+=@{program=$reader;arguments=@((Join-Path $newOutput 'data'),[string]$part);stdout_csv=(Join-Path $newReview ('candidate_'+$part+'.csv'));retained_arguments=@((Join-Path $oldOutput 'data'),[string]$part);retained_stdout_csv=(Join-Path $newReview ('retained_'+$part+'.csv'))}}
    $comparison=@{kind='lossless_native_38_CSV_binary64_comparison';algorithm='Use frozen sw_release_native_r1.py exact(a,b) / sw_shepard_event_r1.py measure on each of five frames: all 1040 IDs x all 38 finite values, identical columns, parse round_trip, view uint64; no exclusions, including signed zero, native clock/Step and signed dterror.';files=@();reader_safety='Existing full 38-field native schema and original drainage/elastic/rho/p0/excess/clock guards; no new pressure-error budget';metadata_absence_independently_reparsed=$false}
    $records+=@(Entry (PathAt $root 'support\sw_release_native_r1.py');Entry (PathAt $root 'support\sw_shepard_event_r1.py'))
  }else{
    $raw=@($oldCheck.files)
    if($spec.contract -eq 'periodic33'){
      if(!$oldRun.owned_solver_exit0){throw 'Retained periodic-variable owned exit proof missing'}
      $owned=ReadJson $oldRun.call.path;$records+=$oldRun.call
      if(!$owned.owned_call_exited -or $owned.exit_code -ne 0){throw 'Retained canonical CPU variable actual call failed'}
      $oldProgram=$owned.program;$raw=@($oldRun.files)
      $solverArguments=@($owned.arguments)
      $readerCall=ReadJson $oldCheck.call.path;$records+=$oldCheck.call
      $reader=$readerCall.program;$readerArgs=@($readerCall.arguments)
      $oldReview=Split-Path -Parent $oldCheck.completion.path
    }else{
      if(!$oldRun.owned_call_exited -or $oldRun.exit_code -ne 0){throw 'Retained canonical CPU public owned exit proof missing'}
      $oldProgram=$oldRun.program;$solverArguments=@($oldRun.arguments)
      $reviewPath=PathAt $t $spec.old_review_check;$review=ReadJson $reviewPath
      if(!$review.passed){throw 'Retained public pure native review required'}
      $records+=Entry $reviewPath;$readerCall=ReadJson $review.reader_call.path;$records+=$review.reader_call
      $reader=$readerCall.program;$readerArgs=@($readerCall.arguments)
      $oldReview=Split-Path -Parent $review.completion.path;$proof+=@($review.files)
    }
    if(!$readerCall.owned_call_exited -or $readerCall.exit_code -ne 0){throw 'Existing pure reader owned exit0 required'}
    $changed=0;for($i=0;$i -lt $solverArguments.Count;$i++){if($solverArguments[$i] -ieq $oldOutput){$solverArguments[$i]=$newOutput;$changed++}}
    if($changed -ne 1 -or $solverArguments -notcontains $inputPrefix -or $solverArguments -contains '-force'){throw 'Only old output token may change in exact main argument recipe'}
    $replacements=0;for($i=0;$i -lt $readerArgs.Count;$i++){if($readerArgs[$i] -ieq (Join-Path $oldOutput 'data')){$readerArgs[$i]=Join-Path $newOutput 'data';$replacements++}elseif($readerArgs[$i] -ieq $oldReview){$readerArgs[$i]=$newReview;$replacements++}}
    if($replacements -ne 2 -or $readerArgs[0] -cne '--read'){throw 'Pure read command requires exactly data/review remaps; no solver mode'}
    $readerCommands=@(@{program=$reader;arguments=$readerArgs})
    $comparison=@{kind=$spec.contract;retained_review=$oldReview;candidate_review=$newReview;exact_leaf_names=@($spec.exact_leaf_names);algorithm='For each named leaf require equal bytes and SHA256, with no masks, interpolation, dterror exclusion or signed-zero exception. Require pure reader completion passed and exact declared counts/model/clocks.';extra_native_ledger='Public native6 arrays and PosDiv / smooth33 actual CPU V,rho,k validated by existing reader from candidate BI4; equality scope is listed exports, not a claim that every BI4 array is separately byte exported.';metadata_absence_independently_reparsed=($spec.contract -eq 'off15')}
    foreach($leaf in $spec.exact_leaf_names){$proof+=Entry (Join-Path $oldReview $leaf)}
  }
  $proof+=$records+$inputRows+$raw+@($oldProgram,$reader)
  $cwd=if($spec.case -eq '01'){Split-Path -Parent $s}else{PathAt $cases '..\..\src'}
  $jobs+=@{job=$spec.job;case=$spec.case;ON=$spec.ON;gravity=$spec.gravity;hydraulic_k0=$spec.hydraulic_k0;soil=$spec.soil;fixed=$spec.fixed;samples=$spec.samples;steps=$spec.steps;dt_s=$spec.dt_s;cadence_s=$spec.cadence_s;end_s=$spec.end_s;inputs=$inputRows;input_prefix=$inputPrefix;inputs_reused_without_GenCase_or_field_rewrite=$true;retained_owned_records=$records;retained_actual_program=$oldProgram;retained_raw_manifest=$raw;program=$build.program;working_directory=$cwd;solver_arguments=$solverArguments;new_output=$newOutput;new_review=$newReview;reader_commands=$readerCommands;comparison=$comparison;actual_candidate_calls_executed=0;physical_acceptance=$false}
}
Verify $proof
$result=[ordered]@{stage='upl_gravity_cpu_native_r1';status='six_candidate_only_actual_main_commands_prepared_NOT_run';source_build=(Entry $buildPath);bindings=$proof;jobs=$jobs;all_main_or_reader_calls_executed=0;no_retained_solver_rerun=$true;no_GenCase=$true;no_runtime_XML_or_BI4_changed=$true;no_half_or_theory_or_new_gravity_admission=$true;physical_acceptance=$false;execution_contract=$declaration.execution_contract}
[IO.File]::WriteAllText($manifest,($result|ConvertTo-Json -Depth 25)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
