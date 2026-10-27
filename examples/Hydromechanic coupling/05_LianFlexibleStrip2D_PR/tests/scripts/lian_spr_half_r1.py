"""One fresh 3-s GPU half-step, only after reviewed mixed-slip SPR comparison."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, write_json, utc
from lian_mirror_review_r1 import sample

TAG='lian_spr_half_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')


def completion_text(status):
    if not isinstance(status,str):raise TypeError('Completion status must be a scalar string, never the full state dictionary')
    text=(f'User-authorized same-thread {TAG}: {status}. Read {STATE} and notes/lian_spr_half_r1.json, '
        'logs/lian_spr_mix_review_r1.check.json and notes/lian_spr_mix_review_r1.md before claims. '
        'Verify native exits/times/IDs/hashes/all61 original5Pa/.005mm half gates and safety; inspect PNG/CSV. '
        'On failure preserve data and diagnose without relaxed guards/duplicate solver. '
        'Continue bounded nonperiodic-HG work then stable-scheme/new formal long-run decision; no automatic100s acceptance. '
        'Old workers stay retired; do not restart/rearm this one-shot. Report Chinese and selective verified local/remoteGit; '
        'no case02/KEEP/u-pl/TPI/Yao/slope reopening. After Lian comes Cryer then selfweight.')
    assert len(text)<2000
    return text


def notify(status):
    message=completion_text(status);thread=os.environ['CODEX_THREAD_ID']
    assert thread==os.environ['CODEX_SESSION_ID']
    with (TESTS/'logs'/(TAG+'.queue_attempt.json')).open('x',encoding='utf8') as f:
        json.dump(dict(event=status,thread=thread,utc=utc(),message=message,message_chars=len(message)),f,indent=2)
    try:
        q=subprocess.run([str(CODEX),'queue','--thread',thread,'--message',message],capture_output=True,
            timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result=dict(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,
            reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as e:result=dict(status='queue_exception_no_retry',error=repr(e))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),result)


def prepare():
    text=(TESTS/'configs/lian_spr_mix_r1_on_3s_Def.xml').read_text()
    for key in ['DtIni','DtFixed']:
        text,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+'.000005'+m[2],text);assert n==1
    config=TESTS/'configs'/(TAG+'_Def.xml');assert not config.exists();config.write_text(text,encoding='utf8')
    text=(TESTS/'configs/xlian_spr_mix_r1_on_3s_win64.bat').read_text().replace('lian_spr_mix_r1_on_3s',TAG)
    bat=TESTS/'configs'/('x'+TAG+'_win64.bat');assert not bat.exists();bat.write_text(text,encoding='utf8')
    return config,bat


def main():
    assert not STATE.exists() and not (TESTS/'outputs'/TAG).exists()
    # Pure local regression of the earlier notifier bug; no message is queued here.
    assert len(completion_text('passed_pending_review'))<2000
    rejected=False
    try:completion_text({'status':'must_not_be_interpolated'})
    except TypeError:rejected=True
    assert rejected
    review_path=TESTS/'logs/lian_spr_mix_review_r1.check.json';review=json.loads(review_path.read_text())
    assert review['passed'] and review['visual_review_passed'] and review['matched_samples']==61
    assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']
    config,bat=prepare();folder=TESTS/'outputs'/TAG
    reference=TESTS/'outputs/lian_spr_mix_r1_on_3s'
    manifest_path=TESTS/'logs/lian_spr_mix_r1_on_3s.run.json';manifest=json.loads(manifest_path.read_text())
    assert manifest['passed'] and manifest['owned_exited'] and manifest['exit_code']==0
    expected={str(Path(p['path']).resolve()).lower():p['sha256'] for p in manifest['outputs']}
    inputs=[bound(p) for p in [__file__,review_path,TESTS/'notes'/f'{TAG}.json',config,bat,manifest_path,
        TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_mirror_review_r1.py',READER,CODEX,
        REPO/'bin/windows/GenCase_win64.exe',REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe']]
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,checked_frames=0,
        last_checked_time_s=None,half_accepted=False,physical_full_accepted=False,HG_tested=False,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        notifier_local_type_length_check_passed=True)
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,STATE)
    save();child=None;log=TESTS/'logs'/(TAG+'.log');history=[];pairs=[];initial=None;checked=0;started=time.perf_counter()
    try:
        with log.open('xb') as f:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(bat)],cwd=CASE,stdout=f,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid']=child.pid;save()
            while True:
                code=child.poll();parts=sorted((folder/'data').glob('Part_*.bi4'))
                available=len(parts) if code is not None else max(0,len(parts)-1)
                while checked<available:
                    a=native(folder,checked);b=native(reference,checked)
                    source=reference/'data'/f'Part_{checked:04d}.bi4'
                    assert bound(source)['sha256']==expected[str(source.resolve()).lower()]
                    if initial is None:
                        initial=a
                        assert np.array_equal(a.id,b.id) and np.array_equal(a[['x','y','z']].to_numpy(),b[['x','y','z']].to_numpy())
                    row=sample(a,initial,5e-6,True);row['part']=checked;row['pressure_max_pa']=float(a.pressure.max());history.append(row)
                    assert np.array_equal(a.id,b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<=1.01e-5
                    top=initial.z.gt(9.99).to_numpy()
                    p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
                    d=1000*float(abs(a.z.to_numpy()[top]-b.z.to_numpy()[top]).max())
                    pairs.append(dict(part=checked,half_time_s=float(a.time_s.iloc[0]),coarse_time_s=float(b.time_s.iloc[0]),
                        pressure_rms_pa=p,top_material_max_mm=d))
                    assert p<=5 and d<=.005,(checked,p,d)
                    checked+=1
                state.update(checked_frames=checked,last_checked_time_s=history[-1]['time_s'] if history else None);save()
                if code is not None:break
                time.sleep(10)
        state.update(exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-started)
        assert code==0 and 'Finished execution (code=0)' in (folder/'Run.out').read_text(errors='replace')
        assert len(history)==61 and abs(history[-1]['time_s']-3)<2e-5
        state.update(status='half_passed_pending_review',half_accepted=True,
            max_pressure_rms_pa=max(p['pressure_rms_pa'] for p in pairs),max_top_material_mm=max(p['top_material_max_mm'] for p in pairs))
    except Exception as e:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=15)
        state.update(status='rejected_or_interrupted',error=repr(e))
    finally:
        artifacts=[]
        for label,data in [('history',history),('half',pairs)]:
            if data:
                p=TESTS/'figures'/(TAG+'_'+label+'.csv');assert not p.exists()
                pd.DataFrame(data).to_csv(p,index=False,float_format='%.17g');artifacts.append(bound(p))
        state.update(finished_utc=utc(),artifacts=artifacts,
            outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+([bound(log)] if log.exists() else []))
        save();notify(state['status'])
    print(state['status'],state.get('error',''),flush=True)


if __name__=='__main__':main()
