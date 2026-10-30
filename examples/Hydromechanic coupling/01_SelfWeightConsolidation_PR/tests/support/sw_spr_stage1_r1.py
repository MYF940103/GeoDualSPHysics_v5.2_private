"""One fresh GPU SPR1/G1/ShepardOFF Stage1 run; SPR0 is retained data only."""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import traceback
import xml.etree.ElementTree as ET
import sw_spr_short_r1 as spr
import sw_grad_stage1_r1 as grad

stage, current, event, short = spr.stage, spr.current, spr.event, spr.short
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = spr.TESTS, spr.CASE, spr.LOGS, spr.CONFIGS, spr.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(spr,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG='sw_spr_stage1_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
CODEX, identity = stage.CODEX, stage.identity
VARIANT, REFERENCE='SPR1_G1_ShepardOFF','SPR0_G1_ShepardOFF'
JOB=dict(suffix='spr1_g1_off',backend='gpu',threads=1,dt='0.000001',shepard=40,on=False,end='0.30',interval='0.005',steps=300001,frames=61)


def expected(job,program):
    xml,bat=spr.expected(job,program)
    return xml.replace('short diagnostic only','Stage1 diagnostic; no equilibrium or restart acceptance'),bat.replace(spr.TAG,TAG)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); xml,bat=expected(JOB,CASE/'private/solver.exe'); tree=ET.fromstring(xml)
    value=lambda key:tree.find('.//parameter[@key="'+key+'"]').get('value')
    for key in ['SoilBoundaryDerivativeSPR','SoilStressRateGradCorr']:assert value(key)=='1' and len(tree.findall('.//parameter[@key="'+key+'"]'))==1
    assert value('TimeMax')=='0.30' and value('TimeOut')=='0.005' and value('DtIni')==value('DtFixed')=='0.000001' and value('SavePosDouble')=='1'
    assert value('SlipMode')=='1' and tree.find('.//PoreShepardRegularization').get('value')=='0' and tree.find('.//PoreShepardInterval').get('value')=='40'
    assert TAG in bat and spr.TAG not in bat and '-gpu -ompthreads:1' in bat and '-nsteps:300001' in bat
    signature=lambda root:[(e.tag,sorted(e.attrib.items())) for e in root.iter() if e.get('key')!='SoilBoundaryDerivativeSPR']
    assert signature(tree)==signature(ET.fromstring(grad.expected(JOB,CASE/'private/solver.exe')[0]))
    assert abs(stage.clock_table(JOB['dt'],JOB['steps'])[-1]-JOB['steps']*float(JOB['dt']))>1e-12
    return dict(passed=True,programs_started=False,files_written=False)


def prerequisites():
    proof=[]
    for path,count,frames in [(spr.CHECK,3,5),(grad.CHECK,1,61)]:
        check=read(path); assert check['passed'] and len(check['jobs'])==count and not check.get('held_jobs',[])
        proof += [bound(path),check['run']]+check['jobs']
        for record in check['jobs']:
            result=read(record['path']); done=read(result['sealed_completion']['path'])
            assert result['passed'] and len(result['rows'])==frames and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
            assert all(row['passed'] for row in result['pairs'] if row.get('gate_applied'))
            proof += [result['sealed_completion']]+done['outputs']+result['artifacts']
    analysis=read(read(grad.CHECK)['analysis']['path']); assert analysis['passed']; proof += [read(grad.CHECK)['analysis']]+analysis['artifacts']
    verify(proof); return proof


def prepare():
    gates=prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(spr.PREP); gpu=next(j for j in prior['jobs'] if j['suffix']=='gpu'); retained=read(grad.PREP); control=retained['job']
    assert identity()==retained['thread'] and bound(CODEX)==retained['codex'] and gpu['program']==control['program'] and gpu['runtime']==control['runtime']
    oldreceipt=LOGS/(control['name']+'.receipt.json'); previous=read(oldreceipt); done=read(previous['sealed_completion']['path']); shortreceipt=LOGS/(gpu['name']+'.receipt.json')
    proof=prior['inputs']+gates+[bound(p) for p in [__file__,NOTE,spr.__file__,spr.PREP,grad.__file__,grad.PREP,oldreceipt,shortreceipt,CODEX]]
    proof += [previous['sealed_completion'],control['config'],control['bat'],gpu['program']]+gpu['runtime']+done['outputs']; proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof)
    job=dict(JOB); name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat'); xml,command=expected(job,Path(gpu['program']['path']))
    with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
    with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
    job.update(name=name,program=gpu['program'],runtime=gpu['runtime'],config=bound(cfg),bat=bound(bat)); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),thread=retained['thread'],codex=retained['codex'],inputs=proof,job=job,parameters=prior['parameters'],
        short_folder=str(OUTPUTS/gpu['name']),short_receipt=bound(shortreceipt),spr0=dict(name=control['name'],folder=str(OUTPUTS/control['name']),dt=control['dt'],steps=control['steps'],
        receipt=bound(oldreceipt),completion=previous['sealed_completion'],outputs=done['outputs'],rows=previous['rows']),physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))


