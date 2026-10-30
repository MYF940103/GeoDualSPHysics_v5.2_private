"""Five gated private GPU checks for the pore-MLS host cell-size fix; default help."""
import argparse
import ast
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import sw_shepard_event_r1 as event

baseline, isolate = event.baseline, event.isolate
TESTS, CASE = event.TESTS, event.CASE
LOGS, CONFIGS, OUTPUTS, FIGURES = event.LOGS, event.CONFIGS, event.OUTPUTS, event.FIGURES
read, seal, verify, unique, bound, utc, inventory = [getattr(event,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG = 'sw_pore_cell_native_r1'
PREP, RUN, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE, BUILD = TESTS/'notes'/(TAG+'.json'), LOGS/'sw_pore_cell_build_r1.check.json'
SANITIZER = Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe')
CONTROLS = {
    'cpu_event_on': (event.TAG+'_cpu_on',event.PREP), 'cpu_event_off': (event.TAG+'_cpu_off',event.PREP),
    'gpu_event_off': (event.TAG+'_gpu_off',event.PREP), 'cpu_short_on': (baseline.TAG+'_cpu_c',baseline.PREP),
    'cpu_short_off': (isolate.TAG+'_cpu_current_off',isolate.PREP), 'gpu_short_off': (isolate.TAG+'_gpu_current_off',isolate.PREP)}
JOBS = [
    dict(suffix='debug_on_event',configuration='Debug',shepard_on=True,steps=80,frames=79,memcheck=True,refs=[('cpu_event_on','screen')]),
    dict(suffix='release_on_event',configuration='Release',shepard_on=True,steps=80,frames=79,memcheck=False,refs=[('cpu_event_on','screen')]),
    dict(suffix='release_off_event',configuration='Release',shepard_on=False,steps=80,frames=79,memcheck=False,refs=[('gpu_event_off','exact38'),('cpu_event_off','screen')]),
    dict(suffix='release_on_short',configuration='Release',shepard_on=True,steps=2000,frames=5,memcheck=False,refs=[('cpu_short_on','screen')]),
    dict(suffix='release_off_short',configuration='Release',shepard_on=False,steps=2000,frames=5,memcheck=False,refs=[('gpu_short_off','exact38'),('cpu_short_off','screen')])]


def expected(job,program):
    xml,bat=baseline.expected((job['suffix'],'gpu','0.000001',job['steps'],40),program)
    if job['steps']==80:
        for key,value in [('TimeMax','0.00008'),('TimeOut','0.000001')]:
            xml,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]+(" comment=")[^"]+("[^\n]+)',
                lambda m:m[1]+value+m[2]+'Bounded pore-MLS launch regression; no physical acceptance'+m[3],xml); assert n==1
    if not job['shepard_on']:
        xml,n=re.subn(r'(<PoreShepardRegularization value=")1(")',r'\g<1>0\2',xml); assert n==1
    bat=bat.replace(baseline.TAG,TAG)
    # Preserve the native/sanitizer exit, including memcheck's requested99.
    head,tail=bat.rsplit('if not "%ERRORLEVEL%" == "0" goto fail',1)
    bat=head+'set solvercode=%ERRORLEVEL%\nif not "%solvercode%" == "0" exit /b %solvercode%'+tail
    if job['memcheck']:
        prefix='"'+str(SANITIZER)+'" --tool memcheck --error-exitcode 99 --log-file "tests/logs/'+TAG+'_'+job['suffix']+'.memcheck.log" '
        assert bat.count('\n%dualsphysics% -gpu ')==1
        bat=bat.replace('\n%dualsphysics% -gpu ','\n'+prefix+'%dualsphysics% -gpu ',1)
    return xml,bat


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); event.selftest()
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); tree=ET.fromstring(xml)
        value=lambda key:tree.find('.//parameter[@key="'+key+'"]').get('value')
        assert value('DtFixed')==value('DtIni')=='0.000001' and value('SavePosDouble')=='1'
        assert value('TimeMax')==('0.00008' if job['steps']==80 else '0.002')
        assert value('TimeOut')==('0.000001' if job['steps']==80 else '0.0005')
        assert tree.find('.//PoreShepardRegularization').get('value')==('1' if job['shepard_on'] else '0')
        assert tree.find('.//PoreShepardInterval').get('value')=='40' and tree.find('.//HydraulicConductivity').get('value')=='0'
        assert ('--tool memcheck --error-exitcode 99' in bat)==job['memcheck'] and ('-nsteps:'+str(job['steps'])) in bat
        assert 'if exist "%dirout%" goto fail' in bat and 'exit /b %solvercode%' in bat and baseline.TAG not in bat
    return dict(passed=True,programs_started=False,files_written=False)


