"""One admitted fresh root PR diagnostic; original native guards, sealed solve, then offline postprocessing."""
import argparse
import ast
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import numpy as np
import sw_mode3_longwin_r1 as old
import sw_freshpr_prepare_r1 as package

TESTS, CASE, LOGS = old.TESTS, old.CASE, old.LOGS
read, seal, verify, unique, bound, utc, inventory = [getattr(old,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG='sw_freshpr_run_r1'; PREP=LOGS/'sw_freshpr_prepare_r2.inputs.json'; NOTE=TESTS/'notes'/(TAG+'.json')
MONITOR, RUN, CHECK, COMPLETE, RECEIPT = [LOGS/(TAG+s) for s in ['.monitor.inputs.json','.run.json','.check.json','.completion.json','.receipt.json']]
POSTCHECK=CASE/'figures'/('CaseSelfWeightConsolidation_Scenario2_FreshPR_nativepr_manifest.json')
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'; CODEX=old.CODEX; DT=3*2.**-23; STEPS=20459420; FRAMES=403


class DyadicClock:
    def __init__(self,steps):
        assert 0<=steps and 3*steps<2**53; self.steps=steps
    def __getitem__(self,n):
        assert int(n)==n and 0<=n<=self.steps
        return float(3*int(n))*2.**-23


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); clock=DyadicClock(STEPS); accumulated=0.
    for n in range(262145):
        assert accumulated==clock[n]
        accumulated+=DT
    plan=package.plan(); assert plan['frames']==FRAMES and plan['saved_steps'][-1]==STEPS and plan['actual_end_s']==clock[STEPS]
    assert all(clock[n]==t for n,t in zip(plan['saved_steps'],plan['saved_times_s']))
    assert clock[STEPS-1]<float(package.END)<=clock[STEPS] and clock[STEPS]==7.316858768463135
    assert set(plan['saved_steps'])&set(range(0,262145,256))=={0},'Changed cadence shares initial state only'
    return dict(passed=True,files_written=False,programs_started=False,reader_started=False,maximum_clock_storage_values=1,recurrence_test_steps=262144)


def tree(root_pid):
    command='@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate) | ConvertTo-Json -Compress'
    raw=subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True,creationflags=subprocess.CREATE_NO_WINDOW).strip(); processes=json.loads(raw) if raw else []
    if isinstance(processes,dict):processes=[processes]
    if root_pid is None:return processes
    owned={root_pid}; last=-1
    while len(owned)!=last:
        last=len(owned); owned.update(int(p['ProcessId']) for p in processes if int(p['ParentProcessId']) in owned)
    return [p for p in processes if int(p['ProcessId']) in owned]


def stop(child):
    record=dict(utc=utc(),wrapper_pid=child.pid,tree_before=tree(child.pid),termination_requested=False)
    if child.poll() is None:
        result=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        record.update(termination_requested=True,exit_code=result.returncode,reply=(result.stdout+result.stderr).decode(errors='replace')); child.wait(timeout=30)
    record['tree_after']=tree(child.pid); return record


