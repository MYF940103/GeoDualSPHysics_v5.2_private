"""Prepare a binary-exact finer CPU startup pair; only --run starts its two jobs."""
import argparse
import json
import os
import re
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE,TESTS,READER,bound,native,utc,write_json
from cryer_dt_short_r1 import inspect
from cryer_grad_short_r1 import verify,inventory,difference

TAG='cryer_grad_fine_r1'
STAGES=[('c','0.000000476837158203125',1024),('h','0.0000002384185791015625',2048)]
DURATION=2.**-11
INTERVAL=2.**-13
PREP=TESTS/'logs'/(TAG+'.inputs.json')


def prerequisites():
    check=TESTS/'logs/cryer_grad_short_r1.check.json'
    old=json.loads(check.read_text(encoding='utf8'));verify([old['run_manifest']])
    run=json.loads(open(old['run_manifest']['path'],encoding='utf8').read())
    assert not old['passed'] and old['paired_samples']==5
    assert all(r['passed'] and r['owned_exited'] and r['exit_code']==0 for r in run['runs'])
    assert len(run['runs'])==2
    prior=run['prepared_inputs'];verify([prior])
    prepared=json.loads(open(prior['path'],encoding='utf8').read());verify(prepared['inputs'])
    verify([prepared['program']])
    assert prepared['program']['sha256']=='dc4e2a1feb2245e5a9c567d1bc1877e774a6b70b1058e805f4c6d61aa063ca9c'
    return old,prepared['program'],[bound(check),old['run_manifest'],prior]


def prepare():
    assert not PREP.exists(), 'Never overwrite prepared evidence'
    old,program,proof=prerequisites()
    inputs=proof+[bound(p) for p in [__file__,TESTS/'notes'/(TAG+'.md'),READER,
        TESTS/'support/cryer_start_r1.py',TESTS/'support/cryer_dt_short_r1.py',TESTS/'support/cryer_grad_short_r1.py']]
    jobs=[]
    for label,decimal,steps in STAGES:
        dt=float(decimal);assert dt*steps==DURATION and INTERVAL/dt==steps/4
        source=TESTS/'configs'/('cryer_grad_short_r1_'+label+'_Def.xml')
        template=TESTS/'configs'/('xcryer_grad_short_r1_'+label+'_win64_CPU.bat')
        name=TAG+'_'+label;cfg=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64_CPU.bat')
        assert not any(p.exists() for p in [cfg,bat,TESTS/'outputs'/name,TESTS/'logs'/(name+'.run.json')])
        text=source.read_text(encoding='utf8')
        for key,value in [('DtIni',decimal),('DtFixed',decimal),('TimeMax','0.00048828125'),('TimeOut','0.0001220703125')]:
            text,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],text)
            assert n==1,key
        cfg.write_text(text,encoding='utf8',newline='\n')
        bat.write_text(template.read_text(encoding='utf8').replace('cryer_grad_short_r1_'+label,name),encoding='utf8',newline='\r\n')
        jobs.append(dict(name=name,dt_s=dt,steps=steps,config=bound(cfg),bat=bound(bat)))
        inputs += [bound(source),bound(template),bound(cfg),bound(bat)]
    write_json(PREP,dict(status='prepared_not_started',utc=utc(),jobs=jobs,inputs=inputs,program=program,
        duration_s=DURATION,interval_s=INTERVAL,prior_half_passed=False,
        prior_half_max_pressure_rms_pa=old['max_pressure_rms_pa'],expected_frames=5,
        planned_total_steps=3072,physical_accepted=False,peak_window_admitted=False,
        time_policy='Binary-exact new times only; no comparison/interpolation against the old decimal sample grid.'))
    print('PREPARED ONLY:',PREP,flush=True)


