param(
    [ValidateSet('Help','Smoke','Full')][string]$Stage='Help',
    [string]$Python='D:\Anaconda3\python.exe'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$CasePath=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$RepoPath=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\..'))
$Tag='lian_server_particles_r1'
$Tests=Join-Path $CasePath 'tests'
$LogPrefix=Join-Path $Tests ('logs\'+$Tag)
$NativeOutput=Join-Path $CasePath 'CaseLianFlexibleStrip2D_PR_release_HGSPR_out'
$DataPath=Join-Path $NativeOutput 'data'
$CaseXml=Join-Path $NativeOutput 'CaseLianFlexibleStrip2D_PR_release.xml'
$PartVtk=Join-Path $RepoPath 'bin\windows\PartVTK_win64.exe'
$SmokePath=Join-Path $Tests 'outputs\lian_server_particles_smoke_r1'
$ParticlesPath=Join-Path $NativeOutput 'particles'
$Reader=Join-Path $Tests 'outputs\hydro_native_r1\ReadHydroNative.exe'
$Parser=Join-Path $Tests 'scripts\compare_lian_timestep.py'
$Variables='+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace'

function Bound([string]$LiteralPath){
    $item=Get-Item -LiteralPath $LiteralPath
    [ordered]@{path=$item.FullName;bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Save-NewJson([string]$LiteralPath,$Value){
    if(Test-Path -LiteralPath $LiteralPath){throw "Never overwrite retained record: $LiteralPath"}
    [IO.File]::WriteAllText($LiteralPath,($Value|ConvertTo-Json -Depth 16),[Text.UTF8Encoding]::new($false))
}
function Verify-Bindings($Bindings){
    foreach($entry in $Bindings){
        if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256){throw "Input hash changed: $($entry.path)"}
    }
}
function Export-Range([string]$Destination,[int]$First,[int]$Last,[string]$LogSuffix){
    $tokens=@('-dirin',$DataPath,'-filexml',$CaseXml,"-first:$First","-last:$Last",'-threads:4',
        '-savevtk',(Join-Path $Destination 'PartFluid'),'-onlytype:-all,fluid',"-vars:$Variables",
        '-savevtk',(Join-Path $Destination 'PartBound'),'-onlytype:-all,bound',"-vars:$Variables")
    $stdout=$LogPrefix+'.'+$LogSuffix+'.stdout.log';$stderr=$LogPrefix+'.'+$LogSuffix+'.stderr.log'
    if((Test-Path -LiteralPath $stdout) -or (Test-Path -LiteralPath $stderr)){throw 'Retained converter log exists'}
    $quoted=@($tokens|ForEach-Object {'"'+$_.Replace('"','\"')+'"'})
    $timer=[Diagnostics.Stopwatch]::StartNew()
    $process=Start-Process -FilePath $PartVtk -ArgumentList $quoted -WorkingDirectory $Destination -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Write-Host "PartVTK PID=$($process.Id), frames $First..$Last, four threads maximum; no physical solver."
    $process.WaitForExit();$process.Refresh();$timer.Stop()
    if($process.ExitCode -ne 0){throw "PartVTK exit $($process.ExitCode); inspect $stdout / $stderr"}
    [ordered]@{owned_pid=$process.Id;owned_exited=$true;exit_code=$process.ExitCode;wall_seconds=$timer.Elapsed.TotalSeconds;tokens=$tokens;stdout=(Bound $stdout);stderr=(Bound $stderr)}
}

# In-memory validation only; it creates no Python source or modified simulation fields.
$ValidatePython=@'
import sys,json,hashlib,subprocess,io
from pathlib import Path
import numpy as np,pandas as pd
case=Path(sys.argv[1]);folder=Path(sys.argv[2]);stage=sys.argv[3]
sys.path.insert(0,str(case/'tests/scripts'))
from compare_lian_timestep import parse_vtk
required={'idp','mk','vel','rhop','press','sigma_kk','sigma_ij','kplastic','fstype','fsnormal','porepress','porepress0','excessporepress','hydromechloadace'}
parts=[0,2000] if stage=='Smoke' else list(range(2001))
native_parts={0,2000} if stage=='Smoke' else {0,10,20,60,2000}
reader=case/'tests/outputs/hydro_native_r1/ReadHydroNative.exe';data=case/'CaseLianFlexibleStrip2D_PR_release_HGSPR_out/data'
files=[];native_checks=[];common_fields=None
for part in parts:
    fluid_fields=None
    for label,count,ids in [('PartFluid',20301,np.arange(1644,21945)),('PartBound',1644,np.arange(1644))]:
        path=folder/f'{label}_{part:04d}.vtk';xyz,fields=parse_vtk(path)
        fields={k.lower():v for k,v in fields.items()}
        assert len(xyz)==count and required<=fields.keys(),(str(path),len(xyz),sorted(fields))
        assert np.isfinite(xyz).all() and all(len(v)==count and np.isfinite(v).all() for v in fields.values()),str(path)
        order=np.argsort(fields['idp']);assert np.array_equal(fields['idp'][order],ids),str(path)
        assert np.array_equal(fields['excessporepress'],(fields['porepress']-fields['porepress0']).astype(np.float32).astype(float)),str(path)
        if common_fields is None:common_fields=sorted(fields)
        assert sorted(fields)==common_fields,(str(path),'schema drift')
        raw=path.read_bytes();files.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        if label=='PartFluid':fluid_fields={k:v[order] for k,v in fields.items()};fluid_xyz=xyz[order]
    if part in native_parts:
        raw=subprocess.check_output([str(reader),str(data),str(part)],creationflags=subprocess.CREATE_NO_WINDOW)
        native=pd.read_csv(io.BytesIO(raw),float_precision='round_trip')
        assert len(native)==20301 and native.native_count.eq(21945).all() and np.array_equal(native.id,np.arange(1644,21945))
        checks={'pressure':np.array_equal(fluid_fields['porepress'],native.pressure),
            'plastic':np.array_equal(fluid_fields['kplastic'],native.kplastic),
            'rho':np.array_equal(fluid_fields['rhop'],native.rho),
            'velocity':np.array_equal(fluid_fields['vel'],native[['vx','vy','vz']]),
            'sigma_kk_float_alias':np.array_equal(fluid_fields['sigma_kk'],native[['sigma_xx','sigma_yy','sigma_zz']].to_numpy().astype(np.float32).astype(float)),
            'sigma_ij_float_alias':np.array_equal(fluid_fields['sigma_ij'],native[['sigma_xy','sigma_yz','sigma_xz']].to_numpy().astype(np.float32).astype(float)),
            'load':np.array_equal(fluid_fields['hydromechloadace'],native[['load_ax','load_ay','load_az']]),
            'fstype':np.array_equal(fluid_fields['fstype'],native.fstype),
            'fsnormal':np.array_equal(fluid_fields['fsnormal'],native[['normal_x','normal_y','normal_z']])}
        assert all(checks.values()),(part,checks)
        x=native[['x','y','z']].to_numpy()
        position_mode='exact_native_double' if np.array_equal(fluid_xyz,x) else 'native_float32_projection'
        assert position_mode=='exact_native_double' or np.array_equal(fluid_xyz,x.astype(np.float32).astype(float)),part
        native_checks.append(dict(part=part,actual_time_s=float(native.time_s.iloc[0]),checks=checks,positions=position_mode,
            pore_min_pa=float(native.pressure.min()),pore_max_pa=float(native.pressure.max()),plastic_max=float(native.kplastic.max())))
assert len(list(folder.glob('PartFluid_*.vtk')))==len(parts) and len(list(folder.glob('PartBound_*.vtk')))==len(parts)
print(json.dumps(dict(passed=True,fluid_frames=len(parts),bound_frames=len(parts),soil_nodes=20301,bound_nodes=1644,total_nodes=21945,
    fields=common_fields,total_vtk_bytes=sum(f['bytes'] for f in files),files=files,native_value_checks=native_checks,
    limits=['Every VTK count/ID/schema/finite field and file hash checked; native numerical comparison is only at the listed snapshots.',
    'Sigma_kk/ij are legacy float display arrays; native double stress remains preserved in unchanged BI4.',
    'Visualization export is not physical accuracy acceptance.'])))
'@

if($Stage -eq 'Help'){
    Write-Output 'Use -Stage Smoke for first/final native-frame conversion and checks, then -Stage Full for all2001 frames. No solver, overwrite, queue or Git.'
    exit 0
}
foreach($path in @($Python,$PartVtk,$CaseXml,$Reader,$Parser,(Join-Path $DataPath 'Part_Head.ibi4'))){if(-not(Test-Path -LiteralPath $path)){throw "Missing input: $path"}}
$nativeFiles=@(Get-ChildItem -LiteralPath $DataPath -Filter 'Part_*.bi4' -File | Sort-Object Name)
if($nativeFiles.Count -ne 2001){throw "Expected2001 native frames, found $($nativeFiles.Count)"}
for($i=0;$i -le 2000;$i++){if($nativeFiles[$i].Name -ne ('Part_{0:D4}.bi4' -f $i)){throw 'Native frame indices are incomplete'}}
$baseInputs=@($PSCommandPath,$PartVtk,$CaseXml,$Reader,$Parser,(Join-Path $Tests 'scripts\read_hydro_native.cpp'),
    (Join-Path $RepoPath 'bin\windows\DsphConfig.xml'),(Join-Path $NativeOutput 'Run.out'),(Join-Path $DataPath 'Part_Head.ibi4'))
$oldOmp=[Environment]::GetEnvironmentVariable('OMP_NUM_THREADS','Process')
[Environment]::SetEnvironmentVariable('OMP_NUM_THREADS','4','Process')
try{
    if($Stage -eq 'Smoke'){
        if(Test-Path -LiteralPath $SmokePath){throw 'Smoke output exists; no overwrite or restart'}
        $free=(Get-PSDrive D).Free;if($free -lt 1GB){throw 'Insufficient D: free space for smoke'}
        $inputs=@($baseInputs+(Join-Path $DataPath 'Part_0000.bi4')+(Join-Path $DataPath 'Part_2000.bi4')|ForEach-Object {Bound $_})
        Save-NewJson ($LogPrefix+'.smoke.inputs.json') ([ordered]@{stage='smoke';utc=[DateTime]::UtcNow.ToString('o');free_D_bytes=$free;inputs=$inputs;variables=$Variables;threads_max=4})
        New-Item -ItemType Directory -Path $SmokePath | Out-Null
        $jobs=@();$jobs+=Export-Range $SmokePath 0 0 'smoke0';$jobs+=Export-Range $SmokePath 2000 2000 'smoke2000'
        $text=& $Python -B -c $ValidatePython $CasePath $SmokePath Smoke
        if($LASTEXITCODE -ne 0){throw 'Smoke VTK/native validation failed'}
        $validation=$text|ConvertFrom-Json;Verify-Bindings $inputs
        Save-NewJson ($LogPrefix+'.smoke.check.json') ([ordered]@{passed=$true;utc=[DateTime]::UtcNow.ToString('o');inputs=$inputs;jobs=$jobs;validation=$validation;physical_accepted=$false})
        Write-Output "SMOKE PASSED: two fluid and two bound VTKs; fields and native snapshots verified. $SmokePath"
    }else{
        $smokeFile=$LogPrefix+'.smoke.check.json';$smoke=Get-Content -LiteralPath $smokeFile -Raw|ConvertFrom-Json
        if(-not $smoke.passed){throw 'Smoke has not passed'}
        Verify-Bindings $smoke.inputs
        foreach($e in $smoke.validation.files){Verify-Bindings @($e)}
        if(Test-Path -LiteralPath $ParticlesPath){throw 'Formal particles already exists; never overwrite'}
        $estimate=[long]([math]::Ceiling($smoke.validation.total_vtk_bytes/2.0*2001));$required=[long]([math]::Ceiling(1.25*$estimate)+1GB)
        $free=(Get-PSDrive D).Free;if($free -lt $required){throw "Insufficient D: free space: $free, need $required"}
        $inputs=@($baseInputs+$nativeFiles.FullName|ForEach-Object {Bound $_})
        Save-NewJson ($LogPrefix+'.inputs.json') ([ordered]@{utc=[DateTime]::UtcNow.ToString('o');inputs=$inputs;smoke=(Bound $smokeFile);free_D_bytes=$free;estimated_vtk_bytes=$estimate;required_free_bytes=$required;variables=$Variables;threads_max=4})
        New-Item -ItemType Directory -Path $ParticlesPath | Out-Null
        $job=Export-Range $ParticlesPath 0 2000 'full'
        Save-NewJson ($LogPrefix+'.completion.json') ([ordered]@{converter_finished=$true;utc=[DateTime]::UtcNow.ToString('o');job=$job;inputs_manifest=(Bound ($LogPrefix+'.inputs.json'));physical_accepted=$false})
        $text=& $Python -B -c $ValidatePython $CasePath $ParticlesPath Full
        if($LASTEXITCODE -ne 0){throw 'Full VTK/native validation failed; retain completed conversion, do not blindly rerun'}
        $validation=$text|ConvertFrom-Json;Verify-Bindings $inputs
        Save-NewJson ($LogPrefix+'.check.json') ([ordered]@{passed=$true;utc=[DateTime]::UtcNow.ToString('o');inputs_manifest=(Bound ($LogPrefix+'.inputs.json'));completion=(Bound ($LogPrefix+'.completion.json'));validation=$validation;physical_accepted=$false;source_data_unchanged=$true})
        Write-Output "FULL PASSED:2001 fluid+2001 bound VTKs, all fields/counts/IDs checked; native numerical snapshots checked. $ParticlesPath"
    }
}finally{
    [Environment]::SetEnvironmentVariable('OMP_NUM_THREADS',$oldOmp,'Process')
}
