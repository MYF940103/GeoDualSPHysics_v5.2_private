"""One fresh real-program 15-s baseline, with native checks and one terminal queue.

No production edits, PART restart, duplicate solver, background watcher or retries.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,TESTS,REPO,READER,bound,native,write_json,utc
from lian_drained_review_r1 import describe,verify

TAG='lian_late15_r1'
DT=1e-5
STATE=TESTS/'logs'/(TAG+'.status.json')
CONTROL=TESTS/'outputs/lian_release_r1_drained_gpu_c'
ADMISSION=TESTS/'logs/lian_drained_review_r1.check.json'


def prepare():
    gate=json.loads(ADMISSION.read_text());assert gate['passed'] and gate['visual_review_passed']
    config=TESTS/'configs'/(TAG+'_Def.xml');batch=TESTS/'configs'/('x'+TAG+'_win64_GPU.bat')
    assert not config.exists() and not batch.exists() and not STATE.exists()
    text=(TESTS/'configs/lian_release_r1_drained_gpu_c_Def.xml').read_text(encoding='utf8')
    text,count=re.subn(r'(<parameter key="TimeMax" value=")[^"]+',lambda m:m[1]+'15',text);assert count==1
    text=text.replace('Short admission across the original 1 s load-ramp and drainage event; not full dissipation',
                      'Late-window diagnostic through the retained first14.1s contact event; not a full dissipation acceptance')
    text=text.replace('Retain original 0.05 s cadence for the coarse and half-step comparison',
                      'Retain original0.05s cadence and native material histories; single10us diagnostic')
    config.write_text(text,encoding='utf8')
    source=(TESTS/'configs/xlian_release_r1_drained_gpu_c_win64.bat').read_text(encoding='utf8')
    batch.write_text(source.replace('lian_release_r1_drained_gpu_c',TAG).replace('\n','\r\n'),encoding='utf8',newline='')
    print('Prepared independent15s XML/BAT; original loading/BC/precision and output0.05s unchanged')


def notify(record,codex,thread):
    attempt=TESTS/'logs'/(TAG+'.queue_attempt.json');assert not attempt.exists()
    message=(f'User-authorized same-thread Lian late-window continuation {TAG}, not a new human observation. Detected '+record['status']+'. '
        f'Read {STATE}, tests/logs/{TAG}.queue_attempt.json and .notification.json, tests/notes/lian_late15_r1.json, '
        'tests/logs/lian_drained_review_r1.check.json and parent validation/poromech_next_r1.json before claims. '
        'Only one fresh actual GPU Release15s original mixed-slip/strict mode4 strip, dt10us, eta.04, dp.1, output.05s, stress double/pore float, SPR/HG/stress-gradient correction off was admitted. '
        'Actual current GPU must be checked from this Run.out; current host is RTX3050, NOT historical A6000. '
        'Verify exact exits/ownership, actual final time/native IDs, all frozen build/input/output hashes, original natural-step/elastic/finite/geometry and all-direction FSType2/3 drainage guards. '
        'Verify shared exact-time/step3s prefix0ULP, not an interpolated nominal-time comparison. BI4 Step is zero-based; this runner uses configured10us for prior source time. '
        'Review all301 histories, original13-node force quadrature, id1744 x/contact/drainage switches, negative-pressure/speed events near14.1s and final pressure/material settlement/stress. '
        'Compare retained old native states at actual matched times, generate and inspect PNGs and matching CSVs. Old load telemetry is zero and cannot establish physically zero force. '
        'Old/current is NOT an isolated stress-precision A/B; old initial positions are float while later states may be double. '
        'If physical solver finished but new analysis failed, preserve the completed solve and repair only new analysis. If runtime interrupted inspect actual sealed time and surviving owned processes; no duplicate or old restart. '
        'Report quantified Chinese results proactively;15s single-dt is not a full-cycle half-step or100s/FEM acceptance. Continue authorized late-platform/contact diagnosis without relaxed thresholds, raised damping or unreviewed boundary changes. '
        'On justified acceptance prepare independent root formal XML/BAT and actually run the complete paper endpoint, figures AND CSVs; preserve prior formal data. '
        'Selectively commit/push each verified stage and verify local/remote refs; raw BI4/executables are not cloud Git backup. '
        'Continue Yao/Cryer and target-slope delivery in the existing gated plan; Yao5.2.3 baseline remains all-free-slip and mixed-slip SPR is not implemented. '
        'Do not reopen accepted case02/KEEP/u-pl/TPI. This new integrated notifier queues once; never restart/rearm it or the old3s watcher, and no connectivity self-tests. Continue without waiting for a progress request.')
    with attempt.open('x',encoding='utf8') as f:json.dump(dict(utc=utc(),thread=thread,event=record['status'],message=message),f,indent=2)
    result=dict(utc=utc(),thread=thread,attempt=str(attempt),never_retries=True)
    try:
        q=subprocess.run([str(codex),'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as error:result.update(status='queue_uncertain_no_retry',error=repr(error))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),result)


def run():
    assert not STATE.exists() and not (TESTS/'outputs'/TAG).exists(), 'Never restart or overwrite an old run'
    gate=json.loads(ADMISSION.read_text());assert gate['passed'] and gate['visual_review_passed'];verify(gate)
    old=json.loads((TESTS/'logs/lian_release_r1_drained_gpu_c.run.json').read_text());assert old['exit_code']==0 and old['owned_exited'];verify(old)
    subprocess.run(['git','diff','--exit-code','--','src/source','src/VS'],cwd=REPO,check=True,capture_output=True)
    codex=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID'] and codex.is_file()
    # The three-second byte hashes bind this exact actual Release executable.
    exe=REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe'
    prior=json.loads((TESTS/'logs/lian_release_r1_drained.status.json').read_text())
    expected=next(e for e in prior['inputs'] if Path(e['path']).resolve()==exe.resolve())
    assert bound(exe)['sha256']==expected['sha256']
    batch=TESTS/'configs'/('x'+TAG+'_win64_GPU.bat')
    inputs=[bound(p) for p in [Path(__file__),TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_drained_review_r1.py',
        ADMISSION,TESTS/'notes/lian_late15_r1.json',TESTS/'configs'/(TAG+'_Def.xml'),batch,READER,exe,
        REPO/'bin/windows/GenCase_win64.exe',codex]]
    record=dict(status='running',stage='real_GPU_solver',owned_sequence_pid=os.getpid(),started_utc=utc(),inputs=inputs,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),duration_s=15,dt_s=DT,cadence_s=.05,
        single_dt_only=True,production_modified=False,formal_inputs_modified=False)
    def save():
        temporary=STATE.with_suffix('.tmp');write_json(temporary,record);os.replace(temporary,STATE)
    save()
    try:
        log=TESTS/'logs'/(TAG+'.log');start=time.perf_counter()
        with log.open('xb') as f:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(batch)],cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            record['owned_wrapper_pid']=child.pid;save();code=child.wait()
        record.update(solver_exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-start,log=bound(log));save()
        assert code==0 and 'Finished execution (code=0)' in log.read_text(errors='replace'), 'Real solver/BAT did not complete'
        folder=TESTS/'outputs'/TAG;parts=sorted((folder/'data').glob('Part_*.bi4'))
        record['saved_frames']=len(parts)
        end=native(folder,int(parts[-1].stem.split('_')[-1]));record['actual_final_time_s']=float(end.time_s.iloc[0])
        record['outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()];record['stage']='native_output_checks';save()
        assert len(parts)==301 and abs(record['actual_final_time_s']-15)<2e-5
        text=(folder/'Run.out').read_text(errors='replace')
        hardware=re.search(r'Device default:.*',text);assert hardware;record['actual_GPU']=hardware[0]
        initial=native(folder,0);assert len(initial)==20301 and initial.position_double.eq(1).all() and initial.stress_double.eq(1).all()
        rows=[];prefix=[]
        for i in range(len(parts)):
            a=native(folder,i);t=float(a.time_s.iloc[0]);record['last_checked_time_s']=t
            row=describe(a,initial)
            active=t-DT>=1 and i>0
            assert active==row['drainage_evaluated_active'], ('Boundary event interpretation changed',i,t)
            row['prior_step_time_estimate_s']=t-DT
            row.update(part=i,loaded_count=int(a.load_az.abs().gt(0).sum()))
            assert a.load_available.eq(1).all() and a.position_double.eq(1).all() and a.stress_double.eq(1).all()
            if i<=60:
                reference=native(CONTROL,i)
                exact_time=float(reference.time_s.iloc[0])==t
                exact_step=int(reference.saved_step.iloc[0])==int(a.saved_step.iloc[0])
                if exact_time and exact_step:
                    assert np.array_equal(a.to_numpy(),reference.to_numpy()), ('Native same-dt prefix not0ULP',i)
                    prefix.append(dict(part=i,time_s=t,saved_step=int(a.saved_step.iloc[0]),all_fields_0ulp=True))
                else:
                    assert i==60, ('Nonfinal prefix time/step changed',i)
            rows.append(row)
            if i%20==0:save()
        assert len(prefix)>=60
        csv=TESTS/'figures'/(TAG+'_history.csv');pd.DataFrame(rows).to_csv(csv,index=False,float_format='%.17g')
        prefix_csv=TESTS/'figures'/(TAG+'_prefix.csv');pd.DataFrame(prefix).to_csv(prefix_csv,index=False,float_format='%.17g')
        for e in inputs:assert bound(e['path'])['sha256']==e['sha256'], e['path']
        record.update(status='completed_pending_review',stage='native_checks_passed_pending_late_physical_review',native_prefix0ulp_frames=len(prefix),
            artifacts=[bound(csv),bound(prefix_csv)],finished_utc=utc(),final_native_row=rows[-1])
    except Exception as error:
        record.update(status='rejected_or_interrupted',error=repr(error),finished_utc=utc())
    finally:
        save()
        with (TESTS/'logs'/(TAG+'.run.json')).open('x',encoding='utf8') as f:json.dump(record,f,indent=2,allow_nan=False)
        notify(record,codex,thread)
    print(record['status'],record.get('error',''),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);a=p.parse_args()
    (prepare if a.action=='prepare' else run)()
