"""Four exact all38-field native regressions for frozen candidate Release programs."""
import argparse
import ast
import json
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
import sw_release_build_r1 as build

stage, current, event, short = hg.stage, hg.current, hg.event, hg.short
TESTS, CASE, LOGS, CONFIGS, OUTPUTS = hg.TESTS, hg.CASE, hg.LOGS, hg.CONFIGS, hg.OUTPUTS
read, seal, verify, unique, bound, utc, inventory = [getattr(hg,n) for n in ['read','seal','verify','unique','bound','utc','inventory']]
TAG='sw_release_native_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE=TESTS/'notes'/(TAG+'.json')
MODE3=LOGS/'sw_mode3_short_r1.check.json'
JOBS=[dict(suffix=backend+('_on' if enabled else '_off'),backend=backend,threads=8 if backend=='cpu' else 1,hg=enabled,
           dt='0.000001',shepard=40,on=False,end='0.002',interval='0.0004999',steps=2000,frames=5)
      for backend in ['cpu','gpu'] for enabled in [False,True]]


def expected(job,program):
    source=hg if job['hg'] else hg.spr; xml,bat=source.expected(job,program)
    return xml,bat.replace(source.TAG,TAG)


def exact(a,b,part):
    assert a.shape==b.shape and len(a.columns)==38 and list(a)==list(b)
    aa,bb=a.to_numpy(dtype='<f8'),b.to_numpy(dtype='<f8'); assert np.isfinite(aa).all() and np.isfinite(bb).all()
    bad=aa.view('<u8')!=bb.view('<u8'); fields=[]
    for i,key in enumerate(a.columns):
        count=int(bad[:,i].sum()); indices=np.flatnonzero(bad[:,i])
        fields.append(dict(part=part,field=key,different_values=count,max_abs_difference=float(abs(aa[:,i]-bb[:,i]).max()),
            first_different_row=int(indices[0]) if count else None,new_first_bits=hex(int(aa.view('<u8')[indices[0],i])) if count else None,
            reference_first_bits=hex(int(bb.view('<u8')[indices[0],i])) if count else None))
    row=dict(part=part,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),saved_step=int(a.saved_step.iloc[0]),reference_saved_step=int(b.saved_step.iloc[0]),
        passed=not bool(bad.any()),compared_particles=len(a),compared_fields=38,compared_values=int(aa.size),different_values=int(bad.sum()),
        different_particles=int(bad.any(axis=1).sum()),different_field_count=int(bad.any(axis=0).sum()),different_fields=';'.join(np.array(a.columns)[bad.any(axis=0)]),
        maximum_absolute_difference=float(abs(aa-bb).max()),dterror_included=True,excluded_fields='')
    return row,fields


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    for job in JOBS:
        xml,bat=expected(job,CASE/'private/solver.exe'); tree=ET.fromstring(xml); flag=tree.findall('.//parameter[@key="SoilHourglassXi"]')
        assert (len(flag)==1 and flag[0].get('value')=='0.1') if job['hg'] else not flag
        assert tree.find('.//HydraulicConductivity').get('value')=='0' and tree.find('.//HydroMechInitMode').get('value')=='1'
        assert tree.find('.//PoreShepardRegularization').get('value')=='0' and ('-'+job['backend']+' -ompthreads:'+str(job['threads'])) in bat
        assert TAG in bat and '-nsteps:2000' in bat and stage.plan(job)==[0,500,1000,1500,2000]
    a=pd.DataFrame(np.zeros((2,38)),columns=['time_s','saved_step','id']+['f'+str(i) for i in range(34)]+['dterror_s']); b=a.copy()
    assert exact(a,b,0)[0]['passed']
    b.loc[0,'f0']=-0.; row,fields=exact(a,b,0); assert not row['passed'] and row['different_values']==1 and row['maximum_absolute_difference']==0
    b=a.copy(); b.loc[0,'dterror_s']=1e-30; row,fields=exact(a,b,0); assert not row['passed'] and row['different_fields']=='dterror_s'
    return dict(passed=True,files_written=False,child_processes_started=False,native_reader_started=False)


