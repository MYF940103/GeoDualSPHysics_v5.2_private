"""Ten-step CPU/GPU Scenario2 restart interoperability, not physical handoff acceptance."""
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
import sw_stage1_current_r2 as old

TESTS, CASE, LOGS, CONFIGS, OUTPUTS = old.TESTS, old.CASE, old.LOGS, old.CONFIGS, old.OUTPUTS
TAG='sw_restart_short_r1'
PREP, RUN, CHECK=[LOGS/(TAG+s) for s in ['.inputs.json','.run.json','.check.json']]
NOTE, TEMPLATE=TESTS/'notes'/(TAG+'.json'),CASE/'CaseSelfWeightConsolidation_Scenario2_Def.xml'
BUILD=LOGS/'sw_pore_cell_build_r1.check.json'
SOURCE=OUTPUTS/'sw_stage1_current_r2_off'
DT, END, INTERVAL='0.00000025','0.0000025','0.0000002499'
PERSIST=['x','y','z','vx','vy','vz','rho','sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_yz','sigma_xz','pressure','porepress0','kplastic']
read, seal, verify, bound, utc, inventory=old.read,old.seal,old.verify,old.bound,old.utc,old.inventory


def unique(records):return old.unique([dict(r,sha256=r['sha256'].lower()) for r in records])
def bits(a):return np.asarray(a,dtype='<f8').view('<u8')


def expected(backend,program):
    name=TAG+'_'+backend;xml=TEMPLATE.read_text(encoding='utf8')
    for key,value in [('SavePosDouble','1'),('DtIni',DT),('DtFixed',DT),('TimeMax',END),('TimeOut',INTERVAL)]:
        xml,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]+(" comment=")[^"]+("[^\n]+)',
            lambda m:m[1]+value+m[2]+'Fresh ten-step restart diagnostic; no physical handoff acceptance'+m[3],xml);assert n==1
    exe=os.path.relpath(program,CASE).replace('\\','/');data=os.path.relpath(SOURCE/'data',CASE).replace('\\','/')
    bat=('@echo off\nsetlocal\ncd /d "%~dp0\\..\\.."\n\n'+f'set name={name}\nset dirout=tests/outputs/%name%\n'
        'set dirbin=../../../bin/windows\nset gencase="%dirbin%/GenCase_win64.exe"\n'+f'set dualsphysics="{exe}"\n\n'
        'if exist "%dirout%" goto fail\n%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all\n'
        'if not "%ERRORLEVEL%" == "0" goto fail\n'+f'%dualsphysics% -{backend} -ompthreads:8 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -partbegin:60:0 "{data}" -nsteps:10\n'
        'set solvercode=%ERRORLEVEL%\nif not "%solvercode%" == "0" exit /b %solvercode%\nexit /b 0\n\n:fail\necho Existing/partial data preserved.\nexit /b 1\n')
    return xml,bat


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    for backend in ['cpu','gpu']:
        xml,bat=expected(backend,CASE/'private/solver.exe');tree=ET.fromstring(xml)
        value=lambda key:tree.find('.//parameter[@key="'+key+'"]').get('value')
        assert value('DtIni')==value('DtFixed')==DT and value('TimeMax')==END and value('TimeOut')==INTERVAL and value('SavePosDouble')=='1'
        for name,value in [('HydroMechInitMode','0'),('HydraulicConductivity','1e-3'),('PoreShepardRegularization','0'),('PoreDtSafety','0.1')]:assert tree.find('.//'+name).get('value')==value
        assert all(key not in xml for key in ['SoilHourglassXi','SoilBoundaryDerivativeSPR','PoreDarcySymmetricCorr','SoilStressRateGradCorr'])
        assert '-partbegin:60:0 "tests/outputs/sw_stage1_current_r2_off/data"' in bat and '-nsteps:10' in bat and 'rd /s' not in bat
    print('SELFTEST PASSED; no prepare/reader/solver/build/queue')


