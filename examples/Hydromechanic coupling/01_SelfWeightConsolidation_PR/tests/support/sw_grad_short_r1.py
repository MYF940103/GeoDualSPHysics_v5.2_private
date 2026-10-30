"""Three short stress-rate-gradient checks; no full run, build, help probe or queue."""
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
import sw_stage1_current_r2 as stage

current, event, baseline = stage.current, stage.event, stage.baseline
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = stage.TESTS, stage.CASE, stage.LOGS, stage.CONFIGS, stage.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(stage,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
clock_table, measure, profiles = stage.clock_table, stage.measure, stage.profiles
TAG='sw_grad_short_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
CPU=baseline.C04/'logs/cryer_darcy_switch_build_r1_ReleaseCPU.build.json'
SIGMA=['sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_yz','sigma_xz']
JOBS=[dict(suffix='cpu',backend='cpu',threads=8,dt='0.000001',shepard=40,on=False,end='0.002',interval='0.0004999',steps=2000,frames=5),
      dict(suffix='gpu',backend='gpu',threads=1,dt='0.000001',shepard=40,on=False,end='0.002',interval='0.0004999',steps=2000,frames=5),
      dict(suffix='half',backend='gpu',threads=1,dt='0.0000005',shepard=80,on=False,end='0.002',interval='0.0004999',steps=4000,frames=5)]


def expected(job,program):
    xml,bat=stage.expected(job,program); key='SoilStressRateGradCorr'
    count=len(ET.fromstring(xml).findall('.//parameter[@key="'+key+'"]')); assert count<=1
    if count:
        xml,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]+("[^\n]+)',r'\g<1>1\2',xml); assert n==1
    else:
        xml,n=re.subn(r'(?m)^([ ]*)(<parameter key="SoilDampingCoef"[^\n]*\n)',
            lambda m:m[0]+m[1]+'<parameter key="'+key+'" value="1" comment="Correct soil stress-rate velocity gradient; short diagnostic only" />\n',xml); assert n==1
    assert bat.count('-gpu -ompthreads:1 ')==1
    return xml,bat.replace(stage.TAG,TAG).replace('-gpu -ompthreads:1 ','-'+job['backend']+' -ompthreads:'+str(job['threads'])+' ',1)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); tree=ET.fromstring(xml); base=ET.fromstring(stage.expected(job,CASE/'private/solver.exe')[0])
        found=tree.findall('.//parameter[@key="SoilStressRateGradCorr"]'); assert len(found)==1 and found[0].get('value')=='1'
        signature=lambda root:[(e.tag,sorted(e.attrib.items())) for e in root.iter() if e.get('key')!='SoilStressRateGradCorr']
        assert signature(tree)==signature(base) and tree.find('.//PoreShepardRegularization').get('value')=='0'
        assert all(x not in xml for x in ['SoilBoundaryDerivativeSPR','SoilHourglassXi','PoreDarcySymmetricCorr'])
        assert ('-'+job['backend']+' -ompthreads:'+str(job['threads'])) in bat and stage.TAG not in bat
        assert stage.plan(job)==([0,1000,2000,3000,4000] if job['suffix']=='half' else [0,500,1000,1500,2000])
    return dict(passed=True,programs_started=False,files_written=False)


def parameters():
    root=ET.parse(baseline.TEMPLATE); value=lambda name:float(root.find('.//'+name).get('value'))
    return dict(K=value('ModulusE')/(3*(1-2*value('PRvs'))),Mf=value('PoreWaterBulkModulus')/value('Porosity'))


def r_values(a,p):
    soil=a.iloc[40:]; r=soil.excess_native.to_numpy()+p['Mf']*(soil.sigma_xx+soil.sigma_yy+soil.sigma_zz).to_numpy()/(3*p['K'])
    return r[((soil.id.to_numpy().astype(int)-40)%100)!=99]


def r_summary(a,p):
    r=r_values(a,p); assert len(r)==990
    return dict(r_excluding_top_rms_pa=float(np.sqrt(np.mean(r*r))),r_excluding_top_absmax_pa=float(abs(r).max()),r_excluding_top_mean_pa=float(r.mean()),r_soil_count=990)


