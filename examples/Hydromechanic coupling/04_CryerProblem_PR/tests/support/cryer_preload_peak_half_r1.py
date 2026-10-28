"""One fresh canonical GPU peak half-step; default help, no formal admission."""
import argparse
import ast
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE,TESTS,REPO,READER,READER_SOURCE,bound,native,pore_dt,utc,write_json
from cryer_gpu_base_r1 import verify
from cryer_grad_peak_r1 import inventory,identity,CODEX
from cryer_grad_short_r1 import difference
from cryer_preload_probe_r1 import Q,K,M,P_TARGET,STRAIN_TARGET,SIGMA,equilibrium
import cryer_preload_peak_r1 as retained_peak

TAG='cryer_preload_peak_half_r1'; DT=2.**-22; RAMP=2.**-8; DRAIN=2.**-7
END=.0703125; INTERVAL=2.**-13; STEPS=294912; FRAMES=577
LOGS=TESTS/'logs'; CONFIG=TESTS/'configs'/(TAG+'_Def.xml'); BAT=TESTS/'configs'/('x'+TAG+'_win64_GPU.bat')
FOLDER=TESTS/'outputs'/TAG; COARSE=TESTS/'outputs/cryer_preload_peak_r1'
PREFIX_REFERENCE=TESTS/'outputs/cryer_preload_half_r1'
PREP=LOGS/(TAG+'.inputs.json'); RUN=LOGS/(TAG+'.run.json'); STATE=LOGS/(TAG+'.status.json')
CHECK=LOGS/(TAG+'.check.json'); COMPLETE=LOGS/(TAG+'.completion.json')
SUMMARY=TESTS/'figures'/(TAG+'_summary.csv'); PAIR=TESTS/'figures'/(TAG+'_half.csv')
PREFIX=LOGS/(TAG+'.prefix.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path,data):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(data,stream,indent=2,allow_nan=False)


def unique_records(records):
    result={}
    for item in records:
        path=str(Path(item['path']).resolve());key=os.path.normcase(path)
        current=dict(item,path=path)
        assert key not in result or result[key]['sha256'].lower()==item['sha256'].lower(),('Conflicting frozen hashes',path)
        result[key]=current
    return list(result.values())


def prerequisites():
    # Pure retained prerequisite checks only: no retained run/prepare/notify is called.
    old,proof=retained_peak.prerequisites()
    path=LOGS/'cryer_preload_peak_r1.check.json';check=read(path)
    assert check['passed'] and check['checked_frames']==FRAMES and check['prefix_samples']==69
    assert check['equilibrium_diagnostics']['equilibrium_diagnostic_passed']
    verify([check['run_manifest'],check['sealed_completion'],check['prefix_receipt']])
    coarse=read(check['run_manifest']['path']);completion=read(check['sealed_completion']['path'])
    assert coarse['owned_exited'] and coarse['exit_code']==0 and coarse['actual_last_saved_time_s']==END
    assert completion['solver_finished'] and completion['owned_exited'] and completion['exit_code']==0
    prepared=read(coarse['prepared_inputs']['path'])
    prefix=read(check['prefix_receipt']['path'])
    assert prefix['checked_samples']==69 and prefix['all35_columns0ulp_passed'] and prefix['excluded_columns']==[]
    assert len(prefix['samples'])==69 and all(x['all_35_columns0ulp'] and not x['differences'] for x in prefix['samples'])
    proof += [bound(path),check['run_manifest'],check['sealed_completion'],check['prefix_receipt'],
        coarse['prepared_inputs'],coarse['program'],prepared['build']]+prepared['inputs']+completion['outputs']+coarse['artifacts']
    reviewpath=LOGS/'cryer_preload_peak_review_r1.check.json';review=read(reviewpath)
    for key in ['evidence_consistency_passed','upstream_original_577_native_safety_adopted',
            'upstream_exact69_all35_prefix_adopted','prefix_individual69_all35_verified','closed_equilibrium_passed']:
        assert review[key] is True,('Retained peak review prerequisite',key)
    proof += [bound(reviewpath)]+review['source_links']
    halfpath=LOGS/'cryer_preload_half_r1.check.json';half=read(halfpath)
    assert half['passed'] and half['half_screen_passed'] and half['paired_samples']==69
    assert half['half_equilibrium_diagnostics']['equilibrium_diagnostic_passed']
    verify([half['run_manifest'],half['sealed_completion']])
    halfrun=read(half['run_manifest']['path']);halfprepared=read(halfrun['prepared_inputs']['path'])
    halfdone=read(half['sealed_completion']['path'])
    assert halfrun['owned_exited'] and halfrun['exit_code']==0 and halfdone['solver_finished']
    assert halfdone['owned_exited'] and halfdone['exit_code']==0
    assert prepared['program']['sha256']==halfprepared['program']['sha256']==old['program']['sha256']
    assert Path(prepared['program']['path']).resolve()==(REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe').resolve()
    proof += [bound(halfpath),half['run_manifest'],half['sealed_completion'],halfrun['prepared_inputs'],
        halfprepared['program'],halfprepared['build']]+halfprepared['inputs']+halfdone['outputs']+halfrun['artifacts']
    # These are reviewed diagnostics, not physical acceptance or a candidate implementation.
    for name in ['cryer_finite_storage_r1','cryer_radial_consistency_r1','cryer_radial_force_r2',
            'cryer_radial_moments_r1','cryer_saved_state_audit_r1']:
        diagnostic=LOGS/(name+'.check.json');record=read(diagnostic)
        assert record['analysis_checks_passed'],('Field diagnostic prerequisite',name)
        proof += [bound(diagnostic)]+record['inputs']+record.get('artifacts',[])
    proof += read(prepared['build']['path'])['inputs']+read(halfprepared['build']['path'])['inputs']
    proof=unique_records(proof);verify(proof)
    return prepared,proof,check['equilibrium_diagnostics']


def reserved():
    paths=[RUN,STATE,CHECK,COMPLETE,SUMMARY,PAIR,PREFIX,FOLDER]+[LOGS/(TAG+s) for s in ['.log','.queue_attempt.json','.notification.json']]
    assert not any(p.exists() for p in paths),'Retained stage exists; no overwrite/restart'


def selftest():
    source=TESTS/'configs/cryer_preload_peak_r1_Def.xml'
    text=source.read_text(encoding='utf8')
    assert text.count('0.000000476837158203125')==2
    assert CONFIG.read_text(encoding='utf8').rstrip()==text.replace('0.000000476837158203125','0.0000002384185791015625').rstrip()
    template=TESTS/'configs/xcryer_preload_peak_r1_win64_GPU.bat'
    assert BAT.read_text(encoding='utf8').rstrip()==template.read_text(encoding='utf8').replace('cryer_preload_peak_r1',TAG).rstrip()
    assert END/DT==STEPS and END/INTERVAL+1==FRAMES and INTERVAL/DT==512
    assert DRAIN/INTERVAL==64 and RAMP/DT==16384 and DRAIN/DT==32768
    oldtree=ast.parse(Path(retained_peak.__file__).read_text(encoding='utf8'))
    newtree=ast.parse(Path(__file__).read_text(encoding='utf8'))
    old=copy.deepcopy(next(n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name=='inspect'))
    new=next(n for n in newtree.body if isinstance(n,ast.FunctionDef) and n.name=='inspect')
    class HalfStep(ast.NodeTransformer):
        def visit_Constant(self,node):
            return ast.copy_location(ast.Constant(value=512),node) if node.value==256 else node
    expected=HalfStep().visit(old)
    assert ast.dump(expected,include_attributes=False)==ast.dump(new,include_attributes=False),'Only the native saved-step factor may change in inspect'
    assert half_screen(dict(pressure_rms_pa=5.,material_displacement_max_mm=.005))
    assert not half_screen(dict(pressure_rms_pa=np.nextafter(5.,np.inf),material_displacement_max_mm=0.))
    assert not half_screen(dict(pressure_rms_pa=0.,material_displacement_max_mm=np.nextafter(.005,np.inf)))
    assert len(notification_message(dict(status='preload_peak_half_rejected_or_interrupted')))<2000
    return dict(passed=True,source_xml_changes='Only DtIni/DtFixed 2^-21 to 2^-22',
        inspect_ast_changes='Only native saved_step part*256-1 to part*512-1',
        expected_steps=STEPS,expected_frames=FRAMES,prefix_columns=35,prefix_samples=69,
        half_limits=dict(pressure_rms_pa=5.,material_displacement_max_mm=.005),
        solver_executed=False,prepared=False,notification_sent=False,files_written=False)


def prepare():
    assert not PREP.exists();reserved();selftest()
    old,proof,diagnostics=prerequisites();thread=identity()
    files=[__file__,TESTS/'notes'/(TAG+'.md'),CONFIG,BAT,READER,READER_SOURCE]
    files += [TESTS/'support'/n for n in ['cryer_start_r1.py','cryer_gpu_base_r1.py','cryer_grad_peak_r1.py',
        'cryer_grad_short_r1.py','cryer_preload_probe_r1.py','cryer_preload_half_r1.py','cryer_preload_peak_r1.py']]
    files += [REPO/'src/source'/n for n in ['JSph.cpp','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.cu','JDsFixedDt.cpp']]
    files += [REPO/'bin/windows'/n for n in ['GenCase_win64.exe','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','DsphConfig.xml']]
    coarse_bytes=sum(p.stat().st_size for p in COARSE.rglob('*') if p.is_file())
    free=shutil.disk_usage(TESTS).free;required=2*coarse_bytes+2*1024**3
    assert free>=required,('Insufficient disk for retained BI4 and analysis margin',free,required)
    seal(PREP,dict(status='prepared_not_started',utc=utc(),thread=thread,
        inputs=unique_records(proof+[bound(p) for p in files]),program=old['program'],build=old['build'],
        config=bound(CONFIG),bat=bound(BAT),dt_s=DT,expected_steps=STEPS,expected_frames=FRAMES,
        adopted_coarse_peak=bound(LOGS/'cryer_preload_peak_r1.check.json'),
        adopted_short_half=bound(LOGS/'cryer_preload_half_r1.check.json'),
        coarse_equilibrium_diagnostics=diagnostics,
        disk_budget=dict(free_bytes=free,coarse_output_bytes=coarse_bytes,
            estimated_new_output_bytes=coarse_bytes,required_free_bytes=required),
        physical_accepted=False,full_cycle_accepted=False,automatic_formal_run_admitted=False))
    print('PREPARED ONLY',PREP,flush=True)


def inspect(a,initial,part):
    assert len(a)==37173 and a.id.nunique()==37173 and np.array_equal(a.id,initial.id),'Native IDs/count changed'
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.nout.eq(0).all() and a.kplastic.eq(0).all() and a.rho.gt(0).all()
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all()
    assert np.array_equal(a[['mass','h','dp']],initial[['mass','h','dp']])
    t=float(a.time_s.iloc[0]);assert a.time_s.eq(part*INTERVAL).all()
    assert a.saved_step.eq(part*512-1 if part else 0).all()
    dtw=pore_dt(float(a.h.iloc[0]));assert DT<=dtw
    if part:assert a.has_dterror.eq(1).all() and float(a.dterror_s.max())<=1e-14
    x=a[['x','y','z']].to_numpy();x0=initial[['x','y','z']].to_numpy();du=x-x0
    r=np.linalg.norm(x,axis=1);r0=np.linalg.norm(x0,axis=1);assert r.max()<=.0525
    v0=initial.mass.to_numpy()/initial.rho.to_numpy();w=v0/v0.sum();vn=a.mass.to_numpy()/a.rho.to_numpy()
    p=a.pressure.to_numpy(dtype=np.float64);sigma=a[SIGMA].to_numpy(dtype=np.float64);total=sigma.copy();total[:,:3]-=p[:,None]
    residual=total.copy();residual[:,:3]+=Q
    rms=lambda v:float(np.sqrt(np.sum(w*np.mean(np.asarray(v)**2,axis=1)))) if np.asarray(v).ndim==2 else float(np.sqrt(np.sum(w*np.asarray(v)**2)))
    mean=lambda v:float(np.sum(w*np.asarray(v)))
    beta=float(np.sum(v0*np.sum(x0*du,axis=1))/np.sum(v0*r0*r0));iso=du-beta*x0
    fit=np.linalg.lstsq(x0*np.sqrt(v0[:,None]),du*np.sqrt(v0[:,None]),rcond=None)[0]
    inward=(r0-r)*1000;target=-STRAIN_TARGET*r0*1000;shell=r0>=.05-2*float(initial.h.iloc[0]);sw=v0[shell]/v0[shell].sum()
    center=r0<=.0025+1e-12;assert center.sum()==18
    surface=a.fstype.isin([2,3]).to_numpy();assert surface.any(),'True FSType2/3 mask empty'
    drained=float(np.max(np.abs(p[surface])));active=t>DRAIN
    if active:assert drained==0.,('Post-event drained pressure',part,drained)
    force=a.mass.to_numpy()[:,None]*a[['load_ax','load_ay','load_az']].to_numpy();net=force.sum(axis=0);torque=np.cross(x,force).sum(axis=0)
    unit=x/np.where(r>0,r,1)[:,None];radial=float(-np.sum(force*unit));virial=float(-np.sum(force*x));volume=4*np.pi*.05**3/3
    if part:assert radial>0 and np.linalg.norm(force,axis=1).max()>0,'Actual inward load absent'
    row=dict(part=part,time_s=t,saved_step=int(a.saved_step.iloc[0]),tau_from_drainage_s=t-DRAIN,drainage_active=active,
        true_surface_count=int(surface.sum()),changed_fstype_count=int((a.fstype!=initial.fstype).sum()),true_surface_pressure_absmax_pa=drained,
        center_fixed_material_count=int(center.sum()),center_pressure_mean_pa=float(p[center].mean()),pressure_mean_pa=mean(p),pressure_min_pa=float(p.min()),pressure_max_pa=float(p.max()),
        pressure_uniform_target_pa=P_TARGET,pressure_target_rms_pa=rms(p-P_TARGET),total_stress_target_six_rms_pa=rms(residual),
        speed_max_m_s=float(np.linalg.norm(a[['vx','vy','vz']],axis=1).max()),rho_mean_kg_m3=mean(a.rho),rho_min_kg_m3=float(a.rho.min()),rho_max_kg_m3=float(a.rho.max()),
        native_current_volume_m3=float(vn.sum()),native_reference_volume_m3=float(v0.sum()),native_over_geometric_volume=float(vn.sum()/volume),r2_mean_m2=mean(r*r),
        isotropic_fit_scalar=beta,isotropic_fit_target=STRAIN_TARGET,isotropic_vector_residual_rms_mm=1000*rms(np.linalg.norm(iso,axis=1)),full_affine_trace=float(np.trace(fit)),
        full_affine_vector_residual_rms_mm=1000*rms(np.linalg.norm(du-x0@fit,axis=1)),shell_inward_mean_mm=float(sw@inward[shell]),shell_target_mean_mm=float(sw@target[shell]),
        shell_target_error_mean_mm=float(sw@(inward-target)[shell]),shell_target_error_rms_mm=float(np.sqrt(sw@((inward-target)[shell]**2))),
        fluid_content_from_stress_conditional=mean(sigma[:,:3].sum(axis=1)/(3*K)+p/M),fluid_content_from_isotropic_fit_conditional=3*beta+mean(p)/M,
        fluid_content_from_full_affine_conditional=float(np.trace(fit))+mean(p)/M,actual_radial_force_N=radial,net_force_norm_N=float(np.linalg.norm(net)),torque_norm_N_m=float(np.linalg.norm(torque)),
        load_virial_over_3qVnative=virial/(3*Q*float(vn.sum())),load_virial_over_3qVgeometric=virial/(3*Q*volume),
        source_clock_q_reference_pa=Q*min(max(t-DT,0)/RAMP,1),dterror_s=float(a.dterror_s.max()),pore_diffusion_dt_s=dtw,fixed_to_pore_dt_ratio=DT/dtw)
    for i,col in enumerate(SIGMA):row['effective_'+col+'_mean_pa']=mean(sigma[:,i]);row['total_'+col+'_mean_pa']=mean(total[:,i])
    row['effective_mean_compression_pa']=-mean(sigma[:,:3].sum(axis=1))/3
    row['total_mean_compression_pa']=-mean(total[:,:3].sum(axis=1))/3
    return row


def half_screen(metrics):
    return metrics['pressure_rms_pa']<=5. and metrics['material_displacement_max_mm']<=.005


def notification_message(state):
    return (f'User-authorized same-thread {TAG}: {state["status"]}. Not a new human observation. Read {STATE}; '
        f'case-relative tests/logs/{TAG}.run.json,.check.json,.completion.json,.prefix.json and tests/notes/{TAG}.md. '
        'Only one fresh canonical GPU HALF dt2^-22,end.0703125s,294912steps/577frames; no PART restart or source/physics changes. '
        'Retained coarse cryer_preload_peak_r1 was not rerun. Adopted cryer_preload_half_r1 supplies69 same-dt/same-cadence prefix states: '
        'all35 native columns including dterror must remain0ULP,no exclusions. Half saved steps part*512-1,coarse part*256-1; never rewrite them. '
        'Verify owned exits,actual times/native IDs and all bound build/input/output hashes; all577 original single-run safety checks,'
        ' Part64 at tD pre-open,all true FSType2/3 p=0 only at t>tD; both Part61-64 five equilibrium diagnostics. '
        'Review every577 actual-matched coarse/half pair under original5Pa/.005mm limits and inspect full CSVs. '
        'Normal exit or a half pass is not theory/physical/full/formal acceptance. No automatic formal run or symC candidate launch. '
        'If only analysis failed repair new analysis without rerunning solver. On runtime failure inspect exact sealed time/reason/survivors;'
        ' retain outputs,no relaxed guards,duplicate solver,old-worker restart or overwritten evidence. '
        'Report Chinese proactively,then decide reviewed diagnosis. This one-shot queues once; never restart/rearm or send self-tests.')


def notify(state):
    assert identity()==state['thread'];message=notification_message(state);assert len(message)<2000
    seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message,message_chars=len(message)))
    try:
        result=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],
            capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='queued' if result.returncode==0 else 'queue_failed_no_retry',
            exit_code=result.returncode,reply=(result.stdout+result.stderr).decode(errors='replace'))
    except Exception as error:record=dict(status='queue_exception_no_retry',error=repr(error))
    seal(LOGS/(TAG+'.notification.json'),record)


