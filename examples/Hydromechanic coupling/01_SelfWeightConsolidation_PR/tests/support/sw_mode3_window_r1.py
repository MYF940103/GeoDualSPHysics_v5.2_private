"""Two fresh dyadic GPU mode3 windows; original safety/half gates, one terminal notification."""
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
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import sw_mode3_short_r1 as old

hg, stage, current, event, short, baseline = old.hg, old.stage, old.current, old.event, old.short, old.baseline
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = old.TESTS, old.CASE, old.LOGS, old.CONFIGS, old.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(old,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
CODEX, identity = stage.CODEX, stage.identity
TAG = 'sw_mode3_window_r1'
PREP, RUN, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE = TESTS/'notes'/(TAG+'.json')
JOBS = [dict(suffix=s,backend='gpu',threads=1,dt=dt,shepard=sh,on=False,end='0.0234375',interval='0.000091552734375',steps=n,frames=257)
        for s,dt,sh,n in [('coarse','0.00000035762786865234375',40,65536),('half','0.000000178813934326171875',80,131072)]]


def expected(job,program):
    xml,bat=old.expected(job,program)
    return xml,bat.replace(old.TAG,TAG)


def plan(job):
    clock=stage.clock_table(job['dt'],job['steps']); interval=float(job['interval'])
    count=math.floor(float(job['end'])/interval)
    result=[int(np.searchsorted(clock,np.float64(i*interval),side='left')) for i in range(count+1)]
    assert result==[math.ceil(i*interval/float(job['dt'])) for i in range(count+1)] and len(result)==job['frames']
    return clock,result


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); clocks=[]
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); tree=ET.fromstring(xml); value=lambda k:tree.find('.//parameter[@key="'+k+'"]').get('value')
        assert value('DtIni')==value('DtFixed')==job['dt'] and value('TimeMax')==job['end'] and value('TimeOut')==job['interval']
        assert value('SoilHourglassXi')=='0.1' and value('SoilBoundaryDerivativeSPR')==value('SoilStressRateGradCorr')==value('SavePosDouble')=='1'
        assert tree.find('.//HydroMechInitMode').get('value')=='3' and tree.find('.//HydraulicConductivity').get('value')=='0.001'
        assert tree.find('.//PoreShepardRegularization').get('value')=='0' and value('SlipMode')=='1' and value('SoilDampingCoef')=='0.02'
        assert TAG in bat and old.TAG not in bat and '-gpu -ompthreads:1' in bat and ('-nsteps:'+str(job['steps'])) in bat and '-partbegin' not in bat.lower()
        clock,steps=plan(job); stride=256 if job['suffix']=='coarse' else 512
        assert steps==[stride*i for i in range(257)] and np.array_equal(clock,np.arange(job['steps']+1)*float(job['dt']))
        assert np.array_equal(clock[steps],np.arange(257)*float(job['interval'])) and clock[-1]==float(job['end']); clocks.append(clock[steps])
        p=old.parameters(xml); assert old.pore_limit(pd.DataFrame(dict(h=[float(np.float32(.018))])),p,job['dt'])['pore_limit_passed']
    assert np.array_equal(*clocks)
    return dict(passed=True,files_written=False,programs_started=False,reader_started=False,paired_clock_max_difference_s=0.,frames=257,no_same_dt_short_prefix=True)


def prerequisites():
    check=read(old.CHECK); assert check['passed'] and len(check['jobs'])==3 and not check['held_jobs']; proof=[bound(old.CHECK),check['run']]+check['jobs']
    for record in check['jobs']:
        result=read(record['path']); done=read(result['sealed_completion']['path'])
        assert result['passed'] and result['hg']['passed'] and result['initial_reference']['passed'] and len(result['rows'])==5
        assert all(r['passed'] for r in result['pairs']) and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
        proof.append(result['sealed_completion'])
    verify(proof); return proof


