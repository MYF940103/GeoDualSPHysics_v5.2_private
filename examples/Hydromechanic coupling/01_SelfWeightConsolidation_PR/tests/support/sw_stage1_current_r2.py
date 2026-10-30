"""Fresh aligned-output coarse/half checks, then gated independent Stage1 ON/OFF."""
import argparse
import ast
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import sw_stage1_current_r1 as old

current, event, baseline = old.current, old.event, old.baseline
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = old.TESTS, old.CASE, old.LOGS, old.CONFIGS, old.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(old,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
clock_table, measure, profiles, identity, CODEX = old.clock_table, old.measure, old.profiles, old.identity, old.CODEX
TAG='sw_stage1_current_r2'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
JOBS=[dict(suffix='coarse',dt='0.000001',shepard=40,on=True,end='0.002',interval='0.0004999',steps=2000,frames=5),
      dict(suffix='half',dt='0.0000005',shepard=80,on=True,end='0.002',interval='0.0004999',steps=4000,frames=5),
      dict(suffix='on',dt='0.000001',shepard=40,on=True,end='0.30',interval='0.005',steps=300001,frames=61),
      dict(suffix='off',dt='0.000001',shepard=40,on=False,end='0.30',interval='0.005',steps=300001,frames=61)]


def expected(job,program):
    xml,bat=old.expected(job,program); return xml,bat.replace(old.TAG,TAG)


def plan(job):
    clock=clock_table(job['dt'],job['steps']); interval=float(job['interval']); count=math.floor(float(job['end'])/interval)
    predicted=[int(np.searchsorted(clock,np.float64(k*interval),side='left')) for k in range(count+1)]
    assert predicted==[math.ceil(k*interval/float(job['dt'])) for k in range(count+1)] and len(predicted)==5
    return predicted


def references():
    prior=read(old.PREP); return dict(legacy_coarse=dict(folder=prior['coarse_folder'],receipt=prior['coarse_receipt'],dt='0.000001',steps=2000),
        legacy_half=dict(folder=str(OUTPUTS/(old.TAG+'_half')),receipt=bound(LOGS/(old.TAG+'_half.receipt.json')),dt='0.0000005',steps=4000))


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); refs=references()
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); tree=ET.fromstring(xml)
        assert TAG in bat and old.TAG not in bat and ('-nsteps:'+str(job['steps'])) in bat
        assert all(tree.find('.//parameter[@key="'+key+'"]').get('value')==job['dt'] for key in ['DtIni','DtFixed'])
        assert tree.find('.//parameter[@key="TimeOut"]').get('value')==job['interval'] and tree.find('.//PoreShepardInterval').get('value')==str(job['shepard'])
        assert tree.find('.//parameter[@key="SavePosDouble"]').get('value')=='1' and tree.find('.//HydraulicConductivity').get('value')=='0'
        if job['suffix'] in ['coarse','half']:
            steps=plan(job); assert steps==([0,500,1000,1500,2000] if job['suffix']=='coarse' else [0,1000,2000,3000,4000])
            rows=read(refs['legacy_'+job['suffix']]['receipt']['path'])['rows']; prior={r['natural_step'] for r in rows}
            assert len(set(steps)&prior)==4
            clock=clock_table(job['dt'],job['steps'])
            for row in rows:assert abs(row['time_s']-clock[row['natural_step']])<=1e-14
    return dict(passed=True,programs_started=False,files_written=False,coarse_steps=plan(JOBS[0]),half_steps=plan(JOBS[1]))


def prepare():
    gates=old.prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(old.PREP); assert identity()==prior['thread']; failed=read(old.CHECK); assert not failed['passed'] and len(failed['jobs'])==1
    refs=references(); proof=prior['inputs']+gates+[bound(p) for p in [__file__,NOTE,old.__file__,old.PREP,old.CHECK,CODEX]]+[failed['run']]+failed['jobs']
    for ref in refs.values():
        result=read(ref['receipt']['path']); done=read(result['sealed_completion']['path'])
        assert done['solver_finished'] and done['exit_code']==0 and done['owned_exited'] and len(result['rows'])==5
        ref.update(completion=result['sealed_completion'],outputs=done['outputs']); proof += [ref['receipt'],ref['completion']]+ref['outputs']
    program=prior['jobs'][0]['program']; runtime=prior['jobs'][0]['runtime']; proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat'); xml,command=expected(job,Path(program['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=program,runtime=runtime,config=bound(cfg),bat=bound(bat)); jobs.append(job); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),thread=identity(),codex=bound(CODEX),inputs=proof,jobs=jobs,references=refs,
        retained_r1_failed=bound(old.CHECK),physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))


