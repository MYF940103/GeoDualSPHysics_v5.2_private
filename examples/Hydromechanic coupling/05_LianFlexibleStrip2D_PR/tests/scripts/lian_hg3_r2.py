"""Fresh 3-s HG/SPR comparison after the documented r1 interval-statistic audit."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, utc, write_json
from lian_spr_half_review_r1 import metrics
from lian_hg_short_r1 import hg_stats, BUILD
from lian_opt3_review_r1 import verify_bindings
from lian_hg_prefix_r2 import compare_prefix

TAG='lian_hg3_r2'
STATE=TESTS/'logs'/(TAG+'.status.json')
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')


def completion_text(status):
    assert isinstance(status,str)
    message=(f'User-authorized same-thread {TAG}: {status}. Read {STATE}, queue_attempt/notification, '
        'notes/lian_hg3_r2.json, logs/lian_hg3_r1_audit.check.json and logs/lian_hg_short_review_r1.check.json. '
        'Frozen r1 stopped at.10001s solely because cross-cadence dterror interval telemetry differed; '
        'its completed SPR0 .15s smoke was adopted, never restarted. Only two fresh3s HG=.1 SPR0/1 GPU runs admitted. '
        'Verify exits/ownership/actual times/20301nativeIDs/frozen hashes and all original finite/elastic/no-exclusion/'
        'geometry/naturalstep/FSType2-3 drainage/13node13000N-m load/HG call-cache-dt-spin gates. '
        'SideFreeSlip/bottomNoSlip,eta.04,grad1,dp.1,floatpore/doublestress unchanged. '
        'Own-smoke shared actual-time-step prefixes must have all34 physical/identity fields0ULP; '
        'record sole excluded dterror_s output-interval statistic and independently enforce original<=1e-14 '
        'in each run. No other exception or interpolation; disclose final-only unmatchedsave. '
        'Inspect PNG/CSV .5/1/3s paper5/5/1.75kPa palette fields,A/B material settlement,totalstress,speed,'
        'side/bottom and HGxSPR interaction against retained HG0 controls. Cross-option changes are not half errors. '
        'No3s half/100s acceptance. If failed inspect exact cause/time/survivors,preserve outputs,no relaxedgates/'
        'duplicates/oldrestart. If passed choose justified independent3s half before new formal100s decision. '
        'PaperSPH/FEM is numerical reference,not truth; no unlimited color tuning. '
        'Report Chinese proactively,selective verified local/remoteGit. AfterLian:Cryer then selfweight; '
        'no case02/KEEP/u-pl/TPI/Yao/slope reopening. One-shot queuesonce; never restart/rearm/selftest.')
    assert len(message)<2000
    return message


def notify(status):
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID']
    message=completion_text(status)
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
    jobs=[]
    for spr,reference in [(0,'lian_hg3_r1_spr0_smoke'),(1,'lian_hg_short_r1_on_c')]:
        old='lian_hg3_r1_spr'+str(spr)+'_3s';name=TAG+'_spr'+str(spr)+'_3s'
        config=TESTS/'configs'/(name+'_Def.xml');batch=TESTS/'configs'/('x'+name+'_win64.bat')
        assert not config.exists() and not batch.exists() and not (TESTS/'outputs'/name).exists()
        config.write_bytes((TESTS/'configs'/(old+'_Def.xml')).read_bytes())
        text=(TESTS/'configs'/('x'+old+'_win64.bat')).read_text()
        batch.write_text(text.replace(old,name).replace('\n','\r\n'),encoding='utf8',newline='')
        jobs.append(dict(name=name,spr=spr,reference=reference,duration=3.,cadence=.05,config=bound(config),bat=bound(batch)))
    destination=TESTS/'logs'/(TAG+'.inputs.json');assert not destination.exists()
    write_json(destination,dict(preparation_only=True,utc=utc(),source=bound(__file__),jobs=jobs))


def main():
    assert not STATE.exists() and os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']
    assert len(completion_text('matrix_3s_passed_pending_review'))<2000
    audit_path=TESTS/'logs/lian_hg3_r1_audit.check.json';audit=json.loads(audit_path.read_text())
    assert audit['passed'], 'r1 cause and comparator self-tests must pass first'
    review_path=TESTS/'logs/lian_hg_short_review_r1.check.json';review=json.loads(review_path.read_text())
    assert review['passed'] and review['visual_review_passed'] and review['half_pairs']==31
    short_path=TESTS/'logs/lian_hg_short_r1.status.json';short=json.loads(short_path.read_text())
    assert short['status']=='short_passed_pending_review' and len(short['runs'])==6 and all(r['passed'] for r in short['runs'])
    verify_bindings(short['inputs'])
    for r in short['runs']:verify_bindings(r['outputs']+r['artifacts'])
    prior_path=TESTS/'logs/lian_hg3_r1.status.json';prior=json.loads(prior_path.read_text())
    assert prior['status']=='rejected_or_interrupted' and prior['runs'][0]['passed']
    prepared=TESTS/'logs'/(TAG+'.inputs.json');preparation=json.loads(prepared.read_text());jobs=preparation['jobs']
    verify_bindings([preparation['source']]+[j[k] for j in jobs for k in ['config','bat']])
    inputs=[bound(p) for p in [__file__,prepared,audit_path,review_path,short_path,prior_path,READER,
        TESTS/'notes/lian_hg3_r2.json',TESTS/'scripts/lian_hg_prefix_r2.py',
        TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_spr_half_review_r1.py',
        TESTS/'scripts/lian_mirror_review_r1.py',TESTS/'scripts/lian_hg_short_r1.py']]
    inputs += [e['retained'] for e in short['snapshots']]+[j[k] for j in jobs for k in ['config','bat']]
    for j in jobs:
        manifest=TESTS/'logs'/(j['reference']+'.run.json');r=json.loads(manifest.read_text())
        assert r['passed'] and r['owned_exited'] and r['exit_code']==0
        verify_bindings(r['outputs']+r['artifacts']);inputs.append(bound(manifest))
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,jobs=jobs,runs=[],
        adopted_smoke='lian_hg3_r1_spr0_smoke',physical_accepted=False,half_step_accepted=False,formal100_admitted=False,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),notifier_program=bound(CODEX))
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,STATE)
    save();child=None;item=None;rows=[]
    baseline=native(TESTS/'outputs/lian_spr_mix_r1_on_3s',0)
    try:
        for job in jobs:
            verify_bindings(inputs)
            name=job['name'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            assert not folder.exists() and not log.exists(), 'Never overwrite a retained run'
            item=dict(name=name,spr=job['spr'],passed=False,checked_frames=0)
            state['runs'].append(item);state['current_run']=name;save()
            rows=[];prefix=[];initial=None;checked=0;started=time.perf_counter()
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
                        if checked<=3:
                            b=native(TESTS/'outputs'/job['reference'],checked*10)
                            shared=a.time_s.iloc[0]==b.time_s.iloc[0] and a.saved_step.iloc[0]==b.saved_step.iloc[0]
                            pair=dict(part=checked,time_s=row['time_s'],reference_time_s=float(b.time_s.iloc[0]),
                                shared_actual_time_step=bool(shared))
                            if shared:pair.update(compare_prefix(a,b))
                            else:assert checked==3, 'Non-final prefix must have identical actual time and step'
                            prefix.append(pair)
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
            assert len(rows)==61 and abs(rows[-1]['time_s']-3)<2e-5
            item['hg_stats']=hg_stats(text)
            assert sum(p.get('physical_identity_columns0ulp',False) for p in prefix)>=3
            artifacts=[]
            for label,data in [('history',rows),('prefix',prefix)]:
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
        state.update(status='rejected_or_interrupted',error=repr(e),traceback=traceback.format_exc())
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
