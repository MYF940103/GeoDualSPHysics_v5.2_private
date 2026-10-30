"""One fresh GPU G1/ShepardOFF Stage1 run; G0 is retained data only."""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import sw_grad_short_r1 as short

stage, current, event = short.stage, short.current, short.event
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = short.TESTS, short.CASE, short.LOGS, short.CONFIGS, short.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(short,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG='sw_grad_stage1_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
CODEX, identity = stage.CODEX, stage.identity
JOB=dict(suffix='g1_off',backend='gpu',threads=1,dt='0.000001',shepard=40,on=False,end='0.30',interval='0.005',steps=300001,frames=61)


def expected(job,program):
    xml,bat=short.expected(job,program)
    return xml.replace('short diagnostic only','Stage1 diagnostic; no equilibrium or restart acceptance'),bat.replace(short.TAG,TAG)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); xml,bat=expected(JOB,CASE/'private/solver.exe'); tree=ET.fromstring(xml)
    value=lambda key:tree.find('.//parameter[@key="'+key+'"]').get('value')
    assert value('SoilStressRateGradCorr')=='1' and len(tree.findall('.//parameter[@key="SoilStressRateGradCorr"]'))==1
    assert value('TimeMax')=='0.30' and value('TimeOut')=='0.005' and value('DtIni')==value('DtFixed')=='0.000001' and value('SavePosDouble')=='1'
    assert tree.find('.//PoreShepardRegularization').get('value')=='0' and tree.find('.//PoreShepardInterval').get('value')=='40'
    assert TAG in bat and short.TAG not in bat and '-gpu -ompthreads:1' in bat and '-nsteps:300001' in bat
    signature=lambda root:[(e.tag,sorted(e.attrib.items())) for e in root.iter() if e.get('key')!='SoilStressRateGradCorr']
    assert signature(tree)==signature(ET.fromstring(stage.expected(JOB,CASE/'private/solver.exe')[0]))
    assert abs(stage.clock_table(JOB['dt'],JOB['steps'])[-1]-JOB['steps']*float(JOB['dt']))>1e-12
    return dict(passed=True,programs_started=False,files_written=False)


def prerequisites():
    check=read(short.CHECK); assert check['passed'] and len(check['jobs'])==3 and not check['held_jobs']
    records=[bound(short.CHECK),check['run']]+check['jobs']
    for record in check['jobs']:
        result=read(record['path']); done=read(result['sealed_completion']['path'])
        assert result['passed'] and done['solver_finished'] and done['exit_code']==0 and done['owned_exited'] and len(result['rows'])==5
        assert all(row['passed'] for row in result['pairs'] if row['gate_applied'])
        records += [result['sealed_completion']]+done['outputs']+result['artifacts']
    verify(records); return records


def prepare():
    gates=prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(short.PREP); gpu=next(j for j in prior['jobs'] if j['suffix']=='gpu'); oldprep=read(stage.PREP)
    g0=next(j for j in oldprep['jobs'] if j['suffix']=='off'); assert gpu['program']==g0['program'] and gpu['runtime']==g0['runtime']
    oldreceipt=LOGS/(g0['name']+'.receipt.json'); previous=read(oldreceipt); done=read(previous['sealed_completion']['path'])
    assert previous['passed'] and done['solver_finished'] and done['exit_code']==0 and done['owned_exited'] and len(previous['rows'])==61
    shortreceipt=LOGS/(gpu['name']+'.receipt.json'); accepted=read(shortreceipt)
    proof=prior['inputs']+gates+[bound(p) for p in [__file__,NOTE,short.__file__,short.PREP,stage.__file__,stage.PREP,oldreceipt,shortreceipt,CODEX]]
    proof += [previous['sealed_completion']]+done['outputs']+previous['artifacts']+[accepted['sealed_completion'],gpu['program']]+gpu['runtime']
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof)
    job=dict(JOB); name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat'); xml,command=expected(job,Path(gpu['program']['path']))
    with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
    with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
    job.update(name=name,program=gpu['program'],runtime=gpu['runtime'],config=bound(cfg),bat=bound(bat)); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),thread=identity(),codex=bound(CODEX),inputs=proof,job=job,parameters=prior['parameters'],
        short_folder=str(OUTPUTS/gpu['name']),short_receipt=bound(shortreceipt),g0=dict(name=g0['name'],folder=str(OUTPUTS/g0['name']),dt=g0['dt'],steps=g0['steps'],
        receipt=bound(oldreceipt),completion=previous['sealed_completion'],outputs=done['outputs'],rows=previous['rows']),physical_acceptance=False,restart_admitted=False,automatic_full_consolidation_admitted=False))


