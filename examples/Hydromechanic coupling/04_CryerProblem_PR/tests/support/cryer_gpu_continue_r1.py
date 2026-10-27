"""Offline-adopt completed Debug; --run starts only the unrun original Release BAT."""
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
from cryer_start_r1 import CASE,TESTS,READER,bound,native,utc,write_json
from cryer_dt_short_r1 import inspect
from cryer_gpu_base_r1 import DT,prerequisites,verify

TAG='cryer_gpu_continue_r1'
PREP=TESTS/'logs'/(TAG+'.inputs.json')
COMPLETION=TESTS/'logs'/(TAG+'.completion.json')


def no_active_gpu():
    command="Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*' -and $_.CommandLine -match 'Cryer|cryer_'} | Select-Object Name,ProcessId,CommandLine | ConvertTo-Json -Compress"
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True,
        timeout=20,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    rows=json.loads(raw) if raw else []
    if isinstance(rows,dict):rows=[rows]
    assert all('CPU' in r['Name'].upper() for r in rows), 'A Cryer GPU solver is still active'
    return rows  # Independent CPU fine work is allowed and is never stopped.


def metadata(folder):
    text=(folder/'Run.out').read_text(errors='replace')
    assert 'Finished execution (code=0)' in text and 'DBC' in text
    assert len(list((folder/'data').glob('Part_*.bi4')))==5
    steps=int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1]);assert steps==200
    hardware=re.search(r'Device default:\s*([^\r\n]+)',text)
    capability=re.search(r'Compute capability:\s*([^\r\n]+)',text)
    assert hardware and capability, 'Actual GPU identity is missing'
    runtime=re.search(r'Simulation Runtime\.*:\s*([\d.]+)\s*sec',text)
    return dict(steps=steps,actual_gpu=hardware[1],compute_capability=capability[1],
        observed_simulation_runtime_s=float(runtime[1]) if runtime else None)


def measure(folder,data,cross):
    initial=native(TESTS/'outputs/cryer_dt_short_r1_c',0)
    center=np.linalg.norm(initial[['x','y','z']],axis=1)<=.0025+1e-12;assert center.any()
    for part in range(5):
        a=native(folder,part)
        if part==0:assert np.array_equal(a[['id','x','y','z','mass','rho','h']],initial[['id','x','y','z','mass','rho','h']])
        assert np.array_equal(a[['mass','h']],initial[['mass','h']])
        assert np.linalg.norm(a[['x','y','z']],axis=1).max()<=.0525
        row,issues=inspect(a,initial,part,DT,center);data['summary'].append(row)
        assert not issues,(part,issues)
        if cross:
            b=native(TESTS/'outputs/cryer_dt_short_r1_c',part)
            delta=abs(float(a.time_s.iloc[0]-b.time_s.iloc[0]));assert delta<1e-12
            assert a.saved_step.iloc[0]==b.saved_step.iloc[0]
            assert np.array_equal(a.id,b.id) and list(a.columns)==list(b.columns)
            assert np.array_equal(a.fstype.isin([2,3]),b.fstype.isin([2,3])), 'Same-dt drained masks differ'
            p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
            d=1000*float(np.linalg.norm(a[['x','y','z']].to_numpy()-b[['x','y','z']].to_numpy(),axis=1).max())
            data['cross'].append(dict(part=part,gpu_time_s=float(a.time_s.iloc[0]),cpu_time_s=float(b.time_s.iloc[0]),
                actual_time_difference_s=delta,pressure_rms_pa=p,material_displacement_max_mm=d,screen_passed=bool(p<=5 and d<=.005)))
            for col in a.columns:
                change=a[col].to_numpy(dtype=float)-b[col].to_numpy(dtype=float)
                data['native_differences'].append(dict(part=part,field=col,rms=float(np.sqrt(np.mean(change**2))),
                    maximum_absolute=float(abs(change).max()),different_count=int(np.count_nonzero(change))))
    assert abs(data['summary'][-1]['time_s']-.0005)<1e-12
    if cross:assert len(data['cross'])==5 and all(r['screen_passed'] for r in data['cross']), 'Original5Pa/.005mm CPU/GPU gate failed'


def csvs(prefix,data):
    files=[]
    for key,rows in data.items():
        if rows:
            path=TESTS/'figures'/(prefix+'_'+key+'.csv');assert not path.exists()
            pd.DataFrame(rows).to_csv(path,index=False,float_format='%.17g');files.append(bound(path))
    return files