def prepare():
    gates=prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(old.PREP); source=next(j for j in prior['jobs'] if j['suffix']=='gpu'); attribution=prior['source_program_attribution']
    assert not attribution['exact_HG_source_at_build_time_proven']
    receipt=LOGS/(source['name']+'.receipt.json'); result=read(receipt); done=read(result['sealed_completion']['path'])
    initial_outputs=[r for r in done['outputs'] if Path(r['path']).name in ['Part_0000.bi4','Part_Head.ibi4','PartInfo.ibi4']]
    assert len(initial_outputs)==3
    helpers=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(CASE.parent)})
    sources=[baseline.REPO/'src/source'/n for n in ['JSph.h','JSph.cpp','JSphCpu.cpp','JSphGpu.cpp','JSphGpu_ker.h','JSphGpu_ker.cu','JSphCpuSingle.cpp','JSphGpuSingle.cpp','JDsFixedDt.cpp','JDsFixedDt.h']]
    reader=read(event.BUILD); assert reader['built'] and reader['exit_code']==0
    proof=gates+[bound(p) for p in helpers+sources+[NOTE,old.PREP,receipt,CODEX,baseline.TEMPLATE,event.BUILD,Path(sys.executable),
        baseline.REPO/'bin/windows/GenCase_win64.exe',baseline.REPO/'doc/xml_format/_FmtXML_ElastoplasticSoil.xml']]
    proof += [source['program'],reader['program'],reader['log'],result['sealed_completion']]+source['runtime']+reader['inputs']+initial_outputs
    proof += attribution['current_HG_sources']+attribution['build_receipts']+attribution['build_logs']+[attribution['prior_six_source_hash_record'],attribution['unchanged_gpu_header_archive']]
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat'); xml,command=expected(job,Path(source['program']['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=source['program'],runtime=source['runtime'],config=bound(cfg),bat=bound(bat),parameters=old.parameters(xml)); jobs.append(job); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),thread=identity(),codex=bound(CODEX),inputs=proof,jobs=jobs,
        initial_reference=dict(folder=str(OUTPUTS/source['name']),receipt=bound(receipt),completion=result['sealed_completion'],outputs=initial_outputs),
        source_program_attribution=attribution,no_same_dt_short_prefix=True,physical_acceptance=False,restart_admitted=False,automatic_full_run_admitted=False))