def load_reference(ref):
    verify([ref['receipt'],ref['completion']]+ref['outputs']); clock=clock_table(ref['dt'],ref['steps']); frames={}
    for row in read(ref['receipt']['path'])['rows']:
        part=row['part']; a=current.native(Path(ref['folder']),part); frames[part]=a; measured=measure(a,frames[0],part,ref,clock)
        assert measured['time_s']==row['time_s'] and measured['saved_step']==row['saved_step']
    return frames


def compare(job,frames,refs):
    rows=old.compare({0:frames[0]},refs['legacy_coarse'],False) if 0 in frames else [dict(passed=False,error='Initial frame absent')]
    if job['suffix'] in ['coarse','half']:
        keyed=lambda cache:{(int(a.saved_step.iloc[0])+1 if part else 0):(part,a) for part,a in cache.items()}
        akey,bkey=keyed(frames),keyed(refs['legacy_'+job['suffix']]); shared=sorted(set(akey)&set(bkey))
        rows.append(dict(comparison='same_dt_shared_coverage',shared_natural_steps=';'.join(map(str,shared)),passed=len(shared)==4))
        for step in shared:
            try:
                pa,a=akey[step]; pb,b=bkey[step]; keep=[c for c in a.columns if c!='dterror_s']; assert len(keep)==37 and list(a)==list(b) and a.shape==b.shape
                bad=a[keep].to_numpy(dtype='<f8').view('<u8')!=b[keep].to_numpy(dtype='<f8').view('<u8')
                rows.append(dict(comparison='same_dt_shared37',natural_step=step,part=pa,reference_part=pb,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),
                    different_fields=';'.join(np.array(keep)[bad.any(axis=0)]),dterror_s=float(a.dterror_s.iloc[0]),reference_dterror_s=float(b.dterror_s.iloc[0]),passed=not bool(bad.any())))
            except BaseException as failure:rows.append(dict(comparison='same_dt_shared37',natural_step=step,passed=False,error=repr(failure)))
    if job['suffix']=='half':
        coarse=refs['new_coarse']
        for part in sorted(set(frames)|set(coarse)):
            try:
                a,b=frames[part],coarse[part]; dt=float(a.time_s.iloc[0]-b.time_s.iloc[0]); assert np.array_equal(a.id,b.id)
                du=(a.iloc[40:][['x','y','z']].to_numpy()-frames[0].iloc[40:][['x','y','z']].to_numpy())-(b.iloc[40:][['x','y','z']].to_numpy()-coarse[0].iloc[40:][['x','y','z']].to_numpy())
                pressure=float(np.sqrt(np.mean((a.pressure.iloc[40:]-b.pressure.iloc[40:])**2))); displacement=float(np.linalg.norm(du,axis=1).max()*1000)
                rows.append(dict(comparison='half_matched_time_only',part=part,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),actual_time_difference_s=dt,
                    saved_step=int(a.saved_step.iloc[0]),reference_saved_step=int(b.saved_step.iloc[0]),pressure_rms_pa=pressure,material_displacement_max_difference_mm=displacement,
                    passed=abs(dt)<=1e-14 and pressure<=5 and displacement<=.005))
            except BaseException as failure:rows.append(dict(comparison='half_matched_time_only',part=part,passed=False,error=repr(failure)))
    return rows


