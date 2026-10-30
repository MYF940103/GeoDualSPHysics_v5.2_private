"""One fresh GPU HG=.1/SPR1/G1/ShepardOFF Stage1 diagnostic; no follow-on run."""
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
import sw_hg_short_r1 as hg
import sw_spr_stage1_r1 as retained

stage, current, event, short = hg.stage, hg.current, hg.event, hg.short
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = hg.TESTS, hg.CASE, hg.LOGS, hg.CONFIGS, hg.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(hg,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG='sw_hg_stage1_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
CODEX, identity = stage.CODEX, stage.identity
VARIANT, REFERENCE='HGxi0p1_SPR1_G1_ShepardOFF','HGxi0_SPR1_G1_ShepardOFF'
JOB=dict(suffix='hg1_spr1_g1_off',backend='gpu',threads=1,dt='0.000001',shepard=40,on=False,end='0.30',interval='0.005',steps=300001,frames=61)


def expected(job,program):
    xml,bat=hg.expected(job,program)
    return xml.replace('short diagnostic only','Stage1 diagnostic; no equilibrium or restart acceptance'),bat.replace(hg.TAG,TAG)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); xml,bat=expected(JOB,CASE/'private/solver.exe'); tree=ET.fromstring(xml)
    value=lambda key:tree.find('.//parameter[@key="'+key+'"]').get('value')
    assert value('SoilHourglassXi')=='0.1' and len(tree.findall('.//parameter[@key="SoilHourglassXi"]'))==1
    assert value('SoilBoundaryDerivativeSPR')==value('SoilStressRateGradCorr')=='1' and value('SlipMode')=='1'
    assert value('TimeMax')=='0.30' and value('TimeOut')=='0.005' and value('DtIni')==value('DtFixed')=='0.000001' and value('SavePosDouble')=='1'
    assert tree.find('.//PoreShepardRegularization').get('value')=='0' and tree.find('.//HydraulicConductivity').get('value')=='0'
    signature=lambda root:[(e.tag,sorted(e.attrib.items())) for e in root.iter() if e.get('key')!='SoilHourglassXi']
    assert signature(tree)==signature(ET.fromstring(retained.expected(JOB,CASE/'private/solver.exe')[0]))
    assert TAG in bat and hg.TAG not in bat and '-gpu -ompthreads:1' in bat and '-nsteps:300001' in bat and '-partbegin' not in bat.lower()
    clock=stage.clock_table(JOB['dt'],JOB['steps']); assert clock[0]==0 and np.all(np.diff(clock)>0) and abs(clock[-1]-JOB['steps']*float(JOB['dt']))>1e-12
    return dict(passed=True,programs_started=False,files_written=False)


def prerequisites():
    proof=[]
    for path,count,frames in [(hg.CHECK,3,5),(retained.CHECK,1,61)]:
        check=read(path); assert check['passed'] and len(check['jobs'])==count and not check.get('held_jobs',[])
        proof += [bound(path),check['run']]+check['jobs']
        for record in check['jobs']:
            result=read(record['path']); done=read(result['sealed_completion']['path'])
            assert result['passed'] and len(result['rows'])==frames and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
            if path==hg.CHECK:assert result['hg']['passed'] and all(r['comparison_valid'] and (not r['gate_applied'] or r['passed']) for r in result['pairs'])
            proof += [result['sealed_completion']]+done['outputs']+result['artifacts']
    record=read(retained.CHECK)['analysis']; analysis=read(record['path']); assert analysis['passed']; proof += [record]+analysis['artifacts']
    verify(proof); return proof


