"""After both prior gates pass, prepare or --run only the binary-exact GPU fine pair."""
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
from cryer_grad_fine_r1 import STAGES,DURATION,INTERVAL
from cryer_gpu_base_r1 import prerequisites as build_proof,verify,GPU_HASHES
from cryer_gpu_continue_r1 import no_active_gpu

TAG='cryer_gpu_grad_fine_r1'
PREP=TESTS/'logs'/(TAG+'.inputs.json')


def prerequisites():
    proofs=[];controls={}
    for tag in ['cryer_grad_fine_r1','cryer_gpu_continue_r1']:
        path=TESTS/'logs'/(tag+'.check.json')
        check=json.loads(path.read_text(encoding='utf8'))
        assert check['passed'] and check['paired_samples']==5,(tag,'Prior gate has not passed')
        verify([check['run_manifest']])
        run=json.loads(Path(check['run_manifest']['path']).read_text(encoding='utf8'))
        prepared=run['prepared_inputs'];verify([prepared])
        inputs=json.loads(Path(prepared['path']).read_text(encoding='utf8'))
        verify(inputs['inputs']);proofs += [bound(path),check['run_manifest'],prepared]+inputs['inputs']
        if tag=='cryer_grad_fine_r1':
            verify([inputs['program']]);proofs.append(inputs['program'])
            assert len(run['runs'])==2 and run['status']=='fine_pair_passed_pending_review'
            for label,_,steps in STAGES:
                r=next(r for r in run['runs'] if r['name']==tag+'_'+label)
                assert r['passed'] and r['owned_exited'] and r['exit_code']==0
                assert r['steps']==steps and r['checked_frames']==5
                verify(r['outputs']);proofs+=r['outputs'];controls[label]=r['name']
        else:
            assert run['status']=='release_cross_passed_pending_review' and run['owned_exited'] and run['exit_code']==0
            assert run['steps']==200 and run['sealed_completion']
            verify([run['sealed_completion']]);proofs.append(run['sealed_completion'])
            complete=json.loads(Path(run['sealed_completion']['path']).read_text(encoding='utf8'))
            assert complete['solver_finished'] and complete['exit_code']==0
            verify(complete['outputs']);proofs+=complete['outputs']
    _,_,builds,_=build_proof()
    gpu=next(b for b in builds if b['label']=='c')
    assert gpu['program']['sha256']==GPU_HASHES['c']
    return controls,gpu,proofs


def prepare():
    assert not PREP.exists(), 'Never overwrite a prepared pair'
    controls,gpu,proofs=prerequisites()  # No inputs are sealed before both completed gates pass.
    inputs=proofs+[bound(p) for p in [__file__,TESTS/'notes'/(TAG+'.md'),READER,
        TESTS/'support/cryer_start_r1.py',TESTS/'support/cryer_dt_short_r1.py',
        TESTS/'support/cryer_grad_short_r1.py',TESTS/'support/cryer_grad_fine_r1.py',
        TESTS/'support/cryer_gpu_base_r1.py',TESTS/'support/cryer_gpu_continue_r1.py']]
    jobs=[]
    for label,decimal,steps in STAGES:
        name=TAG+'_'+label;cfg=TESTS/'configs'/(name+'_Def.xml')
        bat=TESTS/'configs'/('x'+name+'_win64_GPU.bat')
        source=TESTS/'configs'/(controls[label]+'_Def.xml')
        template=TESTS/'configs'/('x'+controls[label]+'_win64_CPU.bat')
        assert cfg.read_text(encoding='utf8')==source.read_text(encoding='utf8'), 'GPU XML must equal CPU physics'
        expected=template.read_text(encoding='utf8').replace(controls[label],name).replace('dualsphysicscpu','dualsphysicsgpu')
        expected=expected.replace('DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe').replace('-cpu -ompthreads:8 -stable','-gpu -stable')
        assert bat.read_text(encoding='utf8')==expected, 'Unexpected BAT change'
        assert not any(p.exists() for p in [TESTS/'outputs'/name,TESTS/'logs'/(name+'.log'),
            TESTS/'logs'/(name+'.run.json'),TESTS/'logs'/(name+'.completion.json')])
        jobs.append(dict(name=name,label=label,dt_s=float(decimal),steps=steps,reference=controls[label],
            config=bound(cfg),bat=bound(bat)))
        inputs += [bound(source),bound(template),bound(cfg),bound(bat)]
    write_json(PREP,dict(status='prepared_not_started',utc=utc(),jobs=jobs,inputs=inputs+[gpu['program'],gpu['build']],
        program=gpu['program'],build=gpu['build'],duration_s=DURATION,interval_s=INTERVAL,
        cpu_fine_half_passed=True,gpu_base_cross_passed=True,expected_frames=5,
        physical_accepted=False,peak_window_admitted=False,long_window_admitted=False))
    print('PREPARED ONLY:',PREP,flush=True)