def prepare():
    stage.old.prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    check=read(stage.CHECK); assert check['passed'] and len(check['jobs'])==4; prior=read(stage.PREP); cpu=read(CPU)
    assert cpu['exit_code']==0 and cpu['owned_exited'] and cpu['protected_inputs_unchanged'] and len(cpu['runtime'])==4
    proof=prior['inputs']+[bound(p) for p in [__file__,NOTE,stage.__file__,stage.PREP,stage.CHECK,CPU,TESTS/'support/sw_stage1_equilibrium_review_r1.py']]+[check['run']]+check['jobs']
    proof += [cpu['program'],cpu['log']]+cpu['artifacts']+[r['target'] for r in cpu['runtime']]
    refs={}
    for key,name,dt,steps,parts in [('cpu_g0',current.isolate.TAG+'_cpu_current_off','0.000001',2000,list(range(5))),
        ('gpu_g0',current.TAG+'_release_off_short','0.000001',2000,list(range(5))),('r2_off_initial',stage.TAG+'_off','0.000001',300001,[0])]:
        receipt=LOGS/(name+'.receipt.json'); result=read(receipt); done=read(result['sealed_completion']['path'])
        assert result['passed'] and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
        selected=[r for r in done['outputs'] if Path(r['path']).name in ['Run.out','Part_Head.ibi4','PartInfo.ibi4']+[f'Part_{part:04d}.bi4' for part in parts]]
        refs[key]=dict(name=name,folder=str(OUTPUTS/name),dt=dt,steps=steps,receipt=bound(receipt),completion=result['sealed_completion'],outputs=selected,rows=[r for r in result['rows'] if r['part'] in parts])
        proof += [bound(receipt),result['sealed_completion']]+selected
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); program=cpu['program'] if job['backend']=='cpu' else prior['jobs'][0]['program']; runtime=[r['target'] for r in cpu['runtime']] if job['backend']=='cpu' else prior['jobs'][0]['runtime']
        name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_'+job['backend'].upper()+'.bat'); xml,command=expected(job,Path(program['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=program,runtime=runtime,config=bound(cfg),bat=bound(bat)); jobs.append(job); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,references=refs,parameters=parameters(),physical_acceptance=False,full_run_admitted=False,restart_admitted=False))


def load_reference(ref):
    verify([ref['receipt'],ref['completion']]+ref['outputs']); frames={}; clock=clock_table(ref['dt'],ref['steps'])
    for row in ref['rows']:
        part=row['part']; a=current.native(Path(ref['folder']),part); frames[part]=a; measured=measure(a,frames[0],part,ref,clock)
        assert measured['time_s']==row['time_s'] and measured['saved_step']==row['saved_step']
    return frames


def pair(label,kind,pa,a,pb,b,a0,b0,p):
    assert a.shape==b.shape and list(a)==list(b) and np.array_equal(a.id,b.id)
    dt=float(a.time_s.iloc[0]-b.time_s.iloc[0]); sa,sb=a.iloc[40:],b.iloc[40:]
    du=(sa[['x','y','z']].to_numpy()-a0.iloc[40:][['x','y','z']].to_numpy())-(sb[['x','y','z']].to_numpy()-b0.iloc[40:][['x','y','z']].to_numpy())
    pressure=float(np.sqrt(np.mean((sa.pressure-sb.pressure)**2))); displacement=float(np.linalg.norm(du,axis=1).max()*1000); ra,rb=r_values(a,p),r_values(b,p)
    gated=kind in ['cpu_gpu','gpu_half']; eligible=abs(dt)<=1e-14 and (kind!='cpu_gpu' or int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0]))
    row=dict(comparison=label,kind=kind,part=pa,reference_part=pb,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),saved_step=int(a.saved_step.iloc[0]),
        reference_saved_step=int(b.saved_step.iloc[0]),actual_time_difference_s=dt,time_eligible=eligible,gate_applied=gated,passed=bool(eligible and pressure<=5 and displacement<=.005) if gated else None,
        pressure_rms_pa=pressure,material_displacement_max_difference_mm=displacement,r_excluding_top_rms_pa=float(np.sqrt(np.mean(ra*ra))),reference_r_excluding_top_rms_pa=float(np.sqrt(np.mean(rb*rb))),
        r_excluding_top_delta_rms_pa=float(np.sqrt(np.mean((ra-rb)**2))),r_excluding_top_delta_absmax_pa=float(abs(ra-rb).max()))
    for key in ['pressure','porepress0','excess_native','rho']+SIGMA+['x','y','z','vx','vy','vz']:
        delta=sa[key].to_numpy()-sb[key].to_numpy(); row[key+'_delta_rms']=float(np.sqrt(np.mean(delta*delta))); row[key+'_delta_absmax']=float(abs(delta).max())
    focus=(event.focus(a).set_index('id')-event.focus(b).set_index('id')).reset_index()
    differences=[dict(comparison=label,part=pa,reference_part=pb,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),**{('delta_'+k if k!='id' else k):v for k,v in r.items()}) for r in focus.to_dict('records')]
    return row,differences


