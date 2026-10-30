"""Fresh dyadic GPU long-window pair; exact old-window prefixes, no formal admission."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import sw_mode3_window_r1 as window
import sw_release_native_r1 as release

old, hg, stage, current, event, short = window.old, window.hg, window.stage, window.current, window.event, window.short
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = window.TESTS, window.CASE, window.LOGS, window.CONFIGS, window.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(window,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
CODEX, identity, plan = window.CODEX, window.identity, window.plan
TAG = 'sw_mode3_longwin_r1'
PREP, RUN, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE = TESTS/'notes'/(TAG+'.json')
ANALYSIS = LOGS/'sw_mode3_window_review_r1.check.json'
DECISION = TESTS/'notes'/(TAG+'.decision.json')
JOBS = [dict(j,end='0.09375',steps=j['steps']*4,frames=1025) for j in window.JOBS]


def expected(job,program):
    xml,bat=window.expected(job,program)
    return xml,bat.replace(window.TAG,TAG)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); clocks=[]
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); root=ET.fromstring(xml)
        value=lambda key:root.find('.//parameter[@key="'+key+'"]').get('value')
        assert value('TimeMax')==job['end'] and value('TimeOut')==job['interval'] and value('DtIni')==value('DtFixed')==job['dt']
        assert value('SoilHourglassXi')=='0.1' and value('SoilBoundaryDerivativeSPR')==value('SoilStressRateGradCorr')=='1'
        assert root.find('.//HydroMechInitMode').get('value')=='3' and root.find('.//HydraulicConductivity').get('value')=='0.001'
        assert root.find('.//PoreShepardRegularization').get('value')=='0' and TAG in bat and window.TAG not in bat and '-partbegin' not in bat.lower()
        assert '-gpu -ompthreads:1' in bat and ('-nsteps:'+str(job['steps'])) in bat
        clock,steps=plan(job); stride=256 if job['suffix']=='coarse' else 512
        assert steps==[stride*i for i in range(1025)] and np.array_equal(clock,np.arange(job['steps']+1)*float(job['dt']))
        assert np.array_equal(clock[steps],np.arange(1025)*float(job['interval'])) and clock[-1]==float(job['end']); clocks.append(clock[steps])
    assert np.array_equal(*clocks)
    a=window.pd.DataFrame(np.zeros((2,38)),columns=['time_s','saved_step','id']+['f'+str(i) for i in range(34)]+['dterror_s'])
    assert release.exact(a,a.copy(),0)[0]['passed']; b=a.copy(); b.loc[0,'dterror_s']=1e-30
    assert not release.exact(a,b,0)[0]['passed']
    return dict(passed=True,files_written=False,programs_started=False,reader_started=False,frames=1025,prefix_frames=257,paired_clock_max_difference_s=0.)


def prerequisites():
    check=read(window.CHECK); review=read(ANALYSIS); decision=read(DECISION)
    assert check['passed'] and len(check['jobs'])==2 and not check['held_jobs'] and review['analysis_checks_passed']
    assert decision['bounded_window_reviewed'] and decision['longwin_admitted']
    assert decision['window_analysis']==bound(ANALYSIS) and decision['window_check']==bound(window.CHECK)
    prior=read(window.PREP); refs={}; proof=[bound(window.CHECK),check['run'],bound(window.PREP),bound(ANALYSIS),bound(DECISION)]+check['jobs']
    for job,record in zip(prior['jobs'],check['jobs']):
        result=read(record['path']); done=read(result['sealed_completion']['path'])
        assert result['passed'] and result['hg']['passed'] and result['initial_reference']['passed'] and len(result['rows'])==257
        assert done['solver_finished'] and done['exit_code']==0 and done['owned_exited'] and not done['surviving_owned']
        assert job['suffix'] in ['coarse','half'] and len(result['pairs'])==(257 if job['suffix']=='half' else 0) and all(r['passed'] for r in result['pairs'])
        refs[job['suffix']]=dict(folder=str(OUTPUTS/job['name']),job=job,receipt=record,completion=result['sealed_completion'])
        proof += [result['sealed_completion'],job['config'],job['bat'],job['program']]+job['runtime']+done['outputs']+result['artifacts']
    proof2,candidates,capture=release.prerequisites(); regression=read(release.CHECK)
    assert regression['passed'] and len(regression['jobs'])==4 and not regression['held_jobs'] and regression['all38_including_dterror'] and not regression['excluded_fields']
    proof += proof2+[bound(release.CHECK),regression['run']]+regression['jobs']
    for record in regression['jobs']:
        result=read(record['path']); done=read(result['sealed_completion']['path'])
        assert result['passed'] and result['all38_including_dterror'] and not result['excluded_fields'] and len(result['pairs'])==5
        assert all(r['passed'] and r['different_values']==0 and r['dterror_included'] for r in result['pairs'])
        assert done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
        proof += [result['sealed_completion']]+done['outputs']+result['artifacts']
    built=read(release.build.CHECK); snapshots=read(built['prepared']['path'])['snapshots']
    proof += [v for r in snapshots for v in [r['original'],r['snapshot']]]
    verify(unique(proof)); return proof,candidates['gpu'],capture,refs


def prepare():
    selftest(); gates,candidate,capture,refs=prerequisites(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    helpers=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(CASE.parent)})
    reader=read(event.BUILD); assert reader['built'] and reader['exit_code']==0
    runtime=[r['target'] for r in candidate['runtime']]
    proof=gates+[bound(p) for p in helpers+[NOTE,CODEX,event.BUILD,Path(sys.executable),window.old.baseline.TEMPLATE,window.old.baseline.REPO/'bin/windows/GenCase_win64.exe']]
    proof += [candidate['program'],reader['program'],reader['log']]+runtime+reader['inputs']
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat'); xml,command=expected(job,Path(candidate['program']['path']))
        previous=ET.parse(refs[job['suffix']]['job']['config']['path']).getroot(); signature=lambda tree:[(e.tag,sorted(e.attrib.items())) for e in tree.iter() if e.get('key')!='TimeMax']
        assert signature(ET.fromstring(xml))==signature(previous),'Only TimeMax changes in numerical XML'
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=candidate['program'],runtime=runtime,config=bound(cfg),bat=bound(bat),parameters=old.parameters(xml)); jobs.append(job); proof += [bound(cfg),bound(bat)]
    proof=unique(proof); verify(proof); seal(PREP,dict(utc=utc(),thread=identity(),codex=bound(CODEX),inputs=proof,jobs=jobs,references=refs,new_build_source_capture=capture,
        prior_window_source_attribution=read(window.PREP)['source_program_attribution'],physical_acceptance=False,formal_admitted=False,restart_admitted=False))


def one_job(job,prepared,coarse,progress):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(q.exists() for q in [folder,log,complete,receipt]); verify(prepared['inputs'])
    p=job['parameters']; clock,steps=plan(job); child=None; started=time.perf_counter(); rows=[]; layers=[]; focus=[]; readers=[]; frames={}; pairs=[]; prefixes=[]; prefix_fields=[]; errors=[]; reference={}; statistics={}; failed_part=None
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll(); count=len(list((folder/'data').glob('Part_*.bi4'))); available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    part=len(rows); failed_part=part; a=current.native(folder,part); readers.append(dict(part=part,exit_code=0))
                    if part==0 or job['suffix']=='coarse':frames[part]=a
                    row=dict(stage.measure(a,frames[0],part,job,clock),**short.r_summary(a,p),**old.pore_limit(a,p,job['dt']))
                    assert row['pore_limit_passed'] and row['natural_step']==steps[part] and row['time_s']==clock[steps[part]]
                    rows.append(row); focus += [dict(part=part,**r) for r in event.focus(a).to_dict('records')]
                    for layer in stage.profiles(a,frames[0],part):layer.update(r_native_pa=layer['excess_native_pa']+p['Mf']*(layer['sigma_xx']+layer['sigma_yy']+layer['sigma_zz'])/(3*p['K']),included_in_r_summary=layer['layer']!=99); layers.append(layer)
                    if part==0:reference,_=old.initial_reference(a,p); assert reference['passed']
                    if part<257:
                        prior=current.native(Path(prepared['references'][job['suffix']]['folder']),part); pair,fields=release.exact(a,prior,part); prefixes.append(pair); prefix_fields+=fields; assert pair['passed'],('All38 exact prefix failed',pair)
                    if job['suffix']=='half':
                        pair,_=short.pair(job['name']+'_vs_coarse','gpu_half',part,a,part,coarse[part],frames[0],coarse[0],p); pairs.append(pair); assert pair['passed'],pair
                    verify([job['program'],job['config'],job['bat']]+job['runtime']); failed_part=None
                solver_pids=[r['ProcessId'] for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
                progress(dict(utc=utc(),owned_wrapper_pid=child.pid,solver_pids=solver_pids,checked_frames=len(rows),latest_native=rows[-1] if rows else None,wall_seconds=time.perf_counter()-started))
                if code is not None:break
                assert time.perf_counter()-started<10800,'Bounded three-hour job timeout; stop only owned wrapper tree'
                time.sleep(2)
    except BaseException as failure:
        errors.append(dict(stage='stream_native_prefix_or_half_gate',part=failed_part,error=repr(failure),traceback=traceback.format_exc()))
        if child is not None and child.poll() is None:subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,owned_exited=not survivors,
        surviving_owned=survivors,program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
    try:
        statistics=hg.parse_hg(text,job); assert statistics['passed'] and reference['passed'] and done['solver_finished'] and done['owned_exited']
        assert len(rows)==1025 and len(layers)==102500 and [r['natural_step'] for r in rows]==steps
        assert sorted(int(q.stem.split('_')[-1]) for q in (folder/'data').glob('Part_*.bi4'))==list(range(1025))
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert len(prefixes)==257 and all(r['passed'] and r['dterror_included'] and r['different_values']==0 for r in prefixes)
        assert len(pairs)==(1025 if job['suffix']=='half' else 0) and all(r['passed'] for r in pairs)
        assert all(s in text for s in ['HydroMechInitMode="AnalyticalSelfWeight1D"','mode=gravity-on self-weight','hydrostatic baseline=retained','SoilBoundaryDerivativeSPR="MirroredWallDerivatives"',
            'SPR stationary wall planes (one per mk): 1','No Penetration=False','SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"',
            'PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"','SoilDampingCoef=0.02','PoreDarcySymmetricCorr="Receiver"'])
        assert float(re.search(r'HydraulicConductivity:\s*(\S+)',text)[1])==.001 and int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']; verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion_or_hg',error=repr(failure),traceback=traceback.format_exc()))
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('history_r',rows),('numeric_profiles',layers),('nativefocus',focus),('prefix_pairs',prefixes),('prefix_fields',prefix_fields)]+([('half_pairs',pairs)] if pairs else [])]
    result=dict(passed=not errors,errors=errors,rows=rows,pairs=pairs,prefixes=prefixes,hg=statistics,initial_reference=reference,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,prefix_all38_including_dterror=True,excluded_fields=[],physical_acceptance=False,formal_admitted=False,restart_admitted=False)
    seal(receipt,result); return result,bound(receipt),frames


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG} terminal: {state["status"]}. Read {RUN}, {CHECK}, tests/notes/{TAG}.json, both job receipts/completions and the prior window decision. '
        'Only two fresh GPU dyadic coarse3*2^-23/half3*2^-24 to.09375s,262144/524288steps,1025frames were admitted; new source-frozen sw_release_build_r1 Release program, no restart/new physics. '
        'Verify owned exits,1040IDs/all38 original safety,exact saved clocks,p0/float32excess,active10drain,natural/pore limits and HG calls/cache/dt/spin; every original1025sample5Pa/.005mm independent half gate remains required. '
        'Each first257 same-dt/cadence states must equal retained sw_mode3_window_r1 all38 columns bitwise INCLUDING dterror,with no exclusions. This is new-binary actual-mode3 adoption,not new theory truth. '
        'Inspect full startup/decay,material settlement,pressure/stress and quasi-static-reference limitations offline. Normal completion/half agreement is not equilibrium,full consolidation,formal or restart acceptance. '
        'If only analysis failed repair offline,never rerun a completed solver; on runtime failure report actual sealed time/reason and surviving owned processes. Preserve all outputs,no relaxed guards,duplicate solver,old-worker restart,rearm or selftest notification. '
        'Report Chinese proactively and continue justified authorized diagnosis; formal cases and Cryer server remain protected. One terminal message only.')
    assert len(message)<2000; seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message))
    try:
        reply=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if reply.returncode==0 else 'queue_failed_no_retry',exit_code=reply.returncode,reply=(reply.stdout+reply.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def run():
    prerequisites(); prepared=read(PREP); verify(prepared['inputs']); assert identity()==prepared['thread'] and bound(CODEX)==prepared['codex'] and not RUN.exists() and not CHECK.exists() and not inventory()
    coarse={}; state=dict(status='running',utc=utc(),worker_pid=os.getpid(),thread=prepared['thread'],prepared=bound(PREP),jobs=[],launched=False)
    def publish():
        temp=RUN.with_suffix('.tmp'); seal(temp,state); os.replace(temp,RUN)
    def progress(value):state.update(progress=value,launched=True); publish()
    publish()
    try:
        for job in prepared['jobs']:
            state.update(current_job=job['name'],progress=None); publish(); result,receipt,frames=one_job(job,prepared,coarse,progress)
            state['jobs'].append(receipt); state['launched']|=result['owned_wrapper_pid'] is not None; publish(); assert result['passed'],('Earlier gate failed; later job held',job['name'],result['errors'])
            if job['suffix']=='coarse':coarse=frames
        verify(prepared['inputs']); state['status']='mode3_long_window_prefix_and_half_passed_pending_physical_review'
    except BaseException as failure:state.update(status='mode3_long_window_rejected_or_interrupted_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish(); passed=state['status']=='mode3_long_window_prefix_and_half_passed_pending_physical_review' and len(state['jobs'])==2
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),new_build_source_capture=prepared['new_build_source_capture'],
        prefix_all38_including_dterror=True,excluded_fields=[],physical_acceptance=False,restart_admitted=False,automatic_full_run_admitted=False,formal_admitted=False))
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
