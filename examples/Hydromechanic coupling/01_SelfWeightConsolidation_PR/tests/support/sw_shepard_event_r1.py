"""Four fresh 80-us Shepard event diagnostics; default help, no physical admission."""
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
import sw_stage1_short_r1 as baseline
import sw_stage1_isolate_r1 as isolate

TESTS, CASE = baseline.TESTS, baseline.CASE
LOGS, CONFIGS, OUTPUTS, FIGURES = baseline.LOGS, baseline.CONFIGS, baseline.OUTPUTS, baseline.FIGURES
read, seal, verify, unique, bound, utc, inventory = [getattr(baseline,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG = 'sw_shepard_event_r1'
PREP, RUN, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE, BUILD = TESTS/'notes'/(TAG+'.json'), LOGS/'sw_native_r1.build.json'
READER = OUTPUTS/'sw_native_r1/ReadSelfWeightNative.exe'
JOBS = [('cpu_on','cpu',True),('gpu_on','gpu',True),('cpu_off','cpu',False),('gpu_off','gpu',False)]


def expected(spec, program):
    suffix,backend,on = spec
    xml,bat = baseline.expected((suffix,backend,'0.000001',80,40),program)
    for key,value in [('TimeMax','0.00008'),('TimeOut','0.000001')]:
        xml,n = re.subn(r'(<parameter key="'+key+r'" value=")[^"]+(" comment=")[^"]+("[^\n]+)',
            lambda m:m[1]+value+m[2]+'Two Shepard event diagnostic; no physical acceptance'+m[3],xml)
        assert n == 1,key
    if not on:
        xml,n = re.subn(r'(<PoreShepardRegularization value=")1(")',r'\g<1>0\2',xml); assert n == 1
    return xml,bat.replace(baseline.TAG,TAG)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); baseline.selftest(); isolate.selftest()
    for spec in JOBS:
        xml,bat=expected(spec,CASE/'private/solver.exe'); tree=ET.fromstring(xml)
        for key,value in [('SavePosDouble','1'),('DtIni','0.000001'),('DtFixed','0.000001'),('TimeMax','0.00008'),('TimeOut','0.000001')]:
            assert tree.find('.//parameter[@key="'+key+'"]').get('value') == value
        assert tree.find('.//PoreShepardRegularization').get('value') == ('1' if spec[2] else '0')
        assert tree.find('.//PoreShepardInterval').get('value') == '40' and tree.find('.//HydraulicConductivity').get('value') == '0'
        assert '-nsteps:80' in bat and 'if exist "%dirout%" goto fail' in bat and baseline.TAG not in bat
    return dict(passed=True,programs_started=False,files_written=False)


def prepare():
    selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,FIGURES])
    prior=read(baseline.PREP); inherited=read(baseline.C02/'logs/symc_1d_short_r1.inputs.json'); build=read(BUILD)
    assert build['exit_code'] == 0 and build['production_modified'] is False
    assert Path(build['program']['path']).resolve() == READER.resolve()
    proof=prior['inputs']+inherited['inputs']+build['inputs']+[build['program'],build['log']]
    proof += [bound(p) for p in [__file__,NOTE,baseline.PREP,isolate.__file__,BUILD]]
    jobs=[]
    for suffix,backend,on in JOBS:
        old=next(j for j in prior['jobs'] if j['suffix'] == ('cpu_c' if backend == 'cpu' else 'gpu_c'))
        manifest=read(old['build']['path']); assert manifest['exit_code'] == 0 and manifest['owned_exited'] and manifest['protected_inputs_unchanged']
        assert len(old['runtime']) == 4
        name=TAG+'_'+suffix; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_'+backend.upper()+'.bat')
        xml,command=expected((suffix,backend,on),Path(old['program']['path']))
        verify(unique(proof+[old['program'],old['build']]+old['runtime']))
        with cfg.open('x',encoding='utf8',newline='') as f:f.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as f:f.write(command)
        jobs.append(dict(name=name,suffix=suffix,backend=backend,shepard_on=on,dt=1e-6,steps=80,shepard=40,
            program=old['program'],runtime=old['runtime'],build=old['build'],config=bound(cfg),bat=bound(bat)))
        proof += [old['program'],old['build'],bound(cfg),bound(bat)]+old['runtime']+[manifest['log']]+manifest['artifacts']
    proof=unique(proof); verify(proof)
    seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,reader=build['program'],physical_acceptance=False,automatic_long_run_admitted=False))


