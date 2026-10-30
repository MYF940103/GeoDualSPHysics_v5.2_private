"""Three fresh HG=.1/SPR1/G1/ShepardOFF short checks; no long run or queue."""
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
import sw_spr_short_r1 as spr

stage, current, event, short, baseline = spr.stage, spr.current, spr.event, spr.short, spr.baseline
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = spr.TESTS, spr.CASE, spr.LOGS, spr.CONFIGS, spr.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(spr,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
clock_table, measure, profiles = stage.clock_table, stage.measure, stage.profiles
TAG='sw_hg_short_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
JOBS=[dict(job) for job in spr.JOBS]


def expected(job,program):
    xml,bat=spr.expected(job,program); key='SoilHourglassXi'
    assert not ET.fromstring(xml).findall('.//parameter[@key="'+key+'"]')
    xml,n=re.subn(r'(?m)^([ ]*)(<parameter key="SoilBoundaryDerivativeSPR"[^\n]*\n)',
        lambda m:m[0]+m[1]+'<parameter key="'+key+'" value="0.1" comment="Existing small-rotation elastic GNOG; fresh short diagnostic only" />\n',xml); assert n==1
    return xml,bat.replace(spr.TAG,TAG)


def parse_hg(text,job):
    def match(pattern):
        found=re.findall(pattern,text); assert len(found)==1,('Missing/duplicate HG runtime record',pattern); return found[0]
    xi,backend=match(r'SoilHourglassXi:\s*(\S+) \((CPU|GPU) elastic GNOG, endpoint-trapezoidal history\)')
    counts=map(int,match(r'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)'))
    record=dict(zip(['forcecalls','predictorupdates','correctorupdates','ratecalls'],counts),xi=float(xi),backend=backend)
    record.update(zip(['ratecalculations','endpoint_rate_reuses'],map(int,match(r'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)'))))
    record.update(zip(['max_net_history_force','max_net_actual_added_force','max_dt_tau','spinbound'],map(float,match(r'SoilHourglass: max\|sum\(m\*H\)\|=(\S+) max\|sum\(m\*deltaAce\)\|=(\S+) max\(dt/tau\)=(\S+) spinbound=(\S+)'))))
    n=job['steps']; record['passed']=bool(record['xi']==.1 and backend==job['backend'].upper() and record['forcecalls']==record['ratecalls']==2*n
        and record['predictorupdates']==record['correctorupdates']==n and record['ratecalculations']+record['endpoint_rate_reuses']==2*n
        and 0<=record['endpoint_rate_reuses']<=2*n and all(np.isfinite(record[k]) and record[k]>=0 for k in ['max_net_history_force','max_net_actual_added_force','max_dt_tau','spinbound'])
        and record['max_dt_tau']<=.2 and record['spinbound']<.01)
    return record


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); tree=ET.fromstring(xml); base=ET.fromstring(spr.expected(job,CASE/'private/solver.exe')[0])
        signature=lambda root:[(e.tag,sorted(e.attrib.items())) for e in root.iter() if e.get('key')!='SoilHourglassXi']
        found=tree.findall('.//parameter[@key="SoilHourglassXi"]'); assert len(found)==1 and found[0].get('value')=='0.1' and signature(tree)==signature(base)
        assert TAG in bat and spr.TAG not in bat and '-partbegin' not in bat.lower() and ('-'+job['backend']+' -ompthreads:'+str(job['threads'])) in bat
        assert stage.plan(job)==([0,1000,2000,3000,4000] if job['suffix']=='half' else [0,500,1000,1500,2000])
        assert 2*float(tree.find('.//hdp').get('value'))*float(tree.find('.//newvarcte[@Dp]').get('Dp'))<.5*float(tree.find('.//newvarcte[@sizefx]').get('sizefx'))
    job=dict(steps=20,backend='gpu'); synthetic=('SoilHourglassXi: 0.1 (GPU elastic GNOG, endpoint-trapezoidal history)\n'
        'SoilHourglass: forcecalls=40 predictorupdates=20 correctorupdates=20 ratecalls=40\n'
        'SoilHourglass: ratecalculations=33 endpoint_rate_reuses=7\nSoilHourglass: max|sum(m*H)|=1e-15 max|sum(m*deltaAce)|=2e-9 max(dt/tau)=0.2 spinbound=0.009\n')
    assert parse_hg(synthetic,job)['passed']
    for old,new in [('forcecalls=40','forcecalls=39'),('predictorupdates=20','predictorupdates=19'),('correctorupdates=20','correctorupdates=19'),('ratecalls=40','ratecalls=39'),
        ('ratecalculations=33','ratecalculations=32'),('endpoint_rate_reuses=7','endpoint_rate_reuses=41'),('max(dt/tau)=0.2','max(dt/tau)=0.200001'),('spinbound=0.009','spinbound=0.01'),
        ('max|sum(m*H)|=1e-15','max|sum(m*H)|=nan'),('Xi: 0.1','Xi: 0.2'),('(GPU elastic','(CPU elastic')]:assert not parse_hg(synthetic.replace(old,new),job)['passed']
    for calcs,hits in [(40,0),(0,40)]:assert parse_hg(synthetic.replace('ratecalculations=33 endpoint_rate_reuses=7',f'ratecalculations={calcs} endpoint_rate_reuses={hits}'),job)['passed']
    return dict(passed=True,programs_started=False,files_written=False)


