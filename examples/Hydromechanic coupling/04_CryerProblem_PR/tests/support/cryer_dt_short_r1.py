"""Two bounded Release CPU starts; strict actual-time half-step screening only."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE,TESTS,REPO,READER,READER_SOURCE,bound,native,pore_dt,utc,write_json

TAG='cryer_dt_short_r1'
STAGES=[('c',2.5e-6),('h',1.25e-6)]


def clock(dt):
    t=0.;n=0;next_save=.000125;saved=[dict(step=0,time_s=0.)]
    while t<.0005:
        t+=dt;n+=1
        if t>=next_save or t>=.0005:
            saved.append(dict(step=n,time_s=t));next_save+=.000125
    assert len(saved)==5
    return saved


def inspect(a,initial,part,dt,center):
    assert len(a)==37173 and a.id.nunique()==37173 and np.array_equal(a.id,initial.id), 'Native soil IDs/count changed'
    assert np.isfinite(a.to_numpy(dtype='<f8')).all(), 'Nonfinite native data'
    assert a.nout.eq(0).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all(), 'Excluded/plastic/invalid-density particle'
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all(), 'Missing double position/stress state'
    assert a.load_available.eq(1).all(), 'Actual load telemetry absent'
    t=float(a.time_s.iloc[0]);mask=a.fstype.isin([2,3]).to_numpy();issues=[]
    if not mask.any():issues.append('True FSType2/3 drainage mask is empty')
    drained=float(abs(a.pressure.to_numpy()[mask]).max()) if mask.any() else 0.
    if drained!=0:issues.append(f'True drained pressure is {drained:.17g}Pa, not0')
    natural=float(a.dterror_s.max());dtw=pore_dt(float(a.h.iloc[0]))
    if t and (not a.has_dterror.eq(1).all() or natural>1e-14):issues.append(f'Mechanical dterror={natural:.17g}s or missing flag')
    if dt>dtw:issues.append(f'Fixed dt={dt:.17g}s exceeds original pore dt={dtw:.17g}s')
    x=a[['x','y','z']].to_numpy();x0=initial[['x','y','z']].to_numpy()
    r=np.linalg.norm(x,axis=1);r0=np.linalg.norm(x0,axis=1)
    force=a.mass.to_numpy()[:,None]*a[['load_ax','load_ay','load_az']].to_numpy()
    loaded=np.linalg.norm(force,axis=1)>0;unit=x/np.where(r>0,r,1)[:,None]
    q=10000.;V=4*np.pi*.05**3/3;A=4*np.pi*.05**2
    radial=float(-np.sum(force*unit));net=force.sum(axis=0);torque=np.cross(x,force).sum(axis=0);moment=-force.T@x/(q*V)
    if t and (not loaded.any() or radial<=0):issues.append('Actual inward confinement telemetry is zero')
    row=dict(part=part,time_s=t,saved_step=int(a.saved_step.iloc[0]),dt_s=dt,
        native_ids=len(a),true_drained_count=int(mask.sum()),drained_pressure_abs_max_pa=drained,
        changed_fstype_from_initial=int((a.fstype.to_numpy()!=initial.fstype.to_numpy()).sum()),
        center_material_count=int(center.sum()),center_pressure_mean_pa=float(a.pressure.to_numpy()[center].mean()),
        pressure_rms_pa=float(np.sqrt(np.mean(a.pressure**2))),pressure_max_pa=float(a.pressure.max()),
        pressure_min_pa=float(a.pressure.min()),center_radial_settlement_mm=1000*float((r0[center]-r[center]).mean()),
        material_displacement_max_mm=1000*float(np.linalg.norm(x-x0,axis=1).max()),
        total_sigma_zz_rms_pa=float(np.sqrt(np.mean((a.sigma_zz-a.pressure)**2))),
        speed_max_m_s=float(np.linalg.norm(a[['vx','vy','vz']],axis=1).max()),
        dterror_s=natural,poreDiffusionDt_s=dtw,fixed_to_pore_dt_ratio=dt/dtw,configured_pore_limit_respected=bool(dt<=dtw),
        loaded_count=int(loaded.sum()),loaded_true_surface_count=int((loaded&mask).sum()),loaded_other_count=int((loaded&~mask).sum()),
        radial_force_over_geometric_area_q=radial/(q*A),net_force_over_area_q=float(np.linalg.norm(net)/(q*A)),
        torque_norm_over_qV=float(np.linalg.norm(torque)/(q*V)),affine_work_over_3qV=float(np.trace(moment)/3),
        moment_diagonal_spread=float(np.ptp(np.diag(moment))),moment_offdiagonal_norm=float(np.linalg.norm(moment-np.diag(np.diag(moment)))))
    for i,s in enumerate('xyz'):
        row['net_force_'+s+'_N']=float(net[i]);row['torque_'+s+'_N_m']=float(torque[i])
        for j,u in enumerate('xyz'):row['moment_'+s+u+'_over_qV']=float(moment[i,j])
    return row,issues


def main():
    state_path=TESTS/'logs'/(TAG+'.run.json');check=TESTS/'logs'/(TAG+'.check.json')
    history_path=TESTS/'figures'/(TAG+'_summary.csv');pair_path=TESTS/'figures'/(TAG+'_half.csv')
    assert not any(p.exists() for p in [state_path,check,history_path,pair_path]), 'Never overwrite/restart a retained test'
    old_check=TESTS/'logs/cryer_start_r1.check.json';old=json.loads(old_check.read_text());assert old['passed']
    assert bound(old['run_manifest']['path'])['sha256']==old['run_manifest']['sha256']
    command="Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*' -and $_.CommandLine -match 'Cryer|cryer_dt_short_r1'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    active=subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    assert not active,'Existing Cryer solver: '+active
    budget=[clock(dt) for _,dt in STAGES]
    assert max(abs(a['time_s']-b['time_s']) for a,b in zip(*budget))<1e-12
    base_xml=(TESTS/'configs/cryer_start_r1_Def.xml').read_text();base_bat=(TESTS/'configs/xcryer_start_r1_win64_CPU.bat').read_text()
    jobs=[]
    for label,dt in STAGES:
        name=TAG+'_'+label;config=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64_CPU.bat')
        expected=base_xml
        for key,value in [('DtIni',str(dt)),('DtFixed',str(dt)),('TimeMax','0.0005'),('TimeOut','0.000125')]:
            expected,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],expected);assert n==1
        expected=expected.replace('CPU Debug baseline startup window','CPU Release short-step startup window')
        assert config.read_text()==expected,'Unexpected XML difference'
        assert bat.read_text()==base_bat.replace('cryer_start_r1',name).replace('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2CPU_win64.exe')
        assert not (TESTS/'outputs'/name).exists() and not (TESTS/'logs'/(name+'.log')).exists()
        jobs.append(dict(name=name,dt=dt,config=bound(config),bat=bound(bat)))
    programs=[REPO/'bin/windows'/n for n in ['GenCase_win64.exe','DualSPHysics5.2CPU_win64.exe','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','DsphConfig.xml']]
    sources=[__file__,TESTS/'notes'/(TAG+'.md'),TESTS/'support/cryer_start_r1.py',READER,READER_SOURCE,old_check,
        Path(old['run_manifest']['path']),TESTS/'configs/cryer_start_r1_Def.xml',TESTS/'configs/xcryer_start_r1_win64_CPU.bat',
        TESTS/'logs'/ (TAG+'_release.build.log')]+programs
    sources += [REPO/'src/source'/n for n in ['JSph.cpp','JSphCpu.cpp','JSphCpuSingle.cpp','JDsFixedDt.cpp','JSphCpu.h','DualSphDef.h']]
    sources.append(REPO/'src/VS/DualSPHysics5ReCpu.vcxproj')
    inputs=[bound(p) for p in sources]+[j[k] for j in jobs for k in ['config','bat']]
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,jobs=jobs,runs=[],
        release_build_observed_exit_code=0,binary64_clock_budget=budget,physical_accepted=False,peak_window_admitted=False,
        screen='Original5Pa fieldRMS/.005mm material-displacement implementation screen, not an analytical accuracy threshold.',
        precision='Float pore state/rate, double persistent stress and saved positions; no hidden change of cryer_start_r1.DT.')
    def save():
        tmp=state_path.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,state_path)
    save();child=None;current=None;history=[];pairs=[];frames={};initial=None;center=None
    try:
        for job in jobs:
            name=job['name'];dt=job['dt'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            current=dict(name=name,dt_s=dt,passed=False,checked_frames=0);state['runs'].append(current);save();started=time.perf_counter()
            with log.open('xb') as stream:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                current['owned_wrapper_pid']=child.pid;save();report=time.perf_counter()
                while child.poll() is None:
                    time.sleep(2)
                    if time.perf_counter()-report>=30:
                        print('RUNNING',name,'wall_s',round(time.perf_counter()-started),flush=True);report=time.perf_counter()
                current.update(exit_code=child.returncode,owned_exited=True,wall_seconds=time.perf_counter()-started)
            assert child.returncode==0,(name,child.returncode)
            assert len(list((folder/'data').glob('Part_*.bi4')))==5
            text=(folder/'Run.out').read_text(errors='replace');assert 'Finished execution (code=0)' in text and 'DBC' in text
            current['steps']=int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])
            assert current['steps']==round(.0005/dt)
            frames[name]=[]
            for part in range(5):
                a=native(folder,part)
                if initial is None:
                    initial=a;radius=np.linalg.norm(a[['x','y','z']],axis=1);center=radius<=.0025+1e-12;assert center.any()
                    state['center_material_ids']=list(map(int,a.id.to_numpy()[center]));state['center_initial_radius_limit_m']=.0025+1e-12
                    state['initial_near_origin_native_count']=int((radius<=1e-10).sum())
                if part==0:assert np.array_equal(a[['id','x','y','z']],initial[['id','x','y','z']])
                row,issues=inspect(a,initial,part,dt,center);row['run']=name;history.append(row);frames[name].append(a)
                current.update(checked_frames=part+1,actual_last_saved_time_s=row['time_s']);save()
                assert not issues,(name,part,row['time_s'],issues)
            assert abs(current['actual_last_saved_time_s']-.0005)<1e-12
            current.update(passed=True,outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)])
            save();print('PASS',name,current['wall_seconds'],flush=True)
        failures=[]
        for i,(c,h) in enumerate(zip(frames[jobs[0]['name']],frames[jobs[1]['name']])):
            delta=abs(float(c.time_s.iloc[0]-h.time_s.iloc[0]));assert delta<1e-12,('Actual output clocks do not match; no interpolation',i,delta)
            assert np.array_equal(c.id,h.id)
            p=float(np.sqrt(np.mean((c.pressure-h.pressure)**2)))
            d=1000*float(np.linalg.norm(c[['x','y','z']].to_numpy()-h[['x','y','z']].to_numpy(),axis=1).max())
            stress=np.column_stack([c[col]-h[col]-(c.pressure-h.pressure if col in ['sigma_xx','sigma_yy','sigma_zz'] else 0) for col in ['sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_yz','sigma_xz']])
            pairs.append(dict(part=i,coarse_time_s=float(c.time_s.iloc[0]),half_time_s=float(h.time_s.iloc[0]),actual_time_difference_s=delta,
                pressure_rms_pa=p,material_displacement_max_mm=d,center_mean_pressure_difference_pa=float((c.pressure-h.pressure).to_numpy()[center].mean()),
                total_stress_six_component_rms_pa=float(np.sqrt(np.mean(stress**2))),velocity_vector_rms_m_s=float(np.sqrt(np.mean(np.sum((c[['vx','vy','vz']].to_numpy()-h[['vx','vy','vz']].to_numpy())**2,axis=1)))),
                initial_transient_sample=bool(i>0),screen_passed=bool(p<=5 and d<=.005)))
            if p>5 or d>.005:failures.append(dict(part=i,time_s=float(c.time_s.iloc[0]),pressure_rms_pa=p,material_displacement_max_mm=d))
        state['half_failures']=failures
        assert not failures,('Conservative startup implementation screen failed; not a theory error',failures)
        for e in inputs:assert bound(e['path'])['sha256']==e['sha256'],e['path']
        state['status']='short_pair_passed_pending_review'
    except Exception as error:
        if child is not None and child.poll() is None:
            stopped=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True);state['owned_stop_exit_code']=stopped.returncode;child.wait(timeout=15)
        state.update(status='short_pair_rejected_or_interrupted',error=repr(error),traceback=traceback.format_exc())
        if current is not None:
            current.update(owned_exited=child is None or child.poll() is not None,exit_code=None if child is None else child.poll())
            folder=TESTS/'outputs'/current['name'];current['retained_outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()]
    finally:
        artifacts=[]
        for path,data in [(history_path,history),(pair_path,pairs)]:
            if data:pd.DataFrame(data).to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
        state.update(finished_utc=utc(),artifacts=artifacts);save()
        write_json(check,dict(passed=state['status']=='short_pair_passed_pending_review',status=state['status'],run_manifest=bound(state_path),
            paired_samples=len(pairs),max_pressure_rms_pa=max((p['pressure_rms_pa'] for p in pairs),default=None),
            max_material_displacement_mm=max((p['material_displacement_max_mm'] for p in pairs),default=None),
            center_material_count=int(center.sum()) if center is not None else None,error=state.get('error'),
            physical_accepted=False,peak_window_admitted=False,
            limits=['Only0.5ms startup, not a peak-window/half-cycle/analytical accuracy acceptance.',
                'Both steps must meet original poreDtSafety separately from mechanical dterror.',
                'Center mean uses fixed initialr<=dp+1e-12 material IDs; no assumed r=0 node.',
                '5Pa/.005mm is a conservative implementation screen; initial step-load transients are separately reported.',
                'No interpolation, threshold relaxation, extra step search, worker, notifier or automatic longer run.']))
    print(json.dumps(dict(status=state['status'],pairs=len(pairs),error=state.get('error')),indent=2),flush=True)


if __name__=='__main__':main()
