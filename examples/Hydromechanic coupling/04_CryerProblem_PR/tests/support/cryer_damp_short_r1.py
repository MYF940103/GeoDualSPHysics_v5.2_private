"""Prepare only by default; --run executes one new, bounded weaker-damping GPU pair."""
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
from cryer_grad_short_r1 import difference
from cryer_gpu_base_r1 import verify
from cryer_grad_fine_r1 import STAGES,DURATION,INTERVAL
from cryer_gpu_continue_r1 import no_active_gpu
from cryer_gpu_grad_fine_r1 import metadata

TAG='cryer_damp_short_r1'
PREP=TESTS/'logs'/(TAG+'.inputs.json')
OLD='<parameter key="SoilDampingCoef" value="0.02"'
NEW='<parameter key="SoilDampingCoef" value="0.00004"'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path,data):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(data,stream,indent=2,allow_nan=False)


def prerequisites():
    peak=TESTS/'logs/cryer_grad_peak_review_r1.check.json';review=read(peak)
    assert review['evidence_consistency_passed'] and review['original_single_run_safety_passed']
    verify([dict(path=str(peak.parent/e['path']),sha256=e['sha256']) for e in review['source_links']])
    check=TESTS/'logs/cryer_gpu_grad_fine_r1.check.json';gate=read(check)
    assert gate['passed'] and gate['cross_samples']==10 and gate['paired_samples']==5
    verify([gate['run_manifest']]);control=read(gate['run_manifest']['path'])
    verify([control['prepared_inputs']]);prepared=read(control['prepared_inputs']['path'])
    verify([prepared['program'],prepared['build']]);verify(read(prepared['build']['path'])['inputs'])
    proof=[bound(peak),bound(check),gate['run_manifest'],control['prepared_inputs']]
    for r in control['runs']:
        assert r['passed'] and r['owned_exited'] and r['exit_code']==0 and r['checked_frames']==5
        verify([r['sealed_completion']]);done=read(r['sealed_completion']['path'])
        assert done['solver_finished'] and done['exit_code']==0
        verify(done['outputs']);proof += [r['sealed_completion']]+done['outputs']
    assert len(control['runs'])==2
    return prepared,proof


def reserved():
    paths=[TESTS/'logs'/(TAG+s) for s in ['.run.json','.check.json']]
    paths += [TESTS/'figures'/(TAG+'_'+s+'.csv') for s in ['summary','effects','half']]
    for label,_,_ in STAGES:
        name=TAG+'_'+label;paths += [TESTS/'outputs'/name]
        paths += [TESTS/'logs'/(name+s) for s in ['.log','.run.json','.completion.json']]
    assert not any(p.exists() for p in paths),'Retained stage exists; never overwrite or restart it'


def prepare():
    assert not PREP.exists(),'Never overwrite prepared inputs'
    reserved();control,proof=prerequisites();jobs=[]
    inputs=proof+[bound(p) for p in [__file__,TESTS/'notes'/(TAG+'.md'),READER,
        TESTS/'support/cryer_start_r1.py',TESTS/'support/cryer_dt_short_r1.py',
        TESTS/'support/cryer_grad_short_r1.py',TESTS/'support/cryer_grad_fine_r1.py',
        TESTS/'support/cryer_gpu_base_r1.py',TESTS/'support/cryer_gpu_continue_r1.py',
        TESTS/'support/cryer_gpu_grad_fine_r1.py']]
    for label,decimal,steps in STAGES:
        reference='cryer_gpu_grad_fine_r1_'+label;name=TAG+'_'+label
        source=TESTS/'configs'/(reference+'_Def.xml');template=TESTS/'configs'/('x'+reference+'_win64_GPU.bat')
        cfg=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64_GPU.bat')
        text=source.read_text(encoding='utf8');assert text.count(OLD)==1
        assert cfg.read_text(encoding='utf8')==text.replace(OLD,NEW),'Only damping value may differ'
        assert bat.read_text(encoding='utf8')==template.read_text(encoding='utf8').replace(reference,name)
        jobs.append(dict(name=name,reference=reference,dt_s=float(decimal),steps=steps,config=bound(cfg),bat=bound(bat)))
        inputs += [bound(p) for p in [source,template,cfg,bat]]
    seal(PREP,dict(status='prepared_not_started',utc=utc(),jobs=jobs,inputs=inputs,
        program=control['program'],build=control['build'],duration_s=DURATION,interval_s=INTERVAL,
        expected_frames=5,changed_parameter='SoilDampingCoef 0.02 to 0.00004 only',
        physical_accepted=False,peak_window_admitted=False))
    print('PREPARED ONLY',PREP,flush=True)


def measure(job,data):
    initial=native(TESTS/'outputs'/job['reference'],0)
    center=np.linalg.norm(initial[['x','y','z']],axis=1)<=.0025+1e-12;assert center.sum()==18
    frames=[]
    for part in range(5):
        a=native(TESTS/'outputs'/job['name'],part);b=native(TESTS/'outputs'/job['reference'],part)
        if part==0:assert np.array_equal(a[['id','x','y','z','rho','mass','h']],initial[['id','x','y','z','rho','mass','h']])
        assert np.array_equal(a[['mass','h']],initial[['mass','h']])
        assert np.linalg.norm(a[['x','y','z']],axis=1).max()<=.0525
        assert float(a.time_s.iloc[0])==float(b.time_s.iloc[0])==part*INTERVAL
        assert int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0])==(int(part*INTERVAL/job['dt_s'])-1 if part else 0)
        row,issues=inspect(a,initial,part,job['dt_s'],center);row['run']=job['name'];data['summary'].append(row)
        assert not issues,(job['name'],part,issues)
        effect=dict(run=job['name'],reference=job['reference'],part=part,time_s=part*INTERVAL,
            comparison='same_dt_weaker_damping_change_not_half_or_theory_error',**difference(a,b))
        effect['speed_max_abs_change_m_s']=float(abs(np.linalg.norm(a[['vx','vy','vz']],axis=1)-np.linalg.norm(b[['vx','vy','vz']],axis=1)).max())
        data['effects'].append(effect);frames.append(a)
    return frames