def native(folder,part):
    raw=subprocess.check_output([str(READER),str(folder/'data'),str(part)],creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
    return pd.read_csv(io.BytesIO(raw),float_precision='round_trip')


def measure(a,initial,part):
    assert len(a.columns)==38 and len(a)==1040 and np.array_equal(a.id,np.arange(1040))
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.nout.eq(0).all()
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.native_count.eq(1040).all()
    assert np.array_equal(a.is_boundary.to_numpy(),np.r_[np.ones(40),np.zeros(1000)])
    assert np.array_equal(a[['mass','dp','h']],initial[['mass','dp','h']]) and np.array_equal(a.porepress0,initial.porepress0)
    assert np.array_equal(a.excess_native.to_numpy(dtype=np.float32),a.pressure.to_numpy(dtype=np.float32)-a.porepress0.to_numpy(dtype=np.float32))
    t=float(a.time_s.iloc[0]); saved=int(a.saved_step.iloc[0]); step=saved+1 if part else 0
    assert a.time_s.eq(t).all() and a.saved_step.eq(saved).all() and abs(t-step*1e-6)<=1e-12
    if part: assert a.has_dterror.eq(1).all() and float(a.dterror_s.max())<=1e-14
    soil=a.iloc[40:]; soil0=initial.iloc[40:]; du=soil[['x','y','z']].to_numpy()-soil0[['x','y','z']].to_numpy()
    dx=(du[:,0]+.05)%.1-.05; span=float(np.ptp(soil.z.to_numpy().reshape(10,100),axis=0).max()*1000)
    assert soil.z.gt(0).all() and abs(dx).max()*1000<.5 and span<.5
    surface=soil.fstype.isin([2,3]); assert set(soil.id[surface])==set(soil0.id.iloc[99::100]) and soil.pressure[surface].eq(0).all()
    return dict(part=part,time_s=t,saved_step=saved,natural_step=step,rho_min=float(a.rho.min()),rho_max=float(a.rho.max()),
        pressure_min_pa=float(a.pressure.min()),pressure_max_pa=float(a.pressure.max()),dterror_s=float(a.dterror_s.max()),
        true_drained_count=int(surface.sum()),periodic_dx_max_mm=float(abs(dx).max()*1000),layer_span_max_mm=span)


def write_csv(name,rows):
    path=FIGURES/(name+'.csv')
    with path.open('x',encoding='utf8',newline='') as stream:pd.DataFrame(rows).to_csv(stream,index=False,float_format='%.17g')
    return bound(path)


def focus(a):
    return a[a.id.lt(40) | ((a.id-40).mod(100).lt(3) & a.id.ge(40))]


def one_job(job,prepared):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt]); verify(prepared['inputs'])
    child=None; started=time.perf_counter(); errors=[]; frames={}; rows=[]; history=[]; readers=[]
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            child.wait(timeout=120)
    except BaseException as failure:
        errors.append(dict(stage='execute',error=repr(failure),traceback=traceback.format_exc()))
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
    survivors=[p for p in inventory() if job['name'] in (p.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],config=job['config'],bat=job['bat'],
        outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+([bound(log)] if log.exists() else []))
    seal(complete,done)
    parts=sorted(int(p.stem.split('_')[-1]) for p in (folder/'data').glob('Part_*.bi4'))
    for part in parts:
        try:
            a=native(folder,part); readers.append(dict(part=part,exit_code=0)); frames[part]=a
            history += [dict(job=job['name'],part=part,natural_step=(int(a.saved_step.iloc[0])+1 if part else 0),**r) for r in focus(a).to_dict('records')]
            rows.append(dict(passed=True,**measure(a,frames[0],part)))
        except BaseException as failure:
            errors.append(dict(stage='native_or_measure',part=part,error=repr(failure),traceback=traceback.format_exc()))
            rows.append(dict(part=part,passed=False,error=repr(failure)))
            if not any(r['part']==part for r in readers): readers.append(dict(part=part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
    try:
        assert done['solver_finished'] and done['owned_exited'] and len(parts)>=3 and parts==list(range(len(parts)))
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==80
        assert 'SlipMode="DBC vel=0"' in text and 'HydroMechInitMode="FreeSurface"' in text and 'PoreDarcySymmetricCorr="Receiver"' in text
        assert 'PoreShepardRegularization="'+('Enabled' if job['shepard_on'] else 'Disabled')+'"' in text
        assert int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==40 and 'SoilDampingCoef=0.02' in text and 'SoilHourglass: forcecalls=' not in text
        good=[r for r in rows if r['passed']]; assert len(good)==len(parts) and good[0]['natural_step']==0 and good[-1]['natural_step']==80
        assert all(a['natural_step']<b['natural_step'] and a['time_s']<b['time_s'] for a,b in zip(good,good[1:]))
        verify(prepared['inputs'])
    except BaseException as failure: errors.append(dict(stage='completion',error=repr(failure),traceback=traceback.format_exc()))
    events=[]
    for step in [40,80]:
        good=[r for r in rows if r['passed']]; before=[r for r in good if r['natural_step']<step]; after=[r for r in good if r['natural_step']>=step]
        events.append(dict(event_natural_step=step,before=before[-1] if before else None,at_or_after=after[0] if after else None))
    artifacts=[write_csv(job['name']+'_history',history),write_csv(job['name']+'_frames',rows)]
    result=dict(passed=not errors,errors=errors,rows=rows,event_brackets=events,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,physical_acceptance=False)
    seal(receipt,result); return result,bound(receipt),frames


def compare(label,left,right):
    keyed=lambda frames:{(int(a.saved_step.iloc[0])+1 if p else 0):(p,a) for p,a in frames.items()}
    aa,bb=keyed(left),keyed(right); rows=[]; differences=[]
    for step in sorted(set(aa)|set(bb)):
        row=dict(comparison=label,natural_step=step,time_eligible=False,comparison_bound_passed=False)
        try:
            pa,a=aa[step]; pb,b=bb[step]; dt=float(a.time_s.iloc[0]-b.time_s.iloc[0])
            row.update(part=pa,reference_part=pb,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),actual_time_difference_s=dt,
                saved_step=int(a.saved_step.iloc[0]),reference_saved_step=int(b.saved_step.iloc[0]))
            assert np.array_equal(a.id,b.id) and len(a)==len(b)==1040
            for r in (focus(a).set_index('id')-focus(b).set_index('id')).reset_index().to_dict('records'):
                differences.append(dict(comparison=label,natural_step=step,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),**{'delta_'+k if k!='id' else k:v for k,v in r.items()}))
            assert np.isfinite(a.to_numpy(dtype='<f8')).all() and np.isfinite(b.to_numpy(dtype='<f8')).all()
            a0,b0=left[0].iloc[40:],right[0].iloc[40:]; sa,sb=a.iloc[40:],b.iloc[40:]
            du=(sa[['x','y','z']].to_numpy()-a0[['x','y','z']].to_numpy())-(sb[['x','y','z']].to_numpy()-b0[['x','y','z']].to_numpy())
            pressure=float(np.sqrt(np.mean((sa.pressure-sb.pressure)**2))); displacement=float(np.linalg.norm(du,axis=1).max()*1000)
            row.update(time_eligible=abs(dt)<=1e-12 and row['saved_step']==row['reference_saved_step'],pressure_rms_pa=pressure,
                pressure_absmax_pa=float(abs(sa.pressure-sb.pressure).max()),boundary_pressure_absmax_pa=float(abs(a.pressure.iloc[:40]-b.pressure.iloc[:40]).max()),
                material_displacement_max_difference_mm=displacement,comparison_bound_passed=pressure<=5 and displacement<=.005)
        except BaseException as failure: row['error']=repr(failure)
        rows.append(row)
    return rows,differences