def one_job(job,prepared,refs,progress):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt]); verify(prepared['inputs'])
    clock=clock_table(job['dt'],job['steps']); child=None; started=time.perf_counter(); frames={}; rows=[]; history=[]; layers=[]; error=None; readers=[]; solver_pids=[]; failed_part=None
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll(); count=len(list((folder/'data').glob('Part_*.bi4'))); available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    part=len(rows); failed_part=part; a=current.native(folder,part); readers.append(dict(part=part,exit_code=0)); frames[part]=a
                    history += [dict(part=part,**r) for r in event.focus(a).to_dict('records')]; row=measure(a,frames[0],part,job,clock)
                    if part==0:assert old.compare({0:a},refs['legacy_coarse'],False)[0]['passed'],'Initial38-field comparison failed'
                    if rows:assert row['natural_step']>rows[-1]['natural_step'] and row['time_s']>rows[-1]['time_s']
                    rows.append(row); layers+=profiles(a,frames[0],part); failed_part=None
                    solver_pids=[p['ProcessId'] for p in inventory() if job['name'] in (p.get('CommandLine') or '')]
                progress(dict(utc=utc(),owned_wrapper_pid=child.pid,solver_pids=solver_pids,checked_frames=len(rows),latest_native=rows[-1] if rows else None,wall_seconds=time.perf_counter()-started))
                if code is not None:break
                time.sleep(2)
    except BaseException as failure:
        error=repr(failure); trace=traceback.format_exc()
        if failed_part is not None and not any(r['part']==failed_part for r in readers):readers.append(dict(part=failed_part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[p for p in inventory() if job['name'] in (p.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],config=job['config'],bat=job['bat'],
        outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
    try:pairs=compare(job,frames,refs)
    except BaseException as failure:pairs=[dict(passed=False,error=repr(failure),traceback=traceback.format_exc())]
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('frames',rows),('history',history),('profiles',layers),('pairs',pairs)]]
    try:
        assert error is None,error
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==job['frames'] and len(layers)==100*job['frames']
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps'] and rows[-1]['natural_step']==job['steps']
        if job['suffix'] in ['coarse','half']:assert [r['natural_step'] for r in rows]==plan(job)
        assert 'SlipMode="DBC vel=0"' in text and 'HydroMechInitMode="FreeSurface"' in text and 'PoreDarcySymmetricCorr="Receiver"' in text
        assert 'PoreShepardRegularization="'+('Enabled' if job['on'] else 'Disabled')+'"' in text and int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']
        assert 'SoilDampingCoef=0.02' in text and 'SoilHourglass: forcecalls=' not in text and all(p['passed'] for p in pairs); verify(prepared['inputs'])
    except BaseException as failure:error=repr(failure); trace=traceback.format_exc()
    result=dict(passed=error is None,error=error,failed_part=failed_part,rows=rows,pairs=pairs,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),
        wall_seconds=time.perf_counter()-started,owned_wrapper_pid=None if child is None else child.pid,physical_acceptance=False,restart_admitted=False)
    if error:result['traceback']=trace
    seal(receipt,result); return result,bound(receipt),frames


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG} terminal: {state["status"]}. Read {RUN}, {CHECK}, tests/notes/{TAG}.json and all new receipts/completions. '
        'Preserve failed r1; its near-time5.10150751Pa screen was not relaxed. Fresh coarse/half2ms used TimeOut.0004999 to save actual matched times<=1e-14, original5Pa/.005mm, no interpolation. '
        'Same-dt four shared states must match all37 fields; only output-interval dterror_s equality is excluded while both original signed safety guards remain. '
        'Full Stage1 ON/OFF.3s admitted only after both new short gates; inspect owned exits, native1040IDs/all38 fields, frozen build/input/output hashes and all61-frame/100-layer profiles. '
        'Normal exit is not equilibrium/full-consolidation/restart acceptance; distinguish native p-p0 from current hydrostatic excess and finite-Kw references. '
        'If solver completed but analysis failed repair offline only. No duplicate solver, old worker restart, relaxed gates, rearming, or queue selftest. '
        'Report Chinese proactively and continue authorized selfweight diagnosis; Cryer server and formal retained results remain protected. One terminal notification only.')
    assert len(message)<2000; seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message))
    try:
        result=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if result.returncode==0 else 'queue_failed_no_retry',exit_code=result.returncode,reply=(result.stdout+result.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def run():
    old.prerequisites(); assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs']); assert identity()==prepared['thread']
    refs={key:load_reference(ref) for key,ref in prepared['references'].items()}; state=dict(status='running',utc=utc(),worker_pid=os.getpid(),thread=prepared['thread'],prepared=bound(PREP),jobs=[],launched=False)
    def publish():
        tmp=RUN.with_suffix('.tmp'); seal(tmp,state); os.replace(tmp,RUN)
    def progress(value):state.update(progress=value,launched=True); publish()
    publish()
    try:
        for job in prepared['jobs']:
            state.update(current_job=job['name'],progress=None); publish(); result,record,frames=one_job(job,prepared,refs,progress)
            state['jobs'].append(record); state['launched']|=result['owned_wrapper_pid'] is not None; publish(); assert result['passed'],('Earlier gate failed; later jobs held',job['name'],result['error'])
            if job['suffix']=='coarse':refs['new_coarse']=frames
        verify(prepared['inputs']); state['status']='stage1_completed_pending_equilibrium_and_reference_review'
    except BaseException as failure:state.update(status='rejected_or_interrupted_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish(); passed=state['status']=='stage1_completed_pending_equilibrium_and_reference_review' and len(state['jobs'])==4
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),matched_time_tolerance_s=1e-14,
        exact_convergence_claimed=False,physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))
    if state['launched']:notify(state)
    return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
