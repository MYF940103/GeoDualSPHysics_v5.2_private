"""One fresh GPU preload peak diagnostic; default help, never automatic physical/full admission."""
import argparse
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
from cryer_preload_probe_r1 import Q,K,M,P_TARGET,STRAIN_TARGET,SIGMA,equilibrium
from cryer_preload_half_r1 import prerequisites as coarse_prerequisites

TAG='cryer_preload_peak_r1'; DT=2.**-21; RAMP=2.**-8; DRAIN=2.**-7
END=.0703125; INTERVAL=2.**-13; STEPS=147456; FRAMES=577
LOGS=TESTS/'logs'; CONFIG=TESTS/'configs'/(TAG+'_Def.xml'); BAT=TESTS/'configs'/('x'+TAG+'_win64_GPU.bat')
FOLDER=TESTS/'outputs'/TAG; COARSE=TESTS/'outputs/cryer_preload_probe_r1'
PREP=LOGS/(TAG+'.inputs.json'); RUN=LOGS/(TAG+'.run.json'); STATE=LOGS/(TAG+'.status.json')
CHECK=LOGS/(TAG+'.check.json'); COMPLETE=LOGS/(TAG+'.completion.json')
SUMMARY=TESTS/'figures'/(TAG+'_summary.csv'); PREFIX=LOGS/(TAG+'.prefix.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path,data):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(data,stream,indent=2,allow_nan=False)


def prerequisites():
    old,proof=coarse_prerequisites()
    path=LOGS/'cryer_preload_half_review_r1.check.json';review=read(path)
    flags=['evidence_consistency_passed','original_single_run_safety_passed','owned_exits_confirmed','original_independent_half_screen_passed',
        'coarse_declared_initial_equilibrium_diagnostics_passed','half_declared_initial_equilibrium_diagnostics_passed']
    assert all(review[k] is True for k in flags),'Independent short-half review is not admitted'
    links=[dict(path=str(path.parent/e['path']),sha256=e['sha256']) for e in review['source_links']];verify(links)
    checkpath=LOGS/'cryer_preload_half_r1.check.json';check=read(checkpath);assert check['passed'] and check['half_screen_passed'] and check['paired_samples']==69
    assert check['half_equilibrium_diagnostics']['equilibrium_diagnostic_passed'] and check['coarse_equilibrium_diagnostics']['equilibrium_diagnostic_passed']
    verify([check['run_manifest'],check['sealed_completion']]);run=read(check['run_manifest']['path'])
    verify([run['prepared_inputs'],run['program']]);prepared=read(run['prepared_inputs']['path']);verify(prepared['inputs'])
    done=read(check['sealed_completion']['path']);assert done['solver_finished'] and done['owned_exited'] and done['exit_code']==0
    verify(done['outputs']);assert old['program']['sha256']==run['program']['sha256']
    return old,proof+[bound(path),bound(checkpath),check['run_manifest'],check['sealed_completion'],run['prepared_inputs']]+links+done['outputs']


def reserved():
    paths=[RUN,STATE,CHECK,COMPLETE,SUMMARY,PREFIX,FOLDER]+[LOGS/(TAG+s) for s in ['.log','.queue_attempt.json','.notification.json']]
    assert not any(p.exists() for p in paths),'Retained stage exists; no overwrite/restart'


def prepare():
    assert not PREP.exists();reserved();old,proof=prerequisites();thread=identity()
    source=TESTS/'configs/cryer_preload_probe_r1_Def.xml';text=source.read_text(encoding='utf8')
    before='<parameter key="TimeMax" value="0.00830078125" comment="GPU preload probe through 17*2^-11 seconds; not a full validation"'
    after='<parameter key="TimeMax" value="0.0703125" comment="GPU preload peak diagnostic through drainage plus 0.0625 seconds; not full validation"'
    assert text.count(before)==1
    expected=text.replace(before,after).replace('native save interval; 69 frames including t=0','native save interval; 577 frames including t=0')
    assert CONFIG.read_text(encoding='utf8').rstrip()==expected.rstrip()
    template=TESTS/'configs/xcryer_preload_probe_r1_win64_GPU.bat'
    assert BAT.read_text(encoding='utf8').rstrip()==template.read_text(encoding='utf8').replace('cryer_preload_probe_r1',TAG).rstrip()
    files=[__file__,TESTS/'notes'/(TAG+'.md'),CONFIG,BAT,source,template,READER,READER_SOURCE]
    files += [TESTS/'support'/n for n in ['cryer_start_r1.py','cryer_gpu_base_r1.py','cryer_grad_peak_r1.py','cryer_preload_probe_r1.py','cryer_preload_half_r1.py']]
    files += [REPO/'src/source'/n for n in ['JSph.cpp','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.cu','JDsFixedDt.cpp']]
    files += [REPO/'bin/windows'/n for n in ['GenCase_win64.exe','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','DsphConfig.xml']]
    coarse_bytes=sum(p.stat().st_size for p in COARSE.rglob('*') if p.is_file());estimated=int(coarse_bytes*FRAMES/69)
    free=shutil.disk_usage(TESTS).free;required=2*estimated+2*1024**3
    assert free>=required,('Insufficient disk for retained BI4 and analysis margin',free,required)
    seal(PREP,dict(status='prepared_not_started',utc=utc(),thread=thread,inputs=proof+[bound(p) for p in files],
        program=old['program'],build=old['build'],config=bound(CONFIG),bat=bound(BAT),dt_s=DT,expected_steps=STEPS,expected_frames=FRAMES,
        disk_budget=dict(free_bytes=free,coarse_output_bytes=coarse_bytes,estimated_output_bytes=estimated,required_free_bytes=required),
        physical_accepted=False,full_cycle_accepted=False))
    print('PREPARED ONLY',PREP,flush=True)


def inspect(a,initial,part):
    assert len(a)==37173 and a.id.nunique()==37173 and np.array_equal(a.id,initial.id),'Native IDs/count changed'
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.nout.eq(0).all() and a.kplastic.eq(0).all() and a.rho.gt(0).all()
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all()
    assert np.array_equal(a[['mass','h','dp']],initial[['mass','h','dp']])
    t=float(a.time_s.iloc[0]);assert a.time_s.eq(part*INTERVAL).all()
    assert a.saved_step.eq(part*256-1 if part else 0).all()
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


def prefix_compare(a,b,part):
    assert list(a.columns)==list(b.columns) and len(a.columns)==35 and len(a)==len(b),('Native prefix schema/count changed',part)
    x=a.to_numpy(dtype='<f8');y=b.to_numpy(dtype='<f8');bad=x.view('<u8')!=y.view('<u8')
    changes=[]
    for col in np.flatnonzero(bad.any(axis=0)):
        ids=np.flatnonzero(bad[:,col]);i=int(ids[0])
        changes.append(dict(field=a.columns[col],count=len(ids),first_native_id=int(a.id.iloc[i]),new_value=float(x[i,col]),retained_value=float(y[i,col])))
    return dict(part=part,time_s=float(a.time_s.iloc[0]),retained_time_s=float(b.time_s.iloc[0]),
        compared_columns=list(a.columns),all_35_columns0ulp=not bool(bad.any()),differences=changes)


def notification_message(state):
    return (f'User-authorized same-thread {TAG}: {state["status"]}. Not a new human observation. Read {STATE}; '
        f'case-relative tests/logs/{TAG}.run.json,.check.json,.completion.json,.prefix.json and tests/notes/{TAG}.md. '
        'One fresh GPU preload PEAK window dt2^-21,end.0703125s=tD+.0625,147456steps/577frames; no PART restart. '
        'Ramp2^-8,drain2^-7,FixedGrid1,original sphere/rawload/grad1/damping.00004,floatpore/density,double stress unchanged. '
        'Verify owned exits, actual times/IDs, all frozen hashes and all577 original native safety checks. '
        'Complete69-sample same-dt/same-cadence coarse prefix must be all35 native columns0ULP, including dterror: no exclusions. '
        'Part64 at tD is pre-open; all true FSType2/3 p=0 only at t>tD. Review Part61-64 five equilibrium diagnostics separately; '
        'uniform undrained targets are not post-opening safety gates. Keep the full startup and every tau sample; inspect577-row CSV. '
        'No peak-half/full/physical acceptance from normal exit or short-half agreement; figures/theory review is a later offline step. '
        'If analysis alone failed repair new analysis without rerunning completed solver; runtime failure requires exact reason/time and survivor audit. '
        'Preserve evidence, no relaxed guards/duplicate solver/old-worker restart. Report Chinese proactively and continue reviewed diagnosis. '
        'This one-shot queues once; never restart/rearm it or send self-tests; no automatic formal/full run.')


def notify(state):
    assert identity()==state['thread'];message=notification_message(state);assert len(message)<2000
    seal(LOGS/(TAG+'.queue_attempt.json'),dict(utc=utc(),thread=state['thread'],message=message,message_chars=len(message)))
    try:
        p=subprocess.run([str(CODEX),'queue','--thread',state['thread'],'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result=dict(status='queued' if p.returncode==0 else 'queue_failed_no_retry',exit_code=p.returncode,reply=(p.stdout+p.stderr).decode(errors='replace'))
    except Exception as error:result=dict(status='queue_exception_no_retry',error=repr(error))
    seal(LOGS/(TAG+'.notification.json'),result)


def run():
    prepared=read(PREP);verify(prepared['inputs']+[prepared['program']]);prerequisites();reserved()
    assert identity()==prepared['thread'] and not inventory(),'Wrong thread or active GPU solver'
    state=dict(status='running',stage='solver',thread=prepared['thread'],owned_sequence_pid=os.getpid(),started_utc=utc(),
        prepared_inputs=bound(PREP),program=prepared['program'],checked_frames=0,physical_accepted=False)
    def publish():
        tmp=RUN.with_suffix('.tmp');write_json(tmp,state);os.replace(tmp,RUN)
        status={k:state.get(k) for k in ['status','stage','owned_sequence_pid','owned_wrapper_pid','checked_frames','actual_last_saved_time_s']}
        status['run_manifest']=bound(RUN);tmp=STATE.with_suffix('.tmp');write_json(tmp,status);os.replace(tmp,STATE)
    publish();child=None;rows=[];prefix=[];log=LOGS/(TAG+'.log');started=time.perf_counter()
    try:
        assert shutil.disk_usage(TESTS).free>=prepared['disk_budget']['required_free_bytes'],'Available disk fell below prepared budget'
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',prepared['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid']=child.pid;publish();report=started
            while child.poll() is None:
                time.sleep(1)
                if time.perf_counter()-report>=30:print('RUNNING',TAG,'wall_s',round(time.perf_counter()-started),flush=True);report=time.perf_counter()
        state.update(exit_code=child.returncode,owned_exited=True,solver_wall_seconds=time.perf_counter()-started)
        text=(FOLDER/'Run.out').read_text(errors='replace') if (FOLDER/'Run.out').exists() else ''
        finished=child.returncode==0 and 'Finished execution (code=0)' in text
        seal(COMPLETE,dict(solver_finished=finished,owned_exited=True,exit_code=child.returncode,owned_wrapper_pid=child.pid,
            utc=utc(),prepared_inputs=bound(PREP),program=prepared['program'],outputs=[bound(p) for p in FOLDER.rglob('*') if p.is_file()]+[bound(log)]))
        state.update(sealed_completion=bound(COMPLETE),stage='offline_analysis');publish();assert finished,'Solver did not finish normally'
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==STEPS
        assert len(list((FOLDER/'data').glob('Part_*.bi4')))==FRAMES and 'SoilStressRateGradCorr="KernelGradient"' in text
        assert 'HydroMechDrainageFixedGrid=True' in text and 'BuiFukagawa2013' in text
        for label,value in [('HydroMechTopLoadQ0',Q),('HydroMechTopLoadRampTime',RAMP),('HydroMechDrainageStartTime',DRAIN)]:
            found=re.search(re.escape(label)+r':\s*([^\r\n]+)',text);assert found and float(found[1])==float(format(value,'.6g'))
        assert float(re.search(r'^\s*SoilDampingCoef=([^\r\n]+)',text,re.M)[1])==.00004
        state['actual_gpu']=re.search(r'Device default:\s*([^\r\n]+)',text)[1]
        initial=native(FOLDER,0);state['center_fixed_material_ids']=list(map(int,initial.id[np.linalg.norm(initial[['x','y','z']],axis=1)<=.0025+1e-12]))
        for part in range(FRAMES):
            a=initial if part==0 else native(FOLDER,part);row=inspect(a,initial,part);rows.append(row)
            if part<69:
                record=prefix_compare(a,native(COARSE,part),part);prefix.append(record)
                assert record['all_35_columns0ulp'],('Same-dt full native prefix changed',record)
            state.update(checked_frames=part+1,actual_last_saved_time_s=row['time_s']);publish()
            if part%32==0:print('CHECKED',part+1,'/',FRAMES,flush=True)
        state['equilibrium_diagnostics']=equilibrium(rows);assert len(prefix)==69 and rows[-1]['time_s']==END
        verify(prepared['inputs']+[prepared['program']])
        state.update(status='preload_peak_safety_completed_pending_causal_review',stage='terminal')
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True);state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='preload_peak_rejected_or_interrupted',stage='terminal',error=repr(error),traceback=traceback.format_exc(),owned_exited=child is None or child.poll() is not None)
    finally:
        artifacts=[]
        if rows:
            with SUMMARY.open('x',encoding='utf8',newline='') as stream:pd.DataFrame(rows).to_csv(stream,index=False,float_format='%.17g')
            artifacts.append(bound(SUMMARY))
        seal(PREFIX,dict(checked_samples=len(prefix),all35_columns0ulp_passed=len(prefix)==69 and all(p['all_35_columns0ulp'] for p in prefix),
            excluded_columns=[],samples=prefix));artifacts.append(bound(PREFIX))
        state.update(finished_utc=utc(),wall_seconds=time.perf_counter()-started,artifacts=artifacts);publish()
        seal(CHECK,dict(passed=state['status']=='preload_peak_safety_completed_pending_causal_review',status=state['status'],run_manifest=bound(RUN),
            sealed_completion=state.get('sealed_completion'),checked_frames=len(rows),prefix_samples=len(prefix),prefix_receipt=bound(PREFIX),error=state.get('error'),
            equilibrium_diagnostics=state.get('equilibrium_diagnostics'),physical_accepted=False,peak_half_accepted=False,
            full_cycle_accepted=False,automatic_formal_run_admitted=False))
        notify(state)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    group.add_argument('--prepare',action='store_true');group.add_argument('--run',action='store_true');args=parser.parse_args()
    if args.prepare:prepare()
    elif args.run:run()
    else:parser.print_help()