def monitor_prepare():
    selftest(); prepared=read(PREP); assert len(prepared['jobs'])==1 and prepared['formal_candidate_prepared'] and not prepared['physical_acceptance'] and not prepared['restart_admitted']
    job=prepared['jobs'][0]; assert job['name']==package.NAME and job['backend']=='gpu' and job['steps']==STEPS and job['frames']==FRAMES and float(job['dt'])==DT
    assert prepared['clock_plan']==package.plan() and prepared['new_build_source_capture']['sources_captured_before_build']
    assert old.identity()==THREAD and not inventory() and not list(LOGS.glob(TAG+'*')) and not list(old.event.FIGURES.glob(TAG+'*')) and not any(p.exists() for p in [CASE/(job['name']+'_out'),POSTCHECK])
    proof=prepared['inputs']+[bound(PREP),prepared['manifest'],bound(NOTE),bound(CODEX),bound(Path(sys.executable))]
    helpers=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(CASE.parent)})
    reader=read(old.event.BUILD); assert reader['built'] and reader['exit_code']==0
    proof += [bound(p) for p in helpers]+[bound(old.event.BUILD),reader['program'],reader['log']]+reader['inputs']
    proof += [r['original'] for r in prepared['capture']['selected_snapshots']]
    prior=read(old.PREP); source=prior['jobs'][0]; rr=LOGS/(source['name']+'.receipt.json'); r=read(rr); done=read(r['sealed_completion']['path'])
    assert r['passed'] and r['initial_reference']['passed'] and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
    initial=[r for r in done['outputs'] if Path(r['path']).name in ['Part_0000.bi4','Part_Head.ibi4','PartInfo.ibi4']]; assert len(initial)==3
    proof += [bound(old.PREP),bound(rr),r['sealed_completion']]+initial; proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof)
    monitor=dict(utc=utc(),thread=THREAD,codex=bound(CODEX),prepared=bound(PREP),inputs=proof,job=job,clock_plan=prepared['clock_plan'],
        initial_reference=dict(folder=str(old.OUTPUTS/source['name']),receipt=bound(rr),completion=r['sealed_completion'],outputs=initial),actual_shared_reference_natural_steps=[0],
        no_same_cadence_prefix=True,no_full_cycle_half=True,physical_acceptance=False,formal_acceptance=False)
    seal(MONITOR,monitor); return monitor


