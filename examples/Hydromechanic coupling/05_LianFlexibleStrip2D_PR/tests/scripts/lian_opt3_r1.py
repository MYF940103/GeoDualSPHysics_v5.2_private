"""Bounded one-option Lian matrix; original mixed-slip boundaries are fixed."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,TESTS,REPO,READER,bound,native,write_json,utc
from lian_mirror_review_r1 import sample
sys.path.insert(0,str(CASE/'support'))
from postprocess_lian_release import weights

TAG='lian_opt3_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
VARIANTS={'grad':{'SoilStressRateGradCorr':'1'},'d0':{'SoilDamping':'0'},
          'd02':{'SoilDampingCoef':'0.02'},'d08':{'SoilDampingCoef':'0.08'}}
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')


def notify(record):
    thread=os.environ['CODEX_THREAD_ID']
    assert thread==os.environ['CODEX_SESSION_ID']
    message=(f'User-authorized same-thread Lian supported-option3s matrix {TAG}, not a new human observation. '
        f'Detected {record["status"]}. Read {STATE}, its queue_attempt/notification, tests/notes/lian_opt3_r1.json, '
        'logs/lian_formal100_r1.user_stop.json and .user_stop_native.json plus parent validation/poromech_next_r2.json. '
        'The user STOPPED old formal100s and requested3s SPR/hourglass/stress-rate-gradient/damping comparisons, '
        'then stable-current fallback for a NEW formal run if differences persist. Paper SPH/FEM is a numerical reference, '
        'not automatically ground truth; do not tune solely to match colors or declare either method wrong from a picture. '
        'This FIRST matrix admits only supported options: one2ms CPU Debug grad smoke, then four independent GPU '
        '.15s smoke/3s pairs at10us: grad1 only, damping off only,eta.02 only,eta.08 only. Baseline eta.04/grad0 is retained '
        'lian_mirror15_r1_c through3s, not rerun. Each full run is invalid if its own smoke failed; other independent variants '
        'are not thereby invalidated. Verify exact owned exits/actualtimes/native20301IDs/input-program-output hashes, '
        'original finite/elastic/no-exclusion/geometry/natural-step, all active FSType2/3 drainage and source-clock13-node '
        '13000N/m force. XML AND Run.out must preserve side mkbound0 FreeSlip and bottom mkbound1 NoSlip. '
        'Inspect exact matching .15s prefixes and any rejected/skipped variants; no half-step or physical acceptance is implied. '
        'Generate/inspect paper Fig10 .5/1/3s PNGs AND CSVs using row limits5/5/1.75kPa and original palette/crops '
        'from lian_fig10_first3_r1; no smoothing/clipping/rescaling, record over-range native fractions. Compare pressure, '
        'paper-position A/B material settlement, side normal and bottom normal/tangent displacement,total stress/speed '
        'and baseline changes at actual matched times. Cross-option differences are NOT5Pa half errors. '
        'OutstandingSPR: current source explicitly rejects per-mk mixed slip; opposite side walls share mkbound0 and '
        '417 normals are zero. Need independent per-face/planar-normal OFF control and per-face NoSlip/FreeSlip CPU/GPU '
        'validation; do not remove the guard blindly or change all walls to one slip. OutstandingHG: current GNOG '
        'cell wrap/minimum-image is x-periodic only, Lian is not periodic. Real nonperiodic neighbors plus affine-null/'
        'conservation/energy/old-periodic regressions are prerequisites; never fake periodicity or silently call it tested. '
        'Continue the justified bounded compatibility work and candidate independent half checks before any long-run decision; '
        'do not expand without bounds merely to fit the paper. User accepts choosing stable current behavior if genuine '
        'reference differences persist after controlled comparisons. Old formal100s stopped at10.90001s/219frames, '
        'is NOT complete and its worker/queue are retired; never restart/rearm or overwrite partial outputs. '
        'On solver/check failure report exact reason/time/survivors and retain evidence; completed-solver analysis failure '
        'needs offline repair, not duplicate solves or relaxed guards. Report Chinese results proactively, selectively '
        'save each verified stage local/remoteGit and verify refs; rawBI4/executables are not cloudGit. '
        'No case02/KEEP/u-pl/TPI/Yao/slope reopening. After Lian comes Cryer then self-weight. '
        'This genuinely new worker queues once; no recursive rearm or connectivity test. Continue without progress prompting.')
    with (TESTS/'logs'/(TAG+'.queue_attempt.json')).open('x',encoding='utf8') as f:
        json.dump(dict(event=record['status'],thread=thread,utc=utc(),message=message),f,indent=2)
    try:
        q=subprocess.run([str(CODEX),'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,
            creationflags=subprocess.CREATE_NO_WINDOW)
        result=dict(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,
            reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as error:
        result=dict(status='queue_uncertain_no_retry',error=repr(error))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),result)


def main():
    assert not STATE.exists()
    assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID'] and CODEX.is_file()
    stopped=json.loads((TESTS/'logs/lian_formal100_r1.status.json').read_text())
    assert stopped['status']=='user_stopped' and stopped['owned_processes_stopped']
    baseline_xml=ET.parse(TESTS/'configs/lian_mirror15_r1_c_Def.xml')
    basevals={e.attrib['key']:e.attrib['value'] for e in baseline_xml.findall('.//parameters/parameter')}
    jobs=[('grad','debug',.002,.001,3)]
    jobs += [(v,s,t,c,n) for v in VARIANTS for s,t,c,n in [('smoke',.15,.005,31),('3s',3.,.05,61)]]
    inputs=[bound(p) for p in [__file__,READER,TESTS/'scripts/lian_release_r1.py',
        TESTS/'scripts/lian_mirror_review_r1.py',CASE/'support/postprocess_lian_release.py',
        TESTS/'notes/lian_opt3_r1.json',TESTS/'logs/lian_formal100_r1.user_stop.json',
        TESTS/'logs/lian_formal100_r1.user_stop_native.json',REPO/'bin/windows/GenCase_win64.exe',
        REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe',REPO/'bin/windows/DualSPHysics5.2CPU_win64_debug.exe',
        TESTS/'logs/lian_mirror15_r1_c.run.json',TESTS/'logs/lian_mirror_build_r1.json',
        TESTS/'logs/lian_mirror_runtime_r1.json',CODEX]]
    runtime=json.loads((TESTS/'logs/lian_mirror_runtime_r1.json').read_text(encoding='utf-8-sig'))
    for item in runtime['files']:
        path=REPO/'bin/windows'/Path(item['path']).name
        current=bound(path)
        assert current['sha256'].lower()==item['sha256'].lower()
        inputs.append(current)
    for variant,stage,duration,cadence,count in jobs:
        name=f'{TAG}_{variant}_{stage}'
        config=TESTS/'configs'/(name+'_Def.xml')
        xml=ET.parse(config)
        values={e.attrib['key']:e.attrib['value'] for e in xml.findall('.//parameters/parameter')}
        changed={k for k in values if float(values[k])!=float(basevals[k])}
        expected_changes=set(VARIANTS[variant])|{'TimeMax'}
        if cadence!=float(basevals['TimeOut']):
            expected_changes.add('TimeOut')
        assert changed==expected_changes, (name,changed,expected_changes)
        assert float(values['DtFixed'])==1e-5 and float(values['TimeMax'])==duration
        assert float(values['TimeOut'])==cadence
        assert {int(e.attrib['mkbound']):int(e.attrib['slipmode']) for e in xml.findall('.//mdbcslip/bound')}=={0:3,1:2}
        for k,v in VARIANTS[variant].items():
            assert values[k]==v
        assert not (TESTS/'outputs'/name).exists()
        inputs += [bound(config),bound(TESTS/'configs'/('x'+name+'_win64.bat'))]
    expected='674f4f37d08ac351b2660e4649ffcca7f17652934356e0de34a718be62ba5845'
    assert bound(REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe')['sha256']==expected
    state=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),runs=[],
        half_step_accepted=False,physical_accepted=False,SPR_tested=False,HG_tested=False)

    def save():
        tmp=STATE.with_suffix('.tmp')
        write_json(tmp,state)
        os.replace(tmp,STATE)

    save()
    try:
        for variant,stage,duration,cadence,count in jobs:
            name=f'{TAG}_{variant}_{stage}'
            if stage=='3s' and not next(r for r in state['runs'] if r['name']==f'{TAG}_{variant}_smoke')['passed']:
                state['runs'].append(dict(name=name,passed=False,status='not_launched_own_smoke_failed'))
                save();continue
            item=dict(name=name,variant=variant,stage=stage,passed=False)
            state['runs'].append(item)
            folder=TESTS/'outputs'/name
            state['current_run']=name
            log=TESTS/'logs'/(name+'.log')
            rows,prefix=[],[]
            child=None
            started=time.perf_counter()
            save()
            try:
                with log.open('xb') as f:
                    child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64.bat'))],
                        cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                    item['owned_wrapper_pid']=child.pid
                    save()
                    checked=0
                    initial=None
                    while True:
                        exit_code=child.poll()
                        parts=sorted((folder/'data').glob('Part_*.bi4'))
                        available=len(parts) if exit_code is not None else max(0,len(parts)-1)
                        while checked<available:
                            a=native(folder,checked)
                            if initial is None:
                                initial=a
                                assert initial.pressure.eq(0).all()
                            row=sample(a,initial,1e-5,True)
                            row['part']=checked
                            for label,point in [('A',(0.,10.)),('B',(1.25,8.75))]:
                                stencil=weights(initial,*point)
                                row['paper_'+label+'_pressure_pa']=sum(w*float(a.pressure.iloc[k]) for k,w in stencil)
                                row['paper_'+label+'_settlement_mm']=1000*sum(w*float(initial.z.iloc[k]-a.z.iloc[k]) for k,w in stencil)
                            for label,mask,col in [('left_normal',np.isclose(initial.x,0,rtol=0,atol=1e-9),'x'),
                                ('right_normal',np.isclose(initial.x,20,rtol=0,atol=1e-9),'x'),
                                ('bottom_normal',np.isclose(initial.z,0,rtol=0,atol=1e-9),'z'),
                                ('bottom_tangent',np.isclose(initial.z,0,rtol=0,atol=1e-9),'x')]:
                                assert mask.any()
                                row[label+'_max_mm']=1000*float(abs(a.loc[mask,col]-initial.loc[mask,col]).max())
                            row['total_sigma_zz_rms_pa']=float(np.sqrt(np.mean((a.sigma_zz-a.pressure)**2)))
                            row['pressure_max_pa']=float(a.pressure.max())
                            rows.append(row)
                            if stage=='3s' and checked<=3:
                                ref=native(TESTS/'outputs'/f'{TAG}_{variant}_smoke',checked*10)
                                shared=float(a.time_s.iloc[0])==float(ref.time_s.iloc[0]) and int(a.saved_step.iloc[0])==int(ref.saved_step.iloc[0])
                                if shared:
                                    assert list(a.columns)==list(ref.columns) and np.array_equal(a.to_numpy(),ref.to_numpy())
                                else:
                                    assert checked==3, ('Nonfinal smoke prefix mismatch',name,checked)
                                prefix.append(dict(part=checked,time_s=row['time_s'],reference_time_s=float(ref.time_s.iloc[0]),all_fields0ulp=shared))
                            checked+=1
                        item.update(checked_frames=checked,last_checked_time_s=rows[-1]['time_s'] if rows else None)
                        save()
                        if exit_code is not None:
                            break
                        time.sleep(15)
                item.update(exit_code=exit_code,owned_exited=True,wall_seconds=time.perf_counter()-started,saved_frames=len(parts))
                text=(folder/'Run.out').read_text(errors='replace')
                item['solver_finished']='Finished execution (code=0)' in text
                assert exit_code==0 and item['solver_finished']
                assert re.search(r'mkbound:\s*0\s*->\s*Free slip',text) and re.search(r'mkbound:\s*1\s*->\s*No-slip',text)
                item['actual_GPU']=re.search(r'Device default:.*',text)[0] if stage!='debug' else 'CPU Debug8'
                assert len(rows)==count and abs(rows[-1]['time_s']-duration)<2e-5
                if stage=='3s':
                    assert sum(p['all_fields0ulp'] for p in prefix)>=3
                artifacts=[]
                for label,frame in [('history',pd.DataFrame(rows)),('prefix',pd.DataFrame(prefix))]:
                    if frame.empty:
                        continue
                    path=TESTS/'figures'/(name+'_'+label+'.csv')
                    assert not path.exists()
                    frame.to_csv(path,index=False,float_format='%.17g')
                    artifacts.append(bound(path))
                item.update(passed=True,status='native_checks_passed_pending_reference_review',actual_final_time_s=rows[-1]['time_s'],artifacts=artifacts)
            except Exception as error:
                if child is not None and child.poll() is None:
                    stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
                    item['owned_tree_stop_exit']=stop.returncode
                    child.wait(timeout=15)
                item.update(status='candidate_rejected_or_interrupted',error=repr(error))
            item['outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()] if folder.exists() else []
            if log.exists():
                item['log']=bound(log)
            write_json(TESTS/'logs'/(name+'.run.json'),item)
            save()
            if stage=='debug':
                assert item['passed'], 'CPU Debug prerequisite failed; no GPU jobs admitted'
            for e in inputs:
                assert bound(e['path'])['sha256']==e['sha256'],e['path']
        state.update(status='matrix_completed_pending_review' if all(r['passed'] for r in state['runs']) else
            'matrix_completed_with_rejected_candidates_pending_review',finished_utc=utc())
    except Exception as error:
        state.update(status='sequence_rejected_or_interrupted',error=repr(error),finished_utc=utc())
    finally:
        save()
        notify(state)
    print(state['status'],state.get('error',''),flush=True)


if __name__=='__main__':
    main()
