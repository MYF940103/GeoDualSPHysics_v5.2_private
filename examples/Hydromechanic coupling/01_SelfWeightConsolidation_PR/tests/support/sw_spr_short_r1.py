"""Three fresh G1/ShepardOFF short SPR checks; no long run, build or queue."""
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
import sw_grad_short_r1 as short

stage, current, event, baseline = short.stage, short.current, short.event, short.baseline
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = short.TESTS, short.CASE, short.LOGS, short.CONFIGS, short.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(short,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
clock_table, measure, profiles = stage.clock_table, stage.measure, stage.profiles
TAG='sw_spr_short_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
JOBS=[dict(job) for job in short.JOBS]


def expected(job,program):
    xml,bat=short.expected(job,program); key='SoilBoundaryDerivativeSPR'
    assert not ET.fromstring(xml).findall('.//parameter[@key="'+key+'"]')
    xml,n=re.subn(r'(?m)^([ ]*)(<parameter key="SoilStressRateGradCorr"[^\n]*\n)',
        lambda m:m[0]+m[1]+'<parameter key="'+key+'" value="1" comment="Mirrored stationary-wall derivatives; short diagnostic only" />\n',xml); assert n==1
    return xml,bat.replace(short.TAG,TAG)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); tree=ET.fromstring(xml); base=ET.fromstring(short.expected(job,CASE/'private/solver.exe')[0])
        value=lambda key:tree.find('.//parameter[@key="'+key+'"]').get('value')
        found=tree.findall('.//parameter[@key="SoilBoundaryDerivativeSPR"]'); assert len(found)==1 and found[0].get('value')=='1'
        signature=lambda root:[(e.tag,sorted(e.attrib.items())) for e in root.iter() if e.get('key')!='SoilBoundaryDerivativeSPR']
        assert signature(tree)==signature(base) and value('SoilStressRateGradCorr')=='1' and value('SlipMode')=='1'
        nopen=tree.find('.//parameter[@key="NoPenetration"]'); assert nopen is None or nopen.get('value')=='0'
        assert value('SoilDampingCoef')=='0.02' and value('SavePosDouble')=='1' and value('TimeOut')=='0.0004999'
        assert tree.find('.//PoreShepardRegularization').get('value')=='0' and tree.find('.//HydraulicConductivity').get('value')=='0'
        assert all(key not in xml for key in ['SoilHourglassXi','PoreDarcySymmetricCorr'])
        assert TAG in bat and short.TAG not in bat and ('-'+job['backend']+' -ompthreads:'+str(job['threads'])) in bat
        assert stage.plan(job)==([0,1000,2000,3000,4000] if job['suffix']=='half' else [0,500,1000,1500,2000])
    return dict(passed=True,programs_started=False,files_written=False)


def prerequisites():
    check=read(short.CHECK); assert check['passed'] and len(check['jobs'])==3 and not check['held_jobs']
    proof=[bound(short.CHECK),check['run']]+check['jobs']; refs={}
    for job in read(short.PREP)['jobs']:
        receipt=LOGS/(job['name']+'.receipt.json'); result=read(receipt); done=read(result['sealed_completion']['path'])
        assert result['passed'] and len(result['rows'])==5 and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
        assert all(r['passed'] for r in result['pairs'] if r['gate_applied'])
        refs[job['suffix']]=dict(name=job['name'],folder=str(OUTPUTS/job['name']),dt=job['dt'],steps=job['steps'],rows=result['rows'],
            receipt=bound(receipt),completion=result['sealed_completion'],outputs=done['outputs'])
        proof += [bound(receipt),result['sealed_completion'],job['config'],job['bat'],job['program']]+job['runtime']+done['outputs']+result['artifacts']
    proof=[dict(r,sha256=r['sha256'].lower()) for r in proof]; verify(proof); return proof,refs


def prepare():
    gates,refs=prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(short.PREP); build=read(current.BUILD); assert build['passed']; built=read(build['prepared']['path']); reader=read(event.BUILD)
    assert reader['built'] and reader['exit_code']==0
    files=[__file__,NOTE,short.__file__,stage.__file__,stage.old.__file__,current.__file__,event.__file__,baseline.__file__,short.PREP,current.BUILD,event.BUILD,
        baseline.TEMPLATE,baseline.C04/'support/cryer_start_r1.py',baseline.C02/'support/symc_1d_short_r1.py',baseline.C02.parent/'support/release_case.py',
        baseline.C02.parent/'support/compare_precision_q0.py',baseline.REPO/'bin/windows/GenCase_win64.exe']
    proof=gates+[bound(p) for p in files]+[build['prepared'],build['adopted_cpu_release']]+build['fresh_stages']+built['inputs']+reader['inputs']+[reader['program'],reader['log']]
    for record in [build['adopted_cpu_release'],build['fresh_stages'][-1]]:
        result=read(record['path']); assert result['exit_code']==0 and result['owned_exited'] and result['protected_inputs_unchanged']
        accepted=next(j for j in prior['jobs'] if j['backend']==('cpu' if record==build['adopted_cpu_release'] else 'gpu'))
        assert result['program']==accepted['program'] and [r['target'] for r in result['runtime']]==accepted['runtime']
        proof += [result['program'],result['log']]+result['artifacts']+[r['target'] for r in result['runtime']]
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); accepted=next(j for j in prior['jobs'] if j['suffix']==job['suffix']); name=TAG+'_'+job['suffix']
        cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_'+job['backend'].upper()+'.bat'); xml,command=expected(job,Path(accepted['program']['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=accepted['program'],runtime=accepted['runtime'],config=bound(cfg),bat=bound(bat)); jobs.append(job); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,references=refs,parameters=prior['parameters'],physical_acceptance=False,full_run_admitted=False,restart_admitted=False))