def execute(monitor,progress):
    job=monitor['job']; folder=CASE/(job['name']+'_out'); log=LOGS/(TAG+'.solver.log'); clock=DyadicClock(job['steps']); plan=monitor['clock_plan']; p=job['parameters']
    verify(monitor['inputs']); initial=old.current.native(Path(monitor['initial_reference']['folder']),0); first=None; child=None; started=time.perf_counter(); last_tree=-60.; owned=[]; rows=[]; layers=[]; focus=[]; readers=[]; initial_fields=[]; errors=[]; reference={}; hg={}; stopped=None; failed_part=None
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path'],'-solver-only'],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            progress(dict(stage='solver',owned_wrapper_pid=child.pid,owned_tree=[],checked_frames=0)); owned=tree(child.pid)
            while True:
                code=child.poll(); count=len(list((folder/'data').glob('Part_*.bi4'))); available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    part=len(rows); failed_part=part; assert part<FRAMES; a=old.current.native(folder,part); readers.append(dict(part=part,exit_code=0))
                    if first is None:
                        first=a; exact,initial_fields=old.release.exact(a,initial,0); assert exact['passed'],'Initial38 changed; cadence does not justify a noninitial prefix claim'
                        reference,_=old.old.initial_reference(a,p); assert reference['passed']
                    row=dict(old.stage.measure(a,first,part,job,clock),**old.short.r_summary(a,p),**old.old.pore_limit(a,p,job['dt'])); rows.append(row)
                    assert row['pore_limit_passed'] and row['natural_step']==plan['saved_steps'][part] and row['time_s']==plan['saved_times_s'][part]
                    focus += [dict(part=part,**r) for r in old.event.focus(a).to_dict('records')]
                    for layer in old.stage.profiles(a,first,part):layer.update(r_native_pa=layer['excess_native_pa']+p['Mf']*(layer['sigma_xx']+layer['sigma_yy']+layer['sigma_zz'])/(3*p['K']),included_in_r_summary=layer['layer']!=99); layers.append(layer)
                    verify([job['program'],job['config'],job['bat']]+job['runtime']); failed_part=None
                elapsed=time.perf_counter()-started
                if elapsed-last_tree>=60 or code is not None:owned=tree(child.pid); last_tree=elapsed
                progress(dict(stage='solver',utc=utc(),owned_wrapper_pid=child.pid,owned_tree=owned,checked_frames=len(rows),latest_native=rows[-1] if rows else None,wall_seconds=elapsed))
                if code is not None:break
                assert elapsed<96*3600,'96-hour owned-job wall bound exceeded'
                time.sleep(5)
    except BaseException as failure:
        errors.append(dict(stage='solver_native_guard',part=failed_part,error=repr(failure),traceback=traceback.format_exc()))
        if child is not None:stopped=stop(child)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; active=tree(None)
    survivors=[r for r in active if job['name'] in (r.get('CommandLine') or '') and r['Name'].lower().startswith(('dualsphysics','gencase'))]
    survivors += [r for r in active if any(all(r[k]==v[k] for k in ['ProcessId','CreationDate','Name','CommandLine']) for v in owned)]
    completion=dict(utc=utc(),exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors and (child is None or child.poll() is not None),surviving_owned=survivors,owned_wrapper_pid=None if child is None else child.pid,last_owned_tree=owned,stop=stopped,
        program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],output_hashes_sealed=not survivors,
        outputs=([bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])) if not survivors else []); seal(COMPLETE,completion)
    try:
        hg=old.hg.parse_hg(text,job); assert hg['passed'] and reference['passed'] and completion['solver_finished'] and completion['owned_exited']
        assert len(rows)==FRAMES and len(layers)==100*FRAMES and [r['natural_step'] for r in rows]==plan['saved_steps'] and rows[-1]['time_s']==clock[STEPS]
        assert sorted(int(q.stem.split('_')[-1]) for q in (folder/'data').glob('Part_*.bi4'))==list(range(FRAMES)) and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==STEPS
        assert all(s in text for s in ['HydroMechInitMode="AnalyticalSelfWeight1D"','mode=gravity-on self-weight','hydrostatic baseline=retained','SoilBoundaryDerivativeSPR="MirroredWallDerivatives"','SPR stationary wall planes (one per mk): 1',
            'No Penetration=False','SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"','PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"','SoilDampingCoef=0.02','PoreDarcySymmetricCorr="Receiver"'])
        assert float(re.search(r'HydraulicConductivity:\s*(\S+)',text)[1])==.001 and int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==40; verify(monitor['inputs'])
    except BaseException as failure:errors.append(dict(stage='sealed_solver_completion_or_hg',error=repr(failure),traceback=traceback.format_exc()))
    artifacts=[old.event.write_csv(TAG+'_'+kind,data) for kind,data in [('history_r',rows),('numeric_profiles',layers),('nativefocus',focus),('initial38_fields',initial_fields)]]
    result=dict(passed=not errors,errors=errors,rows=rows,hg=hg,initial_reference=reference,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(COMPLETE),wall_seconds=time.perf_counter()-started,
        owned_wrapper_pid=None if child is None else child.pid,initial38_only=True,no_same_cadence_prefix=True,no_full_cycle_half=True,physical_acceptance=False,formal_acceptance=False)
    seal(RECEIPT,result); return result


def postprocess(monitor,progress):
    job=monitor['job']; log=LOGS/(TAG+'.postprocess.log'); child=None; errors=[]; report=None; started=time.perf_counter(); env=dict(os.environ,PYTHON=sys.executable)
    try:
        verify(monitor['inputs']); assert not POSTCHECK.exists()
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path'],'-postprocess'],cwd=CASE,env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            progress(dict(stage='postprocess_only_no_solver',owned_wrapper_pid=child.pid,owned_tree=tree(child.pid))); child.wait(timeout=7200)
        assert child.returncode==0 and not tree(child.pid); loaded=read(POSTCHECK); assert isinstance(loaded,dict); report=loaded
        assert all(report[k] for k in ['passed','analysis_checks_passed','postprocessing_completed','native_safety_passed'])
        assert not any(report[k] for k in ['physical_acceptance','formal_acceptance','automatic_full_acceptance']); verify(report['artifacts']); verify(monitor['inputs'])
    except BaseException as failure:
        errors.append(dict(error=repr(failure),traceback=traceback.format_exc()))
        if child is not None:stop(child)
    result=dict(passed=not errors,errors=errors,exit_code=None if child is None else child.returncode,owned_wrapper_pid=None if child is None else child.pid,log=bound(log) if log.exists() else None,
        manifest=bound(POSTCHECK) if POSTCHECK.exists() else None,artifacts=[] if report is None else report.get('artifacts',[]),residual_floor_budget_diagnostic_met=None if report is None else report.get('residual_floor_budget_diagnostic_met'),
        wall_seconds=time.perf_counter()-started,solver_rerun=False,physical_acceptance=False,formal_acceptance=False); seal(LOGS/(TAG+'.postprocess.check.json'),result); return result