def one_job(job,prepared,short_initial,coarse,progress):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(q.exists() for q in [folder,log,complete,receipt]); verify(prepared['inputs'])
    p=job['parameters']; clock,steps=plan(job); child=None; started=time.perf_counter(); rows=[]; layers=[]; focus=[]; readers=[]; frames={}; pairs=[]; errors=[]; reference={}; statistics={}; failed_part=None
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll(); count=len(list((folder/'data').glob('Part_*.bi4'))); available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    part=len(rows); failed_part=part; a=current.native(folder,part); readers.append(dict(part=part,exit_code=0)); frames[part]=a
                    row=dict(stage.measure(a,frames[0],part,job,clock),**short.r_summary(a,p),**old.pore_limit(a,p,job['dt']))
                    assert row['pore_limit_passed'] and row['natural_step']==steps[part] and row['time_s']==clock[steps[part]]
                    if part==0:
                        assert np.array_equal(a.to_numpy(dtype='<f8').view('<u8'),short_initial.to_numpy(dtype='<f8').view('<u8')),'Only initial38 shared with old short'
                        reference,_=old.initial_reference(a,p); assert reference['passed']
                    rows.append(row); focus += [dict(part=part,**r) for r in event.focus(a).to_dict('records')]
                    for layer in stage.profiles(a,frames[0],part):layer.update(r_native_pa=layer['excess_native_pa']+p['Mf']*(layer['sigma_xx']+layer['sigma_yy']+layer['sigma_zz'])/(3*p['K']),included_in_r_summary=layer['layer']!=99); layers.append(layer)
                    if job['suffix']=='half':
                        pair,_=short.pair(job['name']+'_vs_coarse','gpu_half',part,a,part,coarse[part],frames[0],coarse[0],p); pairs.append(pair); assert pair['passed'],pair
                    verify([job['program'],job['config'],job['bat']]+job['runtime']+prepared['source_program_attribution']['current_HG_sources']); failed_part=None
                solver_pids=[r['ProcessId'] for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
                progress(dict(utc=utc(),owned_wrapper_pid=child.pid,solver_pids=solver_pids,checked_frames=len(rows),latest_native=rows[-1] if rows else None,wall_seconds=time.perf_counter()-started))
                if code is not None:break
                assert time.perf_counter()-started<1800,'Bounded 30-minute job timeout; stop only owned wrapper tree'
                time.sleep(2)
    except BaseException as failure:
        errors.append(dict(stage='stream_native_or_half_gate',part=failed_part,error=repr(failure),traceback=traceback.format_exc()))
        if failed_part is not None and not any(r['part']==failed_part for r in readers):readers.append(dict(part=failed_part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
        if child is not None and child.poll() is None:subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,owned_exited=not survivors,
        surviving_owned=survivors,program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
    try:
        statistics=hg.parse_hg(text,job); assert statistics['passed'] and reference['passed'] and done['solver_finished'] and done['owned_exited']
        assert len(rows)==job['frames'] and len(layers)==100*job['frames'] and [r['natural_step'] for r in rows]==steps
        assert sorted(int(q.stem.split('_')[-1]) for q in (folder/'data').glob('Part_*.bi4'))==list(range(job['frames']))
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert len(pairs)==(job['frames'] if job['suffix']=='half' else 0) and all(r['passed'] for r in pairs)
        assert all(s in text for s in ['HydroMechInitMode="AnalyticalSelfWeight1D"','mode=gravity-on self-weight','hydrostatic baseline=retained','SoilBoundaryDerivativeSPR="MirroredWallDerivatives"',
            'SPR stationary wall planes (one per mk): 1','No Penetration=False','SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"',
            'PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"','SoilDampingCoef=0.02','PoreDarcySymmetricCorr="Receiver"'])
        assert float(re.search(r'HydraulicConductivity:\s*(\S+)',text)[1])==.001 and int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']; verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion_or_hg',error=repr(failure),traceback=traceback.format_exc()))
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('history_r',rows),('numeric_profiles',layers),('nativefocus',focus)]+([('half_pairs',pairs)] if pairs else [])]
    result=dict(passed=not errors,errors=errors,rows=rows,pairs=pairs,hg=statistics,initial_reference=reference,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,initial38_only=True,no_same_dt_short_prefix=True,physical_acceptance=False,restart_admitted=False)
    seal(receipt,result); return result,bound(receipt),frames


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG} terminal: {state["status"]}. Read {RUN}, {CHECK}, tests/notes/{TAG}.json and both new receipts/completions. '
        'Only fresh GPU dyadic coarse3*2^-23/half3*2^-24 to.0234375s,65536/131072steps,257frames each were admitted; same old frozen program,exact_HG_source_at_build_time_proven=false. '
        'Verify owned exits,1040IDs/all38 original guards,exact dyadic saved clocks,all frozen hashes,p0/float32excess,active10drain,pore/natural limits and HG call/cache/dt/spin. '
        'Both old2ms jobs share initial38 only: dt changed and no same-dt prefix exists. Require original all257sample5Pa/.005mm independent half gate without interpolation or rewritten metadata. '
        'Normal exit/half agreement are not theory,equilibrium,full-consolidation,restart or formal acceptance. Review initial overshoot,decay,volume-strain/pressure consistency and the actual initial-state reference offline before any further full admission. '
        'If only analysis failed repair offline,never rerun a completed solver; runtime failure requires exact reason/time/survivor audit. Preserve outputs,no relaxed guards,duplicate solver,old-worker restart,rearm or selftest notification. '
        'Report Chinese proactively and continue the authorized bounded review without a progress question. Cryer server,formal cases and retained results remain protected. One terminal notification only.')
    assert len(message)<2000; seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message))
    try:
        reply=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if reply.returncode==0 else 'queue_failed_no_retry',exit_code=reply.returncode,reply=(reply.stdout+reply.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def run():
    prerequisites(); prepared=read(PREP); verify(prepared['inputs']); assert identity()==prepared['thread'] and bound(CODEX)==prepared['codex'] and not RUN.exists() and not CHECK.exists() and not inventory()
    ref=prepared['initial_reference']; verify([ref['receipt'],ref['completion']]+ref['outputs']); initial=current.native(Path(ref['folder']),0); coarse={}
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),thread=prepared['thread'],prepared=bound(PREP),jobs=[],launched=False)
    def publish():
        temp=RUN.with_suffix('.tmp'); seal(temp,state); os.replace(temp,RUN)
    def progress(value):state.update(progress=value,launched=True); publish()
    publish()
    try:
        for job in prepared['jobs']:
            state.update(current_job=job['name'],progress=None); publish(); result,receipt,frames=one_job(job,prepared,initial,coarse,progress)
            state['jobs'].append(receipt); state['launched']|=result['owned_wrapper_pid'] is not None; publish(); assert result['passed'],('Earlier gate failed; later job held',job['name'],result['errors'])
            if job['suffix']=='coarse':coarse=frames
        verify(prepared['inputs']); state['status']='mode3_dyadic_window_half_passed_pending_physical_review'
    except BaseException as failure:state.update(status='mode3_window_rejected_or_interrupted_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish(); passed=state['status']=='mode3_dyadic_window_half_passed_pending_physical_review' and len(state['jobs'])==2
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),source_program_attribution=prepared['source_program_attribution'],
        initial38_only=True,no_same_dt_short_prefix=True,physical_acceptance=False,restart_admitted=False,automatic_full_run_admitted=False))
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