def run():
    assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs'])
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[]); results={}; cache={}; pairs=[]; differences=[]; coverage=[]
    def publish():
        tmp=RUN.with_suffix('.tmp'); seal(tmp,state); os.replace(tmp,RUN)
    publish()
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name']; publish(); result,record,frames=one_job(job,prepared)
            state['jobs'].append(record); results[job['suffix']]=result; cache[job['suffix']]=frames; publish()
        for option in ['on','off']:
            rows,delta=compare('GPU_minus_CPU_Shepard'+option.upper(),cache['gpu_'+option],cache['cpu_'+option]); pairs+=rows; differences+=delta
            coverage.append(bool(rows))
        state.update(comparisons=write_csv(TAG+'_pairs',pairs),backend_differences=write_csv(TAG+'_differences',differences),
            individual_safety_passed=len(results)==4 and all(r['passed'] for r in results.values()),
            all_screen_bounds_passed=all(coverage) and all(r['time_eligible'] and r['comparison_bound_passed'] for r in pairs))
        verify(prepared['inputs']); state['status']='event_diagnostic_complete_pending_causal_review'
    except BaseException as failure: state.update(status='diagnostic_incomplete',error=repr(failure),traceback=traceback.format_exc())
    state['finished_utc']=utc(); publish()
    seal(CHECK,dict(diagnostic_completed=state['status']=='event_diagnostic_complete_pending_causal_review',run=bound(RUN),jobs=state['jobs'],
        individual_safety_passed=state.get('individual_safety_passed',False),all_screen_bounds_passed=state.get('all_screen_bounds_passed',False),
        error=state.get('error'),physical_acceptance=False,automatic_long_run_admitted=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:run()
    else:parser.print_help()