def run():
    prepared=read(PREP);verify(prepared['inputs']);verify([prepared['program']]);prerequisites();reserved()
    runpath=TESTS/'logs'/(TAG+'.run.json');check=TESTS/'logs'/(TAG+'.check.json')
    data={k:[] for k in ['summary','effects','half']};state=dict(status='running',started_utc=utc(),
        owned_sequence_pid=os.getpid(),prepared_inputs=bound(PREP),program=prepared['program'],runs=[],
        physical_accepted=False,peak_window_admitted=False)
    def save():
        temp=runpath.with_suffix('.tmp');write_json(temp,state);os.replace(temp,runpath)
    save();child=None;current=None;frames=[]
    try:
        for job in prepared['jobs']:
            concurrent=no_active_gpu();verify(prepared['inputs']);verify([prepared['program']])
            name=job['name'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            perrun=TESTS/'logs'/(name+'.run.json');completion=TESTS/'logs'/(name+'.completion.json')
            assert not any(p.exists() for p in [folder,log,perrun,completion])
            current=dict(name=name,passed=False,started_utc=utc(),job=job,concurrent_cpu_processes=concurrent,
                prepared_inputs=bound(PREP),program=prepared['program']);state['runs'].append(current);save();write_json(perrun,current)
            started=time.perf_counter()
            with log.open('xb') as stream:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,
                    stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                current['owned_wrapper_pid']=child.pid;save();report=started
                while child.poll() is None:
                    time.sleep(1)
                    if time.perf_counter()-report>20:
                        print('RUNNING',name,'wall_s',round(time.perf_counter()-started),flush=True);report=time.perf_counter()
            current.update(exit_code=child.returncode,owned_exited=True,wall_seconds=time.perf_counter()-started)
            text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
            finished=child.returncode==0 and 'Finished execution (code=0)' in text
            outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)]
            seal(completion,dict(solver_finished=finished,exit_code=child.returncode,owned_exited=True,
                utc=utc(),job=job,prepared_inputs=bound(PREP),program=prepared['program'],outputs=outputs))
            current.update(sealed_completion=bound(completion),outputs=outputs);save();write_json(perrun,current)
            assert finished,(name,child.returncode)
            current.update(**metadata(folder,job['steps']))
            coefficient=re.search(r'^\s*SoilDampingCoef=([^\r\n]+)',text,re.M)
            assert 'BuiFukagawa2013' in text and coefficient and float(coefficient[1])==.00004,'Damping runtime differs'
            frames.append(measure(job,data))
            verify(prepared['inputs']);verify([prepared['program']])
            current.update(passed=True,checked_frames=5,actual_last_saved_time_s=DURATION,finished_utc=utc())
            write_json(perrun,current);save();print('PASS',name,flush=True)
        for part,(c,h) in enumerate(zip(*frames)):
            assert float(c.time_s.iloc[0])==float(h.time_s.iloc[0])==part*INTERVAL
            row=dict(part=part,time_s=part*INTERVAL,**difference(c,h))
            row['screen_passed']=row['pressure_rms_pa']<=5 and row['material_displacement_max_mm']<=.005
            data['half'].append(row)
        assert len(data['half'])==5 and all(r['screen_passed'] for r in data['half']),'Original5Pa/.005mm independent half screen failed'
        state['status']='damping_short_pair_passed_pending_review'
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True);state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='damping_short_pair_rejected_or_interrupted',error=repr(error),traceback=traceback.format_exc())
        if current is not None and not current['passed']:
            current.update(error=repr(error),exit_code=None if child is None else child.poll(),
                owned_exited=child is None or child.poll() is not None,outputs=[bound(p) for p in (TESTS/'outputs'/current['name']).rglob('*') if p.is_file()])
            write_json(TESTS/'logs'/(current['name']+'.run.json'),current)
    finally:
        artifacts=[]
        for key,rows in data.items():
            if rows:
                path=TESTS/'figures'/(TAG+'_'+key+'.csv');pd.DataFrame(rows).to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
        state.update(finished_utc=utc(),artifacts=artifacts);save()
        seal(check,dict(passed=state['status']=='damping_short_pair_passed_pending_review',status=state['status'],
            run_manifest=bound(runpath),paired_samples=len(data['half']),effect_samples=len(data['effects']),error=state.get('error'),
            max_half_pressure_rms_pa=max((r['pressure_rms_pa'] for r in data['half']),default=None),
            max_half_material_displacement_mm=max((r['material_displacement_max_mm'] for r in data['half']),default=None),
            physical_accepted=False,peak_window_admitted=False,
            limits=['Only1024/2048steps and5binary samples per run; no peak/full/physical acceptance.',
                'Different damping controls measure physical-option effects, not5Pa cross gates,0ULP or theory errors.',
                'Original single-run safety and all5 independent5Pa/.005mm half limits remain unchanged.',
                'Completed solvers are sealed before offline analysis; repair analysis only, never rerun retained outputs.',
                'No production/formal change,notifier or automatic longer run.']))
    print(json.dumps(dict(status=state['status'],half_samples=len(data['half']),error=state.get('error')),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:run()
    else:prepare()
