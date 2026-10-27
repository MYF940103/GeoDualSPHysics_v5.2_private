"""Fresh bounded 3-s HG x SPR comparison; no automatic half/100-s admission."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, utc, write_json
from lian_spr_half_review_r1 import metrics
from lian_hg_short_r1 import hg_stats, BUILD
from lian_opt3_review_r1 import verify_bindings

TAG='lian_hg3_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')


def completion_text(status):
    assert isinstance(status,str)
    message=(f'User-authorized same-thread {TAG}: {status}. Read {STATE}, queue_attempt/notification, '
        'notes/lian_hg3_r1.json, logs/lian_hg_short_review_r1.check.json and notes/lian_hg_np_r1.md. '
        'Only fresh nonperiodic HG=.1 SPR0 .15s then3s and HG=.1 SPR1 3s were admitted; retain prior HG0 controls. '
        'Verify owned exits/actual times/20301 native IDs/all frozen input-program-output hashes, original finite/elastic/'
        'no-exclusion/geometry/naturalstep/all-active FSType2-3 drainage/13node13000N-m load and HG call/cache/dt/spin guards. '
        'Side FreeSlip/bottom NoSlip, eta.04, grad1, dp.1, float-pore/double-stress unchanged. '
        'Inspect actual shared own-smoke prefixes0ULP; any final-only unmatched save must be disclosed, never interpolated. '
        'Generate/inspect PNG and CSV pressure fields at.5/1/3s with original paper5/5/1.75kPa palette, '
        'A-B material settlement,totalstress,speed and side/bottom response. Separate HG,SPR and their interaction; '
        'cross-option changes are not5Pa half errors. No3s half or100s acceptance is implied. '
        'If failed preserve outputs, inspect exact cause/time/survivors; no relaxed gates, duplicate solver or old restart. '
        'If passed choose whether a candidate warrants independent3s half before any new formal100s decision; '
        'paperSPH/FEM is numerical reference, not assumed truth, no unlimited color tuning. '
        'Report Chinese proactively and selectively verify local/remoteGit. No case02/KEEP/u-pl/TPI/Yao/slope reopening. '
        'After Lian: Cryer then selfweight. This one-shot queues once; never restart/rearm or send selftests.')
    assert len(message)<2000
    return message


def notify(status):
    message=completion_text(status);thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID']
    with (TESTS/'logs'/(TAG+'.queue_attempt.json')).open('x',encoding='utf8') as f:
        json.dump(dict(event=status,utc=utc(),thread=thread,message=message,message_chars=len(message)),f,indent=2)
    try:
        q=subprocess.run([str(CODEX),'queue','--thread',thread,'--message',message],capture_output=True,
            timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result=dict(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,
            reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as e:result=dict(status='queue_exception_no_retry',error=repr(e))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),result)


def prepare():
    xml=(TESTS/'configs/lian_hg_short_r1_on_c_Def.xml').read_text()
    bat=(TESTS/'configs/xlian_hg_short_r1_on_c_win64.bat').read_text();jobs=[]
    for label,spr,duration,cadence in [('spr0_smoke',0,'.15','.005'),('spr0_3s',0,'3','.05'),('spr1_3s',1,'3','.05')]:
        name=TAG+'_'+label;config=TESTS/'configs'/(name+'_Def.xml');batch=TESTS/'configs'/('x'+name+'_win64.bat')
        assert not config.exists() and not batch.exists() and not (TESTS/'outputs'/name).exists()
        text=xml
        for key,value in [('SoilBoundaryDerivativeSPR',str(spr)),('TimeMax',duration),('TimeOut',cadence)]:
            text,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],text);assert n==1
        text=text.replace('Mixed-slip plane-normal ON control; candidate only','Bounded HG / SPR factorial comparison; not formal release')
        config.write_text(text,encoding='utf8')
        batch.write_text(bat.replace('lian_hg_short_r1_on_c',name).replace('\n','\r\n'),encoding='utf8',newline='')
        jobs.append(dict(name=name,spr=spr,duration=float(duration),cadence=float(cadence),config=bound(config),bat=bound(batch)))
    return jobs


def main():
    assert not STATE.exists() and os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']
    assert len(completion_text('matrix_passed_pending_review'))<2000
    review_path=TESTS/'logs/lian_hg_short_review_r1.check.json';review=json.loads(review_path.read_text())
    assert review['passed'] and review['visual_review_passed'] and review['half_pairs']==31
    short_path=TESTS/'logs/lian_hg_short_r1.status.json';short=json.loads(short_path.read_text())
    assert short['status']=='short_passed_pending_review' and len(short['runs'])==6 and all(r['passed'] for r in short['runs'])
    verify_bindings(short['inputs'])
    for r in short['runs']:verify_bindings(r['outputs']+r['artifacts'])
    prepared=TESTS/'logs'/(TAG+'.inputs.json');jobs=json.loads(prepared.read_text())['jobs']
    assert [j['name'] for j in jobs]==[TAG+'_'+v for v in ['spr0_smoke','spr0_3s','spr1_3s']]
    inputs=[bound(p) for p in [__file__,prepared,review_path,short_path,TESTS/'notes/lian_hg3_r1.json',READER,
        TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_spr_half_review_r1.py',TESTS/'scripts/lian_mirror_review_r1.py',
        TESTS/'scripts/lian_hg_short_r1.py',BUILD/'GenCase_win64.exe',BUILD/'DualSPHysics5.2_GEO_win64.exe']]
    inputs += [e['retained'] for e in short['snapshots']]+[j[k] for j in jobs for k in ['config','bat']]
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,jobs=jobs,runs=[],
        physical_accepted=False,half_step_accepted=False,formal100_admitted=False,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),notifier_program=bound(CODEX))
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,STATE)
    save();child=None;item=None;rows=[]
    baseline=native(TESTS/'outputs/lian_spr_mix_r1_on_3s',0)
    try:
        for job in jobs:
            verify_bindings(inputs)
            name=job['name'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            item=dict(name=name,spr=job['spr'],passed=False,checked_frames=0)
            state['runs'].append(item);state['current_run']=name;save()
            rows=[];prefix=[];initial=None;checked=0;started=time.perf_counter()
            reference=(TAG+'_spr0_smoke') if job['spr']==0 else 'lian_hg_short_r1_on_c'
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
                        row=metrics(a,initial,checked,1e-5);rows.append(row)
                        if job['duration']==3 and checked<=3:
                            source=TESTS/'outputs'/reference/'data'/f'Part_{checked*10:04d}.bi4'
                            manifest=TESTS/'logs'/(reference+'.run.json');saved=json.loads(manifest.read_text())
                            assert saved['passed'] and saved['exit_code']==0 and saved['owned_exited']
                            old=next(e for e in saved['outputs'] if str(Path(e['path']).resolve()).lower()==str(source.resolve()).lower())
                            assert bound(source)['sha256']==old['sha256']
                            b=native(TESTS/'outputs'/reference,checked*10)
                            shared=a.time_s.iloc[0]==b.time_s.iloc[0] and a.saved_step.iloc[0]==b.saved_step.iloc[0]
                            if shared:assert list(a.columns)==list(b.columns) and a.to_numpy(dtype='<f8').tobytes()==b.to_numpy(dtype='<f8').tobytes()
                            else:assert checked==3
                            prefix.append(dict(part=checked,time_s=row['time_s'],reference_time_s=float(b.time_s.iloc[0]),
                                shared_actual_time_step=bool(shared),all_native_fields0ulp=bool(shared)))
                        checked+=1
                    item.update(checked_frames=checked,last_checked_time_s=rows[-1]['time_s'] if rows else None);save()
                    if code is not None:break
                    time.sleep(10)
            item.update(exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-started)
            assert code==0,(name,code)
            text=(folder/'Run.out').read_text(errors='replace')
            assert 'Finished execution (code=0)' in text and 'RTX 3050' in text
            for mk,mode in [(0,'Free slip'),(1,'No-slip'),(2,'Free slip')]:
                assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode,text)
            if job['spr']:assert 'SPR stationary wall planes (one per mk): 3' in text
            assert len(rows)==round(job['duration']/job['cadence'])+1 and abs(rows[-1]['time_s']-job['duration'])<2e-5
            item['hg_stats']=hg_stats(text)
            if job['duration']==3:assert sum(p['all_native_fields0ulp'] for p in prefix)>=3
            artifacts=[]
            for label,data in [('history',rows),('prefix',prefix)]:
                if data:
                    p=TESTS/'figures'/(name+'_'+label+'.csv');assert not p.exists()
                    pd.DataFrame(data).to_csv(p,index=False,float_format='%.17g');artifacts.append(bound(p))
            item.update(passed=True,actual_final_time_s=rows[-1]['time_s'],artifacts=artifacts,
                outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)])
            write_json(TESTS/'logs'/(name+'.run.json'),item);save()
        state['status']='matrix_3s_passed_pending_review'
    except Exception as e:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=15)
        state.update(status='rejected_or_interrupted',error=repr(e))
        if item is not None:
            item.update(owned_exited=child is None or child.poll() is not None,exit_code=None if child is None else child.poll())
            folder=TESTS/'outputs'/item['name'];item['partial_outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()]
            if rows:
                p=TESTS/'figures'/(item['name']+'_interrupted_history.csv');pd.DataFrame(rows).to_csv(p,index=False,float_format='%.17g')
                item['partial_history']=bound(p)
    finally:
        state['finished_utc']=utc();save();notify(state['status'])
    print(state['status'],state.get('error',''),flush=True)


if __name__=='__main__':main()
