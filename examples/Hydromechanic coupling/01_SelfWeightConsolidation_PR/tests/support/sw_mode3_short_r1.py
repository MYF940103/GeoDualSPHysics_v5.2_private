"""Fresh analytical-selfweight gravity-on dissipation startup; three short gates only."""
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
import sw_hg_short_r1 as hg

stage, current, event, short, baseline = hg.stage, hg.current, hg.event, hg.short, hg.baseline
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = hg.TESTS, hg.CASE, hg.LOGS, hg.CONFIGS, hg.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(hg,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG='sw_mode3_short_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
HG_CHECK=LOGS/'sw_hg_stage1_r1.check.json'
JOBS=[dict(suffix=s,backend=b,threads=1,dt=dt,shepard=80 if s=='half' else 40,on=False,end='0.002',interval='0.00049999',steps=n,frames=5)
      for s,b,dt,n in [('cpu','cpu','0.0000004',5000),('gpu','gpu','0.0000004',5000),('half','gpu','0.0000002',10000)]]


def expected(job,program):
    xml,bat=hg.expected(job,program)
    for key,value,comment in [('HydraulicConductivity','0.001','Existing analytical-start dissipation diagnostic; constant k from t=0'),
                              ('HydroMechInitMode','3','Existing AnalyticalSelfWeight1D gravity-on initial state; not paper zero-p loading')]:
        xml,n=re.subn(r'(<'+key+r' value=")[^"]+(" comment=")[^"]+("[^\n]+)',lambda m:m[1]+value+m[2]+comment+m[3],xml); assert n==1
    return xml,bat.replace(hg.TAG,TAG)


def parameters(xml):
    root=ET.fromstring(xml); f=np.float32; value=lambda tag:float(root.find('.//'+tag).get('value'))
    e,nu=f(value('ModulusE')),f(value('PRvs')); k=f(e/(f(3)*(f(1)-f(2)*nu))); shear=f(e/(f(2)*(f(1)+nu)))
    gravity=[float(f(root.find('.//gravity').get(axis))) for axis in ['x','y','z']]; g=math.sqrt(sum(v*v for v in gravity))
    return dict(K=float(k),G=float(shear),M=float(k)+4.*float(shear)/3.,Mf=float(f(value('PoreWaterBulkModulus')))/float(f(value('Porosity'))),nu=float(nu),
        rho=float(f(value('rhop0'))),rho_w=float(f(value('PoreWaterRho'))),g=g,gravity=gravity,k=float(f(value('HydraulicConductivity'))),safety=float(f(value('PoreDtSafety'))),
        H=float(root.find('.//newvarcte[@sizefz]').get('sizefz')),dp=float(root.find('.//newvarcte[@Dp]').get('Dp')))


def analytical(p,z,drained):
    depth=np.maximum(0.,p['H']-np.asarray(z)); ratio=p['Mf']/(p['M']+p['Mf']); effective=p['M']/(p['M']+p['Mf'])
    hydro=p['rho_w']*p['g']*depth; excess=ratio*max(0.,p['rho']-p['rho_w'])*p['g']*depth
    zz=np.asarray(-effective*max(0.,p['rho']-p['rho_w'])*p['g']*depth,dtype='<f4'); f=np.float32; k0=f(f(p['nu'])/(f(1)-f(p['nu'])))
    pressure=np.asarray(hydro+excess,dtype='<f4'); p0=np.asarray(hydro,dtype='<f4'); pressure[drained]=0; p0[drained]=0
    return dict(pressure=pressure.astype('<f8'),porepress0=p0.astype('<f8'),sigma_zz=zz.astype('<f8'),sigma_xx=(k0*zz).astype('<f8'),sigma_yy=(k0*zz).astype('<f8'),
                sigma_xy=np.zeros_like(depth),sigma_yz=np.zeros_like(depth),sigma_xz=np.zeros_like(depth))


def initial_reference(a,p):
    soil=a.iloc[40:]; drained=((soil.id.to_numpy().astype(int)-40)%100)==99; reference=analytical(p,soil.z.to_numpy(),drained); diagnostics=[]; failed=[]
    for key,want in reference.items():
        actual=soil[key].to_numpy(dtype='<f8'); bad=actual.view('<u8')!=want.view('<u8')
        if bad.any():failed.append(key)
        diagnostics.append(dict(field=key,different_bits=int(bad.sum()),max_abs_difference=float(abs(actual-want).max())))
    rows=[dict(id=int(row.id),z_m=float(row.z),drained_top=bool(drained[i]),**{key:float(row[key]) for key in reference},
        **{'reference_'+key:float(v[i]) for key,v in reference.items()}) for i,(_,row) in enumerate(soil.iterrows())]
    source_height=float(soil.z.max()+float(a.dp.iloc[0])*.5); rho_ok=bool(np.all(soil.rho==p['rho'])); top=soil.loc[drained,'sigma_zz']
    return dict(passed=not failed and rho_ok and abs(source_height-p['H'])<=1e-12,bulk_soil_only=True,wall_formula_applied=False,source_height_m=source_height,H1_m=p['H'],
        initial_soil_rho_matches_rhop0=rho_ok,fields=diagnostics,failed_fields=failed,drained_top_sigma_zz_min_pa=float(top.min()),drained_top_sigma_zz_max_pa=float(top.max()),
        drained_top_nonzero_sigma_zz_count=int((top!=0).sum()),stress_storage='float32 assignment then binary64 state; drained-top stress retained'),rows


def pore_limit(a,p,dt):
    h=float(a.h.iloc[0]); assert h>0 and np.all(a.h==h)
    limit=p['safety']*(p['rho_w']*p['g']/p['Mf'])*h*h/p['k']
    return dict(pore_limit_s=limit,native_h_m=h,dt_over_pore_limit=float(dt)/limit,pore_limit_passed=bool(float(dt)<=limit))


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); root=ET.fromstring(xml); original=ET.fromstring(hg.expected(job,CASE/'private/solver.exe')[0])
        signature=lambda tree:[(e.tag,sorted(e.attrib.items())) for e in tree.iter() if e.tag not in ['HydraulicConductivity','HydroMechInitMode']]
        assert signature(root)==signature(original) and root.find('.//HydraulicConductivity').get('value')=='0.001' and root.find('.//HydroMechInitMode').get('value')=='3'
        assert TAG in bat and hg.TAG not in bat and ('-'+job['backend']+' -ompthreads:1') in bat and ('-nsteps:'+str(job['steps'])) in bat
        assert stage.plan(job)==([0,2500,5000,7500,10000] if job['suffix']=='half' else [0,1250,2500,3750,5000])
        p=parameters(xml); limit=pore_limit(pd.DataFrame(dict(h=[float(np.float32(.018))])),p,job['dt']); assert limit['pore_limit_passed'] and .476e-6<limit['pore_limit_s']<.477e-6
        assert not pore_limit(pd.DataFrame(dict(h=[float(np.float32(.018))])),p,'0.0000005')['pore_limit_passed']
        result=analytical(p,np.array([.005,.995]),np.array([False,True])); assert result['pressure'][0]>result['porepress0'][0]>0 and result['pressure'][1]==result['porepress0'][1]==0 and result['sigma_zz'][1]!=0
    return dict(passed=True,files_written=False,programs_started=False,native_reader_started=False)