def run():
    prepared=json.loads(PREP.read_text(encoding='utf8'));verify(prepared['inputs']);verify([prepared['program']]);prerequisites()
    run_path=TESTS/'logs'/(TAG+'.run.json');check=TESTS/'logs'/(TAG+'.check.json')
    csvs={k:TESTS/'figures'/(TAG+'_'+k+'.csv') for k in ['summary','half']}
    assert not any(p.exists() for p in [run_path,check,*csvs.values()]), 'Never restart a retained sequence'
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),prepared_inputs=bound(PREP),
        program=prepared['program'],runs=[],prior_half_passed=False,existing_gpu_processes=inventory(),
        physical_accepted=False,peak_window_admitted=False)
    def save():
        tmp=run_path.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,run_path)
    save();child=None;current=None;history=[];pairs=[];frames={};initial=None;center=None
    try:
        for job in prepared['jobs']:
            concurrent=inventory();verify(prepared['inputs']);verify([prepared['program']])
            name=job['name'];dt=job['dt_s'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            per_run=TESTS/'logs'/(name+'.run.json')
            assert not any(p.exists() for p in [folder,log,per_run])
            current=dict(name=name,dt_s=dt,passed=False,started_utc=utc(),config=job['config'],bat=job['bat'],
                prepared_inputs=bound(PREP),concurrent_gpu_processes=concurrent)
            state['runs'].append(current);save();write_json(per_run,current);started=time.perf_counter()
            with log.open('xb') as stream:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,
                    stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                current['owned_wrapper_pid']=child.pid;save();report=started
                while child.poll() is None:
                    time.sleep(1)
                    if time.perf_counter()-report>20:
                        print('RUNNING',name,'wall_s',round(time.perf_counter()-started),'no automatic time-budget kill',flush=True);report=time.perf_counter()
            current.update(exit_code=child.returncode,owned_exited=True,wall_seconds=time.perf_counter()-started)
            assert child.returncode==0,(name,child.returncode)
            text=(folder/'Run.out').read_text(errors='replace')
            assert 'Finished execution (code=0)' in text and 'SoilStressRateGradCorr="KernelGradient"' in text
            current['steps']=int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])
            assert current['steps']==job['steps'] and len(list((folder/'data').glob('Part_*.bi4')))==5
            loop=re.search(r'Simulation Runtime\.*:\s*([\d.]+)\s*sec',text)
            if loop:current['observed_simulation_runtime_s']=float(loop[1])
            frames[name]=[]
            for part in range(5):
                a=native(folder,part)
                if initial is None:
                    initial=a;center=np.linalg.norm(initial[['x','y','z']],axis=1)<=.0025+1e-12;assert center.any()
                    state['center_material_ids']=list(map(int,initial.id.to_numpy()[center]))
                if part==0:assert np.array_equal(a[['id','x','y','z','rho','mass','h']],initial[['id','x','y','z','rho','mass','h']])
                assert float(a.time_s.iloc[0])==part*INTERVAL, 'Actual binary sample time differs; no interpolation'
                assert int(a.saved_step.iloc[0])==(int(part*INTERVAL/dt)-1 if part else 0), 'Zero-based native step differs'
                row,issues=inspect(a,initial,part,dt,center);row['run']=name;history.append(row)
                assert not issues,(name,part,issues)
                frames[name].append(a);current.update(checked_frames=part+1,actual_last_saved_time_s=row['time_s']);save()
            verify(prepared['inputs']);verify([prepared['program']])
            current.update(passed=True,finished_utc=utc(),outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)])
            write_json(per_run,current);save();print('PASS',name,current['wall_seconds'],flush=True)
        failures=[]
        for part,(c,h) in enumerate(zip(frames[prepared['jobs'][0]['name']],frames[prepared['jobs'][1]['name']])):
            assert float(c.time_s.iloc[0])==float(h.time_s.iloc[0])==part*INTERVAL
            row=dict(part=part,time_s=float(c.time_s.iloc[0]),**difference(c,h))
            row['screen_passed']=row['pressure_rms_pa']<=5 and row['material_displacement_max_mm']<=.005
            pairs.append(row)
            if not row['screen_passed']:failures.append(row)
        state['half_failures']=failures
        assert not failures,('Original5Pa/.005mm independent half screen failed',failures)
        state['status']='fine_pair_passed_pending_review'
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='fine_pair_rejected_or_interrupted',error=repr(error),traceback=traceback.format_exc())
        if current is not None and not current.get('passed'):
            current.update(owned_exited=child is None or child.poll() is not None,error=repr(error),
                exit_code=None if child is None else child.poll(),outputs=[bound(p) for p in (TESTS/'outputs'/current['name']).rglob('*') if p.is_file()])
            write_json(TESTS/'logs'/(current['name']+'.run.json'),current)
    finally:
        artifacts=[]
        for path,rows in [(csvs['summary'],history),(csvs['half'],pairs)]:
            if rows:pd.DataFrame(rows).to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
        state.update(finished_utc=utc(),artifacts=artifacts);save()
        write_json(check,dict(passed=state['status']=='fine_pair_passed_pending_review',status=state['status'],run_manifest=bound(run_path),
            paired_samples=len(pairs),error=state.get('error'),max_pressure_rms_pa=max((r['pressure_rms_pa'] for r in pairs),default=None),
            max_material_displacement_mm=max((r['material_displacement_max_mm'] for r in pairs),default=None),
            physical_accepted=False,peak_window_admitted=False,
            limits=['Only1024/2048steps and5actual binary-exact samples per run; no peak or physical acceptance.',
                'Prior decimal coarse/half failures remain failed; no shifted-time or interpolated old comparison.',
                'Original5Pa/.005mm gate and native safety are unchanged; same grad1/raw force/eta.02 physics.',
                'Concurrent GPU work is not stopped and timings are not isolated; wall budget never triggers a kill.',
                'No new GPU run, notifier, D implementation or automatic longer-window admission.']))
    print(json.dumps(dict(status=state['status'],samples=len(pairs),error=state.get('error')),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:run()
    else:prepare()
