"""Bounded HG actual-program startup admission; no long or formal solve."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, utc, write_json
from lian_spr_half_review_r1 import metrics
from lian_opt3_review_r1 import verify_bindings

TAG='lian_hg_short_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
BUILD=TESTS/'outputs/lian_hg_np_build_r1'
MEM=Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe')
JOBS=[('off_cpu','cpu',0,'0.00001','.002','.001','lian_spr_mix_r1_on_debug'),
      ('off_gpu','gpu',0,'0.00001','.15','.005','lian_spr_mix_r1_on_smoke'),
      ('on_cpu','cpu',.1,'0.00001','.002','.001',None),
      ('on_debug','gpu_debug',.1,'0.00001','.002','.001',None),
      ('on_c','gpu',.1,'0.00001','.15','.005',None),
      ('on_h','gpu',.1,'0.000005','.15','.005',None)]


def hg_stats(text):
    steps=int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])
    match=re.search(r'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)',text)
    assert match
    counts=list(map(int,match.groups()));assert counts==[2*steps,steps,steps,2*steps]
    m=re.search(r'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)',text)
    calculations,hits=map(int,m.groups());assert calculations+hits==2*steps and hits>0
    m=re.search(r'max\|sum\(m\*H\)\|=([^ ]+) max\|sum\(m\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\s]+)',text)
    net,rounded,tau,spin=map(float,m.groups());assert np.isfinite([net,rounded,tau,spin]).all()
    assert tau<=.2 and spin<.01
    return dict(steps=steps,forcecalls=counts[0],ratecalls=counts[3],ratecalculations=calculations,
        endpoint_rate_reuses=hits,max_net_history_force=net,max_actual_float_net=rounded,max_dt_tau=tau,spinbound=spin)


def prepare():
    assert not BUILD.exists();BUILD.mkdir()
    files=[REPO/'bin/windows'/n for n in ['GenCase_win64.exe','DualSPHysics5.2CPU_win64_debug.exe',
        'DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2_win64_debug.exe','DsphConfig.xml']]
    files+=list((REPO/'bin/windows').glob('*.dll'))
    snapshots=[]
    for p in files:
        target=BUILD/p.name;shutil.copy2(p,target)
        assert bound(p)['sha256']==bound(target)['sha256'];snapshots.append(dict(source=bound(p),retained=bound(target)))
    text=(TESTS/'configs/lian_spr_mix_r1_on_3s_Def.xml').read_text()
    base=(TESTS/'configs/xlian_spr_mix_r1_on_smoke_win64.bat').read_text()
    jobs=[]
    for label,backend,xi,dt,duration,cadence,reference in JOBS:
        name=TAG+'_'+label;config=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64.bat')
        assert not config.exists() and not bat.exists() and not (TESTS/'outputs'/name).exists()
        xml=text
        for key,value in [('SoilHourglassXi',str(xi)),('DtIni',dt),('DtFixed',dt),('TimeMax',duration),('TimeOut',cadence)]:
            xml,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],xml);assert n==1
        xml=xml.replace('Disabled to isolate retained u-pw path','Bounded HG short candidate; not formal acceptance')
        config.write_text(xml,encoding='utf8')
        batch=base.replace('lian_spr_mix_r1_on_smoke',name).replace('set dirbin=../../../bin/windows','set dirbin=tests/outputs/lian_hg_np_build_r1')
        if backend=='cpu':
            batch=batch.replace('DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2CPU_win64_debug.exe').replace('-gpu -stable','-cpu -ompthreads:8 -stable')
        if backend=='gpu_debug':
            batch=batch.replace('DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2_win64_debug.exe')
            batch=batch.replace('%dualsphysics% -gpu',f'"{MEM}" --tool memcheck --error-exitcode 99 --leak-check full %dualsphysics% -gpu')
        bat.write_text(batch.replace('\n','\r\n'),encoding='utf8',newline='')
        jobs.append(dict(name=name,backend=backend,xi=xi,dt=float(dt),duration=float(duration),cadence=float(cadence),
            reference=reference,config=bound(config),bat=bound(bat)))
    return jobs,snapshots


def main():
    assert not STATE.exists()
    prerequisite=TESTS/'logs/lian_hg_np_review_r1.check.json';review=json.loads(prerequisite.read_text())
    assert review['passed'] and review['visual_review_passed'] and review['old_periodic_cpu_gpu_snapshot0ulp']
    assert review['gpu_debug_memcheck_errors']==0
    jobs,snapshots=prepare()
    inputs=[bound(p) for p in [__file__,prerequisite,READER,MEM,TESTS/'notes/lian_hg_np_r1.md',
        TESTS/'scripts/lian_spr_half_review_r1.py',TESTS/'scripts/lian_mirror_review_r1.py',TESTS/'scripts/lian_release_r1.py']]
    inputs += [e['retained'] for e in snapshots]+[j[k] for j in jobs for k in ['config','bat']]
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,jobs=jobs,
        snapshots=snapshots,runs=[],physical_accepted=False,long_run_admitted=False,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip())
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,STATE)
    save();child=None;item=None;rows=[]
    baseline=native(TESTS/'outputs/lian_spr_mix_r1_on_3s',0)
    try:
        for job in jobs:
            verify_bindings(inputs)
            name=job['name'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            item=dict(name=name,passed=False,dt=job['dt'],xi=job['xi'],checked_frames=0)
            state['runs'].append(item);state['current_run']=name;save()
            rows=[];prefix=[];initial=None;checked=0;started=time.perf_counter()
            expected=None
            if job['reference']:
                manifest=TESTS/'logs'/(job['reference']+'.run.json');m=json.loads(manifest.read_text())
                assert m['passed'] and m['exit_code']==0 and m['owned_exited']
                expected={str(Path(e['path']).resolve()).lower():e['sha256'] for e in m['outputs']}
                item['reference']=bound(manifest)
            with log.open('xb') as f:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,
                    stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                item['owned_wrapper_pid']=child.pid;save()
                while True:
                    code=child.poll();parts=sorted((folder/'data').glob('Part_*.bi4'))
                    available=len(parts) if code is not None else max(0,len(parts)-1)
                    while checked<available:
                        a=native(folder,checked)
                        if initial is None:
                            initial=a;assert np.array_equal(a[['id','x','y','z']],baseline[['id','x','y','z']])
                        row=metrics(a,initial,checked,job['dt']);rows.append(row)
                        if expected is not None:
                            source=TESTS/'outputs'/job['reference']/'data'/f'Part_{checked:04d}.bi4'
                            assert bound(source)['sha256']==expected[str(source.resolve()).lower()]
                            b=native(TESTS/'outputs'/job['reference'],checked)
                            assert list(a.columns)==list(b.columns) and a.to_numpy(dtype='<f8').tobytes()==b.to_numpy(dtype='<f8').tobytes()
                            prefix.append(dict(part=checked,time_s=row['time_s'],all_native_fields0ulp=True))
                        checked+=1
                    item.update(checked_frames=checked,last_checked_time_s=rows[-1]['time_s'] if rows else None);save()
                    if code is not None:break
                    assert time.perf_counter()-started<3600,'Bounded startup exceeded one-hour wall-time limit'
                    time.sleep(5)
            item.update(exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-started)
            assert code==0,(name,code)
            text=(folder/'Run.out').read_text(errors='replace');assert 'Finished execution (code=0)' in text
            if job['backend']!='cpu':assert 'RTX 3050' in text
            assert 'SPR stationary wall planes (one per mk): 3' in text
            for mk,mode in [(0,'Free slip'),(1,'No-slip'),(2,'Free slip')]:
                assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode,text)
            assert len(rows)==round(job['duration']/job['cadence'])+1 and abs(rows[-1]['time_s']-job['duration'])<2e-5
            if job['xi']:
                item['hg_stats']=hg_stats(text)
                if job['backend']=='gpu_debug':assert 'ERROR SUMMARY: 0 errors' in log.read_text(errors='replace')
            artifacts=[]
            for label,data in [('history',rows),('prefix',prefix)]:
                if data:
                    p=TESTS/'figures'/(name+'_'+label+'.csv');assert not p.exists()
                    pd.DataFrame(data).to_csv(p,index=False,float_format='%.17g');artifacts.append(bound(p))
            item.update(passed=True,actual_final_time_s=rows[-1]['time_s'],artifacts=artifacts,
                outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)])
            write_json(TESTS/'logs'/(name+'.run.json'),item);save()
            print('PASS',name,rows[-1]['time_s'],flush=True)
        pairs=[];c=TESTS/'outputs'/(TAG+'_on_c');h=TESTS/'outputs'/(TAG+'_on_h');origin=native(c,0);top=origin.z.gt(9.99).to_numpy()
        for i in range(31):
            a,b=native(c,i),native(h,i);assert np.array_equal(a.id,b.id)
            assert abs(a.time_s.iloc[0]-b.time_s.iloc[0])<=1.01e-5
            p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)));d=1000*float(abs(a.z.to_numpy()[top]-b.z.to_numpy()[top]).max())
            assert p<=5 and d<=.005,(i,p,d)
            pairs.append(dict(part=i,coarse_time_s=float(a.time_s.iloc[0]),half_time_s=float(b.time_s.iloc[0]),pressure_rms_pa=p,top_material_max_mm=d))
        path=TESTS/'figures'/(TAG+'_half.csv');pd.DataFrame(pairs).to_csv(path,index=False,float_format='%.17g')
        state.update(status='short_passed_pending_review',half_pairs=31,max_pressure_rms_pa=max(p['pressure_rms_pa'] for p in pairs),
            max_top_material_mm=max(p['top_material_max_mm'] for p in pairs),artifacts=[bound(path)])
    except Exception as e:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=15)
        state.update(status='rejected_or_interrupted',error=repr(e))
        if item is not None:
            item.update(owned_exited=child is None or child.poll() is not None,exit_code=None if child is None else child.poll())
            folder=TESTS/'outputs'/item['name']
            item['partial_outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()]
            if rows:
                p=TESTS/'figures'/(item['name']+'_interrupted_history.csv');pd.DataFrame(rows).to_csv(p,index=False,float_format='%.17g')
                item['partial_history']=bound(p)
    finally:
        state['finished_utc']=utc();save()
    print(state['status'],state.get('error',''),flush=True)


if __name__=='__main__':main()
