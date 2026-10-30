"""Bounded Shepard/backend isolation; never rerun completed Stage1 controls."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
import sw_stage1_short_r1 as baseline

TESTS, CASE = baseline.TESTS, baseline.CASE
LOGS, CONFIGS, OUTPUTS, FIGURES = baseline.LOGS, baseline.CONFIGS, baseline.OUTPUTS, baseline.FIGURES
read, seal, verify, unique, native, bound, utc, inventory = [getattr(baseline,n) for n in ['read','seal','verify','unique','native','bound','utc','inventory']]
TAG = 'sw_stage1_isolate_r1'
PREP, RUN, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE = TESTS/'notes'/(TAG+'.json')
JOBS = [('cpu_old_on','cpu','old',True),('gpu_old_on','gpu','old',True),
        ('cpu_current_off','cpu','current',False),('gpu_current_off','gpu','current',False)]


def expected(spec, program):
    suffix, backend, _, shepard_on = spec
    xml, bat = baseline.expected((suffix,backend,'0.000001',2000,40),program)
    bat = bat.replace(baseline.TAG,TAG)
    if not shepard_on:
        xml,n = re.subn(r'(<PoreShepardRegularization value=")1(" comment=")[^"]+("[^\n]+)',
            lambda m:m[1]+'0'+m[2]+'Shepard OFF isolation; other physical settings unchanged'+m[3],xml)
        assert n == 1
    return xml,bat


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    baseline.selftest()
    for spec in JOBS:
        xml,bat=expected(spec,CASE/'private/solver.exe')
        assert ('PoreShepardRegularization value="1"' in xml)==spec[3]
        assert 'PoreDarcySymmetricCorr' not in xml and baseline.TAG not in bat and TAG in bat
    return dict(passed=True,programs_started=False,files_written=False)


def prepare():
    selftest(); assert not list(LOGS.glob(TAG+'*')) and not list(OUTPUTS.glob(TAG+'*'))
    oldcheckpath=LOGS/(baseline.TAG+'.check.json'); oldcheck=read(oldcheckpath)
    assert len(oldcheck['jobs'])==3
    oldrun=read(oldcheck['run']['path']); oldprep=read(oldrun['prepared']['path'])
    proof=[bound(p) for p in [__file__,NOTE,Path(baseline.__file__),baseline.TEMPLATE,baseline.READER,baseline.READER_SOURCE,
        TESTS/'notes/selfweight_readiness_r1.md',baseline.C04/'support/cryer_start_r1.py',baseline.C02/'support/symc_1d_short_r1.py',
        baseline.C02.parent/'support/release_case.py',baseline.C02.parent/'support/compare_precision_q0.py']]
    proof += [bound(oldcheckpath),oldcheck['run'],oldrun['prepared']] + oldprep['inputs']; adopted={}
    for job,record in zip(oldprep['jobs'],oldcheck['jobs']):
        result=read(record['path']); done=read(result['sealed_completion']['path'])
        assert result['passed'] and len(result['rows'])==5 and done['solver_finished'] and done['owned_exited'] and done['exit_code']==0
        assert job['suffix'] in ['cpu_c','gpu_c','gpu_h']
        adopted[job['suffix']]=dict(job=job,receipt=record,completion=result['sealed_completion'])
        proof += [record,result['sealed_completion'],job['program'],job['build'],job['config'],job['bat']]+job['runtime']+done['outputs']+result['artifacts']
    assert len(adopted)==3
    basepath=baseline.C04/'logs/cryer_darcy_switch_r1.base.json'; archive=read(basepath)
    proof.append(bound(basepath)); jobs=[]
    for spec in JOBS:
        suffix,backend,version,on=spec; name=TAG+'_'+suffix
        if version=='old':
            exe='DualSPHysics5.2CPU_win64.exe' if backend=='cpu' else 'DualSPHysics5.2_GEO_win64.exe'
            program=next(x['snapshot'] for x in archive['files'] if Path(x['snapshot']['path']).name==exe)
            runtime=[x['snapshot'] for x in archive['files'] if Path(x['snapshot']['path']).name in ['ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','DsphConfig.xml']]
            build=bound(basepath)
        else:
            previous=adopted['cpu_c' if backend=='cpu' else 'gpu_c']['job']
            program,runtime,build=previous['program'],previous['runtime'],previous['build']
        assert len(runtime)==4
        cfg,bat=CONFIGS/(name+'_Def.xml'),CONFIGS/('x'+name+'_win64_'+backend.upper()+'.bat')
        assert not cfg.exists() and not bat.exists(); xml,command=expected(spec,Path(program['path']))
        with cfg.open('x',encoding='utf8',newline='') as f:f.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as f:f.write(command)
        jobs.append(dict(name=name,suffix=suffix,backend=backend,version=version,shepard_on=on,dt=1e-6,steps=2000,shepard=40,
            program=program,runtime=runtime,build=build,config=bound(cfg),bat=bound(bat)))
        proof += [program,build,bound(cfg),bound(bat)]+runtime
    proof=unique(proof);verify(proof)
    seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,adopted=adopted,
        prior_global_cross_failed=not oldcheck['passed'],prior_individual_safety_adopted=True,physical_acceptance=False,automatic_long_run_admitted=False))


def one_job(job,prepared):
    folder=OUTPUTS/job['name'];log=LOGS/(job['name']+'.log');complete=LOGS/(job['name']+'.completion.json');receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt]);verify(prepared['inputs'])
    child=None;initial=None;rows=[];error=None;started=time.perf_counter();m=baseline.model()
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll();count=len(list((folder/'data').glob('Part_*.bi4')));available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    p=len(rows);a=native(folder,p)
                    if initial is None:initial=a.copy()
                    row,_=baseline.measure(a,initial,p,job,m);rows.append(row)
                if code is not None:break
                time.sleep(2)
    except BaseException as failure:
        error=repr(failure);trace=traceback.format_exc()
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
    survivors=[p for p in inventory() if job['name'] in (p.get('CommandLine') or '')]
    done=dict(solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        exit_code=None if child is None else child.returncode,owned_exited=not survivors,surviving_owned=survivors,
        program=job['program'],config=job['config'],bat=job['bat'],outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+([bound(log)] if log.exists() else []))
    seal(complete,done)
    try:
        assert error is None,error
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==5
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==2000
        assert 'SlipMode="DBC vel=0"' in text and 'HydroMechInitMode="FreeSurface"' in text
        assert 'PoreShepardRegularization="'+('Enabled' if job['shepard_on'] else 'Disabled')+'"' in text
        assert int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==40 and 'SoilDampingCoef=0.02' in text
        assert 'SoilHourglass: forcecalls=' not in text
        if job['version']=='current':assert 'PoreDarcySymmetricCorr="Receiver"' in text
        verify(prepared['inputs'])
    except BaseException as failure:error=repr(failure);trace=traceback.format_exc()
    result=dict(passed=error is None,error=error,rows=rows,sealed_completion=bound(complete),owned_wrapper_pid=None if child is None else child.pid,
        wall_seconds=time.perf_counter()-started,loop_seconds=float(re.search(r'Simulation Runtime\.*:\s*([\d.]+)',text)[1]) if done['solver_finished'] else None,
        physical_acceptance=False)
    if error:result['traceback']=trace
    seal(receipt,result);return result,bound(receipt)


def compare(label,left,right,tolerance,kind):
    rows=[];a0,b0=left[0],right[0]
    for p,(a,b) in enumerate(zip(left,right)):
        assert len(a)==len(b)==1000 and np.array_equal(a.id,b.id) and list(a)==list(b) and len(a.columns)==35
        dt=float(a.time_s.iloc[0]-b.time_s.iloc[0]);bad=a.to_numpy(dtype='<f8').view('<u8')!=b.to_numpy(dtype='<f8').view('<u8')
        du=(a[['x','y','z']].to_numpy()-a0[['x','y','z']].to_numpy())-(b[['x','y','z']].to_numpy()-b0[['x','y','z']].to_numpy())
        pressure=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)));displacement=float(np.linalg.norm(du,axis=1).max()*1000)
        rows.append(dict(comparison=label,kind=kind,part=p,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),actual_time_difference_s=dt,
            saved_step=int(a.saved_step.iloc[0]),reference_saved_step=int(b.saved_step.iloc[0]),time_eligible=abs(dt)<=tolerance,
            pressure_rms_pa=pressure,pressure_absmax_pa=float(abs(a.pressure-b.pressure).max()),material_displacement_max_difference_mm=displacement,
            all35_columns0ulp=not bool(bad.any()),different_fields=';'.join(a.columns[i] for i in np.flatnonzero(bad.any(axis=0))),
            comparison_bound_applied=kind!='option',comparison_bound_passed=(not bool(bad.any())) if kind=='exact35' else (pressure<=5 and displacement<=.005) if kind=='screen' else None))
    assert len(rows)==5
    return rows


def run():
    assert not RUN.exists() and not CHECK.exists() and not inventory();prepared=read(PREP);verify(prepared['inputs'])
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[])
    def publish():
        tmp=RUN.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2,allow_nan=False),encoding='utf8');os.replace(tmp,RUN)
    publish();fresh={};allpairs=[]
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name'];publish();result,record=one_job(job,prepared)
            state['jobs'].append(record);fresh[job['suffix']]=result;publish()
        cache={}
        for suffix,adopt in prepared['adopted'].items():
            verify([adopt['receipt'],adopt['completion']]);verify(read(adopt['completion']['path'])['outputs'])
            cache[suffix]=[native(OUTPUTS/adopt['job']['name'],p) for p in range(5)]
        for suffix,result in fresh.items():
            if result['passed']:cache[suffix]=[native(OUTPUTS/(TAG+'_'+suffix),p) for p in range(5)]
        comparisons=[('current_vs_old_CPU_ShepardON','cpu_c','cpu_old_on',1e-12,'exact35'),
            ('current_vs_old_GPU_ShepardON','gpu_c','gpu_old_on',1e-12,'exact35'),
            ('archivedON_GPU_minus_CPU','gpu_old_on','cpu_old_on',1e-12,'screen'),
            ('currentON_GPU_minus_CPU','gpu_c','cpu_c',1e-12,'screen'),
            ('currentOFF_GPU_minus_CPU','gpu_current_off','cpu_current_off',1e-12,'screen'),
            ('CPU_ShepardOFF_minus_ON','cpu_current_off','cpu_c',1e-12,'option'),
            ('GPU_ShepardOFF_minus_ON','gpu_current_off','gpu_c',1e-12,'option'),
            ('adopted_GPU_ON_half_minus_coarse','gpu_h','gpu_c',1.01e-6,'screen')]
        skipped=[]
        for label,left,right,tolerance,kind in comparisons:
            if left in cache and right in cache:allpairs+=compare(label,cache[left],cache[right],tolerance,kind)
            else:skipped.append(label)
        csv=FIGURES/(TAG+'_comparisons.csv')
        with csv.open('x',encoding='utf8',newline='') as stream:pd.DataFrame(allpairs).to_csv(stream,index=False,float_format='%.17g')
        state.update(status='bounded_isolation_complete_pending_causal_review',comparisons=bound(csv),skipped_comparisons=skipped,
            fresh_individual_safety_passed=all(r['passed'] for r in fresh.values()),
            exact_implementation_passed=all(r['all35_columns0ulp'] and r['time_eligible'] for r in allpairs if r['kind']=='exact35') and sum(r['kind']=='exact35' for r in allpairs)==10,
            all_screen_bounds_passed=all(r['comparison_bound_passed'] and r['time_eligible'] for r in allpairs if r['kind']=='screen'))
        verify(prepared['inputs'])
    except BaseException as failure:state.update(status='diagnostic_incomplete',error=repr(failure),traceback=traceback.format_exc())
    state['finished_utc']=utc();publish()
    seal(CHECK,dict(diagnostic_completed=state['status']=='bounded_isolation_complete_pending_causal_review',run=bound(RUN),jobs=state['jobs'],
        fresh_individual_safety_passed=state.get('fresh_individual_safety_passed',False),exact_implementation_passed=state.get('exact_implementation_passed',False),
        all_screen_bounds_passed=state.get('all_screen_bounds_passed',False),error=state.get('error'),physical_acceptance=False,automatic_long_run_admitted=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:run()
    else:parser.print_help()
