"""Prepare only by default; --run executes one admitted coarse damping peak diagnostic."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE,TESTS,REPO,READER,bound,native,utc,write_json
from cryer_dt_short_r1 import inspect
from cryer_grad_short_r1 import difference
from cryer_gpu_base_r1 import verify
from cryer_grad_peak_r1 import theory_parameters,extend,inventory,compare_prefix,identity,CODEX,THEORY

TAG='cryer_damp_peak_r1'
DT=2.**-21;DURATION=.0625;INTERVAL=2.**-11;STEPS=131072;FRAMES=129
PREP=TESTS/'logs'/(TAG+'.inputs.json')
RUN=TESTS/'logs'/(TAG+'.run.json');STATE=TESTS/'logs'/(TAG+'.status.json')
CHECK=TESTS/'logs'/(TAG+'.check.json');COMPLETE=TESTS/'logs'/(TAG+'.completion.json')
SUMMARY=TESTS/'figures'/(TAG+'_summary.csv');EFFECTS=TESTS/'figures'/(TAG+'_effects.csv')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path,data):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(data,stream,indent=2,allow_nan=False)


def prerequisites():
    proof=[];runs={}
    for review_name,tag in [('cryer_damp_short_review_r1','cryer_damp_short_r1'),('cryer_grad_peak_review_r1','cryer_grad_peak_r1')]:
        path=TESTS/'logs'/(review_name+'.check.json');review=read(path)
        assert review['evidence_consistency_passed'] and review['original_single_run_safety_passed']
        if tag=='cryer_damp_short_r1':assert review['original_independent_half_screen_passed']
        links=[dict(path=str(path.parent/e['path']),sha256=e['sha256']) for e in review['source_links']]
        verify(links);check=TESTS/'logs'/(tag+'.check.json');gate=read(check)
        assert gate['passed'];verify([gate['run_manifest']]);runs[tag]=read(gate['run_manifest']['path'])
        proof += [bound(path),bound(check),gate['run_manifest']]+links
    short=runs['cryer_damp_short_r1'];old=runs['cryer_grad_peak_r1']
    assert len(short['runs'])==2 and all(r['passed'] and r['owned_exited'] and r['exit_code']==0 for r in short['runs'])
    assert old['owned_exited'] and old['exit_code']==0 and old['checked_frames']==FRAMES
    for record in [r['sealed_completion'] for r in short['runs']]+[old['sealed_completion']]:
        verify([record]);done=read(record['path']);assert done['solver_finished'] and done['exit_code']==0
        verify(done['outputs']);proof += [record]+done['outputs']
    verify([old['prepared_inputs']]);prepared=read(old['prepared_inputs']['path'])
    assert short['program']['sha256']==prepared['program']['sha256'],'Short and peak programs differ'
    verify(prepared['inputs']+[prepared['program'],prepared['build']]);verify(read(prepared['build']['path'])['inputs'])
    proof.append(old['prepared_inputs']);return prepared,old,proof


def reserved():
    paths=[RUN,STATE,CHECK,COMPLETE,SUMMARY,EFFECTS,TESTS/'outputs'/TAG]
    paths += [TESTS/'logs'/(TAG+s) for s in ['.log','.queue_attempt.json','.notification.json']]
    assert not any(p.exists() for p in paths),'Retained stage exists; never overwrite or restart it'


def prepare():
    assert not PREP.exists(),'Never overwrite prepared evidence'
    reserved();old,old_run,proof=prerequisites();thread=identity();assert thread==old_run['thread']
    source=TESTS/'configs/cryer_grad_peak_r1_Def.xml';cfg=TESTS/'configs'/(TAG+'_Def.xml')
    template=TESTS/'configs/xcryer_grad_peak_r1_win64_GPU.bat';bat=TESTS/'configs'/('x'+TAG+'_win64_GPU.bat')
    original=source.read_text(encoding='utf8');mark='<parameter key="SoilDampingCoef" value="0.02"'
    assert original.count(mark)==1 and cfg.read_text(encoding='utf8')==original.replace(mark,mark.replace('0.02','0.00004'))
    assert bat.read_text(encoding='utf8')==template.read_text(encoding='utf8').replace('cryer_grad_peak_r1',TAG)
    scripts=[__file__,TESTS/'notes'/(TAG+'.md'),source,template,cfg,bat,
        TESTS/'support/cryer_grad_peak_r1.py',TESTS/'support/cryer_start_r1.py',
        TESTS/'support/cryer_dt_short_r1.py',TESTS/'support/cryer_grad_short_r1.py',
        TESTS/'support/cryer_gpu_base_r1.py',THEORY,READER]
    inputs=proof+old['inputs']+[bound(p) for p in scripts]
    seal(PREP,dict(status='prepared_not_started',utc=utc(),thread=thread,inputs=inputs,
        program=old['program'],build=old['build'],config=bound(cfg),bat=bound(bat),expected_steps=STEPS,
        expected_frames=FRAMES,dt_s=DT,duration_s=DURATION,interval_s=INTERVAL,
        physical_accepted=False,half_window_accepted=False,full_cycle_accepted=False))
    print('PREPARED ONLY',PREP,flush=True)


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG}: {state["status"]}. Not a new human observation. '
        f'Read {STATE}, tests/logs/{TAG}.run.json, tests/logs/{TAG}.check.json, '
        f'tests/logs/{TAG}.completion.json and tests/notes/{TAG}.md. '
        'This is one fresh weaker-damping GPU coarse peak diagnostic: xi=.00004, dt2^-21, end.0625s, '
        '131072steps/129frames, original dp.0025/rawload/grad1/material/geometry. Verify ownership, actual times/IDs, '
        'all frozen hashes/native safety, two weak-short shared samples34columns0ULP with only dterror interval '
        'statistic excluded and both original guards. Review all129 same-time effects against oldxi.02 peak; '
        'these are parameter changes, not5Pa backend/half errors or theory truth. Short half passed, but no '
        'independent peak half/full/physical acceptance. Inspect startup and Tv>=.005 peaks/pressure/stress/load '
        'and figures/CSVs. Keep nativep0=0 versus theoryt0+1 distinct; the18IDs lie at r/a=.05, with finite-radius '
        'theory reviewed separately in cryer_radial_review_r1. If analysis alone failed, repair fresh analysis without rerunning completed solver. '
        'If runtime failed report exact actual time/reason and survivors. Preserve all evidence, no relaxed '
        'gates, duplicate solver or old-worker restart. Report Chinese proactively and continue authorized causal '
        'diagnosis without waiting for progress questions; no automatic formal run or physical acceptance. '
        'This one-shot queues once; never restart/rearm it or send connectivity tests.')
    assert len(message)<2000
    seal(TESTS/'logs'/(TAG+'.queue_attempt.json'),dict(event=state['status'],utc=utc(),thread=state['thread'],message=message,message_chars=len(message)))
    try:
        p=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result=dict(status='queued' if p.returncode==0 else 'queue_failed_no_retry',exit_code=p.returncode,reply=(p.stdout+p.stderr).decode(errors='replace'))
    except Exception as error:result=dict(status='queue_exception_no_retry',error=repr(error))
    seal(TESTS/'logs'/(TAG+'.notification.json'),result)


def run():
    prepared=read(PREP);verify(prepared['inputs']+[prepared['program']]);assert identity()==prepared['thread'];prerequisites();reserved()
    assert not inventory(),'An active GPU solver exists; do not duplicate it'
    state=dict(status='running',stage='solver',thread=prepared['thread'],started_utc=utc(),
        owned_sequence_pid=os.getpid(),prepared_inputs=bound(PREP),program=prepared['program'],checked_frames=0,physical_accepted=False)
    def publish():
        tmp=RUN.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,RUN)
        status=dict(status=state['status'],stage=state['stage'],owned_sequence_pid=os.getpid(),
            owned_wrapper_pid=state.get('owned_wrapper_pid'),checked_frames=state['checked_frames'],
            last_checked_time_s=state.get('actual_last_saved_time_s'),run_manifest=bound(RUN))
        tmp=STATE.with_suffix('.tmp');write_json(tmp,status);os.replace(tmp,STATE)
    publish();child=None;rows=[];effects=[];prefix=[];folder=TESTS/'outputs'/TAG;log=TESTS/'logs'/(TAG+'.log');started=time.perf_counter()
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',prepared['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid']=child.pid;publish();report=started
            while child.poll() is None:
                time.sleep(1)
                if time.perf_counter()-report>30:print('RUNNING',TAG,'wall_s',round(time.perf_counter()-started),flush=True);report=time.perf_counter()
        state.update(exit_code=child.returncode,owned_exited=True,solver_wall_seconds=time.perf_counter()-started)
        text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
        finished=child.returncode==0 and 'Finished execution (code=0)' in text
        outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)]
        seal(COMPLETE,dict(solver_finished=finished,exit_code=child.returncode,owned_exited=True,
            owned_wrapper_pid=child.pid,utc=utc(),prepared_inputs=bound(PREP),program=prepared['program'],outputs=outputs))
        state.update(sealed_completion=bound(COMPLETE),stage='offline_analysis');publish();assert finished
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==STEPS
        assert len(list((folder/'data').glob('Part_*.bi4')))==FRAMES
        assert 'SoilStressRateGradCorr="KernelGradient"' in text and 'BuiFukagawa2013' in text
        coefficient=re.search(r'^\s*SoilDampingCoef=([^\r\n]+)',text,re.M);assert coefficient and float(coefficient[1])==.00004
        state['actual_gpu']=re.search(r'Device default:\s*([^\r\n]+)',text)[1]
        state['compute_capability']=re.search(r'Compute capability:\s*([^\r\n]+)',text)[1]
        runtime=re.search(r'Simulation Runtime\.*:\s*([\d.]+)\s*sec',text);state['observed_simulation_runtime_s']=float(runtime[1]) if runtime else None
        meta,theory=theory_parameters(prepared['config']['path']);state['theory_parameters']=meta
        initial=native(folder,0);r0=np.linalg.norm(initial[['x','y','z']],axis=1);center=r0<=.0025+1e-12;assert center.sum()==18
        masks=dict(center=center,interior=r0<.05-2*float(initial.h.iloc[0]),outer_shell=r0>=.05-2*float(initial.h.iloc[0]))
        oldfolder=TESTS/'outputs/cryer_grad_peak_r1';weakshort=TESTS/'outputs/cryer_damp_short_r1_c'
        state['center_material_ids']=list(map(int,initial.id[center]))
        for part in range(FRAMES):
            a=initial if part==0 else native(folder,part);b=native(oldfolder,part)
            assert float(a.time_s.iloc[0])==float(b.time_s.iloc[0])==part*INTERVAL
            assert int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0])==(part*1024-1 if part else 0)
            if part==0:assert np.array_equal(a[['id','x','y','z','rho','mass','h']],b[['id','x','y','z','rho','mass','h']])
            assert np.array_equal(a[['mass','h']],initial[['mass','h']]) and np.linalg.norm(a[['x','y','z']],axis=1).max()<=.0525
            row,issues=inspect(a,initial,part,DT,center);rows.append(extend(row,a,initial,masks,meta,theory));assert not issues,(part,issues)
            effects.append(dict(part=part,time_s=part*INTERVAL,comparison='same_dt_weaker_damping_change_not_half_or_theory_error',**difference(a,b)))
            if part in [0,1]:prefix.append(dict(peak_part=part,short_part=part*4,actual_time_s=part*INTERVAL,**compare_prefix(a,native(weakshort,part*4))))
            state.update(checked_frames=part+1,actual_last_saved_time_s=row['time_s']);publish()
            if part%16==0:print('CHECKED',part+1,'/',FRAMES,flush=True)
        verify(prepared['inputs']+[prepared['program']]);window=[r for r in rows if r['tv']>=.005];assert window
        peak=lambda data:dict(part=int(data['part']),time_s=data['time_s'],tv=data['tv'],center_p_over_q=data['center_p_over_q'],theory_at_actual_time=data['theory_center_p_over_q'])
        late=max(window,key=lambda r:r['center_p_over_q'])
        state.update(prefix=prefix,full_history_center_max=peak(max(rows,key=lambda r:r['center_p_over_q'])),
            mandel_window_rule='All saved samples Tv>=.005; no smoothing/filtering.',mandel_window_center_max=peak(late),
            mandel_center_peak_at_window_end=late['part']==rows[-1]['part'],last_saved_center_pressure_is_rising=rows[-1]['center_p_over_q']>rows[-2]['center_p_over_q'],
            status='damping_peak_completed_pending_physical_review',stage='terminal')
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True);state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='damping_peak_rejected_or_interrupted',stage='terminal',error=repr(error),traceback=traceback.format_exc(),owned_exited=child is None or child.poll() is not None)
    finally:
        artifacts=[]
        for path,data in [(SUMMARY,rows),(EFFECTS,effects)]:
            if data:pd.DataFrame(data).to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
        state.update(finished_utc=utc(),wall_seconds=time.perf_counter()-started,artifacts=artifacts);publish()
        seal(CHECK,dict(passed=state['status']=='damping_peak_completed_pending_physical_review',status=state['status'],
            run_manifest=bound(RUN),sealed_completion=state.get('sealed_completion'),checked_frames=len(rows),effect_samples=len(effects),
            prefix_samples=prefix,error=state.get('error'),physical_accepted=False,half_window_accepted=False,full_cycle_accepted=False,
            limits=['One coarse damping-sensitivity peak window, not independent peak half/full/physical acceptance.',
                'All129 old/new effects use exact same actualtimes and are not5Pa cross gates or theory errors.',
                'Only two shared weak-short samples; dterror interval statistic is the sole0ULP exclusion, original guards unchanged.',
                'Native center is a fixed18-ID ball, not the analytical point; startup retained without filtering.',
                'No production/formal change or automatic longer/formal run; one terminal queue, no rearm.']))
        notify(state)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:run()
    else:prepare()