def analyze(job,frames,result,control,p):
    assert sorted(frames)==sorted(control)==list(range(61)); histories=[]; layers=[]; pairs=[]; differences=[]
    for row in result['rows']:
        part=row['part']; a,b=frames[part],control[part]; histories.append(dict(row,variant=VARIANT,**short.r_summary(a,p)))
        for layer in stage.profiles(a,frames[0],part):
            layer.update(variant=VARIANT,r_native_pa=layer['excess_native_pa']+p['Mf']*(layer['sigma_xx']+layer['sigma_yy']+layer['sigma_zz'])/(3*p['K']),included_in_r_summary=layer['layer']!=99); layers.append(layer)
        pair,delta=short.pair(VARIANT+'_minus_'+REFERENCE,'spr_option_descriptive',part,a,part,b,frames[0],control[0],p)
        pair.update(variant=VARIANT,reference_variant=REFERENCE,same_saved_step=int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0])); pairs.append(pair); differences+=delta
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('history_r',histories),('profiles_r',layers),('spr1_spr0_pairs',pairs),('spr1_spr0_differences',differences)]]
    return dict(passed=len(histories)==len(pairs)==61 and len(layers)==6100 and all(r['time_eligible'] and r['same_saved_step'] and not r['gate_applied'] for r in pairs),artifacts=artifacts)


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG} terminal: {state["status"]}. Read {CHECK}, {RUN}, tests/logs/{TAG}.analysis.json and '
        f'tests/figures/{TAG}_spr1_g1_off_profiles_r.csv; retained SPR0/G1/ShepardOFF is tests/outputs/{grad.TAG}_g1_off with its sealed check/receipt. '
        'New run is SPR1_G1_ShepardOFF versus retained SPR0_G1_ShepardOFF, never G0/G1 or ShepardON/OFF. '
        'Verify owned exit,native1040 IDs/all38 guards,sequential binary64 clock,fixed p0,float32 excess and frozen input/program/runtime/output hashes. '
        'All61 saved steps/times compare the SPR option descriptively; no5Pa half gate. OwnSPR2ms control shares only initial38 fields,not a full prefix or half validation. '
        'Inspect100-layer native p,p0,q,six stresses,settlement,rho,velocity,R and990 non-top-particle R. Do not run old hardcoded G0/G1 or ON/OFF review commands. '
        'Normal exit is not equilibrium,full-consolidation or restart acceptance. Repair completed-run analysis offline only; no duplicate solver,old worker restart,automatic long cycle or relaxed gate. '
        'Report Chinese proactively and continue authorized offline review. Cryer server,formal cases and retained data remain protected. One terminal notification only,no retry/rearm.')
    assert len(message)<2000; seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message))
    try:
        reply=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if reply.returncode==0 else 'queue_failed_no_retry',exit_code=reply.returncode,reply=(reply.stdout+reply.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def run():
    prerequisites(); assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs']); assert identity()==prepared['thread']
    job=prepared['job']; control=short.load_reference(prepared['spr0']); initial=current.native(Path(prepared['short_folder']),0)
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),thread=prepared['thread'],prepared=bound(PREP),current_job=job['name'],jobs=[],launched=False)
    def publish():
        temp=RUN.with_suffix('.tmp'); seal(temp,state); os.replace(temp,RUN)
    def progress(value):state.update(progress=value,launched=True); publish()
    publish(); analysis=dict(passed=False,variant=VARIANT,reference=REFERENCE,physical_acceptance=False,restart_admitted=False)
    try:
        # Only the own-SPR short initial frame is shared; the frozen full path activates no short-prefix or half comparator.
        result,receipt,frames=stage.one_job(job,prepared,dict(legacy_coarse={0:initial}),progress)
        state['jobs'].append(receipt); state['launched']|=result['owned_wrapper_pid'] is not None; publish(); assert result['passed'],result['error']
        text=(OUTPUTS/job['name']/'Run.out').read_text(errors='replace')
        assert all(value in text for value in ['SoilBoundaryDerivativeSPR="MirroredWallDerivatives"','SPR stationary wall planes (one per mk): 1','No Penetration=False',
            'SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"','PoreShepardRegularization="Disabled"'])
        analysis.update(analyze(job,frames,result,control,prepared['parameters']),execution_receipt=receipt,sealed_completion=result['sealed_completion']); assert analysis['passed'],'SPR option saved-state matching failed'
        verify(prepared['inputs']); state['status']='spr1_g1_shepard_off_stage1_complete_pending_root_review'
    except BaseException as failure:
        analysis.update(passed=False,error=repr(failure),traceback=traceback.format_exc()); state.update(status='stage1_or_offline_analysis_failed_pending_root_review',error=repr(failure))
    analysispath=LOGS/(TAG+'.analysis.json'); seal(analysispath,analysis); state.update(finished_utc=utc(),analysis=bound(analysispath)); publish()
    passed=state['status']=='spr1_g1_shepard_off_stage1_complete_pending_root_review' and len(state['jobs'])==1
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],analysis=bound(analysispath),error=state.get('error'),variant=VARIANT,reference=REFERENCE,
        option_comparison_is_descriptive=True,physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))
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
