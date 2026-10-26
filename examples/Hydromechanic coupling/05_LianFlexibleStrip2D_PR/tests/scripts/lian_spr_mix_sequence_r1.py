"""Fresh plane-normal OFF/ON Lian sequence, after bounded operator regressions."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, write_json, utc
from lian_opt3_review_r1 import metrics

TAG='lian_spr_mix_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')


def notify(status):
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID']
    message=(f'User-authorized same-thread mixed-slip Lian SPR {TAG}, not a new human observation. Detected {status}. '
        f'Read {STATE}, queue_attempt/notification, notes/lian_spr_mix_r1.json, '
        'logs/lian_spr_mix_regression_r1.check.json, all three lian_spr_mix_fields_r1 CPU/GPU receipts, '
        'logs/lian_opt3_review_r1.check.json and notes/lian_opt3_review_r1.md, plus parent validation/poromech_next_r2.json. '
        'This new stage is CPU Debug2ms OFF/ON and gated GPURelease .15s/3s plane-normal OFF/ON, not the old formal100s '
        'or option matrix. Same20301soil IDs/dp.1/eta.04/grad1/mode4 mirrored/q10kPa13node13000N/m mixed boundaries. '
        'Left mk0 and right mk2 FreeSlip, bottom mk1 NoSlip. Only local NoSlip/FreeSlip startup admission changed in '
        'CPU/GPU Single ConfigDomain; vector reflection kernels/physical momentum/Darcy unchanged. Both options share '
        'new explicit planar normals. Separate their OFF change versus retained lian_opt3_r1_grad_3s from true ON/OFF '
        'SPR effect. Check owned exits/actual times/native IDs/input-program-output hashes/all saved finite-elastic-geometry-'
        'naturalstep/sourceclock13nodeforce/all-active FSType2/3 drainage, 3-wall runtime admission and exact matching '
        'own-smoke prefixes. No5Pa half or physical acceptance is implied by cross-option comparison. '
        'Generate/inspect PNGs AND CSVs including .5/1/3s original Fig10 palette and 5/5/1.75kPa row limits, material A/B '
        'settlement, pressure,totalstress,speed,side-normal/bottom-normal-tangent response. Paper raster is numerical '
        'reference, not exact truth; do not tune only to match colors. Analyze any failure before later runs, preserve '
        'evidence and inspect survivors; analysis-only failure needs offline repair, never duplicate solvers/relaxed '
        'bounds/old-worker restart. Keep original independent5Pa/.005mm half criteria for later candidate validation. '
        'No new100s admission. HG nonperiodic neighbor support is still pending, not tested or faked by periodicity. '
        'Continue bounded SPR/HG comparisons and justified half checks, then stable-current fallback/new formal root '
        'long run if reference differences persist. Old100s stopped10.90001s219frames remains protected and retired. '
        'Selectively commit/push verified stages and verify refs; raw BI4/exe not cloudGit. After Lian comes Cryer then '
        'selfweight; no case02/KEEP/u-pl/TPI/Yao/slope reopening. This genuinely new integrated worker queues once, '
        'no restart/rearm/connectivity tests; continue without another progress prompt.')
    p=TESTS/'logs'/(TAG+'.queue_attempt.json')
    with p.open('x',encoding='utf8') as f:json.dump(dict(event=status,thread=thread,utc=utc(),message=message),f,indent=2)
    try:
        q=subprocess.run([str(CODEX),'queue','--thread',thread,'--message',message],capture_output=True,
            timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result=dict(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,
            reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as e:result=dict(status='queue_exception_no_retry',error=repr(e))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),result)


def main():
    assert not STATE.exists()
    assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']
    prep=TESTS/'logs'/(TAG+'.inputs_r2.json');planned=json.loads(prep.read_text())
    checks=[TESTS/'logs'/(n+'.check.json') for n in ['lian_spr_mix_regression_r1',
        'lian_spr_mix_fields_r1_cpu_debug','lian_spr_mix_fields_r1_gpu_release','lian_spr_mix_fields_r1_gpu_debug']]
    assert all(json.loads(p.read_text())['passed'] for p in checks)
    oldstate=json.loads((TESTS/'logs/lian_opt3_r1.status.json').read_text())
    assert oldstate['status']=='matrix_completed_pending_review'
    inputs=[bound(p) for p in [__file__,prep,READER,CODEX,TESTS/'notes/lian_spr_mix_r1.json',
        TESTS/'scripts/lian_opt3_review_r1.py', TESTS/'scripts/lian_mirror_review_r1.py',
        TESTS/'scripts/lian_release_r1.py', CASE/'support/postprocess_lian_release.py',
        REPO/'src/source/JSphCpuSingle.cpp',REPO/'src/source/JSphGpuSingle.cpp',
        REPO/'bin/windows/GenCase_win64.exe',REPO/'bin/windows/DualSPHysics5.2CPU_win64_debug.exe',
        REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe']+checks]
    for job in planned['jobs']:
        inputs.extend([job['definition'],job['bat']])
        assert not (TESTS/'outputs'/job['name']).exists()
    for p in (REPO/'bin/windows').glob('*.dll'):inputs.append(bound(p))
    inputs.append(bound(REPO/'bin/windows/DsphConfig.xml'))
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,runs=[],
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        half_step_accepted=False,physical_accepted=False,HG_tested=False)
    snapshots=[]
    for filename in ['DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2_win64_debug.exe']:
        source=REPO/'bin/windows'/filename;target=TESTS/'outputs/lian_spr_mix_build_r1'/filename
        assert not target.exists();shutil.copy2(source,target)
        assert bound(source)['sha256']==bound(target)['sha256']
        snapshots.append(dict(source=bound(source),retained=bound(target)))
    state['local_program_snapshots']=snapshots
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,STATE)
    save();child=None
    try:
        baseline=native(TESTS/'outputs/lian_opt3_r1_grad_3s',0)
        for job in planned['jobs']:
            for e in inputs:assert bound(e['path'])['sha256']==e['sha256'],e['path']
            name=job['name'];folder=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log')
            item=dict(name=name,option=job['option'],stage=job['stage'],passed=False)
            state['runs'].append(item);state['current_run']=name;save()
            rows=[];prefix=[];initial=None;checked=0;started=time.perf_counter()
            with log.open('xb') as f:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,
                    stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                item['owned_wrapper_pid']=child.pid;save()
                while True:
                    exit_code=child.poll();parts=sorted((folder/'data').glob('Part_*.bi4'))
                    available=len(parts) if exit_code is not None else max(0,len(parts)-1)
                    while checked<available:
                        a=native(folder,checked)
                        if initial is None:
                            initial=a
                            assert np.array_equal(a.id,baseline.id)
                            assert np.array_equal(a[['x','y','z']].to_numpy(),baseline[['x','y','z']].to_numpy())
                        row=metrics(a,initial,checked);rows.append(row)
                        if job['stage']=='3s' and checked<=3:
                            b=native(TESTS/'outputs'/f'{TAG}_{job["option"]}_smoke',checked*10)
                            shared=float(a.time_s.iloc[0])==float(b.time_s.iloc[0]) and int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0])
                            if shared:assert a.to_numpy(dtype='<f8').tobytes()==b.to_numpy(dtype='<f8').tobytes()
                            else:assert checked==3
                            prefix.append(dict(part=checked,time_s=row['time_s'],reference_time_s=float(b.time_s.iloc[0]),all_native_fields0ulp=shared))
                        checked+=1
                    item.update(checked_frames=checked,last_checked_time_s=rows[-1]['time_s'] if rows else None);save()
                    if exit_code is not None:break
                    time.sleep(10)
            item.update(exit_code=exit_code,owned_exited=True,wall_seconds=time.perf_counter()-started)
            assert exit_code==0,(name,exit_code)
            text=(folder/'Run.out').read_text(errors='replace')
            assert 'Finished execution (code=0)' in text
            for mk,mode in [(0,'Free slip'),(1,'No-slip'),(2,'Free slip')]:
                assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode,text)
            if job['option']=='on':assert 'SPR stationary wall planes (one per mk): 3' in text
            assert len(rows)==round(job['duration_s']/job['cadence_s'])+1
            assert abs(rows[-1]['time_s']-job['duration_s'])<2e-5
            if job['stage']=='3s':assert sum(p['all_native_fields0ulp'] for p in prefix)>=3
            artifacts=[]
            for label,data in [('history',rows),('prefix',prefix)]:
                if data:
                    p=TESTS/'figures'/(name+'_'+label+'.csv');assert not p.exists()
                    pd.DataFrame(data).to_csv(p,index=False,float_format='%.17g');artifacts.append(bound(p))
            item.update(passed=True,actual_final_time_s=rows[-1]['time_s'],artifacts=artifacts,
                outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)])
            write_json(TESTS/'logs'/(name+'.run.json'),item);save()
        state.update(status='pair_completed_pending_review',finished_utc=utc())
    except Exception as e:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode
            child.wait(timeout=15)
        state.update(status='rejected_or_interrupted',error=repr(e),finished_utc=utc())
    finally:
        save();notify(state)
    print(state['status'],state.get('error',''),flush=True)


if __name__=='__main__':main()