def metadata(folder,steps):
    text=(folder/'Run.out').read_text(errors='replace')
    assert 'Finished execution (code=0)' in text and 'SoilStressRateGradCorr="KernelGradient"' in text
    assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==steps
    assert len(list((folder/'data').glob('Part_*.bi4')))==5
    hardware=re.search(r'Device default:\s*([^\r\n]+)',text)
    capability=re.search(r'Compute capability:\s*([^\r\n]+)',text)
    assert hardware and capability, 'Actual GPU identity is missing'
    runtime=re.search(r'Simulation Runtime\.*:\s*([\d.]+)\s*sec',text)
    return dict(steps=steps,actual_gpu=hardware[1],compute_capability=capability[1],
        observed_simulation_runtime_s=float(runtime[1]) if runtime else None)


def measure(job,data):
    folder=TESTS/'outputs'/job['name'];cpu=TESTS/'outputs'/job['reference']
    initial=native(cpu,0);center=np.linalg.norm(initial[['x','y','z']],axis=1)<=.0025+1e-12
    assert center.any();frames=[];local=[]
    for part in range(5):
        a=native(folder,part);b=native(cpu,part)
        if part==0:assert np.array_equal(a[['id','x','y','z','rho','mass','h']],initial[['id','x','y','z','rho','mass','h']])
        assert np.array_equal(a[['mass','h']],initial[['mass','h']])
        assert np.linalg.norm(a[['x','y','z']],axis=1).max()<=.0525
        assert float(a.time_s.iloc[0])==float(b.time_s.iloc[0])==part*INTERVAL, 'Actual binary sample time differs'
        assert int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0])==(int(part*INTERVAL/job['dt_s'])-1 if part else 0)
        row,issues=inspect(a,initial,part,job['dt_s'],center);row['run']=job['name'];data['summary'].append(row)
        assert not issues,(job['name'],part,issues)
        assert np.array_equal(a.fstype.isin([2,3]),b.fstype.isin([2,3])), 'Same-dt drained masks differ'
        cross=dict(run=job['name'],reference=job['reference'],part=part,time_s=part*INTERVAL,**difference(a,b))
        cross['screen_passed']=cross['pressure_rms_pa']<=5 and cross['material_displacement_max_mm']<=.005
        data['cross'].append(cross);local.append(cross)
        for column in a.columns:
            delta=a[column].to_numpy(dtype=float)-b[column].to_numpy(dtype=float)
            data['native_differences'].append(dict(run=job['name'],part=part,field=column,
                rms=float(np.sqrt(np.mean(delta**2))),maximum_absolute=float(abs(delta).max()),different_count=int(np.count_nonzero(delta))))
        frames.append(a)
    assert all(r['screen_passed'] for r in local), 'Original5Pa/.005mm same-dt CPU/GPU gate failed'
    return frames