def comparisons(job,frames,refs,p):
    rows=[]; differences=[]; suffix=job['suffix']; tasks=[('spr_option_descriptive',refs[suffix])]
    if suffix=='gpu':tasks += [('cpu_gpu',refs['new_cpu'])]
    if suffix=='half':tasks += [('gpu_half',refs['new_gpu'])]
    for kind,ref in tasks:
        for part in range(5):
            try:
                a,b=frames[part],ref[part]; row,delta=short.pair(job['name']+'_minus_'+kind,kind,part,a,part,b,frames[0],ref[0],p)
                row['comparison_valid']=True; row['initial38_bitexact']=None; rows.append(row); differences+=delta
                if kind=='spr_option_descriptive':
                    row['same_natural_step']=int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0]); assert row['time_eligible'] and row['same_natural_step']
                    if part==0:
                        row['initial38_bitexact']=bool(np.array_equal(a.to_numpy(dtype='<f8').view('<u8'),b.to_numpy(dtype='<f8').view('<u8'))); assert row['initial38_bitexact']
            except BaseException as failure:
                if rows and rows[-1].get('kind')==kind and rows[-1].get('part')==part:rows[-1].update(comparison_valid=False,error=repr(failure))
                else:rows.append(dict(kind=kind,part=part,gate_applied=kind in ['cpu_gpu','gpu_half'],passed=False,comparison_valid=False,error=repr(failure)))
    return rows,differences


def one_job(job,prepared,refs):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt]); verify(prepared['inputs'])
    child=None; started=time.perf_counter(); errors=[]; frames={}; rows=[]; history=[]; layers=[]; readers=[]; p=prepared['parameters']; clock=clock_table(job['dt'],job['steps'])
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=180)
    except BaseException as failure:
        errors.append(dict(stage='execute',error=repr(failure),traceback=traceback.format_exc()))
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],
        outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
    parts=sorted(int(q.stem.split('_')[-1]) for q in (folder/'data').glob('Part_*.bi4'))
    for part in parts:
        try:
            a=current.native(folder,part); frames[part]=a; readers.append(dict(part=part,exit_code=0)); history += [dict(part=part,**r) for r in event.focus(a).to_dict('records')]
            rows.append(dict(**measure(a,frames[0],part,job,clock),**short.r_summary(a,p)))
            for row in profiles(a,frames[0],part):row.update(r_native_pa=row['excess_native_pa']+p['Mf']*(row['sigma_xx']+row['sigma_yy']+row['sigma_zz'])/(3*p['K']),included_in_r_summary=row['layer']!=99); layers.append(row)
        except BaseException as failure:
            errors.append(dict(stage='native_or_measure',part=part,error=repr(failure),traceback=traceback.format_exc()))
            if not any(r['part']==part for r in readers):readers.append(dict(part=part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
    try:
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==5 and parts==list(range(5)) and len(layers)==500
        assert [r['natural_step'] for r in rows]==stage.plan(job) and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert 'SoilBoundaryDerivativeSPR="MirroredWallDerivatives"' in text and 'SPR stationary wall planes (one per mk): 1' in text and 'No Penetration=False' in text
        assert all(value in text for value in ['SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"','PoreShepardRegularization="Disabled"',
            'SlipMode="DBC vel=0"','HydroMechInitMode="FreeSurface"','PoreDarcySymmetricCorr="Receiver"','SoilDampingCoef=0.02'])
        assert int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard'] and 'SoilHourglass: forcecalls=' not in text; verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion',error=repr(failure),traceback=traceback.format_exc()))
    pairs,differences=comparisons(job,frames,refs,p)
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('frames',rows),('history',history),('profiles',layers),('pairs',pairs),('differences',differences)]]
    result=dict(passed=not errors and all(r['comparison_valid'] and (not r['gate_applied'] or r['passed']) for r in pairs),errors=errors,rows=rows,pairs=pairs,reader_exits=readers,
        artifacts=artifacts,sealed_completion=bound(complete),owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,physical_acceptance=False,full_run_admitted=False)
    seal(receipt,result); return result,bound(receipt),frames


def run():
    prerequisites(); assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs'])
    refs={key:short.load_reference(ref) for key,ref in prepared['references'].items()}; state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[])
    def publish():
        temp=RUN.with_suffix('.tmp'); seal(temp,state); os.replace(temp,RUN)
    publish()
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name']; publish(); result,record,frames=one_job(job,prepared,refs); state['jobs'].append(record); publish()
            assert result['passed'],('Earlier gate failed; later short job held',job['name'],result['errors'])
            if job['suffix'] in ['cpu','gpu']:refs['new_'+job['suffix']]=frames
        verify(prepared['inputs']); state['status']='spr_short_checks_complete_pending_root_review'
    except BaseException as failure:state.update(status='short_gate_failed_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish(); passed=state['status']=='spr_short_checks_complete_pending_root_review' and len(state['jobs'])==3
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),physical_acceptance=False,full_run_admitted=False,restart_admitted=False)); return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
