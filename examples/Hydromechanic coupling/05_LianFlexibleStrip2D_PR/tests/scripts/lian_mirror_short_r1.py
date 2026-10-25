"""Fresh, gated mode4 mirror candidate: Debug smoke, .15s then3s GPU pairs."""
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

TAG='lian_mirror_short_r1'
BUILD=TESTS/'outputs/lian_mirror_build_r1'
STATE=TESTS/'logs'/(TAG+'.status.json')
SANITIZER=Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3\compute-sanitizer\compute-sanitizer.exe')
JOBS=[('cpu_debug','.00001','.002','.001'),('gpu_debug','.00001','.002','.001'),
      ('smoke_c','.00001','.15','.005'),('smoke_h','.000005','.15','.005'),
      ('drained_c','.00001','3','.05'),('drained_h','.000005','3','.05')]


def program(name):
    if name=='cpu_debug':return REPO/'bin/windows/DualSPHysics5.2CPU_win64_debug.exe'
    return BUILD/('DualSPHysics5.2_win64_debug.exe' if name=='gpu_debug' else 'DualSPHysics5.2_GEO_win64.exe')


def prepare():
    for suffix,dt,end,out in JOBS:
        name=TAG+'_'+suffix;xml=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64.bat')
        assert not xml.exists() and not bat.exists() and not (TESTS/'outputs'/name).exists()
        text=(TESTS/'configs/lian_release_r1_drained_gpu_c_Def.xml').read_text(encoding='utf8')
        for key,value in [('DtIni',dt),('DtFixed',dt),('TimeMax',end),('TimeOut',out)]:
            text,count=re.subn(r'(<parameter key="'+key+r'" value=")[^"]+',lambda m:m[1]+value,text);assert count==1
        text=text.replace('Short admission across the original 1 s load-ramp and drainage event; not full dissipation','Mirrored-footprint candidate short admission; not late/full-cycle acceptance')
        text=text.replace('Retain original 0.05 s cadence for the coarse and half-step comparison','Native short-window cadence; no special timeout or fixed-grid drainage')
        xml.write_text(text,encoding='utf8')
        template=(TESTS/'configs/xlian_release_r1_drained_gpu_c_win64.bat').read_text(encoding='utf8')
        template=template.replace('lian_release_r1_drained_gpu_c',name)
        template=re.sub(r'set dualsphysics=.*',lambda _:f'set dualsphysics="{program(suffix)}"',template)
        if suffix=='cpu_debug':template=template.replace('-gpu -stable','-cpu -ompthreads:8 -stable')
        if suffix=='gpu_debug':template=template.replace('%dualsphysics% -gpu',f'"{SANITIZER}" --tool memcheck --error-exitcode 99 %dualsphysics% -gpu')
        bat.write_text(template.replace('\n','\r\n'),encoding='utf8',newline='')
    print('Prepared6 independent XML/BAT pairs; no solver launched')


def inspect(folder,dt,end,cadence):
    initial=native(folder,0);ids=initial.id.to_numpy();rows=[]
    assert len(initial)==20301
    parts=sorted((folder/'data').glob('Part_*.bi4'));assert len(parts)==round(end/cadence)+1
    for i in range(len(parts)):
        a=native(folder,i);t=float(a.time_s.iloc[0]);fs=a.fstype.isin([2,3]);drained=fs&a.x.abs().gt(1.25)
        assert np.array_equal(a.id,ids) and np.isfinite(a.to_numpy()).all()
        assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all()
        assert a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.nout.eq(0).all()
        assert a.x.between(-.1,20.1).all() and a.z.between(-.1,10.1).all()
        if i:
            assert a.has_dterror.eq(1).all() and a.dterror_s.le(1e-14).all(),('Original natural step',i)
        if t-dt>=1:
            assert drained.any() and a.pressure[drained].eq(0).all(),('Original drain pressure',i)
        force=float(-(a.mass*a.load_az).sum());expected=13000*min(1,max(0,t-dt))
        assert abs(force-expected)<.002,('Unchanged13-node ramp force',i,force,expected)
        w=a[a.id.eq(1744)].iloc[0]
        rows.append(dict(part=i,time_s=t,pressure_mean_pa=float(a.pressure.mean()),pressure_min_pa=float(a.pressure.min()),
            top_mean_settlement_mm=1000*float((initial.z[initial.z.gt(9.99)].to_numpy()-a.z[initial.z.gt(9.99)].to_numpy()).mean()),
            actual_force_N_m=force,expected_source_time_force_N_m=expected,loaded_count=int(a.load_az.abs().gt(0).sum()),
            true_drained_nodes=int(drained.sum()),drained_max_pa=float(a.pressure[drained].abs().max()) if drained.any() else 0,
            id1744_x_m=float(w.x),id1744_pressure_pa=float(w.pressure)))
    assert abs(rows[-1]['time_s']-end)<2e-5
    return pd.DataFrame(rows)