def prerequisites():
    terminal=read(MODE3); state=read(terminal['run']['path']); assert state['status'] in ['mode3_short_complete_pending_root_review','mode3_short_failed_later_jobs_held']
    assert terminal['jobs']==state['jobs']; records=[bound(MODE3),terminal['run']]+terminal['jobs']
    check=read(build.CHECK); assert check['passed'] and len(check['stages'])==3; verify([check['prepared']]+check['stages']); prepared=read(check['prepared']['path']); candidates={}
    records += [bound(build.CHECK),check['prepared']]+check['stages']
    for record in check['stages']:
        receipt=read(record['path']); assert receipt['exit_code']==0 and receipt['owned_exited'] and receipt['protected_inputs_unchanged'] and len(receipt['runtime'])==4
        assert receipt['exact_HG_sources_captured_before_build'] and receipt['all_captured_inputs_unchanged_before_after'] and not receipt['compiled_from_snapshot']
        assert len(receipt['hg_before_build_capture'])==6 and all(r['captured_utc']<receipt['started_utc'] for r in receipt['hg_before_build_capture'])
        if receipt['configuration'] in ['ReleaseCPU','Release']:
            candidates['cpu' if receipt['configuration']=='ReleaseCPU' else 'gpu']=receipt; records += [receipt['program'],receipt['log'],receipt['binlog']]+[r['target'] for r in receipt['runtime']]
    names={'JSph.h','JSph.cpp','JSphCpu.h','JSphCpu.cpp','JSphGpu.h','JSphGpu.cpp','JSphCpuSingle.h','JSphCpuSingle.cpp','JSphGpuSingle.h','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu',
           'JSphHourglassCpu.h','JSphHourglassCpu.cpp','JSphHourglassGpu.h','JSphHourglassGpu.cpp','JSphHourglassGpu_ker.h','JSphHourglassGpu_ker.cu','DualSPHysics5ReCpu.vcxproj','DualSPHysics5Re.vcxproj','DualSPHysics5ReCpu_vs2022.sln','DualSPHysics5Re.sln'}
    captured=[r for r in prepared['snapshots'] if Path(r['original']['path']).name in names]; assert len(captured)==len(names)
    records += [v for r in captured for v in [r['original'],r['snapshot']]]; verify(records)
    return records,candidates,dict(sources_captured_before_build=True,compiled_from_snapshot=False,scope=prepared['source_scope'],selected_snapshots=captured)


def references():
    records=[]; refs={}
    for job in JOBS:
        source=hg if job['hg'] else hg.spr; check=read(source.CHECK); prior=read(source.PREP); assert check['passed']
        old=next(j for j in prior['jobs'] if j['suffix']==job['backend']); rr=LOGS/(old['name']+'.receipt.json'); result=read(rr); done=read(result['sealed_completion']['path'])
        assert result['passed'] and len(result['rows'])==5 and done['solver_finished'] and done['exit_code']==0 and done['owned_exited']
        names=['Run.out','Part_Head.ibi4','PartInfo.ibi4']+[f'Part_{i:04d}.bi4' for i in range(5)]; outputs=[r for r in done['outputs'] if Path(r['path']).name in names]
        assert sum(Path(r['path']).name.startswith('Part_') and Path(r['path']).suffix=='.bi4' for r in outputs)==5
        refs[job['suffix']]=dict(name=old['name'],folder=str(OUTPUTS/old['name']),dt=old['dt'],steps=old['steps'],rows=result['rows'],receipt=bound(rr),completion=result['sealed_completion'],outputs=outputs,config=old['config'])
        records += [bound(source.CHECK),check['run'],bound(source.PREP),bound(rr),result['sealed_completion'],old['config'],old['bat'],old['program']]+old['runtime']+outputs
    verify(records); return records,refs


def prepare():
    selftest(); assert not inventory(); gates,candidates,capture=prerequisites(); controls,refs=references()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,event.FIGURES])
    helpers=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(CASE.parent)})
    reader=read(event.BUILD); assert reader['built'] and reader['exit_code']==0
    proof=gates+controls+[bound(p) for p in helpers+[NOTE,event.BUILD,TESTS/'support/read_selfweight_native_r1.cpp',hg.baseline.TEMPLATE,hg.baseline.REPO/'bin/windows/GenCase_win64.exe',Path(sys.executable)]]+[reader['program'],reader['log']]
    proof=unique([dict(r,sha256=r['sha256'].lower()) for r in proof]); verify(proof); jobs=[]
    for spec in JOBS:
        job=dict(spec); candidate=candidates[job['backend']]; name=TAG+'_'+job['suffix']; cfg=CONFIGS/(name+'_Def.xml'); bat=CONFIGS/('x'+name+'_win64_'+job['backend'].upper()+'.bat')
        xml,command=expected(job,Path(candidate['program']['path'])); signature=lambda tree:[(e.tag,sorted(e.attrib.items())) for e in tree.iter()]
        assert signature(ET.fromstring(xml))==signature(ET.parse(refs[job['suffix']]['config']['path']))
        with cfg.open('x',encoding='utf8',newline='') as stream:stream.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as stream:stream.write(command)
        job.update(name=name,program=candidate['program'],runtime=[r['target'] for r in candidate['runtime']],config=bound(cfg),bat=bound(bat)); jobs.append(job); proof += [bound(cfg),bound(bat)]
    verify(proof); seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,references=refs,new_build_source_capture=capture,old_source_program_attribution=read(hg.PREP)['source_program_attribution'],
        compared_old_states=20,all38_including_dterror=True,physical_acceptance=False,new_half_validation=False,restart_admitted=False,formal_admitted=False))