def comparisons(job,frames,refs,p):
    rows=[]; differences=[]; suffix=job['suffix']; tasks=[]
    if suffix=='gpu':tasks += [('cpu_gpu',refs['new_cpu'],[(i,i) for i in range(5)])]
    if suffix=='half':tasks += [('gpu_half',refs['new_gpu'],[(i,i) for i in range(5)])]
    if suffix in ['cpu','gpu']:
        ref=refs[suffix+'_g0']; keyed=lambda cache:{(int(a.saved_step.iloc[0])+1 if i else 0):i for i,a in cache.items()}; aa,bb=keyed(frames),keyed(ref)
        shared=sorted(set(aa)&set(bb)); assert len(shared)==4; tasks += [('grad_option_descriptive',ref,[(aa[s],bb[s]) for s in shared])]
    tasks += [('r2_off_initial_only_descriptive',refs['r2_off_initial'],[(0,0)])]
    for kind,ref,indices in tasks:
        for pa,pb in indices:
            try:row,delta=pair(job['name']+'_minus_'+kind,kind,pa,frames[pa],pb,ref[pb],frames[0],ref[0],p); rows.append(row); differences+=delta
            except BaseException as failure:rows.append(dict(comparison=kind,part=pa,reference_part=pb,gate_applied=kind in ['cpu_gpu','gpu_half'],passed=False,error=repr(failure)))
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
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],config=job['config'],bat=job['bat'],outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
    parts=sorted(int(q.stem.split('_')[-1]) for q in (folder/'data').glob('Part_*.bi4'))
    for part in parts:
        try:
            a=current.native(folder,part); frames[part]=a; readers.append(dict(part=part,exit_code=0)); history += [dict(part=part,**r) for r in event.focus(a).to_dict('records')]
            rows.append(dict(**measure(a,frames[0],part,job,clock),**r_summary(a,p)))
            for row in profiles(a,frames[0],part):row.update(r_native_pa=row['excess_native_pa']+p['Mf']*(row['sigma_xx']+row['sigma_yy']+row['sigma_zz'])/(3*p['K']),included_in_r_summary=row['layer']!=99); layers.append(row)
        except BaseException as failure:
            errors.append(dict(stage='native_or_measure',part=part,error=repr(failure),traceback=traceback.format_exc()))
            if not any(r['part']==part for r in readers):readers.append(dict(part=part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
    try:
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==5 and parts==list(range(5)) and len(layers)==500
        assert [r['natural_step'] for r in rows]==stage.plan(job) and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert 'SoilStressRateGradCorr="KernelGradient"' in text and 'PoreCompressionGradCorr="KernelGradient"' in text and 'PoreShepardRegularization="Disabled"' in text
        assert 'SlipMode="DBC vel=0"' in text and 'HydroMechInitMode="FreeSurface"' in text and 'PoreDarcySymmetricCorr="Receiver"' in text
        assert int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard'] and 'SoilDampingCoef=0.02' in text and 'SoilHourglass: forcecalls=' not in text; verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion',error=repr(failure),traceback=traceback.format_exc()))
    try:pairs,differences=comparisons(job,frames,refs,p)
    except BaseException as failure:pairs=[dict(gate_applied=True,passed=False,error=repr(failure))]; differences=[]
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('frames',rows),('history',history),('profiles',layers),('pairs',pairs),('differences',differences)]]
    result=dict(passed=not errors and all(r['passed'] for r in pairs if r['gate_applied']),errors=errors,rows=rows,pairs=pairs,reader_exits=readers,artifacts=artifacts,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,physical_acceptance=False,full_run_admitted=False)
    seal(receipt,result); return result,bound(receipt),frames


def run():
    stage.old.prerequisites(); assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs'])
    refs={key:load_reference(ref) for key,ref in prepared['references'].items()}; state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[])
    def publish():
        temp=RUN.with_suffix('.tmp'); seal(temp,state); os.replace(temp,RUN)
    publish()
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name']; publish(); result,record,frames=one_job(job,prepared,refs); state['jobs'].append(record); publish()
            assert result['passed'],('Earlier gate failed; later short job held',job['name'],result['errors'])
            if job['suffix'] in ['cpu','gpu']:refs['new_'+job['suffix']]=frames
        verify(prepared['inputs']); state['status']='grad_short_checks_complete_pending_root_review'
    except BaseException as failure:state.update(status='short_gate_failed_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish(); passed=state['status']=='grad_short_checks_complete_pending_root_review' and len(state['jobs'])==3
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),physical_acceptance=False,full_run_admitted=False,restart_admitted=False)); return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
