"""Two fresh same-variant GPU regressions for the pore-MLS launch fix; default help."""
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
import numpy as np
import pandas as pd
import symc_1d_short_r1 as old

TESTS, CASE = old.TESTS, old.CASE
LOGS, CONFIGS, OUTPUTS, FIGURES = old.LOGS, old.CONFIGS, old.OUTPUTS, old.FIGURES
C01 = CASE.parent/'01_SelfWeightConsolidation_PR/tests'
TAG = 'sw_pore_cell_1d_r1'
PREP, RUN, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE, BUILD = TESTS/'notes'/(TAG+'.json'), C01/'logs/sw_pore_cell_build_r1.check.json'
NATIVE_GATE, READER_BUILD = C01/'logs/sw_pore_cell_native_r1.check.json', C01/'logs/sw_native_r1.build.json'
read, seal, verify, bound, utc, inventory = old.read, old.seal, old.verify, old.bound, old.utc, old.inventory


def unique(records):
    result={}
    for r in records:
        item=dict(path=str(Path(r['path']).resolve()),bytes=int(r['bytes']),sha256=r['sha256'].lower());key=item['path'].casefold()
        assert key not in result or (result[key]['bytes'],result[key]['sha256'])==(item['bytes'],item['sha256']),('Conflicting binding',r['path'])
        result.setdefault(key,item)
    return list(result.values())


def expected(variant,program,control):
    name=TAG+'_gpu_'+variant;xml=Path(control['config']['path']).read_bytes().decode('utf8')
    bat=Path(control['bat']['path']).read_text(encoding='ascii').replace(control['name'],name)
    relative=os.path.relpath(program,CASE).replace('\\','/')
    bat,n=re.subn(r'(?m)^set dualsphysics=.*$',lambda m:'set dualsphysics="'+relative+'"',bat);assert n==1
    assert ('PoreDarcySymmetricCorr' in xml)==(variant=='on') and '-nsteps:15000' in bat
    return xml,bat


def exact(a,b):
    assert len(a)==len(b)==1040 and len(a.columns)==38 and list(a)==list(b)
    assert np.array_equal(a.id,np.arange(1040)) and np.array_equal(a.id,b.id)
    bad=a.to_numpy(dtype='<f8').view('<u8')!=b.to_numpy(dtype='<f8').view('<u8')
    return dict(all38_bits_exact=not bool(bad.any()),different_fields=';'.join(a.columns[bad.any(axis=0)]),
        differing_native_rows=int(bad.any(axis=1).sum()),first_different_id=int(a.id.iloc[np.flatnonzero(bad.any(axis=1))[0]]) if bad.any() else None)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    a=pd.DataFrame(np.zeros((1040,38)),columns=['id']+['v'+str(i) for i in range(37)]);a['id']=np.arange(1040)
    assert exact(a,a.copy())['all38_bits_exact']
    for col in a.columns[1:]:
        b=a.copy();b.loc[0,col]=-0.;assert not exact(a,b)['all38_bits_exact']
    print('SELFTEST PASSED; no prepare/program/Git/queue')


def prepare():
    selftest();assert not inventory()
    assert not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,FIGURES])
    build=read(BUILD);assert build['passed'] and len(build['fresh_stages'])==3
    prepared=read(build['prepared']['path']);stagepath=next(r for r in build['fresh_stages'] if read(r['path'])['configuration']=='Release')
    stage=read(stagepath['path']);assert stage['exit_code']==0 and stage['owned_exited'] and stage['protected_inputs_unchanged'] and len(stage['runtime'])==4
    gate=read(NATIVE_GATE);assert gate['passed'] and len(gate['jobs'])==5
    reader=read(READER_BUILD);assert reader['built'] and reader['exit_code']==0
    proof=prepared['inputs']+reader['inputs']+[bound(BUILD),build['prepared'],stagepath,stage['program'],stage['log']]+stage['artifacts']
    proof += [r[k] for r in stage['runtime'] for k in ['source','target']]
    proof += [bound(NATIVE_GATE),gate['run']]+gate['jobs']+[bound(READER_BUILD),reader['program'],reader['log']]
    for record in gate['jobs']:
        result=read(record['path']);done=read(result['sealed_completion']['path'])
        assert result['passed'] and done['solver_finished'] and done['owned_exited'] and done['exit_code']==0
        proof += [result['sealed_completion']]+done['outputs']
    proof += [bound(p) for p in [__file__,NOTE,old.__file__,CASE/'support/release_case.py',CASE/'support/compare_precision_q0.py',
        old.CRYER/'support/cryer_start_r1.py',C01/'support/read_selfweight_native_r1.cpp',old.GENCASE]]
    priorpath=LOGS/(old.TAG+'.inputs.json');prior=read(priorpath);proof.append(bound(priorpath));jobs=[]
    for variant in ['off','on']:
        control=next(j for j in prior['jobs'] if j['backend']=='gpu' and j['variant']==variant)
        receipt=LOGS/(control['name']+'.receipt.json');result=read(receipt);done=read(result['sealed_completion']['path'])
        assert result['passed'] and len(result['rows'])==151 and done['solver_finished'] and done['owned_exited'] and done['exit_code']==0
        assert done['program']==control['program'] and len(control['runtime'])==4
        raw=[r for r in done['outputs'] if Path(r['path']).suffix.lower() in ['.bi4','.ibi4'] or Path(r['path']).name in ['Run.out',control['name']+'.xml']]
        assert sum(Path(r['path']).name.startswith('Part_') and Path(r['path']).suffix=='.bi4' for r in raw)==151
        proof += [bound(receipt),result['sealed_completion'],control['config'],control['bat'],control['program'],control['build']]+control['runtime']+raw
        name=TAG+'_gpu_'+variant;cfg=CONFIGS/(name+'_Def.xml');bat=CONFIGS/('x'+name+'_win64_GPU.bat')
        xml,command=expected(variant,Path(stage['program']['path']),control)
        with cfg.open('x',encoding='utf8',newline='') as f:f.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as f:f.write(command)
        assert bound(cfg)['sha256'].lower()==control['config']['sha256'].lower(),'Retained physical XML must be byte-identical'
        jobs.append(dict(name=name,variant=variant,program=stage['program'],runtime=[r['target'] for r in stage['runtime']],
            config=bound(cfg),bat=bound(bat),reference_folder=str(OUTPUTS/control['name']),reference_receipt=bound(receipt),reference_completion=result['sealed_completion']))
        proof += [bound(cfg),bound(bat)]
    proof=unique(proof);verify(proof)
    seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,reader=reader['program'],frames=151,steps=15000,
        old_current_gpu_source_path_reverified=False,physical_acceptance=False,half_step_test=False,automatic_long_run_admitted=False))