def run():
    prepared=json.loads(PREP.read_text(encoding='utf8'));verify(prepared['inputs']);prerequisites()
    run_path=TESTS/'logs'/(TAG+'.run.json');check=TESTS/'logs'/(TAG+'.check.json')
    data={k:[] for k in ['summary','cross','half','native_differences']}
    csvs={k:TESTS/'figures'/(TAG+'_'+k+'.csv') for k in data}
    assert not any(p.exists() for p in [run_path,check,*csvs.values()]), 'Never restart a retained pair'
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),prepared_inputs=bound(PREP),
        program=prepared['program'],runs=[],concurrent_cpu_processes=no_active_gpu(),
        physical_accepted=False,peak_window_admitted=False,long_window_admitted=False)
    def save():
        temp=run_path.with_suffix('.tmp');write_json(temp,state);os.replace(temp,run_path)
    save();child=None;current=None;frames=[]
    try:
        for job in prepared['jobs']:
            concurrent=no_active_gpu();verify(prepared['inputs'])
            name=job['name'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            per_run=TESTS/'logs'/(name+'.run.json');completion=TESTS/'logs'/(name+'.completion.json')
            assert not any(p.exists() for p in [folder,log,per_run,completion])
            current=dict(name=name,passed=False,started_utc=utc(),prepared_inputs=bound(PREP),
                program=prepared['program'],config=job['config'],bat=job['bat'],concurrent_cpu_processes=concurrent)
            state['runs'].append(current);save();write_json(per_run,current);started=time.perf_counter()
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
            current.update(**metadata(folder,job['steps']));verify(prepared['inputs'])
            outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)]
            write_json(completion,dict(solver_finished=True,exit_code=0,utc=utc(),job=job,prepared_inputs=bound(PREP),
                program=prepared['program'],**metadata(folder,job['steps']),outputs=outputs))
            current['sealed_completion']=bound(completion);current['outputs']=outputs;save();write_json(per_run,current)
            frames.append(measure(job,data))
            current.update(passed=True,checked_frames=5,actual_last_saved_time_s=DURATION,finished_utc=utc())
            write_json(per_run,current);save();print('PASS',name,flush=True)
        for part,(c,h) in enumerate(zip(*frames)):
            assert float(c.time_s.iloc[0])==float(h.time_s.iloc[0])==part*INTERVAL
            row=dict(part=part,time_s=part*INTERVAL,**difference(c,h))
            row['screen_passed']=row['pressure_rms_pa']<=5 and row['material_displacement_max_mm']<=.005
            data['half'].append(row)
        assert len(data['half'])==5 and all(r['screen_passed'] for r in data['half']), 'Original5Pa/.005mm independent GPU half gate failed'
        state['status']='gpu_fine_pair_passed_pending_review'
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='gpu_fine_pair_rejected_or_interrupted',error=repr(error),traceback=traceback.format_exc())
        if current is not None and not current['passed']:
            current.update(error=repr(error),owned_exited=child is None or child.poll() is not None,
                exit_code=None if child is None else child.poll(),outputs=[bound(p) for p in (TESTS/'outputs'/current['name']).rglob('*') if p.is_file()])
            write_json(TESTS/'logs'/(current['name']+'.run.json'),current)
    finally:
        artifacts=[]
        for key,rows in data.items():
            if rows:pd.DataFrame(rows).to_csv(csvs[key],index=False,float_format='%.17g');artifacts.append(bound(csvs[key]))
        state.update(finished_utc=utc(),artifacts=artifacts);save()
        write_json(check,dict(passed=state['status']=='gpu_fine_pair_passed_pending_review',status=state['status'],run_manifest=bound(run_path),
            cross_samples=len(data['cross']),paired_samples=len(data['half']),error=state.get('error'),
            max_cross_pressure_rms_pa=max((r['pressure_rms_pa'] for r in data['cross']),default=None),
            max_cross_material_displacement_mm=max((r['material_displacement_max_mm'] for r in data['cross']),default=None),
            max_half_pressure_rms_pa=max((r['pressure_rms_pa'] for r in data['half']),default=None),
            max_half_material_displacement_mm=max((r['material_displacement_max_mm'] for r in data['half']),default=None),
            physical_accepted=False,peak_window_admitted=False,long_window_admitted=False,
            limits=['Only1024/2048steps and5binary-exact native frames per run; no peak or physical acceptance.',
                'CPU independent fine half and prior GPU same-dt cross must pass before preparation.',
                'Original5Pa/.005mm same-dt cross and independent GPU half gates remain unchanged.',
                'Sealed solver completions are reused for offline repair, never rerun after analysis failure.',
                'Independent CPU work is allowed and never stopped; timings are not an isolated benchmark.',
                'No source/formal changes,0ULP claim,notifier or automatic longer run.']))
    print(json.dumps(dict(status=state['status'],cross=len(data['cross']),half=len(data['half']),error=state.get('error')),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:run()
    else:prepare()