def prepare():
    assert not PREP.exists(), 'Never overwrite a prepared continuation'
    prerequisites()
    base_path=TESTS/'logs/cryer_gpu_base_r1.inputs.json'
    base=json.loads(base_path.read_text(encoding='utf8'));verify(base['inputs'])
    old_check=TESTS/'logs/cryer_gpu_base_r1.check.json'
    check=json.loads(old_check.read_text(encoding='utf8'));verify([check['run_manifest']])
    old=json.loads(Path(check['run_manifest']['path']).read_text(encoding='utf8'))
    assert len(old['runs'])==1 and 'Debug memcheck did not pass' in old['error']
    dbg=old['runs'][0];assert dbg['name']=='cryer_gpu_base_r1_dbg' and dbg['exit_code']==0 and dbg['owned_exited']
    per_run=TESTS/'logs/cryer_gpu_base_r1_dbg.run.json'
    record=json.loads(per_run.read_text(encoding='utf8'));assert record==dbg
    verify([old['prepared_inputs']]+dbg['outputs'])
    folder=TESTS/'outputs'/dbg['name'];observed=metadata(folder)
    assert observed['actual_gpu']==dbg['actual_gpu'] and observed['compute_capability']==dbg['compute_capability']
    memcheck=(folder/'memcheck.log').read_text(errors='replace')
    errors=re.findall(r'ERROR SUMMARY:\s*(\d+) errors?',memcheck)
    leaks=re.findall(r'LEAK SUMMARY:\s*(\d+) bytes leaked in (\d+) allocations?',memcheck)
    assert errors and all(int(e)==0 for e in errors), 'Debug memcheck error summary is nonzero or absent'
    assert leaks and all(int(b)==0 and int(n)==0 for b,n in leaks), 'Debug leak summary is nonzero or absent'
    data={'summary':[]};measure(folder,data,False)
    adopt=TESTS/'logs'/(TAG+'.adopt_debug.json');assert not adopt.exists()
    sources=[bound(p) for p in [__file__,TESTS/'notes'/(TAG+'.md'),base_path,old_check,per_run,
        TESTS/'logs/cryer_gpu_base_r1_dbg.log',TESTS/'support/cryer_gpu_base_r1.py',
        TESTS/'support/cryer_start_r1.py',TESTS/'support/cryer_dt_short_r1.py',READER]]+[check['run_manifest']]
    artifacts=csvs(TAG+'_adopt_debug',data)
    write_json(adopt,dict(passed=True,scope='Offline completedDebug review only; old rejection remains unchanged',
        utc=utc(),checked_frames=5,actual_last_saved_time_s=data['summary'][-1]['time_s'],
        error_summary_counts=list(map(int,errors)),leak_summaries=[list(map(int,p)) for p in leaks],
        **observed,sources=sources,retained_outputs=dbg['outputs'],artifacts=artifacts,
        physical_accepted=False,half_step_accepted=False))
    job=next(j for j in base['jobs'] if j['label']=='c')
    assert not any(p.exists() for p in [TESTS/'outputs'/job['name'],TESTS/'logs'/(job['name']+'.log'),
        TESTS/'logs'/(job['name']+'.run.json')]), 'Original Release job already has evidence; never rerun it'
    write_json(PREP,dict(status='prepared_not_started',utc=utc(),job=job,adopted_debug=bound(adopt),
        inputs=sources+[bound(adopt)]+base['inputs'],old_base_status=old['status'],
        cpu_half_pair_passed=False,physical_accepted=False,long_window_admitted=False))
    print('PREPARED ONLY; Debug adopted offline:',PREP,flush=True)


def run():
    prepared=json.loads(PREP.read_text(encoding='utf8'));verify(prepared['inputs']);prerequisites()
    adopted=json.loads(Path(prepared['adopted_debug']['path']).read_text(encoding='utf8'))
    assert adopted['passed'];verify(adopted['retained_outputs'])
    job=prepared['job'];folder=TESTS/'outputs'/job['name'];log=TESTS/'logs'/(job['name']+'.log')
    run_path=TESTS/'logs'/(TAG+'.run.json');check=TESTS/'logs'/(TAG+'.check.json')
    assert not any(p.exists() for p in [folder,log,run_path,check,COMPLETION,TESTS/'logs'/(job['name']+'.run.json')]), 'Never restart the completed/interrupted Release job'
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),prepared_inputs=bound(PREP),
        adopted_debug=prepared['adopted_debug'],job=job,concurrent_cpu_processes=no_active_gpu(),
        cpu_half_pair_passed=False,physical_accepted=False,long_window_admitted=False)
    write_json(run_path,state);child=None;data={k:[] for k in ['summary','cross','native_differences']};started=time.perf_counter()
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,
                stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid']=child.pid;write_json(run_path,state);report=started
            while child.poll() is None:
                time.sleep(1)
                if time.perf_counter()-report>20:
                    print('RUNNING Release only',round(time.perf_counter()-started),'s',flush=True);report=time.perf_counter()
        state.update(exit_code=child.returncode,owned_exited=True,wall_seconds=time.perf_counter()-started)
        assert child.returncode==0,('Release wrapper exit',child.returncode)
        state.update(**metadata(folder));verify(prepared['inputs'])
        write_json(COMPLETION,dict(solver_finished=True,exit_code=0,utc=utc(),job=job,prepared_inputs=bound(PREP),
            **metadata(folder),outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)]))
        state['sealed_completion']=bound(COMPLETION);write_json(run_path,state)
        measure(folder,data,True)
        state['status']='release_cross_passed_pending_review'
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='release_rejected_or_interrupted',error=repr(error),traceback=traceback.format_exc(),
            owned_exited=child is None or child.poll() is not None,exit_code=None if child is None else child.poll())
    finally:
        state.update(finished_utc=utc(),artifacts=csvs(TAG,data),retained_outputs=[bound(p) for p in folder.rglob('*') if p.is_file()])
        write_json(run_path,state)
        write_json(check,dict(passed=state['status']=='release_cross_passed_pending_review',status=state['status'],run_manifest=bound(run_path),
            paired_samples=len(data['cross']),error=state.get('error'),max_pressure_rms_pa=max((p['pressure_rms_pa'] for p in data['cross']),default=None),
            max_material_displacement_mm=max((p['material_displacement_max_mm'] for p in data['cross']),default=None),
            physical_accepted=False,half_step_accepted=False,long_window_admitted=False,
            limits=['Completed Debug was rechecked offline, not rerun; original base rejection is retained.',
                'Only200steps/5frames Release versus same-dt CPU; not independent half or peak acceptance.',
                'Original5Pa/.005mm and native safety remain; old CPU half failure remains failed.',
                'Any sealed solver completion is reused for offline analysis, never rerun after analysis failure.',
                'Concurrent CPU is not stopped; timing is not a controlled benchmark. No notifier or automatic longer run.']))
    print(json.dumps(dict(status=state['status'],samples=len(data['cross']),error=state.get('error')),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:run()
    else:prepare()