def analyze(job,frames,result,g0,p):
    assert sorted(frames)==sorted(g0)==list(range(61)); histories=[]; layers=[]; pairs=[]; differences=[]
    for row in result['rows']:
        part=row['part']; a,b=frames[part],g0[part]
        assert int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0]) and abs(float(a.time_s.iloc[0]-b.time_s.iloc[0]))<=1e-14
        histories.append(dict(row,variant='G1_ShepardOFF',**short.r_summary(a,p)))
        for layer in stage.profiles(a,frames[0],part):
            layer.update(variant='G1_ShepardOFF',r_native_pa=layer['excess_native_pa']+p['Mf']*(layer['sigma_xx']+layer['sigma_yy']+layer['sigma_zz'])/(3*p['K']),included_in_r_summary=layer['layer']!=99); layers.append(layer)
        pair,delta=short.pair('G1_minus_G0_ShepardOFF','gradient_option_descriptive',part,a,part,b,frames[0],g0[0],p)
        assert pair['time_eligible'] and not pair['gate_applied']; pairs.append(pair); differences+=delta
    assert len(histories)==len(pairs)==61 and len(layers)==6100
    return [event.write_csv(job['name']+'_'+kind,data) for kind,data in [('history_r',histories),('profiles_r',layers),('g1_g0_pairs',pairs),('g1_g0_differences',differences)]]


def notify(state):
    assert identity()==state['thread']
    message=(f'User-authorized same-thread {TAG} terminal: {state["status"]}. Read {CHECK}, {RUN}, tests/logs/{TAG}.analysis.json and '
        f'tests/figures/{TAG}_g1_off_profiles_r.csv; retained G0/ShepardOFF control is tests/outputs/{stage.TAG}_off with its sealed receipt. '
        'This new run is G1/ShepardOFF only, never ShepardON. Verify native1040IDs/all38 guards, owned exit, sequential binary64 clock, fixed p0/float32 excess and frozen input/build/output hashes. '
        'All61 matched states compare G1 versus retained G0 descriptively, with no5Pa half-step bound; own2ms short control shares only the initial38-field frame. '
        'Inspect100-layer native p/p0/q/six stress/settlement/rho/velocity/R and990 non-top-particle R. Use new G0/G1 labels; do not call the old hardcoded ON/OFF equilibrium-review workflow. '
        'Normal exit is not equilibrium, restart interoperability or full-consolidation acceptance. Repair completed-run analysis offline only; no duplicate solver/old worker restart/automatic long cycle. '
        'Report Chinese proactively and continue the authorized review. Cryer server and retained data remain protected. One terminal notification only; no retry/rearm.')
    assert len(message)<2000; seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message))
    try:
        reply=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if reply.returncode==0 else 'queue_failed_no_retry',exit_code=reply.returncode,reply=(reply.stdout+reply.stderr).decode(errors='replace'))
    except Exception as failure:record=dict(status='queue_exception_no_retry',error=repr(failure))
    seal(LOGS/(TAG+'.notification.json'),record)


def run():
    prerequisites(); assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs']); assert identity()==prepared['thread']
    job=prepared['job']; g0=short.load_reference(prepared['g0']); initial=current.native(Path(prepared['short_folder']),0)
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),thread=prepared['thread'],prepared=bound(PREP),current_job=job['name'],jobs=[],launched=False)
    def publish():
        temp=RUN.with_suffix('.tmp'); seal(temp,state); os.replace(temp,RUN)
    def progress(value):state.update(progress=value,launched=True); publish()
    publish(); analysis=dict(passed=False,variant='G1_ShepardOFF',reference='G0_ShepardOFF',physical_acceptance=False,restart_admitted=False)
    try:
        # The frozen full-run path checks only the initial short-control frame; no prefix or half comparator is activated.
        result,receipt,frames=stage.one_job(job,prepared,dict(legacy_coarse={0:initial}),progress)
        state['jobs'].append(receipt); state['launched']|=result['owned_wrapper_pid'] is not None; publish(); assert result['passed'],result['error']
        text=(OUTPUTS/job['name']/'Run.out').read_text(errors='replace')
        assert 'SoilStressRateGradCorr="KernelGradient"' in text and 'PoreCompressionGradCorr="KernelGradient"' in text and 'PoreShepardRegularization="Disabled"' in text
        analysis.update(artifacts=analyze(job,frames,result,g0,prepared['parameters']),execution_receipt=receipt,sealed_completion=result['sealed_completion'],passed=True)
        verify(prepared['inputs']); state['status']='g1_shepard_off_stage1_complete_pending_root_review'
    except BaseException as failure:
        analysis.update(passed=False,error=repr(failure),traceback=traceback.format_exc()); state.update(status='stage1_or_offline_analysis_failed_pending_root_review',error=repr(failure))
    analysispath=LOGS/(TAG+'.analysis.json'); seal(analysispath,analysis); state.update(finished_utc=utc(),analysis=bound(analysispath)); publish()
    passed=state['status']=='g1_shepard_off_stage1_complete_pending_root_review' and len(state['jobs'])==1
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],analysis=bound(analysispath),error=state.get('error'),variant='G1_ShepardOFF',reference='retained_G0_ShepardOFF',
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