def prepare():
    selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,FIGURES])
    check=read(BUILD); assert check['passed'] and len(check['fresh_stages'])==3
    built=read(check['prepared']['path']); nativebuild=read(event.BUILD); assert nativebuild['exit_code']==0
    # New build bindings describe the fixed current source. Never descend old source-input lists.
    proof=built['inputs']+nativebuild['inputs']+[bound(BUILD),check['prepared'],bound(event.BUILD),nativebuild['program'],nativebuild['log']]
    proof += [bound(p) for p in [__file__,NOTE,event.__file__,baseline.__file__,isolate.__file__,
        baseline.C02/'support/symc_1d_short_r1.py',baseline.C02.parent/'support/release_case.py',
        baseline.C02.parent/'support/compare_precision_q0.py',baseline.C04/'support/cryer_start_r1.py',
        TESTS/'support/read_selfweight_native_r1.cpp',baseline.TEMPLATE,baseline.REPO/'bin/windows/GenCase_win64.exe',SANITIZER]]
    stages={}
    for record in check['fresh_stages']:
        stage=read(record['path']); assert stage['exit_code']==0 and stage['owned_exited'] and stage['protected_inputs_unchanged'] and len(stage['runtime'])==4
        stages[stage['configuration']]=stage; proof += [record,stage['program'],stage['log']]+stage['artifacts']+[r['target'] for r in stage['runtime']]
    controls={}
    for key,(name,oldprep) in CONTROLS.items():
        prior=read(oldprep); old=next(j for j in prior['jobs'] if j['name']==name)
        receipt=LOGS/(name+'.receipt.json'); result=read(receipt); done=read(result['sealed_completion']['path'])
        assert result['passed'] and done['exit_code']==0 and done['solver_finished'] and done['owned_exited'] and len(old['runtime'])==4
        assert done['program']==old['program']
        native=[r for r in done['outputs'] if Path(r['path']).suffix.lower() in ['.bi4','.ibi4'] or Path(r['path']).name=='Run.out']
        assert native and len(result['rows']) in [5,79]
        controls[key]=dict(name=name,folder=str(OUTPUTS/name),receipt=bound(receipt),completion=result['sealed_completion'],rows=result['rows'],native=native)
        proof += [bound(oldprep),bound(receipt),result['sealed_completion'],old['program'],old['build'],old['config'],old['bat']]+old['runtime']+native
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); name=TAG+'_'+job['suffix']; stage=stages[job['configuration']]
        cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_GPU.bat'); xml,command=expected(job,Path(stage['program']['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=stage['program'],runtime=[r['target'] for r in stage['runtime']],config=bound(cfg),bat=bound(bat))
        jobs.append(job); proof += [bound(cfg),bound(bat)]
    proof=unique(proof); verify(proof)
    seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,controls=controls,sanitizer=bound(SANITIZER),reader=nativebuild['program'],
        old_current_gpu_source_path_reverified=False,physical_acceptance=False,automatic_long_run_admitted=False))