def prerequisites():
    check=read(spr.CHECK); assert check['passed'] and len(check['jobs'])==3 and not check['held_jobs']
    proof=[bound(spr.CHECK),check['run']]+check['jobs']; refs={}
    for job in read(spr.PREP)['jobs']:
        receipt=LOGS/(job['name']+'.receipt.json'); result=read(receipt); done=read(result['sealed_completion']['path'])
        assert result['passed'] and len(result['rows'])==5 and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
        assert all(r['comparison_valid'] and (not r['gate_applied'] or r['passed']) for r in result['pairs'])
        refs[job['suffix']]=dict(name=job['name'],folder=str(OUTPUTS/job['name']),dt=job['dt'],steps=job['steps'],rows=result['rows'],receipt=bound(receipt),completion=result['sealed_completion'],outputs=done['outputs'])
        proof += [bound(receipt),result['sealed_completion'],job['config'],job['bat'],job['program']]+job['runtime']+done['outputs']+result['artifacts']
    verify(proof); return proof,refs


def prepare():
    gates,refs=prerequisites(); selftest(); assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    prior=read(spr.PREP); sources=[bound(baseline.REPO/'src/source'/name) for name in
        ['JSphHourglassCpu.h','JSphHourglassCpu.cpp','JSphHourglassGpu.h','JSphHourglassGpu.cpp','JSphHourglassGpu_ker.h','JSphHourglassGpu_ker.cu']]
    historical=CASE.parent/'05_LianFlexibleStrip2D_PR/tests/logs/lian_hg_np_Release_bounded_r1.build.json'
    header=baseline.C02/'outputs/gpu_spr_15_verified_r2/source/JSphHourglassGpu.h'; hashes={Path(r['path']).name:r['sha256'] for r in sources}
    previous=[r for r in read(historical)['inputs'] if Path(r['path']).name in hashes]; assert len(previous)==6 and all(r['sha256'].lower()==hashes[Path(r['path']).name] for r in previous)
    assert bound(header)['sha256']==hashes['JSphHourglassGpu.h']
    build=read(current.BUILD); builds=[build['adopted_cpu_release'],build['fresh_stages'][-1]]; buildlogs=[]
    for record in builds:
        receipt=read(record['path']); assert receipt['program'] in [j['program'] for j in prior['jobs']]; buildlogs.append(receipt['log'])
        text=Path(receipt['log']['path']).read_text(errors='replace'); assert 'JSphHourglassCpu.cpp' in text
        if receipt['program']==prior['jobs'][1]['program']:assert 'JSphHourglassGpu.cpp' in text and 'JSphHourglassGpu_ker.cu' in text
    attribution=dict(scope='existing_frozen_binary_numerical_option_diagnostic_only',exact_HG_source_at_build_time_proven=False,
        gap='Original same-program build receipts do not seal all six HG source hashes at compile time; current hashes are not that missing archive.',current_HG_sources=sources,build_receipts=builds,build_logs=buildlogs,
        prior_six_source_hash_record=bound(historical),unchanged_gpu_header_archive=bound(header),root_reported_git_review='e28650c3c26b53ee20c91bbfa7305909c47f32ac to f9cb4349fd87a8a56ef5203f703cf0a5744e2704: six HG paths have no commit changes, diff=0 and clean worktree; not compile-time capture',
        later_delivery_requires_new_frozen_build_and_off_on_native_regression=True)
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in prior['inputs']+gates+sources+builds+buildlogs+[bound(p) for p in [__file__,NOTE,spr.__file__,spr.PREP,historical,header]]]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); accepted=next(j for j in prior['jobs'] if j['suffix']==job['suffix']); name=TAG+'_'+job['suffix']
        cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_'+job['backend'].upper()+'.bat'); xml,command=expected(job,Path(accepted['program']['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=accepted['program'],runtime=accepted['runtime'],config=bound(cfg),bat=bound(bat)); jobs.append(job); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,references=refs,parameters=prior['parameters'],source_program_attribution=attribution,physical_acceptance=False,full_run_admitted=False,restart_admitted=False))


