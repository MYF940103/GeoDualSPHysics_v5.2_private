"""One fresh actual root release BAT; saved-native guards and one terminal queue."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, bound, native, write_json, utc
from lian_drained_review_r1 import verify
from lian_mirror_review_r1 import sample

TAG='lian_formal100_r1'
NAME='CaseLianFlexibleStrip2D_PR_release'
STATE=TESTS/'logs'/(TAG+'.status.json')
GATE=TESTS/'logs/lian_mirror15_review_r1.check.json'
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')


def notify(record):
    thread=os.environ['CODEX_THREAD_ID']
    assert thread==os.environ['CODEX_SESSION_ID']
    message=(f'User-authorized same-thread Lian actual formal100s continuation {TAG}, not a new human observation. '
        f'Detected {record["status"]}. Read {STATE}, its queue_attempt/notification, tests/notes/lian_formal100_r1.json, '
        'logs/lian_mirror15_review_r1.check.json and parent validation/poromech_next_r2.json (latest user plan). '
        'Only a fresh actual root xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat was admitted:100s,dt10us,output.05s/2001frames, '
        'dp.1,k1e-3,q10kPa/ramp1s,original13-node+4percent quadrature,eta.04,mixedmDBC,mode4 abs(x)<=1.25, '
        'stressdouble/porefloat,SPR/HG/stress-gradient correction off. No old worker/PART restart. '
        'Verify owned exits/actualRTX3050/actualfinaltime/native20301IDs and all source-build-input-runtime-output hashes, '
        'original finite/elastic/noexclusion/geometry/natural-step/all-activeFSType2or3 drainage and13000N/m source-clock force. '
        'Check the complete same-time/step15s native prefix; disclose only a final-only unmatched save, no interpolation or field omission. '
        'Root BAT runs GenCase, actual Release solver, PartVTK fluid/bound and support/postprocess_lian_release.py. '
        'Native formal plots/CSVs are not SPH/FEM accuracy acceptance. Inspect every formal PNG/CSV and finish the requested '
        'paper Sec4.3 SPH and ABAQUS FEM comparison at A(0,10),B(1.25,8.75) and x0=1.25 displacement profile. '
        'A is native1744; B uses four initial-grid material IDs with bilinear weights, not the old nearest-node diagnostic. '
        'Paper references are raster figures; retain digitization provenance/uncertainty and never invent obscured curves. '
        'Quantify pressure build-up/late decay, settlement, stress/speed/contact/load and remaining differences; '
        '15s half-step is not full-cycle convergence, u-pl/TPI/dynamicDarcy/variable n-k are not implemented here. '
        'If solver completed but PartVTK/analysis failed, preserve it and repair only fresh postprocessing, never rerun the physical solver. '
        'On runtime/guard failure report exact actual sealedtime/reason and surviving owned processes; preserve all output, '
        'no duplicate solvers/relaxed gates/damping increases/old worker restart. '
        'Report Chinese results proactively and save each verified stage selectively local AND remoteGit with refs checked; '
        'rawBI4/executables are not cloudGit. Current user order is Lian then Cryer then01 self-weight consolidation. '
        'Yao and retrogressive slope are deferred; do not reopen accepted case02/KEEP/u-pl/TPI. '
        'After the three cases review with the user whether slope or u-pl comes next. '
        'This genuinely new stage queues once; never restart/rearm it or send connectivity tests. Continue without progress prompting.')
    with (TESTS/'logs'/(TAG+'.queue_attempt.json')).open('x',encoding='utf8') as f:
        json.dump(dict(event=record['status'],thread=thread,utc=utc(),message=message),f,indent=2)
    try:
        q=subprocess.run([str(CODEX),'queue','--thread',thread,'--message',message],capture_output=True,
            timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        outcome=dict(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,
            reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as error:
        outcome=dict(status='queue_uncertain_no_retry',error=repr(error))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),outcome)


def main():
    folder=CASE/(NAME+'_out')
    assert not STATE.exists() and not folder.exists()
    assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID'] and CODEX.is_file()
    gate=json.loads(GATE.read_text())
    assert gate['passed'] and gate['visual_review_passed'] and gate['late_contact_repair_accepted']
    verify(gate)
    program=REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe'
    candidate=TESTS/'outputs/lian_mirror_build_r1/DualSPHysics5.2_GEO_win64.exe'
    assert bound(program)['sha256']==bound(candidate)['sha256']
    runtime=json.loads((TESTS/'logs/lian_mirror_runtime_r1.json').read_text(encoding='utf-8-sig'))
    for item in runtime['files']:
        assert bound(item['path'])['sha256'].lower()==item['sha256'].lower()
    batch=CASE/('x'+NAME+'_win64_GPU.bat')
    inputs=[bound(p) for p in [__file__,GATE,TESTS/'notes/lian_formal100_r1.json',
        CASE/(NAME+'_Def.xml'),batch,CASE/'support/postprocess_lian_release.py',
        TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_mirror_review_r1.py',READER,program,
        REPO/'bin/windows/GenCase_win64.exe',REPO/'bin/windows/PartVTK_win64.exe',CODEX]]
    for item in runtime['files']:
        canonical=program.parent/Path(item['path']).name
        assert bound(canonical)['sha256'].lower()==item['sha256'].lower()
        inputs.append(bound(canonical))
    record=dict(status='running',stage='actual_formal_BAT',started_utc=utc(),owned_sequence_pid=os.getpid(),
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        duration_s=100,dt_s=1e-5,cadence_s=.05,inputs=inputs,physical_reference_accepted=False)

    def save():
        temporary=STATE.with_suffix('.tmp')
        write_json(temporary,record)
        os.replace(temporary,STATE)

    rows,prefix=[],[]
    child=None
    save()
    try:
        start=time.perf_counter()
        log=TESTS/'logs'/(TAG+'.log')
        with log.open('xb') as f:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(batch),'--unattended'],
                cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            record['owned_wrapper_pid']=child.pid
            save()
            initial=None
            checked=0
            while True:
                code=child.poll()
                parts=sorted((folder/'data').glob('Part_*.bi4'))
                # Leave the newest file alone until the BAT exits: no partial-frame reads.
                available=len(parts) if code is not None else max(0,len(parts)-1)
                while checked<available:
                    a=native(folder,checked)
                    if initial is None:
                        initial=a
                    row=sample(a,initial,1e-5,True)
                    row['part']=checked
                    rows.append(row)
                    if checked<=300:
                        b=native(TESTS/'outputs/lian_mirror15_r1_c',checked)
                        shared=(float(a.time_s.iloc[0])==float(b.time_s.iloc[0]) and
                            int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0]))
                        if shared:
                            assert list(a.columns)==list(b.columns) and np.array_equal(a.to_numpy(),b.to_numpy())
                        else:
                            assert checked==300, ('Nonfinal15s prefix mismatch',checked)
                        prefix.append(dict(part=checked,time_s=row['time_s'],reference_time_s=float(b.time_s.iloc[0]),
                            all_native_fields_0ulp=shared))
                    checked+=1
                record.update(last_checked_time_s=rows[-1]['time_s'] if rows else None,checked_frames=checked)
                save()
                if code is not None:
                    break
                time.sleep(30)
        record.update(BAT_exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-start,log=bound(log))
        text=(folder/'Run.out').read_text(errors='replace')
        record['solver_finished']=('Finished execution (code=0)' in text)
        record['actual_GPU']=re.search(r'Device default:.*',text)[0]
        record['actual_final_time_s']=float(native(folder,len(parts)-1).time_s.iloc[0])
        record['outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()]
        save()
        assert code==0 and record['solver_finished']
        assert len(rows)==2001 and abs(record['actual_final_time_s']-100)<2e-5
        assert sum(r['all_native_fields_0ulp'] for r in prefix)>=300
        artifacts=[]
        for name,frame in [('history',pd.DataFrame(rows)),('prefix',pd.DataFrame(prefix))]:
            path=TESTS/'figures'/(TAG+'_'+name+'.csv')
            assert not path.exists()
            frame.to_csv(path,index=False,float_format='%.17g')
            artifacts.append(bound(path))
        analysis=CASE/'figures/lian_release100_r1.check.json'
        result=json.loads(analysis.read_text())
        assert result['passed'] and result['saved_frames']==2001
        verify(result)
        for item in inputs:
            assert bound(item['path'])['sha256']==item['sha256'],item['path']
        record.update(status='formal100_completed_pending_reference_review',artifacts=artifacts+[bound(analysis)],
            prefix0ulp_frames=sum(r['all_native_fields_0ulp'] for r in prefix),finished_utc=utc())
    except Exception as error:
        if child is not None and child.poll() is None:
            # Only the still-owned Popen process tree, never all solver processes.
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            record['owned_tree_stop_exit']=stop.returncode
        record.update(status='rejected_or_interrupted',error=repr(error),finished_utc=utc())
    finally:
        save()
        write_json(TESTS/'logs'/(TAG+'.run.json'),record)
        notify(record)
    print(record['status'],record.get('error',''),flush=True)


if __name__=='__main__':
    main()
