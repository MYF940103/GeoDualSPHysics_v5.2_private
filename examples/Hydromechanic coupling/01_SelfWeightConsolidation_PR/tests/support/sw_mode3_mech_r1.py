"""One fresh mode3 k=0 mechanical isolation; root admission required, optional terminal queue."""
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

old, hg, stage, current, event, short, baseline = window.old, window.hg, window.stage, window.current, window.event, window.short, window.baseline
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = window.TESTS, window.CASE, window.LOGS, window.CONFIGS, window.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(window,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
CODEX, identity = window.CODEX, window.identity
TAG='sw_mode3_mech_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
JOB=dict(window.JOBS[0],suffix='k0')
LABEL, REFERENCE='Mode3_k0_SPR1_G1_HG0p1','Mode3_k1em3_SPR1_G1_HG0p1'


def expected(job,program):
    xml,bat=window.expected(job,program)
    xml,n=re.subn(r'(<HydraulicConductivity value=")0.001(" comment=")[^"]+("[^\n]+)',
        lambda m:m[1]+'0'+m[2]+'Mechanical isolation only; Darcy disabled without changing initial state'+m[3],xml); assert n==1
    return xml,bat.replace(window.TAG,TAG)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); xml,bat=expected(JOB,CASE/'private/solver.exe')
    signature=lambda root:[(e.tag,sorted(e.attrib.items())) for e in root.iter() if e.tag!='HydraulicConductivity']
    assert signature(ET.fromstring(xml))==signature(ET.fromstring(window.expected(JOB,CASE/'private/solver.exe')[0]))
    assert old.parameters(xml)['k']==0 and TAG in bat and window.TAG not in bat and '-partbegin' not in bat.lower()
    assert '-gpu -ompthreads:1' in bat and '-nsteps:65536' in bat
    clock,steps=window.plan(JOB); assert steps==[256*i for i in range(257)] and clock[-1]==.0234375
    assert np.array_equal(clock[steps],np.arange(257)*float(JOB['interval']))
    return dict(passed=True,files_written=False,programs_started=False,reader_started=False,only_physical_change='k .001 to 0',pore_diffusion_bound_applicable=False)


def prerequisites():
    check=read(window.CHECK); assert check['passed'] and len(check['jobs'])==2 and not check['held_jobs']; proof=[bound(window.CHECK),check['run']]+check['jobs']
    for record in check['jobs']:
        result=read(record['path']); done=read(result['sealed_completion']['path'])
        assert result['passed'] and result['hg']['passed'] and result['initial_reference']['passed'] and len(result['rows'])==257 and all(r['passed'] for r in result['pairs'])
        assert done['solver_finished'] and done['exit_code']==0 and done['owned_exited']; proof.append(result['sealed_completion'])
    verify(proof); return proof


def prepare():
    gates=prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(window.PREP); ref=next(j for j in prior['jobs'] if j['suffix']=='coarse'); attribution=prior['source_program_attribution']
    assert not attribution['exact_HG_source_at_build_time_proven'] and ref['dt']==JOB['dt'] and ref['steps']==JOB['steps']
    receipt=LOGS/(ref['name']+'.receipt.json'); result=read(receipt); done=read(result['sealed_completion']['path'])
    native=[r for r in done['outputs'] if Path(r['path']).name in ['Part_Head.ibi4','PartInfo.ibi4','Run.out'] or re.fullmatch(r'Part_\d{4}\.bi4',Path(r['path']).name)]
    assert len(native)==260
    helpers=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(CASE.parent)})
    sources=[baseline.REPO/'src/source'/n for n in ['JSph.h','JSph.cpp','JSphCpu.cpp','JSphGpu.cpp','JSphGpu_ker.h','JSphGpu_ker.cu','JSphCpuSingle.cpp','JSphGpuSingle.cpp','JDsFixedDt.cpp','JDsFixedDt.h']]
    reader=read(event.BUILD); assert reader['built'] and reader['exit_code']==0
    proof=gates+[bound(p) for p in helpers+sources+[NOTE,window.PREP,receipt,CODEX,baseline.TEMPLATE,event.BUILD,Path(sys.executable),baseline.REPO/'bin/windows/GenCase_win64.exe',baseline.REPO/'doc/xml_format/_FmtXML_ElastoplasticSoil.xml']]
    proof += native+[result['sealed_completion'],ref['program'],ref['config'],ref['bat'],reader['program'],reader['log']]+ref['runtime']+reader['inputs']+attribution['current_HG_sources']
    proof += attribution['build_receipts']+attribution['build_logs']+[attribution['prior_six_source_hash_record'],attribution['unchanged_gpu_header_archive']]
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof)
    job=dict(JOB); name=TAG+'_k0'; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat'); xml,command=expected(job,Path(ref['program']['path']))
    with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
    with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
    job.update(name=name,program=ref['program'],runtime=ref['runtime'],config=bound(cfg),bat=bound(bat),parameters=old.parameters(xml)); proof += [bound(cfg),bound(bat)]; verify(proof)
    seal(PREP,dict(utc=utc(),thread=identity(),codex=bound(CODEX),inputs=proof,job=job,reference=dict(job=ref,folder=str(OUTPUTS/ref['name']),receipt=bound(receipt),completion=result['sealed_completion'],native=native),
        source_program_attribution=attribution,physical_acceptance=False,half_or_backend_validation=False,restart_admitted=False,automatic_full_run_admitted=False))