def native(folder,part):
    raw=subprocess.check_output([str(event.READER),str(folder/'data'),str(part)],creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
    # Explicit float parsing retains signed zero in otherwise all-zero fields.
    return pd.read_csv(io.BytesIO(raw),dtype='<f8',float_precision='round_trip')


def control_frames(control):
    verify([control['receipt'],control['completion']]+control['native']); frames={}
    for row in control['rows']:
        part=row['part']; a=native(Path(control['folder']),part); frames[part]=a; measured=event.measure(a,frames[0],part)
        assert measured['time_s']==row['time_s'] and measured['saved_step']==row['saved_step']
    return frames


def comparisons(job,frames,references):
    pairs=[]; differences=[]
    for key,kind in job['refs']:
        label=job['name']+'_minus_'+key
        try:
            rows,delta=event.compare(label,frames,references[key]); differences+=delta
            aa={(int(a.saved_step.iloc[0])+1 if p else 0):a for p,a in frames.items()}
            bb={(int(a.saved_step.iloc[0])+1 if p else 0):a for p,a in references[key].items()}
            for row in rows:
                row.update(reference=key,gate_kind=kind,all38_bits_exact=None)
                if kind=='exact38':
                    try:
                        a,b=aa[row['natural_step']],bb[row['natural_step']]
                        assert list(a)==list(b) and len(a.columns)==38 and a.shape==b.shape
                        bad=a.to_numpy(dtype='<f8').view('<u8')!=b.to_numpy(dtype='<f8').view('<u8')
                        row.update(all38_bits_exact=not bool(bad.any()),different_fields=';'.join(a.columns[bad.any(axis=0)]))
                    except BaseException as failure:row.update(all38_bits_exact=False,exact_error=repr(failure))
                row['gate_passed']=bool(row['time_eligible'] and (row['all38_bits_exact'] if kind=='exact38' else row['comparison_bound_passed']))
            pairs += rows or [dict(comparison=label,reference=key,gate_kind=kind,gate_passed=False,error='No comparison frames')]
        except BaseException as failure:pairs.append(dict(comparison=label,reference=key,gate_kind=kind,gate_passed=False,error=repr(failure)))
    return pairs,differences


def one_job(job,prepared,references):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); memlog=LOGS/(job['name']+'.memcheck.log')
    complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,memlog,complete,receipt]); verify(prepared['inputs'])
    child=None; started=time.perf_counter(); errors=[]; frames={}; rows=[]; history=[]; readers=[]; sanitizer_passed=None
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            child.wait(timeout=180)
    except BaseException as failure:
        errors.append(dict(stage='execute',error=repr(failure),traceback=traceback.format_exc()))
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
    survivors=[p for p in inventory() if job['name'] in (p.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],config=job['config'],bat=job['bat'],
        outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+[bound(p) for p in [log,memlog] if p.exists()])
    seal(complete,done)
    parts=sorted(int(p.stem.split('_')[-1]) for p in (folder/'data').glob('Part_*.bi4'))
    for part in parts:
        try:
            a=native(folder,part); readers.append(dict(part=part,exit_code=0)); frames[part]=a
            history += [dict(job=job['name'],part=part,natural_step=(int(a.saved_step.iloc[0])+1 if part else 0),**r) for r in event.focus(a).to_dict('records')]
            rows.append(dict(passed=True,**event.measure(a,frames[0],part)))
        except BaseException as failure:
            errors.append(dict(stage='native_or_measure',part=part,error=repr(failure),traceback=traceback.format_exc())); rows.append(dict(part=part,passed=False,error=repr(failure)))
            if not any(r['part']==part for r in readers):readers.append(dict(part=part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
    try:
        assert done['solver_finished'] and done['owned_exited'] and len(parts)==job['frames'] and parts==list(range(len(parts)))
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert 'SlipMode="DBC vel=0"' in text and 'HydroMechInitMode="FreeSurface"' in text and 'PoreDarcySymmetricCorr="Receiver"' in text
        assert 'PoreShepardRegularization="'+('Enabled' if job['shepard_on'] else 'Disabled')+'"' in text
        assert int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==40 and 'SoilDampingCoef=0.02' in text and 'SoilHourglass: forcecalls=' not in text
        good=[r for r in rows if r['passed']]; assert len(good)==len(parts) and good[0]['natural_step']==0 and good[-1]['natural_step']==job['steps']
        assert all(a['natural_step']<b['natural_step'] and a['time_s']<b['time_s'] for a,b in zip(good,good[1:]))
        if job['memcheck']:
            summaries=re.findall(r'ERROR SUMMARY:\s*(\d+)\s+errors',memlog.read_text(errors='replace'))
            sanitizer_passed=bool(summaries) and all(int(n)==0 for n in summaries); assert sanitizer_passed,'Memcheck summary missing or nonzero'
        verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion',error=repr(failure),traceback=traceback.format_exc()))
    pairs,differences=comparisons(job,frames,references)
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('frames',rows),('history',history),('pairs',pairs),('differences',differences)]]
    result=dict(passed=not errors and bool(pairs) and all(r['gate_passed'] for r in pairs),errors=errors,rows=rows,pairs=pairs,sanitizer_passed=sanitizer_passed,
        reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),owned_wrapper_pid=None if child is None else child.pid,
        wall_seconds=time.perf_counter()-started,physical_acceptance=False)
    seal(receipt,result); return result,bound(receipt)


def run():
    assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs'])
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[]); cache={}; pairs=[]
    def publish():
        tmp=RUN.with_suffix('.tmp'); seal(tmp,state); os.replace(tmp,RUN)
    publish()
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name']; publish()
            for key,_ in job['refs']:
                if key not in cache:cache[key]=control_frames(prepared['controls'][key])
            result,record=one_job(job,prepared,cache); state['jobs'].append(record); pairs+=result['pairs']; publish()
            assert result['passed'],('Gate failed; later jobs held',job['name'],result['errors'])
        verify(prepared['inputs']); state['status']='bounded_regression_passed_pending_review'
    except BaseException as failure:state.update(status='gate_failed_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]])
    if pairs:state['comparisons']=event.write_csv(TAG+'_pairs',pairs)
    publish(); passed=state['status']=='bounded_regression_passed_pending_review' and len(state['jobs'])==5
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),
        physical_acceptance=False,formal_admitted=False,automatic_long_run_admitted=False)); return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