def prepare():
    gates=prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(hg.PREP); gpu=next(j for j in prior['jobs'] if j['suffix']=='gpu'); old=read(retained.PREP); control=old['job']
    assert identity()==old['thread'] and bound(CODEX)==old['codex'] and gpu['program']==control['program'] and gpu['runtime']==control['runtime']
    assert not prior['source_program_attribution']['exact_HG_source_at_build_time_proven']
    oldreceipt=LOGS/(control['name']+'.receipt.json'); result=read(oldreceipt); done=read(result['sealed_completion']['path']); shortreceipt=LOGS/(gpu['name']+'.receipt.json')
    proof=prior['inputs']+gates+[bound(p) for p in [__file__,NOTE,hg.__file__,hg.PREP,retained.__file__,retained.PREP,oldreceipt,shortreceipt,CODEX]]
    proof += [result['sealed_completion'],control['config'],control['bat'],gpu['program']]+gpu['runtime']+done['outputs']; proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof)
    job=dict(JOB); name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat'); xml,command=expected(job,Path(gpu['program']['path']))
    with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
    with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
    job.update(name=name,program=gpu['program'],runtime=gpu['runtime'],config=bound(cfg),bat=bound(bat)); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),thread=old['thread'],codex=old['codex'],inputs=proof,job=job,parameters=prior['parameters'],source_program_attribution=prior['source_program_attribution'],
        short_folder=str(OUTPUTS/gpu['name']),short_receipt=bound(shortreceipt),hg0=dict(name=control['name'],folder=str(OUTPUTS/control['name']),dt=control['dt'],steps=control['steps'],
        receipt=bound(oldreceipt),completion=result['sealed_completion'],outputs=done['outputs'],rows=result['rows']),physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))


