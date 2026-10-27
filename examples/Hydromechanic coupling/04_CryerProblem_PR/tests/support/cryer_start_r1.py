"""One fresh CPU Debug Cryer startup; no worker, notifier or physical repair."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
from datetime import datetime, timezone
import numpy as np
import pandas as pd

CASE=Path(__file__).resolve().parents[2]
TESTS=CASE/'tests'
REPO=CASE.parents[2]
TAG='cryer_start_r1'
DT=5e-6
READER=CASE.parent/'05_LianFlexibleStrip2D_PR/tests/outputs/hydro_native_r1/ReadHydroNative.exe'
READER_SOURCE=CASE.parent/'05_LianFlexibleStrip2D_PR/tests/scripts/read_hydro_native.cpp'


def bound(path):
    path=Path(path);digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=digest.hexdigest())


def utc():return datetime.now(timezone.utc).isoformat()


def write_json(path,data):
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf8')


def native(folder,part):
    raw=subprocess.check_output([str(READER),str(folder/'data'),str(part)],creationflags=subprocess.CREATE_NO_WINDOW)
    return pd.read_csv(io.BytesIO(raw),float_precision='round_trip')


def pore_dt(h):
    # Same constants/storage as JSphCpu::DtVariable; zero gravity uses9.80665.
    return (float(np.float32(.1))*float(np.float32(1000))*9.80665*float(np.float32(.3))
        /float(np.float32(2e8))*h*h/float(np.float32(1e-5)))


def inspect(a,initial,part):
    assert len(a)==37173 and a.id.nunique()==37173 and np.array_equal(a.id,initial.id), 'Native soil IDs/count changed'
    assert np.isfinite(a.to_numpy(dtype='<f8')).all(), f'Nonfinite native data in PART{part}'
    assert a.nout.eq(0).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all(), f'Excluded/plastic/invalid-density particle in PART{part}'
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all(), 'Expected double saved positions/stress state'
    assert a.load_available.eq(1).all(), 'HydroMechLoadAce telemetry is absent; cannot claim a load check'
    t=float(a.time_s.iloc[0]);drained=a.fstype.isin([2,3]).to_numpy();issues=[]
    drained_count=int(drained.sum())
    if not drained_count:issues.append('No true FSType2/3 drained nodes: drainage check would be vacuous')
    drained_max=float(a.pressure.to_numpy()[drained].__abs__().max()) if drained_count else 0.
    if drained_max!=0:issues.append(f'PART{part} t={t:.17g}: active FSType2/3 pressure maximum is {drained_max:.17g}Pa, not0')
    natural=float(a.dterror_s.max())
    if t and (not a.has_dterror.eq(1).all() or natural>1e-14):
        issues.append(f'PART{part} t={t:.17g}: original mechanical natural-step guard failed: has_dterror={int(a.has_dterror.min())}, max(DtFixed-DtVariable)={natural:.17g}s >1e-14s or missing')
    x=a[['x','y','z']].to_numpy();load=a[['load_ax','load_ay','load_az']].to_numpy();force=a.mass.to_numpy()[:,None]*load
    radius=np.linalg.norm(x,axis=1);unit=x/np.where(radius>0,radius,1)[:,None]
    loaded=np.linalg.norm(load,axis=1)>0
    q=10000.;R=.05;volume=4*np.pi*R**3/3;area=4*np.pi*R**2
    radial=float(-np.sum(force*unit));net=force.sum(axis=0);torque=np.cross(x,force).sum(axis=0)
    moment=-force.T@x/(q*volume)
    if t and (not loaded.any() or radial<=0):issues.append(f'PART{part}: no nonzero inward confinement load telemetry')
    row=dict(part=part,time_s=t,saved_step=int(a.saved_step.iloc[0]),native_soil_count=len(a),
        dterror_s=natural,has_dterror=int(a.has_dterror.min()),
        fstype0_count=int(a.fstype.eq(0).sum()),fstype1_count=int(a.fstype.eq(1).sum()),
        fstype2_count=int(a.fstype.eq(2).sum()),fstype3_count=int(a.fstype.eq(3).sum()),
        changed_fstype_from_initial=int((a.fstype.to_numpy()!=initial.fstype.to_numpy()).sum()),
        true_drained_count=drained_count,drained_pressure_abs_max_pa=drained_max,
        loaded_count=int(loaded.sum()),loaded_true_surface_count=int((loaded&drained).sum()),
        loaded_other_count=int((loaded&~drained).sum()),
        pressure_min_pa=float(a.pressure.min()),pressure_max_pa=float(a.pressure.max()),
        pressure_mean_pa=float(a.pressure.mean()),speed_max_m_s=float(np.linalg.norm(a[['vx','vy','vz']],axis=1).max()),
        total_sigma_zz_rms_pa=float(np.sqrt(np.mean((a.sigma_zz-a.pressure)**2))),
        saved_radius_min_m=float(radius.min()),saved_radius_max_m=float(radius.max()),
        near_origin_native_count=int((radius<=1e-10).sum()),
        native_volume_over_sphere=float((a.mass/a.rho).sum()/volume),
        poreDiffusionDt_s=pore_dt(float(a.h.iloc[0])),
        fixed_to_pore_dt_ratio=DT/pore_dt(float(a.h.iloc[0])),
        configured_pore_limit_respected=bool(DT<=pore_dt(float(a.h.iloc[0]))),
        radial_force_over_geometric_area_q=radial/(q*area),net_force_over_area_q=float(np.linalg.norm(net)/(q*area)),
        torque_norm_over_qV=float(np.linalg.norm(torque)/(q*volume)),affine_work_over_3qV=float(np.trace(moment)/3),
        moment_diagonal_spread=float(np.ptp(np.diag(moment))),
        moment_offdiagonal_norm=float(np.linalg.norm(moment-np.diag(np.diag(moment)))))
    for i,axis in enumerate('xyz'):
        row['net_force_'+axis+'_N']=float(net[i]);row['torque_'+axis+'_N_m']=float(torque[i])
        for j,other in enumerate('xyz'):row['moment_'+axis+other+'_over_qV']=float(moment[i,j])
    return row,issues


def main():
    assert os.name=='nt', 'Windows CPU Debug startup only'
    folder=TESTS/'outputs'/TAG;log=TESTS/'logs'/(TAG+'.log')
    run_path=TESTS/'logs'/(TAG+'.run.json');check=TESTS/'logs'/(TAG+'.check.json')
    summary=TESTS/'figures'/(TAG+'_summary.csv')
    assert not any(p.exists() for p in [folder,log,run_path,check,summary]), 'Never overwrite or restart an existing run'
    # Read-only process inventory; no other local Cryer solver may already be active.
    command="Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*' -and $_.CommandLine -match 'Cryer|cryer_start_r1'} | Select-Object Name,ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    active=subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True,
        timeout=20,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    assert not active, 'An existing Cryer solver is active: '+active
    root_xml=CASE/'CaseCryerProblem_PR_Def.xml';config=TESTS/'configs'/(TAG+'_Def.xml');bat=TESTS/'configs'/('x'+TAG+'_win64_CPU.bat')
    expected=root_xml.read_text(encoding='utf8')
    for key,value in [('SavePosDouble','1'),('TimeMax','0.001'),('TimeOut','0.00025')]:
        expected,count=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],expected);assert count==1,key
    expected=expected.replace('Full Cryer period for k=1e-5, corresponding to Tv=1','CPU Debug baseline startup window; not a full Cryer validation')
    expected=expected.replace('Output interval corresponding to Delta Tv=0.001; ignore t=0 for analytical comparison','Startup native save interval; five frames including t=0')
    explicit=''.join('            <parameter key="'+key+'" value="0" comment="Disabled for baseline startup (old default)" />\n'
        for key in ['SoilBoundaryDerivativeSPR','SoilHourglassXi','SoilStressRateGradCorr'])
    expected=expected.replace('        <parameters>\n','        <parameters>\n'+explicit)
    assert config.read_text(encoding='utf8')==expected, 'Unexpected XML change beyond the declared startup/output settings'
    audit=TESTS/'logs/cryer_load_audit_r1.json';old=json.loads(audit.read_text());assert old['soil_count']==37173
    assert bound(READER)['sha256']=='5d8fbeadc5f5b953eff85457c1bff690e22afc06a345d6d752113a1fa8f52502'
    programs=[REPO/'bin/windows'/n for n in ['GenCase_win64.exe','DualSPHysics5.2CPU_win64_debug.exe',
        'ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','DsphConfig.xml']]
    sources=[__file__,TESTS/'notes'/(TAG+'.md'),root_xml,config,bat,audit,READER,READER_SOURCE]+programs
    sources += [REPO/'src/source'/n for n in ['JSph.cpp','JSphCpu.cpp','JSphCpuSingle.cpp','JSphCpu.h',
        'JSphCpuSingle.h','DualSphDef.h','JDsFixedDt.cpp','JDsFixedDt.h']]
    sources += [REPO/'src/VS/DualSPHysics5ReCpu.vcxproj']
    inputs=[bound(p) for p in sources]
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,
        command=[os.environ['ComSpec'],'/d','/c',str(bat)],checked_frames=0,
        no_prior_Cryer_solver_observed=True,physical_accepted=False,theory_compared=False,
        long_window_admitted=False,
        fixed_step_pore_limit_note='The original5us fixed-step branch bypasses min(dt,dtw). Mechanical dterror passing does not demonstrate pore-diffusion safety; this is an intentionally retained diagnostic, not a step admission.',
        precision='Saved positions and persistent stress double; pore state/rate remain float. Native reader requires PorePress DatFloat.')
    def save():
        temporary=run_path.with_suffix('.tmp');write_json(temporary,state);os.replace(temporary,run_path)
    save();child=None;rows=[];initial=None;started=time.perf_counter()
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen(state['command'],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid']=child.pid;save();checked=0
            while True:
                code=child.poll();parts=sorted((folder/'data').glob('Part_*.bi4'))
                available=len(parts) if code is not None else max(0,len(parts)-1)
                while checked<available:
                    a=native(folder,checked)
                    if initial is None:
                        initial=a;state['initial_fstype_counts']={str(int(k)):int(v) for k,v in a.fstype.value_counts().items()}
                        state['initial_true_drained_count']=int(a.fstype.isin([2,3]).sum())
                    row,issues=inspect(a,initial,checked);rows.append(row)
                    if checked==0:
                        state['initial_geometry']=dict(radius_min_m=row['saved_radius_min_m'],radius_max_m=row['saved_radius_max_m'],
                            near_origin_native_count=row['near_origin_native_count'],origin_tolerance_m=1e-10,
                            native_volume_over_sphere=row['native_volume_over_sphere'])
                    state.update(checked_frames=len(rows),last_checked_time_s=row['time_s']);save()
                    assert not issues,'; '.join(issues)
                    checked+=1
                if code is not None:break
                time.sleep(2)
        state.update(exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-started)
        assert code==0,('CPU Debug wrapper exit',code)
        text=(folder/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text and 'DBC' in text
        assert len(rows)==5 and abs(rows[-1]['time_s']-.001)<=5.1e-6
        steps=int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1]);assert 200<=steps<=201
        for entry in inputs:assert bound(entry['path'])['sha256']==entry['sha256'],entry['path']
        state.update(status='startup_passed',steps=steps,observed_fstype_changed_in_window=any(r['changed_fstype_from_initial'] for r in rows))
    except Exception as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=15)
        state.update(status='startup_rejected_or_interrupted',error=repr(error),traceback=traceback.format_exc(),
            owned_exited=child is None or child.poll() is not None,exit_code=None if child is None else child.poll(),
            wall_seconds=time.perf_counter()-started)
    finally:
        if rows:pd.DataFrame(rows).to_csv(summary,index=False,float_format='%.17g')
        state.update(finished_utc=utc(),outputs=[bound(p) for p in folder.rglob('*') if p.is_file()],
            artifacts=([bound(summary)] if summary.exists() else [])+([bound(log)] if log.exists() else []))
        save()
        write_json(check,dict(passed=state['status']=='startup_passed',status=state['status'],run_manifest=bound(run_path),
            actual_last_saved_time_s=rows[-1]['time_s'] if rows else None,checked_frames=len(rows),
            error=state.get('error'),physical_accepted=False,theory_compared=False,
            poreDiffusionDt_s=rows[0]['poreDiffusionDt_s'] if rows else pore_dt(float(np.float32(.0045))),
            fixed_to_pore_dt_ratio=rows[0]['fixed_to_pore_dt_ratio'] if rows else DT/pore_dt(float(np.float32(.0045))),
            configured_pore_limit_respected=False,long_window_admitted=False,
            limits=['Startup only; no full Cryer/half-step/theory acceptance.',
                'The retained5us fixed step exceeds the configured pore-diffusion limit(~2.9788us); mechanical dterror does not check that limit. No automatic longer-window admission.',
                'No load-only correction, geometry normalization or physical operator change.',
                'Force moments and discrete-volume ratios are diagnostics, not imposed traction-error tolerances.',
                'Initial load telemetry is zero before the first force call, not a claim of zero applied pressure.',
                'True FSType2/3 masks are checked; saved membership may evolve under dynamic tracking.',
                'There may be no native r=0 node; future center pressure needs a declared fixed-material ball average/interpolation, not an assumed center ID.',
                'Cross-case reader executable/source hashes are bound; keep that retained reader available.']))
    print(json.dumps(dict(status=state['status'],checked_frames=len(rows),last_time_s=rows[-1]['time_s'] if rows else None,
        error=state.get('error')),indent=2),flush=True)


if __name__=='__main__':main()