def comparisons(job,frames,refs,p):
    rows=[]; differences=[]; suffix=job['suffix']; tasks=[('hg_option_descriptive',refs[suffix])]
    if suffix=='gpu':tasks += [('cpu_gpu',refs['new_cpu'])]
    if suffix=='half':tasks += [('gpu_half',refs['new_gpu'])]
    for kind,ref in tasks:
        for part in range(5):
            try:
                a,b=frames[part],ref[part]; row,delta=short.pair(job['name']+'_minus_'+kind,kind,part,a,part,b,frames[0],ref[0],p)
                row.update(comparison_valid=True,initial38_bitexact=None,variant='HGxi0p1_SPR1_G1_ShepardOFF',reference_variant='HGxi0_SPR1_G1_ShepardOFF' if kind=='hg_option_descriptive' else 'HGxi0p1_SPR1_G1_ShepardOFF'); rows.append(row); differences+=delta
                if kind=='hg_option_descriptive':
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
    child=None; started=time.perf_counter(); errors=[]; frames={}; rows=[]; history=[]; layers=[]; readers=[]; hg={}; p=prepared['parameters']; clock=clock_table(job['dt'],job['steps'])
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=180)
    except BaseException as failure:
        errors.append(dict(stage='execute',error=repr(failure),traceback=traceback.format_exc()))
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()]+([bound(log)] if log.exists() else [])); seal(complete,done)
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
        hg=parse_hg(text,job); assert hg['passed'],hg
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==5 and parts==list(range(5)) and len(layers)==500
        assert [r['natural_step'] for r in rows]==stage.plan(job) and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert all(value in text for value in ['SoilBoundaryDerivativeSPR="MirroredWallDerivatives"','SPR stationary wall planes (one per mk): 1','No Penetration=False',
            'SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"','PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"',
            'HydroMechInitMode="FreeSurface"','PoreDarcySymmetricCorr="Receiver"','SoilDampingCoef=0.02'])
        assert int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']; verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion_or_hg',error=repr(failure),traceback=traceback.format_exc()))
    pairs,differences=comparisons(job,frames,refs,p)
    artifacts=[event.write_csv(job['name']+'_'+kind,data) for kind,data in [('frames',rows),('history',history),('profiles',layers),('pairs',pairs),('differences',differences),('hg',[hg])]]
    result=dict(passed=not errors and all(r['comparison_valid'] and (not r['gate_applied'] or r['passed']) for r in pairs),errors=errors,rows=rows,pairs=pairs,hg=hg,reader_exits=readers,
        artifacts=artifacts,sealed_completion=bound(complete),owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,physical_acceptance=False,full_run_admitted=False,restart_admitted=False)
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
        verify(prepared['inputs']); state['status']='hg_short_checks_complete_pending_root_review'
    except BaseException as failure:state.update(status='short_gate_failed_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish(); passed=state['status']=='hg_short_checks_complete_pending_root_review' and len(state['jobs'])==3
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),physical_acceptance=False,full_run_admitted=False,restart_admitted=False)); return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