def one_job(job,prepared,reference):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); completion=LOGS/(job['name']+'.completion.json'); receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,completion,receipt]); verify(prepared['inputs']); started=time.perf_counter(); child=None
    errors=[]; rows=[]; focus=[]; layers=[]; frames={}; pairs=[]; fields=[]; readers=[]; statistics={}; clock=stage.clock_table(job['dt'],job['steps'])
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=180)
    except BaseException as failure:
        errors.append(dict(stage='execute',error=repr(failure),traceback=traceback.format_exc()))
        if child is not None and child.poll() is None:subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''; survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,owned_exited=not survivors,
        surviving_owned=survivors,program=job['program'],runtime=job['runtime'],config=job['config'],bat=job['bat'],outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+([bound(log)] if log.exists() else [])); seal(completion,done)
    parts=sorted(int(p.stem.split('_')[-1]) for p in (folder/'data').glob('Part_*.bi4'))
    for part in parts:
        try:
            a=current.native(folder,part); readers.append(dict(part=part,exit_code=0)); frames[part]=a; focus += [dict(r,part=part) for r in event.focus(a).to_dict('records')]
            rows.append(stage.measure(a,frames[0],part,job,clock)); layers+=stage.profiles(a,frames[0],part)
        except BaseException as failure:
            errors.append(dict(stage='native_or_measure',part=part,error=repr(failure),traceback=traceback.format_exc()))
            if not any(r['part']==part for r in readers):readers.append(dict(part=part,exit_code=getattr(failure,'returncode',None),error=repr(failure)))
    for part in range(5):
        try:row,detail=exact(frames[part],reference[part],part); pairs.append(row); fields+=detail
        except BaseException as failure:pairs.append(dict(part=part,passed=False,error=repr(failure)))
    try:
        assert done['solver_finished'] and done['owned_exited'] and parts==list(range(5)) and len(rows)==5 and len(layers)==500
        assert [r['natural_step'] for r in rows]==stage.plan(job) and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        if job['hg']:statistics=hg.parse_hg(text,job); assert statistics['passed']
        else:assert 'SoilHourglassXi:' not in text and 'SoilHourglass: forcecalls=' not in text
        assert all(value in text for value in ['SoilBoundaryDerivativeSPR="MirroredWallDerivatives"','SPR stationary wall planes (one per mk): 1','No Penetration=False',
            'SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"','PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"','HydroMechInitMode="FreeSurface"','SoilDampingCoef=0.02'])
        verify(prepared['inputs'])
    except BaseException as failure:errors.append(dict(stage='completion_or_flags',error=repr(failure),traceback=traceback.format_exc()))
    artifacts=[event.write_csv(job['name']+'_'+kind,value) for kind,value in [('frames',rows),('nativefocus',focus),('profiles',layers),('exact_pairs',pairs),('exact_fields',fields)]]
    result=dict(passed=not errors and len(pairs)==5 and all(r['passed'] for r in pairs),errors=errors,rows=rows,pairs=pairs,hg=statistics,reader_exits=readers,artifacts=artifacts,
        sealed_completion=bound(completion),owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,all38_including_dterror=True,excluded_fields=[],physical_acceptance=False,new_half_validation=False)
    seal(receipt,result); return result,bound(receipt)


def run():
    assert not RUN.exists() and not CHECK.exists() and not inventory(); prerequisites(); prepared=read(PREP); verify(prepared['inputs'])
    refs={key:short.load_reference(ref) for key,ref in prepared['references'].items()}; state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[])
    def publish():
        temporary=RUN.with_suffix('.tmp'); seal(temporary,state); os.replace(temporary,RUN)
    publish()
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name']; publish(); result,record=one_job(job,prepared,refs[job['suffix']]); state['jobs'].append(record); publish()
            assert result['passed'],('Exact native regression failed; later jobs held',job['name'],result['errors'])
        verify(prepared['inputs']); state['status']='four_exact_native_regressions_passed_pending_root_review'
    except BaseException as failure:state.update(status='native_regression_failed_later_jobs_held',error=repr(failure),traceback=traceback.format_exc())
    state.update(finished_utc=utc(),held_jobs=[j['name'] for j in prepared['jobs'][len(state['jobs']):]]); publish(); passed=state['status']=='four_exact_native_regressions_passed_pending_root_review' and len(state['jobs'])==4
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],held_jobs=state['held_jobs'],error=state.get('error'),new_build_source_capture=prepared['new_build_source_capture'],
        all38_including_dterror=True,excluded_fields=[],old_source_program_attribution_unchanged=True,physical_acceptance=False,new_half_validation=False,restart_admitted=False,formal_admitted=False)); return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
