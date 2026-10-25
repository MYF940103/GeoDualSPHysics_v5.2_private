"""One fresh15s coarse/half candidate pair; no prior worker or PART restart."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,TESTS,REPO,READER,bound,native,write_json,utc,pair
from lian_drained_review_r1 import verify
from lian_mirror_review_r1 import sample

TAG='lian_mirror15_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
ADMISSION=TESTS/'logs/lian_mirror_review_r1.check.json'
PROGRAM=TESTS/'outputs/lian_mirror_build_r1/DualSPHysics5.2_GEO_win64.exe'


def prepare():
    gate=json.loads(ADMISSION.read_text());assert gate['passed'] and gate['visual_review_passed']
    for suffix in ['c','h']:
        old='lian_mirror_short_r2_drained_'+suffix;new=TAG+'_'+suffix
        for oldfile,newfile in [(old+'_Def.xml',new+'_Def.xml'),('x'+old+'_win64.bat','x'+new+'_win64.bat')]:
            target=TESTS/'configs'/newfile;assert not target.exists() and not (TESTS/'outputs'/new).exists()
            text=(TESTS/'configs'/oldfile).read_text(encoding='utf8').replace(old,new)
            if newfile.endswith('.xml'):
                text,count=re.subn(r'(<parameter key="TimeMax" value=")[^"]+',lambda m:m[1]+'15',text);assert count==1
                text=text.replace('Mirrored-footprint candidate short admission; not late/full-cycle acceptance','Mirrored-footprint15s late-window pair; not100s or FEM acceptance')
            target.write_text(text.replace('\n','\r\n'),encoding='utf8',newline='')
    print('Prepared fresh15s coarse/half; only duration changes from accepted3s inputs')


def notify(record):
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID']
    message=(f'User-authorized same-thread Lian mirrored-contact15s continuation {TAG}, not a new human observation. Detected '+record['status']+'. '
        f'Read {STATE}, queue_attempt/notification, tests/notes/lian_mirror15_r1.json and logs/lian_mirror_review_r1.check.json plus parent validation/poromech_next_r1.json. '
        'Only fresh actualGPURelease15s coarse10us thenhalf5us, output.05s/301native frames each, original mixedmDBC/strict rightedge/q10kPa/ramp1s/13nodequadrature/eta.04/dp.1/k1e-3/stressdouble-porefloat/SPR-HGoff were admitted. Mode4 alone mirrors x0 footprint abs(x)<=1.25. '
        'Verify actualRTX3050 hardware/ownedexits/native20301IDs/actualfinaltimes/all source-build-input-runtime-output hashes, original finite/elastic/noexclusion/geometry/naturalstep and allactive FSType2/3 drainage. Preserve original all301sample5Pa/.005mm independent half bounds and13000N/m postramp resultant with original source-clock timing. '
        'Review each complete same-dt3s shared exact-time/step prefix0ULP; disclose final-only unmatched save if any, never interpolate or omit physical fields. No later run is admitted if a prior check failed. '
        'Inspect native pressure/material settlement/stress/speed and1744x/contact/load/drain history through strict12.4/14.1s events; compare strict15s ac5dec9 retained actual matched times, not legacyfloat as precision-only truth. Generate and inspect fresh PNGs AND CSVs. '
        'Strict control had1000N/m loss and minimum-3211.99Pa. New3s short pair passed.0112047Pa/.0000128985mm, not proof of late repair. This15s pair is not100s/FEM/generalcontact acceptance. Original13node load width remains+4percent; do not silently rescale it or enable newSPR/HG/damping. '
        'If solver completed but new checking failed, preserve it and repair only new offline analysis. If runtime interrupted inspect exact sealedtime/reason and survivors; no duplicate solvers, overwritten evidence, relaxed thresholds or oldworker restart. '
        'Proactively report quantified Chinese outcome and continue justified diagnosis; on physical acceptance prepare independent root formalXML/BAT and actually execute complete paper100s plus native comparison PNG/CSV. Save every verified stage selectively local AND remoteGit, verify refs; rawBI4/executables are not cloudGit. '
        'Canonical strictGPU control remains unchanged; candidateGPU is under outputs/lian_mirror_build_r1. Continue scopedYao/Cryer/slope delivery, no case02 rewrites/KEEP/u-pl/TPI. This genuinely new stage queues exactlyonce; never rearm/restart anyold/current worker or send selftests. Continue without progress prompting.')
    attempt=TESTS/'logs'/(TAG+'.queue_attempt.json')
    with attempt.open('x',encoding='utf8') as f:json.dump(dict(event=record['status'],thread=thread,message=message,utc=utc()),f,indent=2)
    try:
        exe=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
        q=subprocess.run([str(exe),'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        outcome=dict(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as error:outcome=dict(status='queue_uncertain_no_retry',error=repr(error))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),outcome)


def run():
    assert not STATE.exists() and not (TESTS/'logs'/(TAG+'.queue_attempt.json')).exists()
    assert os.environ.get('CODEX_THREAD_ID') and os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']
    gate=json.loads(ADMISSION.read_text());assert gate['passed'] and gate['visual_review_passed'];verify(gate)
    oldpath=TESTS/'logs/lian_mirror_short_r2.status.json';old=json.loads(oldpath.read_text());verify(old)
    assert old['status']=='short_gates_passed_pending_physical_review'
    buildpath=TESTS/'logs/lian_mirror_build_r1.json';build=json.loads(buildpath.read_text(encoding='utf-8-sig'));verify(build)
    expected=next(e for e in build['programs'] if Path(e['path']).resolve()==PROGRAM.resolve())
    assert bound(PROGRAM)['sha256'].lower()==expected['sha256'].lower()
    runtimepath=TESTS/'logs/lian_mirror_runtime_r1.json';runtime=json.loads(runtimepath.read_text(encoding='utf-8-sig'))
    for e in runtime['files']:assert bound(e['path'])['sha256'].lower()==e['sha256'].lower()
    inputs=[bound(p) for p in [Path(__file__),TESTS/'scripts/lian_mirror_review_r1.py',TESTS/'scripts/lian_release_r1.py',
        TESTS/'scripts/lian_drained_review_r1.py',TESTS/'notes/lian_mirror15_r1.json',ADMISSION,oldpath,buildpath,runtimepath,PROGRAM,READER,REPO/'bin/windows/GenCase_win64.exe']]
    inputs += [bound(e['path']) for e in build['inputs']]+[bound(e['path']) for e in runtime['files']]
    for suffix in ['c','h']:
        inputs += [bound(TESTS/'configs'/(TAG+'_'+suffix+'_Def.xml')),bound(TESTS/'configs'/('x'+TAG+'_'+suffix+'_win64.bat')),
            bound(TESTS/'logs'/('lian_mirror_short_r2_drained_'+suffix+'.run.json'))]
    record=dict(status='running',started_utc=utc(),owned_sequence_pid=os.getpid(),inputs=inputs,runs=[],
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),physical_full_cycle_accepted=False)
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,record);os.replace(tmp,STATE)
    save()
    try:
        for suffix,dt in [('c',1e-5),('h',5e-6)]:
            name=TAG+'_'+suffix;folder=TESTS/'outputs'/name;assert not folder.exists()
            reference=TESTS/'outputs'/('lian_mirror_short_r2_drained_'+suffix)
            ref=json.loads((TESTS/'logs'/('lian_mirror_short_r2_drained_'+suffix+'.run.json')).read_text());assert ref['exit_code']==0;verify(ref)
            record['current_run']=name;log=TESTS/'logs'/(name+'.log');start=time.perf_counter()
            with log.open('xb') as f:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64.bat'))],cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                record['owned_wrapper_pid']=child.pid;save();code=child.wait()
            item=dict(name=name,exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-start,log=bound(log));record['runs'].append(item)
            parts=sorted((folder/'data').glob('Part_*.bi4'));item['saved_frames']=len(parts)
            if parts:item['actual_final_time_s']=float(native(folder,int(parts[-1].stem.split('_')[-1])).time_s.iloc[0])
            item['outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()];save()
            text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
            assert code==0 and 'Finished execution (code=0)' in text,name
            item['actual_GPU']=re.search(r'Device default:.*',text)[0]
            assert len(parts)==301 and abs(item['actual_final_time_s']-15)<2e-5
            initial=native(folder,0);rows=[];prefix=[]
            for i in range(301):
                a=native(folder,i);row=sample(a,initial,dt,True);row['part']=i;rows.append(row)
                if i<=60:
                    b=native(reference,i);same=float(a.time_s.iloc[0])==float(b.time_s.iloc[0]) and int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0])
                    if same:assert np.array_equal(a.to_numpy(),b.to_numpy()),('Same-time/step native prefix',i)
                    else:assert i==60,('Nonfinal prefix time changed',i)
                    prefix.append(dict(part=i,long_time_s=float(a.time_s.iloc[0]),short_time_s=float(b.time_s.iloc[0]),shared_all_fields0ulp=same))
                if i%30==0:item['last_checked_time_s']=row['time_s'];save()
            assert sum(e['shared_all_fields0ulp'] for e in prefix)>=60
            artifacts=[]
            for label,frame in [('history',pd.DataFrame(rows)),('prefix',pd.DataFrame(prefix))]:
                csv=TESTS/'figures'/(name+'_'+label+'.csv');frame.to_csv(csv,index=False,float_format='%.17g');artifacts.append(bound(csv))
            item.update(artifacts=artifacts,prefix0ulp_shared_frames=sum(e['shared_all_fields0ulp'] for e in prefix),all_saved_native_checks_passed=True)
            write_json(TESTS/'logs'/(name+'.run.json'),item);save()
        frame,passed=pair(TESTS/'outputs'/(TAG+'_c'),TESTS/'outputs'/(TAG+'_h'))
        csv=TESTS/'figures'/(TAG+'_half.csv');frame.to_csv(csv,index=False,float_format='%.17g')
        record['half']=dict(passed=passed,sample_pairs=len(frame),pressure_rms_max_pa=float(frame.pressure_rms_difference_pa.max()),top_material_max_mm=float(frame.top_material_max_difference_mm.max()),artifact=bound(csv))
        assert passed,('Original full301-sample half limits',record['half'])
        for e in inputs:assert bound(e['path'])['sha256']==e['sha256'],e['path']
        record.update(status='pair_passed_pending_late_physical_review',finished_utc=utc())
    except Exception as error:record.update(status='rejected_or_interrupted',error=repr(error),finished_utc=utc())
    finally:save();notify(record)
    print(record['status'],record.get('error',''),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args()
    (prepare if args.action=='prepare' else run)()
