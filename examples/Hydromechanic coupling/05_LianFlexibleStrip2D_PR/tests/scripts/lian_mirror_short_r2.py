"""Continue only unrun mirror jobs after fixing the isolated DLL runtime."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,TESTS,REPO,READER,bound,native,write_json,utc,pair
from lian_drained_review_r1 import verify
from lian_mirror_short_r1 import inspect,program

TAG='lian_mirror_short_r2'
JOBS=[('gpu_debug',1e-5,.002,.001),('smoke_c',1e-5,.15,.005),('smoke_h',5e-6,.15,.005),('drained_c',1e-5,3,.05),('drained_h',5e-6,3,.05)]
STATE=TESTS/'logs'/(TAG+'.status.json')


def prepare():
    for suffix,*_ in JOBS:
        old='lian_mirror_short_r1_'+suffix;new=TAG+'_'+suffix
        for oldfile,newfile in [(old+'_Def.xml',new+'_Def.xml'),('x'+old+'_win64.bat','x'+new+'_win64.bat')]:
            target=TESTS/'configs'/newfile;assert not target.exists() and not (TESTS/'outputs'/new).exists()
            text=(TESTS/'configs'/oldfile).read_text(encoding='utf8').replace(old,new)
            target.write_text(text.replace('\n','\r\n'),encoding='utf8',newline='')
    print('Prepared5 fresh missing jobs; completed CPU Debug is adopted, never rerun')


def notify(record):
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID']
    message=(f'User-authorized same-thread Lian mirror short continuation {TAG}, not a new human observation. Detected '+record['status']+'. '
        f'Read {STATE}, its queue_attempt/notification, tests/notes/lian_mirror_r2.json and lian_mirror_r1.json, logs/lian_mirror_runtime_r1.json and logs/lian_late15_review_r1.check.json. '
        'Frozen r1 CPU Debug2ms passed and was adopted, not rerun. r1 GPU Debug never reached CUDA: isolated candidate directory missed dsphchrono/Chrono DLLs (directhelp exit0xc0000135). Canonical DLL/config copies were SHA verified; executable/physics unchanged and both candidate help commands now exit0. Never restart r1. '
        'Only fresh r2 GPU Debug2ms memcheck, GPU Release.15s then3s coarse10us/half5us were admitted in gated order. Verify owned exits, actualtimes/native20301IDs, frozen source/build/input/output/runtime hashes, all original finite/elastic/geometry/naturalstep and FSType2/3 drainage guards. '
        'Mode4 alone mirrors x0 wall using abs(x)<=1.25; original domain/q/13-node quadrature/mixedmDBC/eta.04/dp.1/stressdouble/porefloat/SPR-HGoff remain. Preserve original all-sample5Pa/.005mm independent half gates and13-node13000N/m postramp force (actual prior source time, not fixed-grid event). '
        'Inspect strict same-dt changes and plots/CSVs before conclusions; no assumed0ULP or Debug/Release equivalence. On a prior failure no later data are admitted; diagnose exact reason/time and survivors, no duplicate solvers, relaxed bounds, raised damping or overwritten evidence. Completed solver plus postcheck failure needs offline repair, not rerun. '
        'On pass proactively report Chinese short outcome, selectively verify local/remote Git backup of the two predicate changes/docs/evidence, then justified fresh15s coarse/half covering strict12.4/14.1s switching before formal100s root XML/BAT actual execution/PNG/CSV. Shortpass is not late/full/FEM/generalcontact acceptance. '
        'Strict15s review at ac5dec9 had repeated1000N/m contactloss, min-3211.99Pa; CPU/GPU mirror is still a candidate. Canonical GPU control and raw results remain; candidateGPU lives under outputs/lian_mirror_build_r1. Continue authorized Yao/Cryer/slope plan without reopening case02/KEEP/u-pl/TPI. This new integrated notifier queues once; never restart/rearm old or current workers or send self-tests. Continue without progress prompting.')
    attempt=TESTS/'logs'/(TAG+'.queue_attempt.json')
    with attempt.open('x',encoding='utf8') as f:json.dump(dict(event=record['status'],thread=thread,message=message,utc=utc()),f,indent=2)
    try:
        exe=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
        q=subprocess.run([str(exe),'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        outcome=dict(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as error:outcome=dict(status='queue_uncertain_no_retry',error=repr(error))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),outcome)


def run():
    assert not STATE.exists() and os.environ.get('CODEX_THREAD_ID')==os.environ.get('CODEX_SESSION_ID')
    oldpath=TESTS/'logs/lian_mirror_short_r1.status.json';old=json.loads(oldpath.read_text());verify(old)
    assert old['status']=='rejected_or_interrupted' and old['current_run'].endswith('gpu_debug')
    cpu=old['runs'][0];assert cpu['exit_code']==0 and cpu['owned_exited'] and cpu['name'].endswith('cpu_debug');verify(cpu)
    assert abs(cpu['actual_final_time_s']-.002)<1e-14 and bound(cpu['history']['path'])['sha256']==cpu['history']['sha256']
    runtimepath=TESTS/'logs/lian_mirror_runtime_r1.json';runtime=json.loads(runtimepath.read_text(encoding='utf-8-sig'));assert runtime['passed']
    for e in runtime['files']:assert bound(e['path'])['sha256'].lower()==e['sha256'].lower()
    inputs=[bound(p) for p in [Path(__file__),TESTS/'scripts/lian_mirror_short_r1.py',TESTS/'notes/lian_mirror_r1.json',TESTS/'notes/lian_mirror_r2.json',
        oldpath,runtimepath,TESTS/'logs/lian_mirror_build_r1.json',READER]]
    inputs+= [bound(e['path']) for e in old['inputs']]
    for suffix,*_ in JOBS:inputs += [bound(TESTS/'configs'/(TAG+'_'+suffix+'_Def.xml')),bound(TESTS/'configs'/('x'+TAG+'_'+suffix+'_win64.bat'))]
    record=dict(status='running',owned_sequence_pid=os.getpid(),started_utc=utc(),inputs=inputs,runs=[],pairs=[],adopted_CPU_Debug=cpu,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),physical_full_cycle_accepted=False)
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,record);os.replace(tmp,STATE)
    save()
    try:
        for suffix,dt,end,cadence in JOBS:
            name=TAG+'_'+suffix;folder=TESTS/'outputs'/name;assert not folder.exists()
            record['current_run']=name;log=TESTS/'logs'/(name+'.log');start=time.perf_counter()
            with log.open('xb') as f:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64.bat'))],cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                record['owned_wrapper_pid']=child.pid;save();code=child.wait()
            item=dict(name=name,exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-start,log=bound(log));record['runs'].append(item)
            parts=sorted((folder/'data').glob('Part_*.bi4'))
            if parts:item['actual_final_time_s']=float(native(folder,int(parts[-1].stem.split('_')[-1])).time_s.iloc[0])
            item['outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()];save()
            assert code==0 and (folder/'Run.out').exists() and 'Finished execution (code=0)' in (folder/'Run.out').read_text(errors='replace'),name
            if suffix=='gpu_debug':assert 'ERROR SUMMARY: 0 errors' in log.read_text(errors='replace')
            history=inspect(folder,dt,end,cadence);csv=TESTS/'figures'/(name+'_history.csv');history.to_csv(csv,index=False,float_format='%.17g');item['history']=bound(csv)
            if suffix!='gpu_debug':
                stage=suffix.split('_')[0];reference=TESTS/'outputs'/('lian_release_r1_'+('smoke' if stage=='smoke' else 'drained')+'_gpu_'+suffix[-1]);origin=native(reference,0);diff=[]
                for i in range(len(history)):
                    a,b=native(folder,i),native(reference,i);assert np.array_equal(a.id,b.id) and abs(float(a.time_s.iloc[0]-b.time_s.iloc[0]))<=1.01e-5
                    top=origin.z.gt(9.99).to_numpy()
                    diff.append(dict(part=i,time_s=float(a.time_s.iloc[0]),all_fields0ulp=bool(np.array_equal(a.to_numpy(),b.to_numpy())),
                        pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),top_material_max_mm=float(1000*np.max(abs(a.z.to_numpy()[top]-b.z.to_numpy()[top])))))
                csv=TESTS/'figures'/(name+'_strict.csv');pd.DataFrame(diff).to_csv(csv,index=False,float_format='%.17g');item['strict_comparison']=bound(csv)
            write_json(TESTS/'logs'/(name+'.run.json'),item);save()
            if suffix.endswith('_h'):
                frame,passed=pair(TESTS/'outputs'/(TAG+'_'+suffix[:-1]+'c'),folder);csv=TESTS/'figures'/(TAG+'_'+suffix.split('_')[0]+'_half.csv');frame.to_csv(csv,index=False,float_format='%.17g')
                result=dict(stage=suffix.split('_')[0],passed=passed,max_pressure_RMS_Pa=float(frame.pressure_rms_difference_pa.max()),max_top_material_mm=float(frame.top_material_max_difference_mm.max()),artifact=bound(csv));record['pairs'].append(result);save()
                assert passed,('Original independent half bounds',result)
        for e in inputs:assert bound(e['path'])['sha256']==e['sha256'],e['path']
        record.update(status='short_gates_passed_pending_physical_review',finished_utc=utc())
    except Exception as error:record.update(status='rejected_or_interrupted',error=repr(error),finished_utc=utc())
    finally:save();notify(record)
    print(record['status'],record.get('error',''),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args()
    (prepare if args.action=='prepare' else run)()