def native(reader,folder,part):
    raw=subprocess.check_output([reader['path'],str(folder/'data'),str(part)],creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
    return pd.read_csv(io.BytesIO(raw),dtype='<f8',float_precision='round_trip')


def one_job(job,prepared):
    folder=OUTPUTS/job['name'];log=LOGS/(job['name']+'.log');complete=LOGS/(job['name']+'.completion.json');receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt]);verify(prepared['inputs'])
    child=None;initial=None;rows=[];pairs=[];error=None;started=time.perf_counter();model=None
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll();count=len(list((folder/'data').glob('Part_*.bi4')));available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    p=len(rows);a=native(prepared['reader'],folder,p);b=native(prepared['reader'],Path(job['reference_folder']),p)
                    assert len(a.columns)==38 and np.isfinite(a.to_numpy()).all() and a.rho.gt(0).all()
                    soil=a.iloc[40:,:35].reset_index(drop=True)
                    if initial is None:initial=soil.copy();model=old.release_case.model(folder/(job['name']+'.xml'))
                    row=old.measure(soil,initial,p,model);rows.append(row)
                    pairs.append(dict(part=p,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),
                        saved_step=int(a.saved_step.iloc[0]),reference_saved_step=int(b.saved_step.iloc[0]),**exact(a,b)))
                if code is not None:break
                print(job['name'],'checked',len(rows),'wall_s',round(time.perf_counter()-started),flush=True);time.sleep(3)
    except BaseException as failure:
        error=repr(failure);trace=traceback.format_exc()
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
    survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        exit_code=None if child is None else child.returncode,owned_exited=not survivors,surviving_owned=survivors,
        program=job['program'],config=job['config'],bat=job['bat'],outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+([bound(log)] if log.exists() else []))
    seal(complete,done);artifacts=[]
    for kind,data in [('history',rows),('same_variant',pairs)]:
        if data:
            csv=FIGURES/(job['name']+'_'+kind+'.csv')
            with csv.open('x',encoding='utf8',newline='') as f:pd.DataFrame(data).to_csv(f,index=False,float_format='%.17g')
            artifacts.append(bound(csv))
    hg=None
    try:
        assert error is None,error
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==len(pairs)==151
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==15000
        assert 'PoreDarcySymmetricCorr="'+('SymmetricSoilPair' if job['variant']=='on' else 'Receiver')+'"' in text
        hg=old.hg_check(text);verify(prepared['inputs'])
        assert all(r['all38_bits_exact'] for r in pairs),'Same-variant full38-field regression differs; CSV preserved'
    except BaseException as failure:error=repr(failure);trace=traceback.format_exc()
    result=dict(passed=error is None,error=error,rows=rows,pairs=pairs,artifacts=artifacts,hourglass=hg,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,physical_acceptance=False)
    if error:result['traceback']=trace
    seal(receipt,result);return result,bound(receipt)


def run():
    assert not RUN.exists() and not CHECK.exists() and not inventory();prepared=read(PREP);verify(prepared['inputs'])
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[])
    def publish():
        temp=RUN.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2,allow_nan=False),encoding='utf8');os.replace(temp,RUN)
    publish()
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name'];publish();result,record=one_job(job,prepared);state['jobs'].append(record);publish()
            assert result['passed'],('Earlier gate failed; later job held',job['name'],result['error'])
        verify(prepared['inputs']);state['status']='same_variant_302_frames_all38_exact_pending_review'
    except BaseException as failure:state.update(status='rejected_or_interrupted',error=repr(failure),traceback=traceback.format_exc())
    state['finished_utc']=utc();publish();passed=state['status']=='same_variant_302_frames_all38_exact_pending_review' and len(state['jobs'])==2
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],error=state.get('error'),
        physical_acceptance=False,half_step_test=False,automatic_long_run_admitted=False));return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:selftest()
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
