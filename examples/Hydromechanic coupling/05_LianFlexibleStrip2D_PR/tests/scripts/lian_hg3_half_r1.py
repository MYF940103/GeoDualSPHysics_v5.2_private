"""Conditionally admitted fresh H1S1 3-s GPU half; never auto-admits 100 s."""
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

TAG='lian_hg3_half_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
COARSE='lian_hg3_r2_spr1_3s'
PREFIX='lian_hg_short_r1_on_h'
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')


def completion_text(status):
    assert isinstance(status,str)
    message=(f'User-authorized same-thread {TAG}: {status}. Read {STATE}, queue_attempt/notification, '
        'notes/lian_hg3_half_r1.json, notes/lian_hg3_decision_r1.json, logs/lian_hg3_review_r1.check.json '
        'and logs/lian_hg3_figures_r1.check.json. Only a fresh H1S1 HG.1/SPR1 GPU3s half5us was admitted '
        'after root numerical/visual review; retained r2 H1S1 coarse10us was not rerun. '
        'Verify actual exits/owned processes/20301nativeIDs/frozen hashes, original finite/elastic/noexclusion/'
        'geometry/naturalstep/allactiveFSType2-3 drainage/13node13000N-m load and HG call-cache-dt-spin guards. '
        'SideFreeSlip/bottomNoSlip,eta.04,grad1,dp.1,floatpore/doublestress unchanged. '
        'Inspect all61 actual-matched independent5Pa pressureRMS/.005mm topmaterial half pairs, '
        'time difference<=10.1us,no interpolation; shared retainedhalf-smoke prefixes require exact34state/'
        'identity fields and original independent dterror<=1e-14,record sole interval-statistic difference. '
        'Only final prefix save may be unmatched; at least3shared. The78 comparator tests do not relax a physical guard. '
        'If runtime/check failed inspect exact time/reason/survivors,preserve data,no relaxedgates/duplicate/'
        'oldrestart; if only postcheck failed repair offline,never rerun a completed solver. '
        'On pass generate/inspect PNG+CSV full3s pressure,A/B material settlement,stress,speed,boundaries '
        'and paper.5/1/3s5/5/1.75kPa comparison before a NEW formal100s decision. '
        'Half agreement is not100s/FEM/generalcontact acceptance; paperSPH/FEM is a numerical reference. '
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


def admission():
    paths=[TESTS/'logs/lian_hg3_review_r1.check.json',TESTS/'logs/lian_hg3_figures_r1.check.json',
        TESTS/'notes/lian_hg3_decision_r1.json',TESTS/'logs/lian_hg3_r2.status.json',
        TESTS/'logs'/(COARSE+'.run.json'),TESTS/'logs'/(PREFIX+'.run.json')]
    review,figures,decision,prior,coarse,short=[json.loads(p.read_text()) for p in paths]
    assert review['passed'] and figures['passed'] and figures['visual_review_passed']
    assert decision['candidate']=='H1S1' and decision['half_admitted'] is True
    assert prior['status']=='matrix_3s_passed_pending_review' and len(prior['runs'])==2
    assert all(r['passed'] and r['owned_exited'] and r['exit_code']==0 for r in prior['runs'])
    assert coarse==next(r for r in prior['runs'] if r['name']==COARSE)
    assert coarse['checked_frames']==61 and coarse['passed'] and coarse['owned_exited'] and coarse['exit_code']==0
    assert short['passed'] and short['owned_exited'] and short['exit_code']==0 and short['checked_frames']==31
    verify_bindings(prior['inputs'])
    for run in prior['runs']+[short]:verify_bindings(run['outputs']+run['artifacts'])
    return paths,prior,coarse,short


def prepare():
    # Called explicitly only after the root's numerical/visual candidate decision.
    admission()
    config=TESTS/'configs'/(TAG+'_Def.xml');batch=TESTS/'configs'/('x'+TAG+'_win64.bat')
    prepared=TESTS/'logs'/(TAG+'.inputs.json')
    assert not any(p.exists() for p in [config,batch,prepared,STATE,TESTS/'outputs'/TAG])
    source_xml=TESTS/'configs'/(COARSE+'_Def.xml')
    source_bat=TESTS/'configs'/('x'+COARSE+'_win64.bat')
    text=source_xml.read_text()
    for key in ['DtIni','DtFixed']:
        pattern=r'(<parameter key="'+key+r'" value=")([^"]*)(")'
        match=re.search(pattern,text);assert match and float(match[2])==1e-5
        text,n=re.subn(pattern,lambda m:m[1]+'0.000005'+m[3],text);assert n==1
    for key,value in [('TimeMax',3.),('TimeOut',.05),('SoilBoundaryDerivativeSPR',1.),
        ('SoilHourglassXi',.1),('SoilStressRateGradCorr',1.)]:
        assert float(re.search(r'<parameter key="'+key+r'" value="([^"]*)"',text)[1])==value
    batch_text=source_bat.read_text()
    assert 'set dirbin=tests/outputs/lian_hg_np_build_r1' in batch_text
    assert 'DualSPHysics5.2_GEO_win64.exe' in batch_text and '-gpu -stable' in batch_text
    config.write_text(text,encoding='utf8')
    batch.write_text(batch_text.replace(COARSE,TAG).replace('\n','\r\n'),encoding='utf8',newline='')
    job=dict(name=TAG,coarse=COARSE,reference=PREFIX,dt=5e-6,duration=3.,cadence=.05,
        config=bound(config),bat=bound(batch))
    write_json(prepared,dict(preparation_only=True,utc=utc(),source=bound(__file__),
        source_xml=bound(source_xml),source_bat=bound(source_bat),job=job))
    return job


def main():
    assert not STATE.exists() and os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']
    assert len(completion_text('half_3s_passed_pending_review'))<2000
    prerequisites,prior,coarse,short=admission()
    prepared=TESTS/'logs'/(TAG+'.inputs.json');preparation=json.loads(prepared.read_text());job=preparation['job']
    assert job['name']==TAG and job['dt']==5e-6 and job['duration']==3 and job['cadence']==.05
    verify_bindings([preparation[k] for k in ['source','source_xml','source_bat']]+[job['config'],job['bat']])
    sources=[__file__,prepared,TESTS/'notes'/(TAG+'.json'),READER,
        TESTS/'scripts/lian_hg_prefix_r2.py',TESTS/'scripts/lian_release_r1.py',
        TESTS/'scripts/lian_spr_half_review_r1.py',TESTS/'scripts/lian_mirror_review_r1.py',
        TESTS/'scripts/lian_hg_short_r1.py',BUILD/'DualSPHysics5.2_GEO_win64.exe']+prerequisites
    inputs=[bound(p) for p in sources]+prior['inputs']+[job['config'],job['bat']]
    folder=TESTS/'outputs'/TAG;log=TESTS/'logs'/(TAG+'.log')
    assert not folder.exists() and not log.exists(), 'Never overwrite a retained solver result'
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,job=job,
        runs=[],physical_accepted=False,half_accepted=False,formal100_admitted=False,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),notifier_program=bound(CODEX))
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,STATE)
    save();child=None;rows=[];prefix=[];pairs=[]
    item=dict(name=TAG,passed=False,dt=5e-6,xi=.1,spr=1,checked_frames=0)
    state['runs'].append(item);state['current_run']=TAG;save()
    try:
        verify_bindings(inputs)
        origin=native(TESTS/'outputs'/COARSE,0);top=origin.z.gt(9.99).to_numpy();assert top.any()
        coarse_files={str(Path(e['path']).resolve()).lower():e for e in coarse['outputs']}
        short_files={str(Path(e['path']).resolve()).lower():e for e in short['outputs']}
        initial=None;checked=0;started=time.perf_counter()
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
                        initial=a;assert np.array_equal(a[['id','x','y','z']],origin[['id','x','y','z']])
                    rows.append(metrics(a,initial,checked,5e-6))
                    if checked<=3:
                        source=TESTS/'outputs'/PREFIX/'data'/f'Part_{checked*10:04d}.bi4'
                        verify_bindings([short_files[str(source.resolve()).lower()]])
                        b=native(TESTS/'outputs'/PREFIX,checked*10)
                        shared=a.time_s.iloc[0]==b.time_s.iloc[0] and a.saved_step.iloc[0]==b.saved_step.iloc[0]
                        pair=dict(part=checked,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),
                            saved_step=int(a.saved_step.iloc[0]),reference_step=int(b.saved_step.iloc[0]),shared_actual_time_step=bool(shared))
                        if shared:pair.update(compare_prefix(a,b))
                        else:assert checked==3, 'Only the final smoke save may be unmatched'
                        prefix.append(pair)
                    source=TESTS/'outputs'/COARSE/'data'/f'Part_{checked:04d}.bi4'
                    verify_bindings([coarse_files[str(source.resolve()).lower()]])
                    c=native(TESTS/'outputs'/COARSE,checked);metrics(c,origin,checked,1e-5)
                    assert np.array_equal(a.id,c.id) and abs(a.time_s.iloc[0]-c.time_s.iloc[0])<=1.01e-5
                    p=float(np.sqrt(np.mean((a.pressure-c.pressure)**2)))
                    d=1000*float(abs(a.z.to_numpy()[top]-c.z.to_numpy()[top]).max())
                    assert p<=5 and d<=.005,(checked,p,d)
                    pairs.append(dict(part=checked,coarse_time_s=float(c.time_s.iloc[0]),half_time_s=float(a.time_s.iloc[0]),
                        pressure_rms_pa=p,top_material_max_mm=d))
                    checked+=1
                item.update(checked_frames=checked,last_checked_time_s=rows[-1]['time_s'] if rows else None);save()
                if code is not None:break
                time.sleep(10)
        item.update(exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-started)
        assert code==0,('Half solver exited',code)
        text=(folder/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text and 'RTX 3050' in text
        assert 'SPR stationary wall planes (one per mk): 3' in text
        for mk,mode in [(0,'Free slip'),(1,'No-slip'),(2,'Free slip')]:
            assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode,text)
        assert len(rows)==len(pairs)==61 and abs(rows[-1]['time_s']-3)<2e-5
        assert sum(p.get('physical_identity_columns0ulp',False) for p in prefix)>=3
        item['hg_stats']=hg_stats(text)
        artifacts=[]
        for label,data in [('history',rows),('prefix',prefix),('half',pairs)]:
            path=TESTS/'figures'/(TAG+'_'+label+'.csv');assert not path.exists()
            pd.DataFrame(data).to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
        item.update(passed=True,actual_final_time_s=rows[-1]['time_s'],artifacts=artifacts,
            outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)])
        write_json(TESTS/'logs'/(TAG+'.run.json'),item)
        state.update(status='half_3s_passed_pending_review',half_accepted=True,half_pairs=61,
            max_pressure_rms_pa=max(p['pressure_rms_pa'] for p in pairs),
            max_top_material_mm=max(p['top_material_max_mm'] for p in pairs))
    except Exception as e:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=15)
        state.update(status='rejected_or_interrupted',error=repr(e),traceback=traceback.format_exc())
        item.update(owned_exited=child is None or child.poll() is not None,exit_code=None if child is None else child.poll())
        item['partial_outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()]
        if log.exists():item['partial_outputs'].append(bound(log))
        partial=[]
        for label,data in [('history',rows),('prefix',prefix),('half',pairs)]:
            if data:
                path=TESTS/'figures'/(TAG+'_interrupted_'+label+'.csv');assert not path.exists()
                pd.DataFrame(data).to_csv(path,index=False,float_format='%.17g');partial.append(bound(path))
        item['partial_artifacts']=partial
    finally:
        state['finished_utc']=utc();save();notify(state['status'])
    print(state['status'],state.get('error',''),flush=True)


if __name__=='__main__':main()
