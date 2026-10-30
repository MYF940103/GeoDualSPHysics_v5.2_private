"""Gated current-GPU half-step diagnostic and independent Stage1 ON/OFF runs."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import sw_pore_cell_native_r1 as current

event, baseline = current.event, current.baseline
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = current.TESTS, current.CASE, current.LOGS, current.CONFIGS, current.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(current,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG = 'sw_stage1_current_r1'
PREP, RUN, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE = TESTS/'notes'/(TAG+'.json')
C02CHECK = baseline.C02/'logs/sw_pore_cell_1d_r1.check.json'
COARSE = current.TAG+'_release_on_short'
CLOCKHALF = LOGS/(baseline.TAG+'_gpu_h.receipt.json')
CODEX = Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
JOBS = [dict(suffix='half',dt='0.0000005',shepard=80,on=True,end='0.002',interval='0.0005',steps=4000,frames=5),
        dict(suffix='on',dt='0.000001',shepard=40,on=True,end='0.30',interval='0.005',steps=300001,frames=61),
        dict(suffix='off',dt='0.000001',shepard=40,on=False,end='0.30',interval='0.005',steps=300001,frames=61)]


def clock_table(dt,steps):
    table=np.empty(steps+1,dtype='<f8'); table[0]=0; delta=np.float64(dt)
    for step in range(1,steps+1):table[step]=table[step-1]+delta
    return table


def identity():
    thread=os.environ['CODEX_THREAD_ID']
    assert thread and thread==os.environ['CODEX_SESSION_ID'] and CODEX.is_file()
    return thread


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG}: {state["status"]}. Read {RUN}, {CHECK}, tests/notes/{TAG}.json and all three job receipts/completions. '
        'Only corrected-GPU ShepardON half2ms then independent Stage1 ON/OFF .3s were admitted; k0,dt1us,damping.02,mDBCvel0,original material,SavePosDouble1. '
        'Verify owned exits/actual time-step/native1040IDs/build-input-output hashes and all38 native fields; original safety/drainage/p0/excess/dterror guards unchanged. '
        'Half .5us uses the original5Pa/.005mm near-time<=1.01us screen, not exact convergence. Full .005s cadence shares only initial state with retained2ms control. '
        'Inspect full61-frame histories/100-layer profiles/CSVs; distinguish native p-p0 from current hydrostatic excess and finite-Kw references before equilibrium/theory claims. '
        'Normal exit is not physical/full-consolidation/restart acceptance. If solver completed but analysis failed,repair offline only; inspect exact cause/time/survivors on failure. '
        'Preserve data,no relaxed guards/duplicate solver/old-worker restart. Report Chinese proactively and continue authorized selfweight diagnosis then gated restart interoperability and formal delivery. '
        'Cryer server remains untouched; case02 accepted results stand. Selective verified local/remoteGit each verified stage. One-shot only; never restart/rearm or send selftests.')
    assert len(message)<2000
    seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message))
    try:
        result=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if result.returncode==0 else 'queue_failed_no_retry',exit_code=result.returncode,reply=(result.stdout+result.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def expected(job,program):
    xml,bat=baseline.expected((job['suffix'],'gpu',job['dt'],job['steps'],job['shepard']),program)
    for key,value in [('TimeMax',job['end']),('TimeOut',job['interval'])]:
        xml,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]+(" comment=")[^"]+("[^\n]+)',
            lambda m:m[1]+value+m[2]+'Fresh current Stage1 diagnostic; equilibrium and restart not admitted'+m[3],xml); assert n==1
    if not job['on']:
        xml,n=re.subn(r'(<PoreShepardRegularization value=")1(")',r'\g<1>0\2',xml); assert n==1
    bat=bat.replace(baseline.TAG,TAG); head,tail=bat.rsplit('if not "%ERRORLEVEL%" == "0" goto fail',1)
    return xml,head+'set solvercode=%ERRORLEVEL%\nif not "%solvercode%" == "0" exit /b %solvercode%'+tail


def prerequisites():
    records=[]
    for path,count in [(current.CHECK,5),(C02CHECK,2)]:
        assert path.is_file(),('Required regression is not complete',str(path))
        check=read(path); assert check['passed'] and len(check['jobs'])==count
        records += [bound(path),check['run']]+check['jobs']
        for record in check['jobs']:
            result=read(record['path']); done=read(result['sealed_completion']['path'])
            assert result['passed'] and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
            records += [result['sealed_completion']]+done['outputs']
    verify(records); return records


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); tree=ET.fromstring(xml)
        assert tree.find('.//parameter[@key="TimeMax"]').get('value')==job['end'] and ('-nsteps:'+str(job['steps'])) in bat
        assert all(tree.find('.//parameter[@key="'+key+'"]').get('value')==job['dt'] for key in ['DtIni','DtFixed']) and tree.find('.//parameter[@key="TimeOut"]').get('value')==job['interval']
        assert tree.find('.//parameter[@key="SavePosDouble"]').get('value')=='1' and tree.find('.//PoreShepardInterval').get('value')==str(job['shepard'])
        assert tree.find('.//PoreShepardRegularization').get('value')==('1' if job['on'] else '0') and tree.find('.//HydraulicConductivity').get('value')=='0'
    for path,dt,steps in [(LOGS/(COARSE+'.receipt.json'),'0.000001',2000),(CLOCKHALF,'0.0000005',4000)]:
        table=clock_table(dt,steps)
        for row in read(path)['rows']:
            folder=OUTPUTS/(COARSE if steps==2000 else baseline.TAG+'_gpu_h'); a=current.native(folder,row['part'])
            step=int(a.saved_step.iloc[0])+1 if row['part'] else 0; assert a.time_s.eq(row['time_s']).all() and a.saved_step.eq(row['saved_step']).all() and abs(float(a.time_s.iloc[0])-table[step])<=1e-14
    assert abs(clock_table('0.000001',300001)[-1]-300001*1e-6)>1e-12
    return dict(passed=True,solver_started=False,reader_invocations=10,files_written=False,actual_retained_clocks_verified=True)


def prepare():
    gates=prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(current.PREP); coarse=next(j for j in prior['jobs'] if j['name']==COARSE)
    receipt=LOGS/(COARSE+'.receipt.json'); result=read(receipt); done=read(result['sealed_completion']['path'])
    half=read(CLOCKHALF); halfdone=read(half['sealed_completion']['path'])
    proof=prior['inputs']+gates+[bound(p) for p in [__file__,NOTE,current.PREP,current.__file__,receipt,CLOCKHALF,CODEX]]
    proof += [result['sealed_completion'],half['sealed_completion'],coarse['program'],coarse['config'],coarse['bat']]+coarse['runtime']+done['outputs']+halfdone['outputs']
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat')
        xml,command=expected(job,Path(coarse['program']['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=coarse['program'],runtime=coarse['runtime'],config=bound(cfg),bat=bound(bat)); jobs.append(job); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),thread=identity(),inputs=proof,jobs=jobs,coarse_folder=str(OUTPUTS/COARSE),coarse_receipt=bound(receipt),
        physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))


def measure(a,initial,part,job,clock):
    assert len(a.columns)==38 and len(a)==1040 and np.array_equal(a.id,np.arange(1040))
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.nout.eq(0).all()
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.native_count.eq(1040).all()
    assert np.array_equal(a.is_boundary,np.r_[np.ones(40),np.zeros(1000)]) and np.array_equal(a[['mass','dp','h']],initial[['mass','dp','h']])
    assert np.array_equal(a.porepress0.to_numpy(dtype='<f8').view('<u8'),initial.porepress0.to_numpy(dtype='<f8').view('<u8'))
    assert np.array_equal(a.excess_native.to_numpy(dtype='<f4').view('<u4'),(a.pressure.to_numpy(dtype='<f4')-a.porepress0.to_numpy(dtype='<f4')).view('<u4'))
    t=float(a.time_s.iloc[0]); saved=int(a.saved_step.iloc[0]); step=saved+1 if part else 0
    assert 0<=step<=job['steps'] and a.time_s.eq(t).all() and a.saved_step.eq(saved).all() and abs(t-clock[step])<=1e-14
    if part:assert a.has_dterror.eq(1).all() and float(a.dterror_s.max())<=1e-14
    soil=a.iloc[40:]; s0=initial.iloc[40:]; du=soil[['x','y','z']].to_numpy()-s0[['x','y','z']].to_numpy()
    dx=(du[:,0]+.05)%.1-.05; span=float(np.ptp(soil.z.to_numpy().reshape(10,100),axis=0).max()*1000)
    assert soil.z.gt(0).all() and abs(dx).max()*1000<.5 and span<.5
    surface=soil.fstype.isin([2,3]); assert set(soil.id[surface])==set(s0.id.iloc[99::100]) and soil.pressure[surface].eq(0).all()
    return dict(part=part,time_s=t,saved_step=saved,natural_step=step,clock_recurrence_error_s=float(t-clock[step]),
        clock_minus_step_times_dt_s=float(clock[step]-step*float(job['dt'])),rho_min=float(a.rho.min()),rho_max=float(a.rho.max()),
        pressure_min_pa=float(a.pressure.min()),pressure_max_pa=float(a.pressure.max()),excess_min_pa=float(a.excess_native.min()),excess_max_pa=float(a.excess_native.max()),
        dterror_s=float(a.dterror_s.max()),true_drained_count=int(surface.sum()),periodic_dx_max_mm=float(abs(dx).max()*1000),layer_span_max_mm=span,
        settlement_max_mm=float((s0.z.to_numpy()-soil.z.to_numpy()).max()*1000),speed_max_m_s=float(np.linalg.norm(soil[['vx','vy','vz']],axis=1).max()))


def profiles(a,initial,part):
    rows=[]; soil=a.iloc[40:]; s0=initial.iloc[40:]
    for layer in range(100):
        b=soil.iloc[layer::100]; b0=s0.iloc[layer::100]
        row=dict(part=part,time_s=float(a.time_s.iloc[0]),natural_step=int(a.saved_step.iloc[0])+1 if part else 0,layer=layer,
            z0_m=float(b0.z.mean()),z_m=float(b.z.mean()),pressure_pa=float(b.pressure.mean()),porepress0_pa=float(b.porepress0.mean()),excess_native_pa=float(b.excess_native.mean()),
            total_sigma_zz_pa=float((b.sigma_zz-b.pressure).mean()),settlement_mm=float((b0.z.to_numpy()-b.z.to_numpy()).mean()*1000),rho_kg_m3=float(b.rho.mean()),
            speed_max_m_s=float(np.linalg.norm(b[['vx','vy','vz']],axis=1).max()))
        row.update({key:float(b[key].mean()) for key in ['sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_yz','sigma_xz','vx','vy','vz']}); rows.append(row)
    return rows


def compare(frames,coarse,half):
    try:
        assert frames[0].shape==coarse[0].shape and list(frames[0])==list(coarse[0])
        bad=frames[0].to_numpy(dtype='<f8').view('<u8')!=coarse[0].to_numpy(dtype='<f8').view('<u8')
        rows=[dict(comparison='initial_only_all38',part=0,passed=not bool(bad.any()),different_fields=';'.join(frames[0].columns[bad.any(axis=0)]))]
    except BaseException as failure:rows=[dict(comparison='initial_only_all38',part=0,passed=False,error=repr(failure))]
    if half:
        for part in sorted(set(frames)|set(coarse)):
            try:
                a,b=frames[part],coarse[part]; dt=float(a.time_s.iloc[0]-b.time_s.iloc[0]); assert np.array_equal(a.id,b.id)
                du=(a.iloc[40:][['x','y','z']].to_numpy()-frames[0].iloc[40:][['x','y','z']].to_numpy())-(b.iloc[40:][['x','y','z']].to_numpy()-coarse[0].iloc[40:][['x','y','z']].to_numpy())
                pressure=float(np.sqrt(np.mean((a.pressure.iloc[40:]-b.pressure.iloc[40:])**2))); displacement=float(np.linalg.norm(du,axis=1).max()*1000)
                rows.append(dict(comparison='half_near_time_only',part=part,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),saved_step=int(a.saved_step.iloc[0]),
                    reference_saved_step=int(b.saved_step.iloc[0]),actual_time_difference_s=dt,pressure_rms_pa=pressure,material_displacement_max_difference_mm=displacement,
                    passed=abs(dt)<=1.01e-6 and pressure<=5 and displacement<=.005))
            except BaseException as failure:rows.append(dict(comparison='half_near_time_only',part=part,passed=False,error=repr(failure)))
    return rows


def one_job(job,prepared,coarse,progress):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt]); verify(prepared['inputs'])
    clock=clock_table(job['dt'],job['steps']); child=None; started=time.perf_counter(); frames={}; rows=[]; history=[]; layerrows=[]; error=None; readers=[]; solver_pids=[]; failed_part=None
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll(); count=len(list((folder/'data').glob('Part_*.bi4'))); available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    part=len(rows); failed_part=part; a=current.native(folder,part); readers.append(dict(part=part,exit_code=0)); frames[part]=a
                    history += [dict(part=part,**r) for r in event.focus(a).to_dict('records')]
                    row=measure(a,frames[0],part,job,clock)
                    if part==0:assert compare({0:a},coarse,False)[0]['passed'],'Initial38-field comparison failed'
                    if rows:assert row['natural_step']>rows[-1]['natural_step'] and row['time_s']>rows[-1]['time_s']
                    rows.append(row); layerrows+=profiles(a,frames[0],part); failed_part=None
                    solver_pids=[p['ProcessId'] for p in inventory() if job['name'] in (p.get('CommandLine') or '')]
                progress(dict(utc=utc(),owned_wrapper_pid=child.pid,solver_pids=solver_pids,checked_frames=len(rows),latest_native=rows[-1] if rows else None,wall_seconds=time.perf_counter()-started))
                if code is not None:break
                time.sleep(2)
    except BaseException as failure:
        error=repr(failure); trace=traceback.format_exc()
        if failed_part is not None and not any(r['part']==failed_part for r in readers):readers.append(dict(part=failed_part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
    survivors=[p for p in inventory() if job['name'] in (p.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],config=job['config'],bat=job['bat'],
        outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
    pairs=compare(frames,coarse,job['suffix']=='half') if 0 in frames else [dict(passed=False,error='Initial frame absent')]
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('frames',rows),('history',history),('profiles',layerrows),('pairs',pairs)]]
    try:
        assert error is None,error
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==job['frames'] and len(layerrows)==100*job['frames']
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps'] and rows[-1]['natural_step']==job['steps']
        assert 'SlipMode="DBC vel=0"' in text and 'HydroMechInitMode="FreeSurface"' in text and 'PoreDarcySymmetricCorr="Receiver"' in text
        assert 'PoreShepardRegularization="'+('Enabled' if job['on'] else 'Disabled')+'"' in text and int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']
        assert 'SoilDampingCoef=0.02' in text and 'SoilHourglass: forcecalls=' not in text and all(p['passed'] for p in pairs)
        verify(prepared['inputs'])
    except BaseException as failure:error=repr(failure); trace=traceback.format_exc()
    result=dict(passed=error is None,error=error,failed_part=failed_part,rows=rows,pairs=pairs,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),
        wall_seconds=time.perf_counter()-started,owned_wrapper_pid=None if child is None else child.pid,physical_acceptance=False,restart_admitted=False)
    if error:result['traceback']=trace
    seal(receipt,result); return result,bound(receipt)


def run():
    prerequisites(); assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs'])
    assert identity()==prepared['thread']
    coarse={r['part']:current.native(Path(prepared['coarse_folder']),r['part']) for r in read(prepared['coarse_receipt']['path'])['rows']}
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),thread=prepared['thread'],prepared=bound(PREP),jobs=[])
    def publish():
        tmp=RUN.with_suffix('.tmp'); seal(tmp,state); os.replace(tmp,RUN)
    def progress(value):state.update(progress=value); publish()
    publish()
    try:
        for job in prepared['jobs']:
            state.update(current_job=job['name'],progress=None); publish(); result,record=one_job(job,prepared,coarse,progress)
            state['jobs'].append(record); publish(); assert result['passed'],('Earlier gate failed; later jobs held',job['name'],result['error'])
        verify(prepared['inputs']); state['status']='stage1_completed_pending_equilibrium_and_reference_review'
    except BaseException as failure:state.update(status='rejected_or_interrupted_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish()
    passed=state['status']=='stage1_completed_pending_equilibrium_and_reference_review' and len(state['jobs'])==3
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),half_is_near_time_diagnostic=True,
        exact_convergence_claimed=False,physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))
    notify(state); return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