def run():
    prepared=read(PREP);reserved();assert identity()==prepared['thread'],'Wrong conversation'
    state=dict(status='running',stage='admission',thread=prepared['thread'],owned_sequence_pid=os.getpid(),
        started_utc=utc(),prepared_inputs=bound(PREP),program=prepared['program'],checked_frames=0,
        physical_accepted=False,automatic_formal_run_admitted=False)
    def publish():
        tmp=RUN.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,RUN)
        status={k:state.get(k) for k in ['status','stage','owned_sequence_pid','owned_wrapper_pid','checked_frames','actual_last_saved_time_s']}
        status['run_manifest']=bound(RUN);tmp=STATE.with_suffix('.tmp');write_json(tmp,status);os.replace(tmp,STATE)
    publish();child=None;rows=[];pairs=[];prefix=[];log=LOGS/(TAG+'.log');started=time.perf_counter()
    try:
        verify(prepared['inputs']+[prepared['program'],prepared['build']]);prerequisites();selftest()
        assert not inventory(),'An existing GPU solver is active; no duplicate admitted'
        assert shutil.disk_usage(TESTS).free>=prepared['disk_budget']['required_free_bytes'],'Available disk fell below prepared budget'
        state['stage']='solver';publish()
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',prepared['bat']['path']],
                cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid']=child.pid;publish();report=started
            while child.poll() is None:
                time.sleep(1)
                if time.perf_counter()-report>=30:
                    print('RUNNING',TAG,'wall_s',round(time.perf_counter()-started),flush=True);report=time.perf_counter()
        state.update(exit_code=child.returncode,owned_exited=True,solver_wall_seconds=time.perf_counter()-started)
        text=(FOLDER/'Run.out').read_text(errors='replace') if (FOLDER/'Run.out').exists() else ''
        leftovers=[p for p in inventory() if TAG in (p.get('CommandLine') or '')]
        state['owned_gpu_processes_after_wrapper']=leftovers
        finished=child.returncode==0 and 'Finished execution (code=0)' in text and not leftovers
        # Completion, including raw hashes, is sealed before native analysis.
        seal(COMPLETE,dict(solver_finished=finished,owned_exited=not bool(leftovers),exit_code=child.returncode,
            owned_wrapper_pid=child.pid,owned_gpu_processes_after_wrapper=leftovers,utc=utc(),
            prepared_inputs=bound(PREP),program=prepared['program'],
            outputs=[bound(p) for p in FOLDER.rglob('*') if p.is_file()]+[bound(log)]))
        state.update(sealed_completion=bound(COMPLETE),stage='offline_analysis');publish()
        assert finished,'Solver did not finish normally or owned GPU process survived'
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==STEPS
        assert len(list((FOLDER/'data').glob('Part_*.bi4')))==FRAMES
        assert 'SoilStressRateGradCorr="KernelGradient"' in text and 'HydroMechDrainageFixedGrid=True' in text
        assert 'PoreCompressionSourceMode="PairDivergence"' in text and 'PoreCompressionGradCorr="KernelGradient"' in text
        assert 'BuiFukagawa2013' in text
        for label,value in [('HydroMechTopLoadQ0',Q),('HydroMechTopLoadRampTime',RAMP),('HydroMechDrainageStartTime',DRAIN)]:
            found=re.search(re.escape(label)+r':\s*([^\r\n]+)',text);assert found and float(found[1])==float(format(value,'.6g'))
        assert float(re.search(r'^\s*SoilDampingCoef=([^\r\n]+)',text,re.M)[1])==.00004
        state['actual_gpu']=re.search(r'Device default:\s*([^\r\n]+)',text)[1]
        initial=native(FOLDER,0);coarse_initial=native(COARSE,0)
        state['center_fixed_material_ids']=list(map(int,initial.id[np.linalg.norm(initial[['x','y','z']],axis=1)<=.0025+1e-12]))
        assert len(state['center_fixed_material_ids'])==18
        for part in range(FRAMES):
            a=initial if part==0 else native(FOLDER,part)
            b=coarse_initial if part==0 else native(COARSE,part)
            row=inspect(a,initial,part);rows.append(row)
            assert list(a.columns)==list(b.columns) and np.array_equal(a.id,b.id)
            assert b.time_s.eq(part*INTERVAL).all() and b.saved_step.eq(part*256-1 if part else 0).all()
            assert float(a.time_s.iloc[0])==float(b.time_s.iloc[0]),'No time interpolation/nominal matching'
            if part<69:
                item=retained_peak.prefix_compare(a,native(PREFIX_REFERENCE,part),part);prefix.append(item)
                assert item['all_35_columns0ulp'],('Same-dt full native prefix changed',item)
            metrics=difference(a,b);metrics.update(part=part,time_s=row['time_s'],coarse_time_s=float(b.time_s.iloc[0]))
            metrics['screen_passed']=half_screen(metrics);pairs.append(metrics)
            state.update(checked_frames=part+1,actual_last_saved_time_s=row['time_s']);publish()
            if part%32==0:print('CHECKED',part+1,'/',FRAMES,flush=True)
        state['half_equilibrium_diagnostics']=equilibrium(rows)
        state['coarse_equilibrium_diagnostics']=prepared['coarse_equilibrium_diagnostics']
        state['half_screen_passed']=all(p['screen_passed'] for p in pairs)
        state['half_failures']=[p for p in pairs if not p['screen_passed']]
        assert len(prefix)==69 and len(pairs)==FRAMES and rows[-1]['time_s']==END
        verify(prepared['inputs']+[prepared['program'],prepared['build']])
        assert state['half_screen_passed'],('Original all577 5Pa/.005mm half gate failed',state['half_failures'])
        state.update(status='preload_peak_half_passed_pending_physical_review',stage='terminal')
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='preload_peak_half_rejected_or_interrupted',stage='terminal',error=repr(error),
            traceback=traceback.format_exc(),owned_exited=child is None or child.poll() is not None)
    finally:
        artifacts=[]
        for path,data in [(SUMMARY,rows),(PAIR,pairs)]:
            if data:
                with path.open('x',encoding='utf8',newline='') as stream:pd.DataFrame(data).to_csv(stream,index=False,float_format='%.17g')
                artifacts.append(bound(path))
        seal(PREFIX,dict(checked_samples=len(prefix),all35_columns0ulp_passed=len(prefix)==69 and all(x['all_35_columns0ulp'] for x in prefix),
            excluded_columns=[],samples=prefix));artifacts.append(bound(PREFIX))
        state.update(finished_utc=utc(),wall_seconds=time.perf_counter()-started,artifacts=artifacts);publish()
        seal(CHECK,dict(passed=state['status']=='preload_peak_half_passed_pending_physical_review',status=state['status'],
            run_manifest=bound(RUN),sealed_completion=state.get('sealed_completion'),checked_frames=len(rows),
            paired_samples=len(pairs),prefix_samples=len(prefix),prefix_receipt=bound(PREFIX),error=state.get('error'),
            half_screen_passed=state.get('half_screen_passed'),half_equilibrium_diagnostics=state.get('half_equilibrium_diagnostics'),
            coarse_equilibrium_diagnostics=state.get('coarse_equilibrium_diagnostics'),physical_accepted=False,
            full_cycle_accepted=False,automatic_formal_run_admitted=False))
        notify(state)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    group.add_argument('--prepare',action='store_true');group.add_argument('--run',action='store_true')
    group.add_argument('--selftest',action='store_true');args=parser.parse_args()
    if args.prepare:prepare()
    elif args.run:run()
    elif args.selftest:print(json.dumps(selftest(),indent=2))
    else:parser.print_help()