def one_job(job,prepared,progress):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(q.exists() for q in [folder,log,complete,receipt]); verify(prepared['inputs'])
    p=job['parameters']; assert p['k']==0; clock,steps=window.plan(job); ref=prepared['reference']; b0=current.native(Path(ref['folder']),0)
    child=None; started=time.perf_counter(); rows=[]; layers=[]; focus=[]; pairs=[]; readers=[]; errors=[]; initial=None; reference={}; statistics={}; failed_part=None
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll(); count=len(list((folder/'data').glob('Part_*.bi4'))); available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    part=len(rows); failed_part=part; a=current.native(folder,part); readers.append(dict(part=part,exit_code=0))
                    if part==0:
                        initial=a; assert np.array_equal(a.to_numpy(dtype='<f8').view('<u8'),b0.to_numpy(dtype='<f8').view('<u8')),'Same mode3 initial38 mismatch'
                        reference,_=old.initial_reference(a,p); assert reference['passed']
                    row=dict(stage.measure(a,initial,part,job,clock),**short.r_summary(a,p),pore_diffusion_bound_applicable=False,pore_limit_s=None,pore_limit_passed=None,pore_limit_reason='k=0; Darcy inactive')
                    assert row['natural_step']==steps[part] and row['time_s']==clock[steps[part]]; rows.append(row)
                    b=current.native(Path(ref['folder']),part); stage.measure(b,b0,part,ref['job'],clock)
                    assert old.pore_limit(b,ref['job']['parameters'],ref['job']['dt'])['pore_limit_passed']
                    pair,_=short.pair(LABEL+'_vs_'+REFERENCE,'k_option_descriptive',part,a,part,b,initial,b0,p)
                    pair.update(variant=LABEL,reference_variant=REFERENCE,same_saved_step=int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0]),initial38_bitexact=True if part==0 else None)
                    pairs.append(pair); assert pair['time_eligible'] and pair['same_saved_step'] and not pair['gate_applied']
                    focus += [dict(part=part,**r) for r in event.focus(a).to_dict('records')]
                    for layer in stage.profiles(a,initial,part):layer.update(r_native_pa=layer['excess_native_pa']+p['Mf']*(layer['sigma_xx']+layer['sigma_yy']+layer['sigma_zz'])/(3*p['K']),included_in_r_summary=layer['layer']!=99); layers.append(layer)
                    verify([job['program'],job['config'],job['bat']]+job['runtime']+prepared['source_program_attribution']['current_HG_sources']); failed_part=None
                progress(dict(utc=utc(),owned_wrapper_pid=child.pid,solver_pids=[r['ProcessId'] for r in inventory() if job['name'] in (r.get('CommandLine') or '')],checked_frames=len(rows),latest_native=rows[-1] if rows else None,wall_seconds=time.perf_counter()-started))
                if code is not None:break
                assert time.perf_counter()-started<1800,'Bounded30-minute job timeout; stop only owned wrapper tree'
                time.sleep(2)
    except BaseException as failure:
        errors.append(dict(stage='stream_native_or_option_comparison',part=failed_part,error=repr(failure),traceback=traceback.format_exc()))
        if failed_part is not None and not any(r['part']==failed_part for r in readers):readers.append(dict(part=failed_part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
        if child is not None and child.poll() is None:subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,owned_exited=not survivors,
        surviving_owned=survivors,program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
    try:
        statistics=hg.parse_hg(text,job); assert statistics['passed'] and reference['passed'] and done['solver_finished'] and done['owned_exited']
        assert len(rows)==len(pairs)==257 and len(layers)==25700 and [r['natural_step'] for r in rows]==steps
        assert sorted(int(q.stem.split('_')[-1]) for q in (folder/'data').glob('Part_*.bi4'))==list(range(257)) and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert all(s in text for s in ['HydroMechInitMode="AnalyticalSelfWeight1D"','mode=gravity-on self-weight','hydrostatic baseline=retained','SoilBoundaryDerivativeSPR="MirroredWallDerivatives"',
            'SPR stationary wall planes (one per mk): 1','No Penetration=False','SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"',
            'PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"','SoilDampingCoef=0.02','PoreDarcySymmetricCorr="Receiver"'])
        assert float(re.search(r'HydraulicConductivity:\s*(\S+)',text)[1])==0 and int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']; verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion_or_hg',error=repr(failure),traceback=traceback.format_exc()))
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('history_r',rows),('numeric_profiles',layers),('k0_k1em3_pairs',pairs),('nativefocus',focus)]]
    result=dict(passed=not errors,errors=errors,rows=rows,pairs=pairs,hg=statistics,initial_reference=reference,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,initial38_bitexact=bool(reference),pore_diffusion_bound_applicable=False,pore_limit_passed=None,
        option_changes_are_descriptive=True,physical_acceptance=False,half_or_backend_validation=False,restart_admitted=False)
    seal(receipt,result); return result,bound(receipt)


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG} terminal: {state["status"]}. Read {RUN}, {CHECK}, tests/notes/{TAG}.json and new receipt/completion. '
        'One fresh old-frozen GPU mode3 k0 control only,dt3*2^-23,end.0234375s,65536steps,257frames. Compare retained window coarse k1e-3 at all exact actual times/steps;only initial38 fields must be0ULP. '
        'Keep all original1040ID/38-field finite/elastic/no-exclusion/geometry/p0/float32excess/drainage/clock/signed-natural/HG guards. k0 pore diffusion bound is NOT APPLICABLE,limit/pass null;never claim a diffusion-budget pass. '
        'All pressure/material displacement/stress/velocity/R changes are descriptive k isolation,not5Pa half/backend errors. Same old binary retains exact_HG_source_at_build_time_proven=false. '
        'Inspect initial mechanical/preload transient versus coupled diffusion before any longer/full admission. No physical/full/restart acceptance follows from safe completion. '
        'Completed-solver analysis failure needs offline repair,not rerun. Preserve all evidence,no duplicate solver,old-worker restart,guard relaxation,rearm or selftest notification. Protect Cryer/formal/retained results. Report Chinese proactively and continue authorized reviewed diagnosis. One terminal notification only.')
    assert len(message)<2000; seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message))
    try:
        reply=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if reply.returncode==0 else 'queue_failed_no_retry',exit_code=reply.returncode,reply=(reply.stdout+reply.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def run(send_notification=False):
    prerequisites(); prepared=read(PREP); verify(prepared['inputs']); assert identity()==prepared['thread'] and bound(CODEX)==prepared['codex'] and not RUN.exists() and not CHECK.exists() and not inventory()
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),thread=prepared['thread'],prepared=bound(PREP),jobs=[],launched=False,terminal_notification_requested=send_notification)
    def publish():
        temporary=RUN.with_suffix('.tmp'); seal(temporary,state); os.replace(temporary,RUN)
    def progress(value):state.update(progress=value,launched=True); publish()
    publish()
    try:
        result,receipt=one_job(prepared['job'],prepared,progress); state['jobs'].append(receipt); state['launched']|=result['owned_wrapper_pid'] is not None; publish()
        assert result['passed'],result['errors']; verify(prepared['inputs']); state['status']='mode3_k0_complete_pending_causal_review'
    except BaseException as failure:state.update(status='mode3_k0_rejected_or_interrupted_pending_review',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc()); publish(); passed=state['status']=='mode3_k0_complete_pending_causal_review' and len(state['jobs'])==1
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],error=state.get('error'),source_program_attribution=prepared['source_program_attribution'],
        option_changes_are_descriptive=True,physical_acceptance=False,half_or_backend_validation=False,restart_admitted=False,automatic_full_run_admitted=False))
    if send_notification and state['launched']:notify(state)
    return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    parser.add_argument('--notify',action='store_true',help='Explicitly request one terminal queue with --run only')
    args=parser.parse_args(); assert not args.notify or args.run,'--notify requires --run'
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run(args.notify) else 1)
    else:parser.print_help()
