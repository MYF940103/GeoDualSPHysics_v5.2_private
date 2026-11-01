param(
  [ValidateSet('Build','Run')][string]$Mode='Build',
  [ValidateSet('Debug','Release')][string]$Configuration='Debug',
  [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Label='r1',
  [switch]$ReviewedForExecution
)
$ErrorActionPreference='Stop'
if(!$ReviewedForExecution){throw 'Author-only until the root reviews this exact consistency/energy screen.'}
$tests=Split-Path -Parent $PSScriptRoot
$repo=(Get-Item -LiteralPath $tests).Parent.Parent.Parent.Parent.FullName
$source=Join-Path $repo 'src'
$logs=Join-Path $tests 'logs'
$name="upl_p3_consist_${Configuration}_$Label"
$folder=Join-Path $tests "outputs\$name"
$harness=Join-Path $PSScriptRoot 'upl_p3_consist_r1.cpp'
$oldSource=Join-Path $PSScriptRoot 'upl_p3_pair_r1.cpp'
$note=Join-Path $tests 'notes\upl_p3_consist_r1.json'
$exe=Join-Path $folder 'upl_p3_consist_r1.exe'
$buildReceipt=Join-Path $logs ($name+'.build.json')
$oldPrefix="upl_p3_pair_${Configuration}_r1"
$oldBuildPath=Join-Path $logs ($oldPrefix+'.build.json')
$oldCheckPath=Join-Path $logs ($oldPrefix+'_run.check.json')
function Entry([string]$path){$f=Get-Item -LiteralPath $path;[pscustomobject][ordered]@{path=$f.FullName;bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
function Verify($entries){foreach($i in $entries){$f=Entry $i.path;if($f.sha256 -ne $i.sha256 -or $f.bytes -ne $i.bytes){throw "Frozen artifact changed: $($i.path)"}}}
function NewJson([string]$path,$value){if(Test-Path -LiteralPath $path){throw "Retained artifact protected: $path"};[IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 14)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))}
$oldBuild=Get-Content -LiteralPath $oldBuildPath -Raw|ConvertFrom-Json
$oldCheck=Get-Content -LiteralPath $oldCheckPath -Raw|ConvertFrom-Json
if($oldBuild.exit_code -ne 0 -or !$oldCheck.frozen_algebraic_gates_passed){throw 'Required original sealed P3 controls are absent/rejected; no rebaseline'}
$sourceEntry=@($oldBuild.inputs|Where-Object {$_.path -eq $oldSource})
if($sourceEntry.Count -ne 1){throw 'Old source was not bound by the retained original build'}
Verify $sourceEntry;Verify $oldCheck.files
if($Mode -eq 'Build'){
  if((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $buildReceipt)){throw 'Use a fresh label; no build overwrite'}
  $env:VSCMD_SKIP_SENDTELEMETRY='1'
  $lines=& $env:ComSpec /d /c 'call "D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && set'
  if($LASTEXITCODE){throw 'Visual Studio environment setup failed'}
  foreach($line in $lines){$i=$line.IndexOf('=');if($i -gt 0){[Environment]::SetEnvironmentVariable($line.Substring(0,$i),$line.Substring($i+1),'Process')}}
  $headers=@(Get-ChildItem -LiteralPath (Join-Path $source 'source') -File -Recurse|Where-Object {$_.Extension -in '.h','.hpp','.inl'}|ForEach-Object {$_.FullName})
  $inputs=@(@($harness,$oldSource,$PSCommandPath,$note,$oldBuildPath,$oldCheckPath)+$headers|Sort-Object -Unique|ForEach-Object {Entry $_})
  New-Item -ItemType Directory -Path $folder|Out-Null
  $snapshots=@();foreach($p in @($harness,$oldSource,$PSCommandPath,$note)){$dest=Join-Path $folder ([IO.Path]::GetFileName($p));Copy-Item -LiteralPath $p -Destination $dest;if((Entry $dest).sha256 -ne (Entry $p).sha256){throw 'Used-recipe snapshot mismatch'};$snapshots+=Entry $dest}
  $log=Join-Path $logs ($name+'.build.log');if(Test-Path -LiteralPath $log){throw 'Retained build log protected'}
  [IO.File]::WriteAllBytes($log,[byte[]]@())
  $flags=if($Configuration -eq 'Debug'){@('/Od','/MTd','/Zi','/RTC1')}else{@('/O2','/MT')}
  $compile=@('/nologo','/std:c++17','/EHsc','/W3','/fp:precise',"/I$source\source","/Fo$folder\upl_p3_consist_r1.obj","/Fe$exe","/Fd$folder\compile.pdb",'/sourceDependencies',(Join-Path $folder 'compile.dependencies.json'))+$flags+@($harness,'/link','/MACHINE:X64','/SUBSYSTEM:CONSOLE')
  if($Configuration -eq 'Debug'){$compile+=@('/DEBUG',"/PDB:$folder\link.pdb")}
  $started=[DateTime]::UtcNow.ToString('o');$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & cl.exe @compile 2>&1|Tee-Object -FilePath $log|Out-Host
  $exitCode=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  Verify $inputs;Verify $snapshots
  NewJson $buildReceipt ([ordered]@{status=if($exitCode -eq 0){'built_not_run'}else{'build_rejected_retained'};started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');exit_code=$exitCode;configuration=$Configuration;git_head=(& git -C $repo rev-parse HEAD);inputs=$inputs;snapshots=$snapshots;command=$compile;program=if(Test-Path -LiteralPath $exe){Entry $exe}else{$null};log=(Entry $log);production_objects_used=$false;production_program_replaced=$false;solver_started=$false;physical_acceptance=$false})
  if($exitCode -ne 0){throw 'Standalone consistency compile rejected; preserve evidence'}
  Write-Output "BUILT standalone consistency screen, not run: $exe";exit 0
}
if($Mode -eq 'Run'){
  $b=Get-Content -LiteralPath $buildReceipt -Raw|ConvertFrom-Json
  if($b.status -ne 'built_not_run'){throw 'No successful frozen standalone build'}
  Verify $b.inputs;Verify $b.snapshots;Verify @($b.program)
  $runName=$name+'_run';$out=Join-Path $tests "outputs\$runName";$control=$out+'_control'
  $log=Join-Path $logs ($runName+'.log');$receipt=Join-Path $logs ($runName+'.run.json');$check=Join-Path $logs ($runName+'.check.json');$controlCheck=Join-Path $logs ($runName+'.control.check.json');$energyCheck=Join-Path $logs ($runName+'.energy.check.json')
  foreach($p in @($out,$control,$log,$receipt,$check,$controlCheck,$energyCheck)){if(Test-Path -LiteralPath $p){throw 'Retained output protected; no automatic retry'}}
  $program=Entry $exe;$arguments=@('--out',$out);$started=[DateTime]::UtcNow.ToString('o')
  [IO.File]::WriteAllBytes($log,[byte[]]@());$oldAction=$ErrorActionPreference;$ErrorActionPreference='Continue'
  & $exe @arguments 2>&1|Tee-Object -FilePath $log|Out-Host
  $exitCode=$LASTEXITCODE;$ErrorActionPreference=$oldAction
  NewJson $receipt ([ordered]@{exit_code=$exitCode;started_utc=$started;ended_utc=[DateTime]::UtcNow.ToString('o');owned_call_exited=$true;program=$program;build_receipt=(Entry $buildReceipt);arguments=$arguments;log=(Entry $log);solver_started=$false;physical_acceptance=$false})
  if($exitCode -ne 0){throw 'Consistency component gate rejected; preserve outputs and do not rerun this label'}
  Verify $b.inputs;Verify $b.snapshots;Verify @($b.program);Verify $oldCheck.files
  $comparisons=@()
  foreach($file in $oldCheck.files){$copy=Entry (Join-Path $control ([IO.Path]::GetFileName($file.path)));if($copy.sha256 -ne $file.sha256 -or $copy.bytes -ne $file.bytes){throw 'Old13-field/all-row control changed; no candidate admission'};$comparisons+=@{frozen=$file;fresh=$copy}}
  if($comparisons.Count -ne 5){throw 'Old control coverage changed'}
  NewJson $controlCheck ([ordered]@{passed=$true;all_five_files_byte_identical=$true;old_fields_per_patch=13;old_rate_rows=63180;old_summary_rows=156;comparisons=$comparisons;retained_old_outputs_overwritten=$false;solver_started=$false;physical_acceptance=$false})
  $done=Get-Content -LiteralPath (Join-Path $out 'complete.json') -Raw|ConvertFrom-Json
  if(!$done.screening_stage_gates_passed -or $done.operators -ne 4 -or $done.field_patch_cases -ne 100 -or $done.matrix_rows -ne 6480 -or $done.quadratic_balance_rows -ne 6480 -or !$done.central_neighbor_support_verified -or $done.production_rate_pass_called -or $done.physical_acceptance){throw 'Completion disagrees with reviewed component scope'}
  $energyCode=@'
import csv,json,pathlib,sys,numpy as np
folder=pathlib.Path(sys.argv[1]);groups={}
for r in csv.DictReader((folder/'dirichlet_matrices.csv').open(newline='')):
 key=(int(r['dimension']),int(r['jitter']),r['operator']);groups.setdefault(key,[]).append(r)
assert len(groups)==16
results=[]
for (dim,jitter,op),rows in sorted(groups.items()):
 n=9 if dim==2 else 27;assert len(rows)==n*n
 A=np.full((n,n),np.nan);S=np.full(n,np.nan)
 for r in rows:
  i,j=int(r['row']),int(r['col']);assert np.isnan(A[i,j]);A[i,j]=float(r['A_per_s']);w=float(r['storage_weight_Vn_Kw'])
  assert np.isnan(S[i]) or S[i]==w
  S[i]=w
 assert np.isfinite(A).all() and np.isfinite(S).all() and (S>0).all()
 root=np.sqrt(S);B=root[:,None]*A/root[None,:];norm=float(np.linalg.norm(B,2));tolerance=4096*np.finfo(np.float64).eps*max(1.,norm)
 eigH=np.linalg.eigvalsh((B+B.T)*.5);eigA=np.linalg.eigvals(B);hmax=float(eigH[-1]);rmax=float(eigA.real.max());passed=hmax<=tolerance and rmax<=tolerance
 results.append(dict(dimension=dim,jitter=jitter,operator=op,core_size=n,norm2_B_per_s=norm,tolerance_per_s=tolerance,max_eig_symmetric_B_per_s=hmax,min_eig_symmetric_B_per_s=float(eigH[0]),max_real_eig_B_per_s=rmax,positive_growth_gate_passed=passed))
core_rows=sum(1 for _ in csv.DictReader((folder/'core.csv').open(newline='')));summary_rows=sum(1 for _ in csv.DictReader((folder/'summary.csv').open(newline='')))
assert core_rows==7776 and summary_rows==400
print(json.dumps(dict(passed=all(r['positive_growth_gate_passed'] for r in results),scope='Frozen9/27-core pressure Dirichlet restriction; outer pressure held0, not a production wall',python_version=sys.version,numpy_version=np.__version__,storage_metric='S=diag(Vi*ni/Kw); B=sqrtS*A*invsqrtS',positive_growth_tolerance='4096*eps*max(1,norm2(B))',matrix_count=16,matrix_rows=6480,core_csv_rows=core_rows,summary_csv_rows=summary_rows,results=results,physical_acceptance=False)))
'@
  $energyOutput=& 'D:\Anaconda3\python.exe' -B -c $energyCode $out
  if($LASTEXITCODE -ne 0){throw 'Offline matrix analysis failed; repair analysis only, do not rerun completed fixture'}
  $energy=$energyOutput|ConvertFrom-Json;NewJson $energyCheck $energy
  if(!$energy.passed){throw 'Frozen core Dirichlet positive-growth gate rejected; candidate held, no later run admitted'}
  $files=@(Get-ChildItem -LiteralPath $out,$control -File|Sort-Object FullName|ForEach-Object {Entry $_.FullName});Verify $files
  NewJson $check ([ordered]@{screening_gates_passed=$true;completion=$done;run_receipt=(Entry $receipt);build_receipt=(Entry $buildReceipt);old_controls=(Entry $controlCheck);core_energy=(Entry $energyCheck);files=$files;manifest_posthoc=$true;candidate_admission_requires_review=$true;new_global_budget_and_energy_diagnostic_only=$true;production_rate_overwrite_verified=$false;solver_started=$false;physical_acceptance=$false})
  Write-Output "Consistency/control/core-energy gates passed; no production/physical admission: $check";exit 0
}