def prepare():
    selftest();assert not inventory() and not any(list(d.glob(TAG+'*'))+list(d.glob('x'+TAG+'*')) for d in [LOGS,CONFIGS,OUTPUTS,old.event.FIGURES])
    check=read(old.CHECK);assert check['passed'] and len(check['jobs'])==4
    receipt=next(r for r in check['jobs'] if Path(r['path']).name.endswith('_off.receipt.json'));source=read(receipt['path']);done=read(source['sealed_completion']['path'])
    assert source['passed'] and done['solver_finished'] and done['exit_code']==0 and done['owned_exited'] and len(source['rows'])==61
    assert source['rows'][-1]['part']==60 and source['rows'][-1]['natural_step']==300001
    build=read(BUILD);assert build['passed'];compiled=read(build['prepared']['path'])
    gpu_path=next(r for r in build['fresh_stages'] if read(r['path'])['configuration']=='Release');cpu_path=build['adopted_cpu_release']
    reader_build_path=LOGS/'sw_native_r1.build.json';reader=read(reader_build_path);assert reader['built'] and reader['exit_code']==0
    needed={'Part_0060.bi4','PartExtra_0060.bi4','Part_Head.ibi4','Run.out','CfgInit_NormalsGhost.vtk'}
    handoff=[r for r in done['outputs'] if Path(r['path']).name in needed];assert {Path(r['path']).name for r in handoff}==needed
    proof=compiled['inputs']+reader['inputs']+[bound(p) for p in [__file__,NOTE,TEMPLATE,old.__file__,old.old.__file__,old.current.__file__,old.baseline.__file__,
        old.CHECK,BUILD,reader_build_path,old.baseline.REPO/'bin/windows/GenCase_win64.exe',old.baseline.C04/'support/cryer_start_r1.py']]
    proof += [check['run'],receipt,source['sealed_completion'],build['prepared'],reader['program'],reader['log']]+handoff;jobs=[]
    for backend,record in [('cpu',cpu_path),('gpu',gpu_path)]:
        stage=read(record['path']);assert stage['exit_code']==0 and stage['owned_exited'] and stage['protected_inputs_unchanged'] and len(stage['runtime'])==4
        name=TAG+'_'+backend;cfg=CONFIGS/(name+'_Def.xml');bat=CONFIGS/('x'+name+'_win64_'+backend.upper()+'.bat');xml,command=expected(backend,Path(stage['program']['path']))
        with cfg.open('x',encoding='utf8',newline='') as f:f.write(xml)
        with bat.open('x',encoding='ascii',newline='\r\n') as f:f.write(command)
        jobs.append(dict(name=name,backend=backend,dt=DT,steps=10,frames=11,program=stage['program'],runtime=[r['target'] for r in stage['runtime']],config=bound(cfg),bat=bound(bat)))
        proof += [record,stage['program'],stage['log'],bound(cfg),bound(bat)]+stage['artifacts']+[r[k] for r in stage['runtime'] for k in ['source','target']]
    proof=unique(proof);verify(proof)
    seal(PREP,dict(utc=utc(),inputs=proof,jobs=jobs,reader=reader['program'],handoff_time_s=source['rows'][-1]['time_s'],handoff_is_physical_accepted=False,
        stage_local_time_reset=True,physical_acceptance=False,restart_general_accepted=False,automatic_long_run_admitted=False))


def pore_limit(a,xml):
    tree=ET.parse(xml);f=lambda name:float(np.float32(tree.find('.//'+name).get('value')))
    gravity=np.array([tree.find('.//constantsdef/gravity').get(c) for c in ['x','y','z']],dtype='<f4').astype('<f8')
    g=float(np.linalg.norm(gravity));g=g if g>0 else 9.80665
    kwn=f('PoreWaterBulkModulus')/f('Porosity');cw=f('PoreWaterRho')*g/kwn;h=float(a.h.iloc[0])
    return f('PoreDtSafety')*cw*h*h/f('HydraulicConductivity')


def initial_check(a,reference):
    assert np.array_equal(a.id,reference.id) and np.array_equal(a.is_boundary,reference.is_boundary)
    bad=bits(a[PERSIST])!=bits(reference[PERSIST]);assert not bad.any(),list(np.array(PERSIST)[bad.any(axis=0)])
    assert a.time_s.eq(0).all() and a.saved_step.eq(0).all() and a.stress_double.eq(1).all() and a.position_double.eq(1).all()
    for col in ['mass','dp','h']:assert np.array_equal(bits(a[col]),bits(reference[col])),col
    different=[col for col in ['fstype','normal_x','normal_y','normal_z'] if not np.array_equal(bits(a[col]),bits(reference[col]))]
    return dict(persistent_state16_bits_exact=True,identity_bits_exact=True,soilstate_double=True,new_local_time_s=0,new_saved_step=0,
        source_actual_time_s=float(reference.time_s.iloc[0]),derived_recomputed_fields_different=different,
        normal_difference_max=float(abs(a[['normal_x','normal_y','normal_z']].to_numpy()-reference[['normal_x','normal_y','normal_z']].to_numpy()).max()))