def prerequisite():
    check=read(HG_CHECK); assert check['passed'] and len(check['jobs'])==1; verify([check['run']]+check['jobs'])
    receipt=read(check['jobs'][0]['path']); done=read(receipt['sealed_completion']['path'])
    assert receipt['passed'] and receipt['hg']['passed'] and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']; verify([receipt['sealed_completion']])
    return [bound(HG_CHECK),check['run'],check['jobs'][0],receipt['sealed_completion']]


def prepare():
    gates=prerequisite(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(hg.PREP); attribution=prior['source_program_attribution']; assert not attribution['exact_HG_source_at_build_time_proven']
    helpers=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(CASE.parent)})
    sources=[baseline.REPO/'src/source'/name for name in ['JSph.h','JSph.cpp','JSphCpu.cpp','JSphGpu.cpp','JSphGpu_ker.h','JSphGpu_ker.cu','JSphCpuSingle.cpp','JSphGpuSingle.cpp','JDsFixedDt.cpp','JDsFixedDt.h']]
    reader=read(event.BUILD); assert reader['built'] and reader['exit_code']==0
    proof=gates+[bound(p) for p in helpers+sources+[NOTE,hg.PREP,baseline.TEMPLATE,event.BUILD,baseline.REPO/'bin/windows/GenCase_win64.exe',baseline.REPO/'doc/xml_format/_FmtXML_ElastoplasticSoil.xml',Path(sys.executable)]]
    proof += attribution['current_HG_sources']+attribution['build_receipts']+attribution['build_logs']+[attribution['prior_six_source_hash_record'],attribution['unchanged_gpu_header_archive'],reader['program'],reader['log']]+reader['inputs']
    for record in attribution['build_receipts']:
        built=read(record['path']); assert built['exit_code']==0 and built['owned_exited'] and built['protected_inputs_unchanged']; proof += [built['program']]+[r['target'] for r in built['runtime']]
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); accepted=next(j for j in prior['jobs'] if j['backend']==job['backend']); name=TAG+'_'+job['suffix']
        verify([accepted['program']]+accepted['runtime']); cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_'+job['backend'].upper()+'.bat'); xml,command=expected(job,Path(accepted['program']['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=accepted['program'],runtime=accepted['runtime'],config=bound(cfg),bat=bound(bat),parameters=parameters(xml)); jobs.append(job); proof += [bound(cfg),bound(bat),job['program']]+job['runtime']
    proof=unique(proof); verify(proof); seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,source_program_attribution=attribution,prior_raw_outputs_used=False,
        scope='existing binary analytical-initial-state dissipation short diagnostic,not zero-p gravity-loading reproduction',physical_acceptance=False,restart_admitted=False,automatic_full_run_admitted=False))