def notify(state):
    assert old.identity()==THREAD and state['thread']==THREAD
    message=(f'User-authorized same-thread {TAG} terminal: {state["status"]}. Read {RUN}, {CHECK}, tests/notes/{TAG}.json, monitor inputs, solver receipt/completion and postprocess check. '
        'Only fresh root CaseSelfWeightConsolidation_Scenario2_FreshPR_out was admitted: dt3*2^-23,20459420steps,403 nativeframes,actualend7.316858768463135s. No PART restart or full-cycle half validation. '
        'Verify owned exits,all1040IDs/all38 original safety,p0/float32excess,actual planned saved clocks,configured pore/natural limits,full HGcalls/cache/dt/spin and every frozen source-build-input-program-runtime-output hash. '
        'Cadence changed: initial38 equality is not a longwin prefix. Solver completion was sealed before BAT-postprocess;check nativepr manifest and inspect formal PNGs plus matching CSVs,actual finite/legacyTv,settlement/stress and late-floor diagnostics. '
        'Bounded half and startup/near-top~178Pa residual permitted full diagnostic only,not physical acceptance. Keep<=5Pa late-pressure floor budget separate from half bound;no100Pa uniform-stress gate applies. '
        'If postprocessing alone failed repair new offline analysis only,NEVER rerun completed solver. On runtime failure report exact sealed time/reason and surviving owned processes. Preserve outputs,no duplicate solver,relaxed guards,old-worker restart,rearm or connectivity selftest. '
        'Proactively report Chinese conclusions and continue authorized review without a progress prompt;Cryer/server and all retained/formal results stay protected. One terminal notification only.')
    assert len(message)<2000; seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=THREAD,message=message))
    try:
        reply=subprocess.run([str(CODEX),'queue','--thread',THREAD,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if reply.returncode==0 else 'queue_failed_no_retry',exit_code=reply.returncode,reply=(reply.stdout+reply.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def run():
    monitor=monitor_prepare(); state=dict(status='running',utc=utc(),thread=THREAD,worker_pid=os.getpid(),prepared=bound(PREP),monitor=bound(MONITOR),launched=False)
    def publish():
        temporary=RUN.with_suffix('.tmp'); seal(temporary,state); os.replace(temporary,RUN)
    def progress(value):state.update(progress=value,launched=True); publish()
    publish(); solver=None; post=None
    try:
        solver=execute(monitor,progress); state['solver_receipt']=bound(RECEIPT); publish(); assert solver['passed'],solver['errors']
        post=postprocess(monitor,progress); state['postprocess_check']=bound(LOGS/(TAG+'.postprocess.check.json')); publish()
        state['status']='freshpr_safe_solver_and_postprocess_completed_pending_physical_review' if post['passed'] else 'freshpr_solver_completed_postprocess_failed_repair_offline_only'
    except BaseException as failure:state.update(status='freshpr_rejected_or_interrupted',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc()); publish()
    passed=bool(solver and solver['passed'] and post and post['passed']); seal(CHECK,dict(passed=passed,run=bound(RUN),solver_checks_passed=bool(solver and solver['passed']),postprocessing_checks_passed=bool(post and post['passed']),
        solver_receipt=bound(RECEIPT) if RECEIPT.exists() else None,postprocess_check=state.get('postprocess_check'),error=state.get('error'),physical_acceptance=False,formal_acceptance=False,no_full_cycle_half=True,no_same_cadence_prefix=True))
    if state['launched']:notify(state)
    return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(); modes.add_argument('--selftest',action='store_true'); modes.add_argument('--run',action='store_true'); args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