def one_job(job,prepared,reference):
    folder=OUTPUTS/job['name'];log=LOGS/(job['name']+'.log');complete=LOGS/(job['name']+'.completion.json');receipt=LOGS/(job['name']+'.receipt.json')
    assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt]);verify(prepared['inputs'])
    clock=old.clock_table(DT,10);frames={};rows=[];child=None;error=None;initial=None;started=time.perf_counter();dtw=pore_limit(reference,TEMPLATE)
    assert float(DT)<=dtw,'Configured diffusion step limit is mandatory'
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll();count=len(list((folder/'data').glob('Part_*.bi4')));available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    p=len(rows);a=old.current.native(folder,p);frames[p]=a
                    row=old.measure(a,frames[0],p,job,clock);assert row['natural_step']==p
                    if p==0:initial=initial_check(a,reference)
                    row.update(pore_dt_s=dtw,configured_pore_limit_respected=True);rows.append(row)
                if code is not None:break
                time.sleep(1)
    except BaseException as failure:
        error=repr(failure);trace=traceback.format_exc()
        if child is not None and child.poll() is None:subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else '';survivors=[r for r in inventory() if job['name'] in (r.get('CommandLine') or '')]
    done=dict(exit_code=None if child is None else child.returncode,solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        owned_exited=not survivors,surviving_owned=survivors,program=job['program'],config=job['config'],bat=job['bat'],
        outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+([bound(log)] if log.exists() else []));seal(complete,done)
    artifacts=[]
    if rows:artifacts.append(old.event.write_csv(job['name']+'_frames',rows))
    try:
        assert error is None,error
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==11 and rows[-1]['natural_step']==10
        for message in ['PartBegin=60','PartBeginFirst=0','Restart soil data: Sigma inherited, Kplastic reset for restart stage.',
            'Restart hydromechanical data: PorePress and PorePress0 inherited.','HydroMechInitMode="None"','PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"']:assert message in text,message
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==10 and 'SoilHourglass: forcecalls=' not in text
        normal=folder/'CfgInit_NormalsGhost.vtk';assert bound(normal)['sha256']==bound(SOURCE/normal.name)['sha256'],'mDBC loaded boundary normals changed'
        verify(prepared['inputs'])
    except BaseException as failure:error=repr(failure);trace=traceback.format_exc()
    result=dict(passed=error is None,error=error,rows=rows,initial=initial,reader_frames=len(frames),artifacts=artifacts,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,physical_acceptance=False,restart_general_accepted=False)
    if error:result['traceback']=trace
    seal(receipt,result);return result,bound(receipt),frames


def run():
    assert not RUN.exists() and not CHECK.exists() and not inventory();prepared=read(PREP);verify(prepared['inputs']);reference=old.current.native(SOURCE,60)
    assert float(reference.time_s.iloc[0])==prepared['handoff_time_s'] and reference.stress_double.eq(1).all() and reference.rho.eq(2100).all() and reference.kplastic.eq(0).all()
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[]);cache={};pairs=[]
    def publish():
        temp=RUN.with_suffix('.tmp');seal(temp,state);os.replace(temp,RUN)
    publish()
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name'];publish();result,record,frames=one_job(job,prepared,reference);state['jobs'].append(record);publish()
            assert result['passed'],('Earlier guard failed; later job held',job['name'],result['error']);cache[job['backend']]=frames
        for p in range(11):
            a,b=cache['gpu'][p],cache['cpu'][p];delta=float(a.time_s.iloc[0]-b.time_s.iloc[0])
            du=(a.iloc[40:][['x','y','z']].to_numpy()-reference.iloc[40:][['x','y','z']].to_numpy())-(b.iloc[40:][['x','y','z']].to_numpy()-reference.iloc[40:][['x','y','z']].to_numpy())
            pressure=float(np.sqrt(np.mean((a.pressure.iloc[40:]-b.pressure.iloc[40:])**2)));displacement=float(np.linalg.norm(du,axis=1).max()*1000)
            pairs.append(dict(part=p,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),actual_time_difference_s=delta,
                pressure_rms_pa=pressure,material_displacement_max_difference_mm=displacement,passed=abs(delta)<=1e-14 and pressure<=5 and displacement<=.005))
        state['pairs']=old.event.write_csv(TAG+'_pairs',pairs);assert len(pairs)==11 and all(r['passed'] for r in pairs)
        verify(prepared['inputs']);state['status']='restart_interoperability_short_passed_pending_review'
    except BaseException as failure:state.update(status='rejected_or_interrupted',error=repr(failure),traceback=traceback.format_exc())
    state['finished_utc']=utc();publish();passed=state['status']=='restart_interoperability_short_passed_pending_review'
    seal(CHECK,dict(passed=passed,run=bound(RUN),jobs=state['jobs'],error=state.get('error'),physical_acceptance=False,restart_general_accepted=False,automatic_long_run_admitted=False));return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']:group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:selftest()
    elif args.prepare:prepare()
    elif args.run:raise SystemExit(0 if run() else 1)
    else:parser.print_help()