def notify(record):
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID']
    codex=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
    message=(f'User-authorized same-thread Lian mirror short diagnostic {TAG}, not a new human observation. Detected '+record['status']+'. '
        f'Read {STATE}, its queue_attempt/notification, tests/notes/lian_mirror_r1.json, logs/lian_late15_review_r1.check.json and parent validation/poromech_next_r1.json. '
        'Only mode4 footprint CPU/GPU changed from x>=0&&x<=1.25 to abs(x)<=1.25 to mirror the strip across its free-slip x0 face. Physical in-domain strip, q,13-node quadrature, original mixed mDBC, SPR/HGoff, stress double/pore float remain. '
        'Verify all owned exits/native IDs/actual times/source-input-build-output hashes, DebugCPU/GPU .002s smoke and GPU memcheck zero errors, real GPU Release .15s then3s coarse10us/half5us in gated order. '
        'Original full-history5Pa/.005mm independent half limits, natural-step/elastic/finite/no-exclusion/geometry/all-direction FSType2/3 drainage remain; new drain footprint is mirrored and actual source-clock event is not fixed-grid aligned. '
        'Verify actual13-node force13000N/m after ramp and ramp timing. Check saved candidate-vs-strict same-dt native differences, do not presume0ULP or Debug/Release equivalence. '
        'On any prior failure do not admit later data. Inspect actual reason/time and survivors, preserve evidence and repair without relaxed gates/raised damping/duplicate or old workers. Completed solver plus failed new analysis needs offline repair, not rerun. '
        'On pass inspect new/strict comparison PNGs AND CSVs and report quantified Chinese short outcome. A short pass does NOT prove late repair; continue justified fresh15s coarse/half checking12.4/14.1s switching before formal100s root XML/BAT actual run. '
        'Strict15s had minimumpressure-3211.99Pa and repeated1000N/m loss; legacy firstswitch14.1s, current12.4s. The frozen mirror comparison altered only native1744, not a repaired trajectory. '
        'Candidate GPU executables live in tests/outputs/lian_mirror_build_r1; old canonical GPU Release remains unchanged; old CPU Debug executable was copied and hash verified before rebuild. '
        'Selectively commit/push verified stages; raw executables/BI4 are not cloud backed. Continue existing Yao/Cryer/slope plan, no KEEP/u-pl/TPI, no case02 rewrites, no full2D/FEM/general-contact acceptance. This integrated notifier queues exactlyonce: never restart/rearm or send self-tests. Continue without progress prompting.')
    attempt=TESTS/'logs'/(TAG+'.queue_attempt.json')
    with attempt.open('x',encoding='utf8') as f:json.dump(dict(utc=utc(),thread=thread,event=record['status'],message=message),f,indent=2)
    try:
        q=subprocess.run([str(codex),'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        outcome=dict(status='queued' if q.returncode==0 else 'queue_failed_no_retry',exit_code=q.returncode,reply=(q.stdout+q.stderr).decode(errors='replace'))
    except Exception as error:outcome=dict(status='queue_uncertain_no_retry',error=repr(error))
    write_json(TESTS/'logs'/(TAG+'.notification.json'),outcome)


def run():
    assert not STATE.exists() and not (TESTS/'logs'/(TAG+'.queue_attempt.json')).exists()
    buildpath=TESTS/'logs/lian_mirror_build_r1.json';b=json.loads(buildpath.read_text(encoding='utf-8-sig'));assert b['built'];verify(b)
    for item in b['programs']:assert bound(item['path'])['sha256'].lower()==item['sha256'].lower()
    priorpath=TESTS/'logs/lian_late15_review_r1.check.json';g=json.loads(priorpath.read_text());assert g['passed'] and g['visual_review_passed'];verify(g)
    inputs=[bound(p) for p in [Path(__file__),TESTS/'notes/lian_mirror_r1.json',priorpath,buildpath,READER,SANITIZER,
        TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_drained_review_r1.py',REPO/'bin/windows/GenCase_win64.exe']]
    for suffix,*_ in JOBS:inputs += [bound(TESTS/'configs'/(TAG+'_'+suffix+'_Def.xml')),bound(TESTS/'configs'/('x'+TAG+'_'+suffix+'_win64.bat')),bound(program(suffix))]
    record=dict(status='running',owned_sequence_pid=os.getpid(),started_utc=utc(),inputs=inputs,runs=[],pairs=[],
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),physical_full_cycle_accepted=False)
    def save():
        temporary=STATE.with_suffix('.tmp');write_json(temporary,record);os.replace(temporary,STATE)
    save()
    try:
        for suffix,dt,end,cadence in JOBS:
            name=TAG+'_'+suffix;folder=TESTS/'outputs'/name;assert not folder.exists()
            record['current_run']=name;log=TESTS/'logs'/(name+'.log');start=time.perf_counter()
            with log.open('xb') as f:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64.bat'))],cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                record['owned_wrapper_pid']=child.pid;save();code=child.wait()
            item=dict(name=name,exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-start,log=bound(log));record['runs'].append(item);save()
            assert code==0 and 'Finished execution (code=0)' in log.read_text(errors='replace'),name
            if suffix=='gpu_debug':assert 'ERROR SUMMARY: 0 errors' in log.read_text(errors='replace')
            parts=sorted((folder/'data').glob('Part_*.bi4'));item['actual_final_time_s']=float(native(folder,int(parts[-1].stem.split('_')[-1])).time_s.iloc[0])
            item['outputs']=[bound(p) for p in folder.rglob('*') if p.is_file()];save()
            history=inspect(folder,float(dt),float(end),float(cadence));path=TESTS/'figures'/(name+'_history.csv');history.to_csv(path,index=False,float_format='%.17g');item['history']=bound(path)
            if suffix.endswith(('_c','_h')):
                oldstage='smoke' if suffix.startswith('smoke') else 'drained'
                control=TESTS/'outputs'/('lian_release_r1_'+oldstage+'_gpu_'+suffix[-1]);initial=native(control,0);diff=[]
                for i in range(len(history)):
                    a,o=native(folder,i),native(control,i);assert np.array_equal(a.id,o.id)
                    mismatch=abs(float(a.time_s.iloc[0]-o.time_s.iloc[0]));assert mismatch<=1.01e-5
                    top=initial.z.gt(9.99).to_numpy()
                    diff.append(dict(part=i,time_s=float(a.time_s.iloc[0]),same_time_all_fields_0ulp=bool(np.array_equal(a.to_numpy(),o.to_numpy())),
                        pressure_rms_difference_pa=float(np.sqrt(np.mean((a.pressure-o.pressure)**2))),top_material_max_difference_mm=float(1000*np.max(abs(a.z.to_numpy()[top]-o.z.to_numpy()[top])))))
                comparison=TESTS/'figures'/(name+'_strict.csv');pd.DataFrame(diff).to_csv(comparison,index=False,float_format='%.17g');item['strict_comparison']=bound(comparison)
            write_json(TESTS/'logs'/(name+'.run.json'),item);save()
            if suffix.endswith('_h'):
                frame,passed=pair(TESTS/'outputs'/(TAG+'_'+suffix[:-1]+'c'),folder)
                csv=TESTS/'figures'/(TAG+'_'+suffix.split('_')[0]+'_half.csv');frame.to_csv(csv,index=False,float_format='%.17g')
                result=dict(stage=suffix.split('_')[0],passed=passed,pressure_rms_half_max_pa=float(frame.pressure_rms_difference_pa.max()),top_material_half_max_mm=float(frame.top_material_max_difference_mm.max()),artifact=bound(csv))
                record['pairs'].append(result);save();assert passed,('Original full-history half gate',result)
        for e in inputs:assert bound(e['path'])['sha256']==e['sha256'],e['path']
        record.update(status='short_gates_passed_pending_physical_review',finished_utc=utc())
    except Exception as error:record.update(status='rejected_or_interrupted',error=repr(error),finished_utc=utc())
    finally:save();notify(record)
    print(record['status'],record.get('error',''),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args()
    (prepare if args.action=='prepare' else run)()