def one_job(job,prepared,control,short_initial,progress):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt]); verify(prepared['inputs'])
    child=None; started=time.perf_counter(); rows=[]; layers=[]; focus=[]; pairs=[]; readers=[]; errors=[]; initial=None; failed_part=None; statistics={}; solver_pids=[]
    clock=stage.clock_table(job['dt'],job['steps']); p=prepared['parameters']
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll(); count=len(list((folder/'data').glob('Part_*.bi4'))); available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    part=len(rows); failed_part=part; a=current.native(folder,part); readers.append(dict(part=part,exit_code=0))
                    focus += [dict(r,part=part,variant=VARIANT) for r in event.focus(a).to_dict('records')]
                    if part==0:
                        initial=a; assert np.array_equal(a.to_numpy(dtype='<f8').view('<u8'),short_initial.to_numpy(dtype='<f8').view('<u8')),'Own HG short initial38 mismatch'
                    row=dict(stage.measure(a,initial,part,job,clock),variant=VARIANT,**short.r_summary(a,p))
                    if rows:assert row['natural_step']>rows[-1]['natural_step'] and row['time_s']>rows[-1]['time_s']
                    rows.append(row)
                    for layer in stage.profiles(a,initial,part):layer.update(r_native_pa=layer['excess_native_pa']+p['Mf']*(layer['sigma_xx']+layer['sigma_yy']+layer['sigma_zz'])/(3*p['K']),included_in_r_summary=layer['layer']!=99); layers.append(layer)
                    b=control[part]; pair,_=short.pair(VARIANT+'_minus_'+REFERENCE,'hg_option_descriptive',part,a,part,b,initial,control[0],p)
                    pair.update(variant=VARIANT,reference_variant=REFERENCE,same_saved_step=int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0])); pairs.append(pair)
                    assert pair['time_eligible'] and pair['same_saved_step'] and not pair['gate_applied'],'Actual saved-state mismatch'
                    verify([job['program'],job['config'],job['bat']]+job['runtime']+prepared['source_program_attribution']['current_HG_sources'])
                    failed_part=None; solver_pids=[r['ProcessId'] for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
                progress(dict(utc=utc(),owned_wrapper_pid=child.pid,solver_pids=solver_pids,checked_frames=len(rows),latest_native=rows[-1] if rows else None,wall_seconds=time.perf_counter()-started))
                if code is not None:break
                time.sleep(2)
    except BaseException as failure:
        errors.append(dict(stage='stream_execute_native_or_compare',part=failed_part,error=repr(failure),traceback=traceback.format_exc()))
        if failed_part is not None and not any(r['part']==failed_part for r in readers):readers.append(dict(part=failed_part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
    try:
        statistics=hg.parse_hg(text,job); assert statistics['passed'],statistics
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==len(pairs)==job['frames'] and len(layers)==100*job['frames']
        assert sorted(int(q.stem.split('_')[-1]) for q in (folder/'data').glob('Part_*.bi4'))==list(range(job['frames']))
        assert rows[-1]['natural_step']==job['steps'] and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert all(value in text for value in ['SoilBoundaryDerivativeSPR="MirroredWallDerivatives"','SPR stationary wall planes (one per mk): 1','No Penetration=False',
            'SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"','PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"',
            'HydroMechInitMode="FreeSurface"','PoreDarcySymmetricCorr="Receiver"','SoilDampingCoef=0.02'])
        assert int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']; verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion_or_hg',error=repr(failure),traceback=traceback.format_exc()))
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('history_r',rows),('numeric_profiles',layers),('hg1_hg0_pairs',pairs),('nativefocus',focus)]]
    result=dict(passed=not errors,errors=errors,failed_part=failed_part,rows=rows,pairs=pairs,hg=statistics,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,variant=VARIANT,reference=REFERENCE,initial38_only=True,physical_acceptance=False,restart_admitted=False)
    seal(receipt,result); return result,bound(receipt)


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG} terminal: {state["status"]}. Read {CHECK}, {RUN} and the new receipt/completion; '
        f'profiles: tests/figures/{TAG}_hg1_spr1_g1_off_numeric_profiles.csv. Retained HG0/SPR1/G1/ShepardOFF control: tests/outputs/{retained.TAG}_spr1_g1_off. '
        'Use labels HGxi0p1_SPR1_G1_ShepardOFF versus HGxi0_SPR1_G1_ShepardOFF; no G0/G1 or ShepardON/OFF relabeling. '
        'Verify owned exit,native1040IDs/all38 guards,sequential binary64 clock,fixed p0,float32 excess,all61 actual saved steps/times and frozen input/program/runtime/output hashes. '
        'Inspect actual HG calls/cache/maxdt-tau/spin and internal-guard completion,990 non-top R,one6100-row profile CSV,61 descriptive option pairs and nativefocus. '
        'Own2msHGshort shares initial38 only,not full prefix or long half/CPU validation. No5Pa gate on option change. Source-attribution gap remains: same frozen-binary diagnostic,not compile-time source capture or formal release. '
        'Normal exit is not equilibrium,full-consolidation or restart acceptance. Repair completed-run postprocessing offline only; no duplicate solver,old worker restart,automatic follow-on,relaxed gate,retry/rearm. '
        'Report Chinese proactively and continue authorized offline physical review. Protect old Cryer processes,formal cases and retained data. One terminal notification only.')
    assert len(message)<2000; seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message))
    try:
        reply=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if reply.returncode==0 else 'queue_failed_no_retry',exit_code=reply.returncode,reply=(reply.stdout+reply.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def run():
    prerequisites(); assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs']); assert identity()==prepared['thread']
    job=prepared['job']; control=short.load_reference(prepared['hg0']); initial=current.native(Path(prepared['short_folder']),0)
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),thread=prepared['thread'],prepared=bound(PREP),current_job=job['name'],jobs=[],launched=False)
    def publish():
        temp=RUN.with_suffix('.tmp'); seal(temp,state); os.replace(temp,RUN)
    def progress(value):state.update(progress=value,launched=True); publish()
    publish()
    try:
        result,receipt=one_job(job,prepared,control,initial,progress); state['jobs'].append(receipt); state['launched']|=result['owned_wrapper_pid'] is not None; publish()
        assert result['passed'],result['errors']; verify(prepared['inputs']); state['status']='hg_stage1_complete_pending_root_physical_review'
    except BaseException as failure:state.update(status='hg_stage1_rejected_or_interrupted_pending_root_review',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc()); publish(); passed=state['status']=='hg_stage1_complete_pending_root_physical_review' and len(state['jobs'])==1
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],error=state.get('error'),variant=VARIANT,reference=REFERENCE,option_comparison_is_descriptive=True,
        source_program_attribution=prepared['source_program_attribution'],physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))
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