def comparisons(job,frames,refs,p):
    pairs=[]; differences=[]; kind='cpu_gpu' if job['suffix']=='gpu' else 'gpu_half'; reference=refs.get('cpu' if job['suffix']=='gpu' else 'gpu')
    if job['suffix']=='cpu':return pairs,differences
    for part in range(5):
        try:
            row,delta=short.pair(job['name']+'_'+kind,kind,part,frames[part],part,reference[part],frames[0],reference[0],p); pairs.append(row); differences+=delta
        except BaseException as failure:pairs.append(dict(comparison=kind,part=part,gate_applied=True,passed=False,error=repr(failure)))
    return pairs,differences


def one_job(job,prepared,refs):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); completion=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(q.exists() for q in [folder,log,completion,receipt]); verify(prepared['inputs']); started=time.perf_counter(); child=None
    p=job['parameters']; clock=stage.clock_table(job['dt'],job['steps']); errors=[]; frames={}; rows=[]; focus=[]; layers=[]; readers=[]; reference={}; initial_csv=[]; statistics={}
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=300)
    except BaseException as failure:
        errors.append(dict(stage='execute',error=repr(failure),traceback=traceback.format_exc()))
        if child is not None and child.poll() is None:subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,owned_exited=not survivors,
        surviving_owned=survivors,program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])); seal(completion,done)
    parts=sorted(int(q.stem.split('_')[-1]) for q in (folder/'data').glob('Part_*.bi4'))
    for part in parts:
        try:
            a=current.native(folder,part); readers.append(dict(part=part,exit_code=0)); frames[part]=a; focus += [dict(r,part=part) for r in event.focus(a).to_dict('records')]
            row=dict(stage.measure(a,frames[0],part,job,clock),**short.r_summary(a,p),**pore_limit(a,p,job['dt'])); rows.append(row); assert row['pore_limit_passed']
            if part==0:reference,initial_csv=initial_reference(a,p)
            for layer in stage.profiles(a,frames[0],part):layer.update(r_native_pa=layer['excess_native_pa']+p['Mf']*(layer['sigma_xx']+layer['sigma_yy']+layer['sigma_zz'])/(3*p['K']),included_in_r_summary=layer['layer']!=99); layers.append(layer)
        except BaseException as failure:
            errors.append(dict(stage='native_measure_or_initial_formula',part=part,error=repr(failure),traceback=traceback.format_exc()))
            if not any(r['part']==part for r in readers):readers.append(dict(part=part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
    try:
        statistics=hg.parse_hg(text,job); assert statistics['passed'] and reference['passed']
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==5 and parts==list(range(5)) and len(layers)==500 and len(initial_csv)==1000
        assert [r['natural_step'] for r in rows]==stage.plan(job) and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert all(value in text for value in ['HydroMechInitMode="AnalyticalSelfWeight1D"','mode=gravity-on self-weight','hydrostatic baseline=retained',
            'SoilBoundaryDerivativeSPR="MirroredWallDerivatives"','SPR stationary wall planes (one per mk): 1','No Penetration=False','SoilStressRateGradCorr="KernelGradient"',
            'PoreCompressionGradCorr="KernelGradient"','PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"','SoilDampingCoef=0.02','PoreDarcySymmetricCorr="Receiver"'])
        assert float(re.search(r'HydraulicConductivity:\s*(\S+)',text)[1])==.001 and int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']; verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion_hg_or_reference',error=repr(failure),traceback=traceback.format_exc()))
    pairs,differences=comparisons(job,frames,refs,p); data=[('frames',rows),('nativefocus',focus),('profiles',layers),('initial_soil_reference',initial_csv)]
    if pairs:data += [('pairs',pairs),('differences',differences)]
    artifacts=[event.write_csv(job['name']+'_'+kind,value) for kind,value in data]
    result=dict(passed=not errors and all(r['passed'] for r in pairs),errors=errors,rows=rows,pairs=pairs,hg=statistics,initial_reference=reference,reader_exits=readers,artifacts=artifacts,
        sealed_completion=bound(completion),owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,physical_acceptance=False,restart_admitted=False)
    seal(receipt,result); return result,bound(receipt),frames


def run():
    prerequisite(); assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs']); refs={}
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[])
    def publish():
        temporary=RUN.with_suffix('.tmp'); seal(temporary,state); os.replace(temporary,RUN)
    publish()
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name']; publish(); result,record,frames=one_job(job,prepared,refs); state['jobs'].append(record); publish()
            assert result['passed'],('Earlier gate failed; later jobs held',job['name'],result['errors']); refs[job['suffix']]=frames
        verify(prepared['inputs']); state['status']='mode3_short_complete_pending_root_review'
    except BaseException as failure:state.update(status='mode3_short_failed_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish(); passed=state['status']=='mode3_short_complete_pending_root_review' and len(state['jobs'])==3
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),source_program_attribution=prepared['source_program_attribution'],
        physical_acceptance=False,restart_admitted=False,automatic_full_run_admitted=False)); return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
