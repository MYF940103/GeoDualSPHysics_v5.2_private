"""Prepare only by default; --run admits one Debug/memcheck then Release GPU start."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE, TESTS, REPO, READER, bound, native, utc, write_json
from cryer_dt_short_r1 import inspect

TAG='cryer_gpu_base_r1'
DT=2.5e-6
GPU_HASHES={'dbg':'57ef82c47d3afd34e2723bdcd1024b6d55137a7bdbd696804b92ff1084053feb',
    'c':'260c3d4c845db380f93257f96fba77034b1c6e2047d6780702b2483b974c933c'}
LIAN=CASE.parent/'05_LianFlexibleStrip2D_PR/tests'
PREP=TESTS/'logs'/(TAG+'.inputs.json')


def verify(records):
    for e in records:
        assert bound(e['path'])['sha256'].lower()==e['sha256'].lower(), e['path']


def prerequisites():
    check=TESTS/'logs/cryer_dt_short_r1.check.json'
    old=json.loads(check.read_text(encoding='utf8'))
    verify([old['run_manifest']])
    run=json.loads(Path(old['run_manifest']['path']).read_text(encoding='utf8'))
    coarse=next(r for r in run['runs'] if r['name']=='cryer_dt_short_r1_c')
    assert coarse['passed'] and coarse['owned_exited'] and coarse['exit_code']==0
    assert coarse['checked_frames']==5 and coarse['steps']==200
    verify(run['inputs']+coarse['outputs'])
    # Adopting a passed individual coarse run does not override its failed half pair.
    assert old['passed'] is False and old['paired_samples']==5
    builds=[]
    for label,config,exe in [('dbg','Debug','DualSPHysics5.2_win64_debug.exe'),
                            ('c','Release','DualSPHysics5.2_GEO_win64.exe')]:
        receipt=LIAN/'logs'/('lian_hg_np_'+config+'_bounded_r1.build.json')
        built=json.loads(receipt.read_text(encoding='utf-8-sig'))
        assert built['built'] and built['configuration']==config
        verify(built['inputs'])
        program=REPO/'bin/windows'/exe
        assert bound(program)['sha256']==GPU_HASHES[label]
        assert bound(LIAN/'outputs/lian_hg_np_build_r1'/exe)['sha256']==GPU_HASHES[label]
        builds.append(dict(label=label,program=bound(program),build=bound(receipt),
            verified_build_inputs=len(built['inputs'])))
    sanitizer=shutil.which('compute-sanitizer.exe')
    if not sanitizer:
        sanitizer=r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe'
    assert Path(sanitizer).is_file(), 'Blocked: compute-sanitizer is unavailable; Debug gate is not skipped'
    return old, coarse, builds, Path(sanitizer)


def prepare():
    assert not PREP.exists(), 'Prepared inputs already exist; use --run, never overwrite'
    old,coarse,builds,sanitizer=prerequisites()
    xml=TESTS/'configs/cryer_dt_short_r1_c_Def.xml'
    template=TESTS/'configs/xcryer_start_r1_win64_CPU.bat'
    jobs=[]
    for build in builds:
        name=TAG+'_'+build['label']
        cfg=TESTS/'configs'/(name+'_Def.xml')
        bat=TESTS/'configs'/('x'+name+'_win64_GPU.bat')
        assert not any(p.exists() for p in [cfg,bat,TESTS/'outputs'/name,
            TESTS/'logs'/(name+'.log'),TESTS/'logs'/(name+'.run.json')])
        cfg.write_bytes(xml.read_bytes())
        text=template.read_text(encoding='utf8').replace('cryer_start_r1',name)
        text=text.replace('dualsphysicscpu','dualsphysicsgpu')
        text=text.replace('DualSPHysics5.2CPU_win64_debug.exe',Path(build['program']['path']).name)
        text=text.replace('-cpu -ompthreads:8 -stable','-gpu -stable')
        if build['label']=='dbg':
            text=text.replace('%dualsphysicsgpu% -gpu',
                '"'+str(sanitizer)+'" --tool memcheck --error-exitcode 86 --leak-check full '
                '--log-file "%dirout%\\memcheck.log" %dualsphysicsgpu% -gpu')
        bat.write_text(text,encoding='utf8',newline='\r\n')
        jobs.append(dict(name=name,label=build['label'],config=bound(cfg),bat=bound(bat),**{
            k:v for k,v in build.items() if k!='label'}))
    paths=[__file__,TESTS/'notes'/(TAG+'.md'),xml,template,READER,
        TESTS/'support/cryer_start_r1.py',TESTS/'support/cryer_dt_short_r1.py',
        TESTS/'logs/cryer_dt_short_r1.check.json',TESTS/'logs/cryer_dt_short_r1.run.json',
        sanitizer]+[REPO/'bin/windows'/n for n in ['GenCase_win64.exe','ChronoEngine.dll',
            'dsphchrono.dll','vcomp140.dll','DsphConfig.xml']]
    inputs=[bound(p) for p in paths]+[job[k] for job in jobs for k in ['config','bat','program','build']]
    write_json(PREP,dict(status='prepared_not_started',utc=utc(),inputs=inputs,jobs=jobs,
        sanitizer=bound(sanitizer),cpu_reference=coarse['name'],cpu_pair_passed=old['passed'],
        cpu_pair_max_pressure_rms_pa=old['max_pressure_rms_pa'],duration_s=.0005,dt_s=DT,
        expected_steps=200,expected_frames=5,physical_accepted=False,long_window_admitted=False))
    print('PREPARED ONLY:',PREP,flush=True)


def no_active_cryer():
    command="Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*' -and $_.CommandLine -match 'Cryer|cryer_'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    active=subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True,
        timeout=20,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    assert not active, 'Another Cryer solver exists: '+active


def run():
    prepared=json.loads(PREP.read_text(encoding='utf8'));verify(prepared['inputs'])
    old,coarse,_,_=prerequisites()
    state_path=TESTS/'logs'/(TAG+'.run.json');check=TESTS/'logs'/(TAG+'.check.json')
    summary=TESTS/'figures'/(TAG+'_summary.csv');pairs_path=TESTS/'figures'/(TAG+'_cross.csv')
    fields_path=TESTS/'figures'/(TAG+'_native_differences.csv')
    assert not any(p.exists() for p in [state_path,check,summary,pairs_path,fields_path]), 'Never restart a retained sequence'
    no_active_cryer()
    state=dict(status='running',utc=utc(),owned_sequence_pid=os.getpid(),prepared_inputs=bound(PREP),
        runs=[],cpu_coarse_adopted=True,cpu_half_pair_passed=False,
        prior_half_max_pressure_rms_pa=old['max_pressure_rms_pa'],physical_accepted=False,
        half_step_accepted=False,long_window_admitted=False)
    def save():
        temp=state_path.with_suffix('.tmp');write_json(temp,state);os.replace(temp,state_path)
    save();history=[];pairs=[];field_differences=[];child=None;current=None
    try:
        cpu_folder=TESTS/'outputs'/coarse['name'];initial=native(cpu_folder,0)
        center=np.linalg.norm(initial[['x','y','z']],axis=1)<=.0025+1e-12
        assert center.any();state['center_material_ids']=list(map(int,initial.id.to_numpy()[center]))
        for job in prepared['jobs']:
            no_active_cryer();verify(prepared['inputs'])
            folder=TESTS/'outputs'/job['name'];log=TESTS/'logs'/(job['name']+'.log')
            per_run=TESTS/'logs'/(job['name']+'.run.json')
            assert not any(p.exists() for p in [folder,log,per_run])
            current=dict(name=job['name'],passed=False,started_utc=utc(),program=job['program'],
                config=job['config'],bat=job['bat'],prepared_inputs=bound(PREP))
            state['runs'].append(current);save();write_json(per_run,current)
            started=time.perf_counter()
            with log.open('xb') as stream:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,
                    stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                current['owned_wrapper_pid']=child.pid;save();report=started
                while child.poll() is None:
                    time.sleep(1)
                    if time.perf_counter()-report>20:
                        print('RUNNING',job['name'],'wall_s',round(time.perf_counter()-started),flush=True);report=time.perf_counter()
            current.update(exit_code=child.returncode,owned_exited=True,wall_seconds=time.perf_counter()-started)
            assert child.returncode==0,(job['name'],child.returncode)
            text=(folder/'Run.out').read_text(errors='replace')
            assert 'Finished execution (code=0)' in text and 'DBC' in text
            hardware=re.search(r'Device default:\s*([^\r\n]+)',text)
            capability=re.search(r'Compute capability:\s*([^\r\n]+)',text)
            assert hardware and capability, 'Actual GPU hardware is missing from Run.out'
            current.update(actual_gpu=hardware[1],compute_capability=capability[1],
                steps=int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1]))
            assert current['steps']==200
            loop=re.search(r'Simulation Runtime\.*:\s*([\d.]+)\s*sec',text)
            if loop:current['observed_simulation_runtime_s']=float(loop[1])
            assert len(list((folder/'data').glob('Part_*.bi4')))==5
            if job['label']=='dbg':
                memcheck=(folder/'memcheck.log').read_text(errors='replace')
                assert 'ERROR SUMMARY: 0 errors' in memcheck and 'All heap blocks were freed' in memcheck, 'Debug memcheck did not pass'
                current['memcheck_zero_errors_and_leaks']=True
            for part in range(5):
                a=native(folder,part)
                if part==0:
                    assert np.array_equal(a[['id','x','y','z','mass','rho','h']],initial[['id','x','y','z','mass','rho','h']]), 'CPU/GPU initial geometry or material differs'
                assert np.array_equal(a[['mass','h']],initial[['mass','h']]), 'Mass/kernel radius changed'
                assert np.linalg.norm(a[['x','y','z']],axis=1).max()<=.0525, 'Sphere geometry exceeds R+dp startup bound'
                row,issues=inspect(a,initial,part,DT,center);row['run']=job['name'];history.append(row)
                assert not issues,(job['name'],part,issues)
                current.update(checked_frames=part+1,actual_last_saved_time_s=row['time_s']);save()
                if job['label']=='c':
                    c=native(cpu_folder,part)
                    delta=abs(float(c.time_s.iloc[0]-a.time_s.iloc[0]));assert delta<1e-12, 'Actual clocks differ; no interpolation'
                    assert np.array_equal(a.id,c.id) and list(a.columns)==list(c.columns)
                    assert np.array_equal(a.fstype.isin([2,3]),c.fstype.isin([2,3])), 'Same-dt drained masks differ'
                    p=float(np.sqrt(np.mean((a.pressure-c.pressure)**2)))
                    d=1000*float(np.linalg.norm(a[['x','y','z']].to_numpy()-c[['x','y','z']].to_numpy(),axis=1).max())
                    pairs.append(dict(part=part,gpu_time_s=float(a.time_s.iloc[0]),cpu_time_s=float(c.time_s.iloc[0]),
                        actual_time_difference_s=delta,pressure_rms_pa=p,material_displacement_max_mm=d,
                        center_pressure_difference_pa=float((a.pressure-c.pressure).to_numpy()[center].mean()),
                        screen_passed=bool(p<=5 and d<=.005)))
                    for column in a.columns:
                        difference=a[column].to_numpy(dtype=float)-c[column].to_numpy(dtype=float)
                        field_differences.append(dict(part=part,field=column,rms=float(np.sqrt(np.mean(difference**2))),
                            maximum_absolute=float(abs(difference).max()),different_count=int(np.count_nonzero(difference))))
            assert abs(current['actual_last_saved_time_s']-.0005)<1e-12
            if job['label']=='c':assert all(p['screen_passed'] for p in pairs), 'Original5Pa/.005mm CPU/GPU comparison failed'
            verify(prepared['inputs']);verify(coarse['outputs'])
            current.update(passed=True,finished_utc=utc(),outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)])
            write_json(per_run,current);save();print('PASS',job['name'],current['wall_seconds'],flush=True)
        assert len(pairs)==5
        state['status']='gpu_startup_cross_passed_pending_review'
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='gpu_startup_rejected_or_interrupted',error=repr(error),traceback=traceback.format_exc())
        if current is not None:
            folder=TESTS/'outputs'/current['name']
            current.update(passed=False,owned_exited=child is None or child.poll() is not None,
                exit_code=None if child is None else child.poll(),error=repr(error),
                outputs=[bound(p) for p in folder.rglob('*') if p.is_file()])
            write_json(TESTS/'logs'/(current['name']+'.run.json'),current)
    finally:
        artifacts=[]
        for path,rows in [(summary,history),(pairs_path,pairs),(fields_path,field_differences)]:
            if rows:pd.DataFrame(rows).to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
        state.update(finished_utc=utc(),artifacts=artifacts);save()
        write_json(check,dict(passed=state['status']=='gpu_startup_cross_passed_pending_review',status=state['status'],
            run_manifest=bound(state_path),paired_samples=len(pairs),error=state.get('error'),
            max_pressure_rms_pa=max((p['pressure_rms_pa'] for p in pairs),default=None),
            max_material_displacement_mm=max((p['material_displacement_max_mm'] for p in pairs),default=None),
            physical_accepted=False,half_step_accepted=False,long_window_admitted=False,
            limits=['Only200steps/5saved frames per GPU run; not a peak/half-step/theory acceptance.',
                'The retained CPU independent half pair failed5Pa; adopting its passed coarse does not reverse that result.',
                'Debug and Release are not0ULP controls; the comparison is GPU Release versus same-dt CPU Release.',
                'Original geometry/load/drainage/damping/operators are unchanged; no load-only correction.',
                'Observed startup loop cost is not a controlled benchmark or a long-window prediction.',
                'No GPU half, notifier or automatic longer run is admitted.']))
    print(json.dumps(dict(status=state['status'],samples=len(pairs),error=state.get('error')),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if args.run:run()
    else:prepare()
