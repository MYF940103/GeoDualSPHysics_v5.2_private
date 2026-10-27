"""Prepare one existing-gradient-switch CPU pair; --run executes only this 0.5ms pair."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE,TESTS,REPO,READER,bound,native,utc,write_json
from cryer_dt_short_r1 import STAGES,inspect,clock

TAG='cryer_grad_short_r1'
PREP=TESTS/'logs'/(TAG+'.inputs.json')


def verify(entries):
    for e in entries:
        assert bound(e['path'])['sha256']==e['sha256'], e['path']


def reference():
    check=TESTS/'logs/cryer_dt_short_r1.check.json'
    old=json.loads(check.read_text(encoding='utf8'));verify([old['run_manifest']])
    run=json.loads(Path(old['run_manifest']['path']).read_text(encoding='utf8'))
    assert old['passed'] is False and old['paired_samples']==5
    verify(run['inputs'])
    for label,dt in STAGES:
        r=next(r for r in run['runs'] if r['name']=='cryer_dt_short_r1_'+label)
        assert r['passed'] and r['owned_exited'] and r['exit_code']==0
        assert r['checked_frames']==5 and r['steps']==round(.0005/dt)
        verify(r['outputs'])
    program=next(e for e in run['inputs'] if Path(e['path']).name=='DualSPHysics5.2CPU_win64.exe')
    assert program['sha256']=='dc4e2a1feb2245e5a9c567d1bc1877e774a6b70b1058e805f4c6d61aa063ca9c'
    return old,run,program


def prepare():
    assert not PREP.exists(), 'Inputs already prepared; never overwrite or restart'
    old,_,program=reference()
    proof=TESTS/'outputs/cryer_force_cpu_r1_run/force_summary.json'
    manufactured=json.loads(proof.read_text(encoding='utf8'))
    assert manufactured['diagnostic_completed'] and manufactured['time_integrated'] is False
    assert any(c['label']=='affine_grad1' and c['runtime_gradcorr'] for c in manufactured['cases'])
    inputs=[bound(p) for p in [__file__,TESTS/'notes'/(TAG+'.md'),
        TESTS/'support/cryer_start_r1.py',TESTS/'support/cryer_dt_short_r1.py',READER,
        TESTS/'logs/cryer_dt_short_r1.check.json',TESTS/'logs/cryer_dt_short_r1.run.json',proof]]
    jobs=[]
    oldline='<parameter key="SoilStressRateGradCorr" value="0" comment="Disabled for baseline startup (old default)" />'
    newline='<parameter key="SoilStressRateGradCorr" value="1" comment="Enabled for controlled stress-rate gradient comparison" />'
    for label,dt in STAGES:
        oldname='cryer_dt_short_r1_'+label;name=TAG+'_'+label
        source=TESTS/'configs'/(oldname+'_Def.xml');template=TESTS/'configs'/('x'+oldname+'_win64_CPU.bat')
        cfg=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64_CPU.bat')
        assert not any(p.exists() for p in [cfg,bat,TESTS/'outputs'/name,TESTS/'logs'/(name+'.run.json')])
        text=source.read_text(encoding='utf8');assert text.count(oldline)==1
        cfg.write_text(text.replace(oldline,newline),encoding='utf8',newline='\n')
        bat.write_text(template.read_text(encoding='utf8').replace(oldname,name),encoding='utf8',newline='\r\n')
        jobs.append(dict(name=name,label=label,dt_s=dt,config=bound(cfg),bat=bound(bat),reference=oldname))
        inputs += [bound(source),bound(template),bound(cfg),bound(bat)]
    write_json(PREP,dict(status='prepared_not_started',utc=utc(),jobs=jobs,inputs=inputs,program=program,
        declared_change='SoilStressRateGradCorr0to1 only; existing production option, no force/operator patch',
        old_cpu_pair_passed=False,old_cpu_pair_max_pressure_rms_pa=old['max_pressure_rms_pa'],
        clock_budget=[clock(dt) for _,dt in STAGES],physical_accepted=False,peak_window_admitted=False))
    print('PREPARED ONLY:',PREP,flush=True)


def inventory():
    command="Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*' -and $_.CommandLine -match 'Cryer|cryer_'} | Select-Object Name,ProcessId,CommandLine | ConvertTo-Json -Compress"
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True,
        timeout=20,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    rows=json.loads(raw) if raw else []
    if isinstance(rows,dict):rows=[rows]
    assert not any('CPU' in row['Name'].upper() for row in rows), 'Another Cryer CPU solver exists'
    return rows  # Existing GPU diagnostic is allowed, never stopped; timing is not isolated.


def difference(a,b):
    assert np.array_equal(a.id,b.id) and list(a.columns)==list(b.columns)
    dp=a.pressure.to_numpy()-b.pressure.to_numpy()
    tensor=np.column_stack([a[c]-b[c]-(dp if c in ['sigma_xx','sigma_yy','sigma_zz'] else 0)
        for c in ['sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_yz','sigma_xz']])
    return dict(pressure_rms_pa=float(np.sqrt(np.mean(dp**2))),
        material_displacement_max_mm=1000*float(np.linalg.norm(a[['x','y','z']].to_numpy()-b[['x','y','z']].to_numpy(),axis=1).max()),
        total_stress_six_component_rms_pa=float(np.sqrt(np.mean(tensor**2))),
        velocity_vector_rms_m_s=float(np.sqrt(np.mean(np.sum((a[['vx','vy','vz']].to_numpy()-b[['vx','vy','vz']].to_numpy())**2,axis=1)))),
        density_rms_kg_m3=float(np.sqrt(np.mean((a.rho-b.rho)**2))),
        load_vector_rms_m_s2=float(np.sqrt(np.mean(np.sum((a[['load_ax','load_ay','load_az']].to_numpy()-b[['load_ax','load_ay','load_az']].to_numpy())**2,axis=1)))),
        fstype_mismatches=int(np.count_nonzero(a.fstype.to_numpy()!=b.fstype.to_numpy())),
        drained_mask_mismatches=int(np.count_nonzero(a.fstype.isin([2,3]).to_numpy()!=b.fstype.isin([2,3]).to_numpy())))


def run():
    prepared=json.loads(PREP.read_text(encoding='utf8'));verify(prepared['inputs']);verify([prepared['program']])
    old,_,_=reference()
    run_path=TESTS/'logs'/(TAG+'.run.json');check=TESTS/'logs'/(TAG+'.check.json')
    csvs={k:TESTS/'figures'/(TAG+'_'+k+'.csv') for k in ['summary','half','options','native_differences']}
    assert not any(p.exists() for p in [run_path,check,*csvs.values()]), 'Never restart a retained sequence'
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),prepared_inputs=bound(PREP),
        program=prepared['program'],runs=[],cpu_pair_reference_passed=False,
        old_cpu_pair_max_pressure_rms_pa=old['max_pressure_rms_pa'],existing_gpu_processes=inventory(),
        physical_accepted=False,peak_window_admitted=False)
    def save():
        temporary=run_path.with_suffix('.tmp');write_json(temporary,state);os.replace(temporary,run_path)
    save();child=None;current=None;data={k:[] for k in csvs};frames={}
    try:
        initial=native(TESTS/'outputs/cryer_dt_short_r1_c',0)
        center=np.linalg.norm(initial[['x','y','z']],axis=1)<=.0025+1e-12
        assert center.any();state['center_material_ids']=list(map(int,initial.id.to_numpy()[center]))
        for job in prepared['jobs']:
            concurrent=inventory();verify(prepared['inputs']);verify([prepared['program']])
            name=job['name'];dt=job['dt_s'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            receipt=TESTS/'logs'/(name+'.run.json')
            assert not any(p.exists() for p in [folder,log,receipt])
            current=dict(name=name,dt_s=dt,passed=False,config=job['config'],bat=job['bat'],
                prepared_inputs=bound(PREP),started_utc=utc(),concurrent_gpu_processes=concurrent)
            state['runs'].append(current);save();write_json(receipt,current);started=time.perf_counter()
            with log.open('xb') as stream:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,
                    stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                current['owned_wrapper_pid']=child.pid;save();report=started
                while child.poll() is None:
                    time.sleep(1)
                    if time.perf_counter()-report>20:
                        print('RUNNING',name,'wall_s',round(time.perf_counter()-started),flush=True);report=time.perf_counter()
            current.update(exit_code=child.returncode,owned_exited=True,wall_seconds=time.perf_counter()-started)
            assert child.returncode==0,(name,child.returncode)
            text=(folder/'Run.out').read_text(errors='replace')
            assert 'Finished execution (code=0)' in text and 'DBC' in text
            assert 'SoilStressRateGradCorr="KernelGradient"' in text, 'Existing stress-rate switch did not activate'
            current['steps']=int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])
            assert current['steps']==round(.0005/dt) and len(list((folder/'data').glob('Part_*.bi4')))==5
            loop=re.search(r'Simulation Runtime\.*:\s*([\d.]+)\s*sec',text)
            if loop:current['observed_simulation_runtime_s']=float(loop[1])
            frames[name]=[]
            for part in range(5):
                a=native(folder,part)
                if part==0:assert np.array_equal(a[['id','x','y','z','rho','mass','h']],initial[['id','x','y','z','rho','mass','h']])
                row,issues=inspect(a,initial,part,dt,center);row['run']=name;data['summary'].append(row)
                assert not issues,(name,part,issues)
                current.update(checked_frames=part+1,actual_last_saved_time_s=row['time_s']);save();frames[name].append(a)
                b=native(TESTS/'outputs'/job['reference'],part)
                assert abs(float(a.time_s.iloc[0]-b.time_s.iloc[0]))<1e-12 and a.saved_step.iloc[0]==b.saved_step.iloc[0], 'Same-dt option clocks differ'
                data['options'].append(dict(run=name,reference=job['reference'],part=part,time_s=row['time_s'],
                    comparison='grad1_minus_same_dt_grad0_not_half_or_theory_error',**difference(a,b)))
                for column in a.columns:
                    change=a[column].to_numpy(dtype=float)-b[column].to_numpy(dtype=float)
                    data['native_differences'].append(dict(run=name,part=part,field=column,rms=float(np.sqrt(np.mean(change**2))),
                        maximum_absolute=float(abs(change).max()),different_count=int(np.count_nonzero(change))))
            assert abs(current['actual_last_saved_time_s']-.0005)<1e-12
            verify(prepared['inputs']);verify([prepared['program']]);reference()
            current.update(passed=True,finished_utc=utc(),outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)])
            write_json(receipt,current);save();print('PASS',name,current['wall_seconds'],flush=True)
        failures=[]
        for part,(c,h) in enumerate(zip(frames[prepared['jobs'][0]['name']],frames[prepared['jobs'][1]['name']])):
            delta=abs(float(c.time_s.iloc[0]-h.time_s.iloc[0]));assert delta<1e-12, 'Half clocks differ; no interpolation'
            row=dict(part=part,coarse_time_s=float(c.time_s.iloc[0]),half_time_s=float(h.time_s.iloc[0]),
                actual_time_difference_s=delta,**difference(c,h))
            row['screen_passed']=row['pressure_rms_pa']<=5 and row['material_displacement_max_mm']<=.005
            data['half'].append(row)
            if not row['screen_passed']:failures.append(row)
        state['half_failures']=failures
        assert not failures,('Original5Pa/.005mm independent half screen failed',failures)
        state['status']='grad_short_pair_passed_pending_review'
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='grad_short_pair_rejected_or_interrupted',error=repr(error),traceback=traceback.format_exc())
        if current is not None and not current.get('passed'):
            current.update(owned_exited=child is None or child.poll() is not None,error=repr(error),
                exit_code=None if child is None else child.poll(),outputs=[bound(p) for p in (TESTS/'outputs'/current['name']).rglob('*') if p.is_file()])
            write_json(TESTS/'logs'/(current['name']+'.run.json'),current)
    finally:
        artifacts=[]
        for key,path in csvs.items():
            if data[key]:pd.DataFrame(data[key]).to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
        state.update(finished_utc=utc(),artifacts=artifacts);save()
        write_json(check,dict(passed=state['status']=='grad_short_pair_passed_pending_review',status=state['status'],
            run_manifest=bound(run_path),paired_samples=len(data['half']),error=state.get('error'),
            max_pressure_rms_pa=max((p['pressure_rms_pa'] for p in data['half']),default=None),
            max_material_displacement_mm=max((p['material_displacement_max_mm'] for p in data['half']),default=None),
            physical_accepted=False,peak_window_admitted=False,
            limits=['Only200/400steps and5saved frames each; no peak-window/full/analytical acceptance.',
                'Same-dt grad0/1 differences are not half-step or theory errors; no5Pa threshold is applied to option changes.',
                'OldCPU half failed56.380737Pa and remains failed; old individual trajectories are adopted only as controls.',
                'No external-load, density, damping, Darcy, geometry or persistent-precision change; no D clone.',
                'Existing GPU work is permitted and never stopped; observed timings are not isolated benchmarks.',
                'No notifier, threshold relaxation or automatic longer run.']))
    print(json.dumps(dict(status=state['status'],samples=len(data['half']),error=state.get('error')),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:run()
    else:prepare()
