"""Prepare only by default; --run starts one fresh, gated GPU peak window."""
import argparse
import importlib.util
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
from cryer_start_r1 import CASE,TESTS,REPO,READER,bound,native,utc,write_json
from cryer_dt_short_r1 import inspect
from cryer_gpu_base_r1 import verify,GPU_HASHES

LIAN=CASE.parent/'05_LianFlexibleStrip2D_PR/tests/scripts'
sys.path.insert(0,str(LIAN))
from lian_hg_prefix_r2 import compare_prefix
TAG='cryer_grad_peak_r1'
DT=2.**-21;DURATION=2.**-4;INTERVAL=2.**-11;STEPS=131072;FRAMES=129
PREP=TESTS/'logs'/(TAG+'.inputs.json')
RUN=TESTS/'logs'/(TAG+'.run.json');STATE=TESTS/'logs'/(TAG+'.status.json')
CHECK=TESTS/'logs'/(TAG+'.check.json');COMPLETE=TESTS/'logs'/(TAG+'.completion.json')
SUMMARY=TESTS/'figures'/(TAG+'_summary.csv')
CODEX=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
THEORY=CASE/'support/plot_cryer_poisson_sweep.py'


def exclusive(path,data):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(data,stream,indent=2,allow_nan=False)


def identity():
    thread=os.environ['CODEX_THREAD_ID']
    assert thread and thread==os.environ['CODEX_SESSION_ID'] and CODEX.is_file()
    return thread


def inventory():
    cmd="Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*' -and $_.Name -notmatch 'CPU'} | Select-Object Name,ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-Command',cmd],text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    rows=json.loads(raw) if raw else []
    return [rows] if isinstance(rows,dict) else rows


def prerequisites():
    cpu=TESTS/'logs/cryer_grad_fine_r1.review.json';review=json.loads(cpu.read_text(encoding='utf8'))
    assert review['evidence_consistency_passed'] and review['original_independent_half_screen_passed']
    cpucheck=TESTS/'logs/cryer_grad_fine_r1.check.json'
    assert json.loads(cpucheck.read_text(encoding='utf8'))['passed']
    verify([dict(path=str(cpu.parent/e['path']),sha256=e['sha256']) for e in review['source_links']])
    gate=TESTS/'logs/cryer_gpu_grad_fine_r1.check.json';check=json.loads(gate.read_text(encoding='utf8'))
    assert check['passed'] and check['paired_samples']==5 and check['cross_samples']==10
    verify([check['run_manifest']]);run=json.loads(Path(check['run_manifest']['path']).read_text(encoding='utf8'))
    assert run['status']=='gpu_fine_pair_passed_pending_review' and len(run['runs'])==2 and run['finished_utc']
    proofs=[bound(cpu),bound(cpucheck),bound(gate),check['run_manifest'],run['prepared_inputs']]
    verify([run['prepared_inputs']]);fine=json.loads(Path(run['prepared_inputs']['path']).read_text(encoding='utf8'))
    for r in run['runs']:
        assert r['passed'] and r['owned_exited'] and r['exit_code']==0 and r['checked_frames']==5
        complete=r['sealed_completion'];verify([complete]);sealed=json.loads(Path(complete['path']).read_text(encoding='utf8'))
        assert sealed['solver_finished'] and sealed['exit_code']==0
        proofs += [complete]+sealed['outputs']
    assert fine['program']['sha256']==GPU_HASHES['c']
    verify(proofs+[fine['program'],fine['build']])
    return fine,proofs


def prepare():
    assert not PREP.exists(),'Never overwrite a prepared stage'
    fine,proofs=prerequisites();thread=identity()
    source=TESTS/'configs/cryer_gpu_grad_fine_r1_c_Def.xml';cfg=TESTS/'configs'/(TAG+'_Def.xml')
    template=TESTS/'configs/xcryer_gpu_grad_fine_r1_c_win64_GPU.bat';bat=TESTS/'configs'/('x'+TAG+'_win64_GPU.bat')
    expected=source.read_text(encoding='utf8')
    for key,value,comment in [('TimeMax','0.0625','GPU peak window 0.0625 s; not a full Cryer validation'),
                             ('TimeOut','0.00048828125','Binary-exact native save interval; 129 frames including t=0')]:
        expected,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(" comment=")[^"]*(")',lambda m:m[1]+value+m[2]+comment+m[3],expected);assert n==1
    assert cfg.read_text(encoding='utf8')==expected,'Only two time values and their two descriptions may differ from GPU fine coarse XML'
    assert bat.read_text(encoding='utf8')==template.read_text(encoding='utf8').replace('cryer_gpu_grad_fine_r1_c',TAG)
    reserved=[TESTS/'outputs'/TAG,RUN,STATE,CHECK,COMPLETE,SUMMARY,TESTS/'logs'/(TAG+'.log'),
        TESTS/'logs'/(TAG+'.queue_attempt.json'),TESTS/'logs'/(TAG+'.notification.json')]
    assert not any(p.exists() for p in reserved),'Retained stage path already exists'
    scripts=[__file__,TESTS/'notes'/(TAG+'.md'),source,template,cfg,bat,THEORY,READER,
        TESTS/'support/cryer_start_r1.py',TESTS/'support/cryer_dt_short_r1.py',
        TESTS/'support/cryer_gpu_base_r1.py',LIAN/'lian_hg_prefix_r2.py']
    scripts += [REPO/'src/papers/PDF'/n for n in [
        'a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf',
        '2019 - Zhao - A generic approach to modelling flexible confined boundary conditions in SPH and.pdf']]
    runtime=[REPO/'bin/windows'/n for n in ['GenCase_win64.exe','DualSPHysics5.2_GEO_win64.exe','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','DsphConfig.xml']]
    inputs=[bound(p) for p in scripts+runtime]
    assert DT*STEPS==DURATION and DURATION/INTERVAL+1==FRAMES
    exclusive(PREP,dict(status='prepared_not_started',utc=utc(),thread=thread,program=fine['program'],build=fine['build'],
        config=bound(cfg),bat=bound(bat),inputs=inputs,completed_prerequisites=proofs,expected_steps=STEPS,
        expected_frames=FRAMES,dt_s=DT,duration_s=DURATION,interval_s=INTERVAL,
        physical_accepted=False,half_window_accepted=False,full_cycle_accepted=False))
    print('PREPARED ONLY',PREP,flush=True)


def theory_parameters(config):
    root=ET.parse(config).getroot()
    val=lambda name:float(root.find('.//'+name).attrib['value'])
    radius=float(root.find('.//newvarcte[@radius]').attrib['radius']);dp=float(root.find('.//newvarcte[@Dp]').attrib['Dp'])
    meta=dict(e=val('ModulusE'),nu=val('PRvs'),khyd=val('HydraulicConductivity'))
    spec=importlib.util.spec_from_file_location('cryer_peak_theory',THEORY);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    cv,eta=module.material_values(meta)
    explicit=meta['khyd']*meta['e']*(1-meta['nu'])/((1+meta['nu'])*(1-2*meta['nu'])*val('PoreWaterRho')*9.81)
    assert val('PoreWaterRho')==module.RHO_W and module.G_REF==9.81 and abs(cv-explicit)<1e-15
    return dict(**meta,radius_m=radius,dp_m=dp,q_pa=val('HydroMechTopLoadQ0'),cv_m2_s=cv,eta=eta,
        gravity_for_theory_m_s2=9.81,series_roots=module.NROOTS),module.theory_function(meta['nu'])


def extend(row,a,initial,masks,meta,theory):
    x=a[['x','y','z']].to_numpy();x0=initial[['x','y','z']].to_numpy();r=np.linalg.norm(x,axis=1);r0=np.linalg.norm(x0,axis=1)
    unit=x0/np.where(r0>0,r0,1)[:,None];p=a.pressure.to_numpy()
    s=np.zeros((len(a),3,3));s[:,0,0]=a.sigma_xx;s[:,1,1]=a.sigma_yy;s[:,2,2]=a.sigma_zz
    s[:,0,1]=s[:,1,0]=a.sigma_xy;s[:,0,2]=s[:,2,0]=a.sigma_xz;s[:,1,2]=s[:,2,1]=a.sigma_yz
    comp=-np.trace(s,axis1=1,axis2=2)/3;radial=-np.einsum('ni,nij,nj->n',unit,s,unit)
    speed=np.linalg.norm(a[['vx','vy','vz']],axis=1);force=a.mass.to_numpy()[:,None]*a[['load_ax','load_ay','load_az']].to_numpy()
    tv=meta['cv_m2_s']*row['time_s']/meta['radius_m']**2
    row.update(tv=tv,theory_center_p_over_q=float(theory(tv)),center_p_over_q=row['center_pressure_mean_pa']/meta['q_pa'],
        native_initial_vs_quasistatic_theory_mismatch=bool(row['time_s']==0),
        total_mean_compression_pa=float((comp+p).mean()),effective_mean_compression_pa=float(comp.mean()))
    volume=4*np.pi*meta['radius_m']**3/3
    for label,mask in masks.items():
        row.update({label+'_count':int(mask.sum()),label+'_pressure_mean_pa':float(p[mask].mean()),
            label+'_pressure_max_pa':float(p[mask].max()),label+'_pressure_min_pa':float(p[mask].min()),
            label+'_effective_mean_compression_pa':float(comp[mask].mean()),label+'_total_mean_compression_pa':float((comp+p)[mask].mean()),
            label+'_total_radial_compression_pa':float((radial+p)[mask].mean()),
            label+'_total_tangent_compression_pa':float(((3*comp-radial)/2+p)[mask].mean()),
            label+'_radial_settlement_mean_mm':1000*float((r0-r)[mask].mean()),
            label+'_speed_rms_m_s':float(np.sqrt(np.mean(speed[mask]**2))),label+'_speed_max_m_s':float(speed[mask].max()),
            label+'_load_radial_force_N':float(-np.sum(force[mask]*unit[mask])),
            label+'_load_net_force_norm_N':float(np.linalg.norm(force[mask].sum(axis=0))),
            label+'_load_torque_norm_N_m':float(np.linalg.norm(np.cross(x[mask],force[mask]).sum(axis=0))),
            label+'_load_isotropic_work_over_3qV':float(-np.sum(force[mask]*x[mask])/(3*meta['q_pa']*volume))})
    return row


def notify(state):
    thread=identity();assert thread==state['thread']
    message=(f'User-authorized same-thread {TAG}: {state["status"]}. Read {STATE}, '
        f'tests/logs/{TAG}.run.json, tests/logs/{TAG}.check.json, tests/logs/{TAG}.completion.json, '
        f'tests/notes/{TAG}.md and queue_attempt/notification before claims. One fresh canonical GPU Release raw-confinement '
        'grad1 peak window only: dp.0025,k1e-5,eta.02,dt2^-21,end.0625s,131072steps,129binary native frames; noD/shifting. '
        'Verify owned exits/actualtimes/37173IDs/build-input-output hashes and original finite/elastic/no-exclusion/'
        'drainage/radius.0525/naturalstep/poredt/actualload guards. Only two shared actual time-step samples0 and2^-11 '
        'are compared with GPUfine coarse:34physical/identity columns0ULP; dterror_s is the sole interval-statistic '
        'exclusion and both original guards<=1e-14 remain. Do not claim an entire fine prefix or new half/full acceptance. '
        'Review complete startup history and declaredTv>=.005 Mandel window, native fixed18-ID center ball, pressure/'
        'totalstress/settlement/load against theory at actualtimes. Theoryt0=1 differs from nativep0=0. Oldfloat is not '
        'an isolated stress-precision control. If analysis failed,repair new analysis only; never rerun a completed solve. '
        'Report Chinese results proactively and continue the already authorized bounded damping/consistency review '
        'and final-admission decision; no automatic physical acceptance or formal run. On failure inspect exactreason/'
        'actualsealedtime/survivors, preserve data,no relaxedguards or duplicate solver. This one-shot queuesonce; '
        'never restart/rearm any old worker or send connectivity tests.')
    assert len(message)<2000
    exclusive(TESTS/'logs'/(TAG+'.queue_attempt.json'),dict(event=state['status'],utc=utc(),thread=thread,message=message,message_chars=len(message)))
    try:
        p=subprocess.run([str(CODEX),'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result=dict(status='queued' if p.returncode==0 else 'queue_failed_no_retry',exit_code=p.returncode,reply=(p.stdout+p.stderr).decode(errors='replace'))
    except Exception as error:result=dict(status='queue_exception_no_retry',error=repr(error))
    exclusive(TESTS/'logs'/(TAG+'.notification.json'),result)


def run():
    prepared=json.loads(PREP.read_text(encoding='utf8'));verify(prepared['inputs']);assert identity()==prepared['thread']
    for p in [RUN,STATE,CHECK,COMPLETE,SUMMARY,TESTS/'outputs'/TAG,TESTS/'logs'/(TAG+'.log'),TESTS/'logs'/(TAG+'.queue_attempt.json'),TESTS/'logs'/(TAG+'.notification.json')]:assert not p.exists(),p
    # Verify the already sealed gate receipts and their two shared native controls once, not entire legacy trees repeatedly.
    reference=TESTS/'outputs/cryer_gpu_grad_fine_r1_c'
    verify([e for e in prepared['completed_prerequisites'] if Path(e['path']).suffix=='.json' or Path(e['path']) in [reference/'data/Part_0000.bi4',reference/'data/Part_0004.bi4']])
    assert not inventory(),'An existing GPU solver is active; do not duplicate it'
    state=dict(status='running',stage='solver',thread=prepared['thread'],started_utc=utc(),owned_sequence_pid=os.getpid(),prepared_inputs=bound(PREP),program=prepared['program'],checked_frames=0,physical_accepted=False)
    def publish():
        temp=RUN.with_suffix('.tmp');write_json(temp,state);os.replace(temp,RUN)
        status=dict(status=state['status'],stage=state['stage'],owned_sequence_pid=os.getpid(),owned_wrapper_pid=state.get('owned_wrapper_pid'),checked_frames=state['checked_frames'],last_checked_time_s=state.get('actual_last_saved_time_s'),run_manifest=bound(RUN))
        temp=STATE.with_suffix('.tmp');write_json(temp,status);os.replace(temp,STATE)
    publish();child=None;rows=[];prefix=[];folder=TESTS/'outputs'/TAG;log=TESTS/'logs'/(TAG+'.log');started=time.perf_counter()
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',prepared['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid']=child.pid;publish();report=started
            while child.poll() is None:
                time.sleep(1)
                if time.perf_counter()-report>30:print('RUNNING',TAG,'wall_s',round(time.perf_counter()-started),flush=True);report=time.perf_counter()
        state.update(exit_code=child.returncode,owned_exited=True,solver_wall_seconds=time.perf_counter()-started)
        text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
        outputs=[bound(p) for p in folder.rglob('*') if p.is_file()]+[bound(log)]
        # Solver completion is sealed BEFORE native analysis; later analysis rejection never authorizes a rerun.
        exclusive(COMPLETE,dict(solver_finished=child.returncode==0 and 'Finished execution (code=0)' in text,
            exit_code=child.returncode,owned_exited=True,owned_wrapper_pid=child.pid,utc=utc(),prepared_inputs=bound(PREP),program=prepared['program'],outputs=outputs))
        state.update(sealed_completion=bound(COMPLETE),stage='offline_analysis');publish()
        assert child.returncode==0 and 'Finished execution (code=0)' in text
        assert 'SoilStressRateGradCorr="KernelGradient"' in text and 'DBC' in text
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==STEPS
        assert len(list((folder/'data').glob('Part_*.bi4')))==FRAMES
        state['actual_gpu']=re.search(r'Device default:\s*([^\r\n]+)',text)[1]
        state['compute_capability']=re.search(r'Compute capability:\s*([^\r\n]+)',text)[1]
        loop=re.search(r'Simulation Runtime\.*:\s*([\d.]+)\s*sec',text);state['observed_simulation_runtime_s']=float(loop[1]) if loop else None
        meta,theory=theory_parameters(prepared['config']['path']);state['theory_parameters']=meta
        initial=native(folder,0);r0=np.linalg.norm(initial[['x','y','z']],axis=1)
        center=r0<=meta['dp_m']+1e-12;assert center.sum()==18
        masks=dict(center=center,interior=r0<meta['radius_m']-2*float(initial.h.iloc[0]),outer_shell=r0>=meta['radius_m']-2*float(initial.h.iloc[0]))
        state['center_material_ids']=list(map(int,initial.id[center]));state['center_rule']='Fixed initial r<=dp+1e-12m; point-center theory compared with finite native ball, not identical observables.'
        for part in range(FRAMES):
            a=initial if part==0 else native(folder,part)
            assert float(a.time_s.iloc[0])==part*INTERVAL
            assert int(a.saved_step.iloc[0])==(part*1024-1 if part else 0)
            assert np.array_equal(a[['mass','h']],initial[['mass','h']]) and np.linalg.norm(a[['x','y','z']],axis=1).max()<=.0525
            row,issues=inspect(a,initial,part,DT,center);rows.append(extend(row,a,initial,masks,meta,theory));assert not issues,(part,issues)
            if part in [0,1]:prefix.append(dict(peak_part=part,fine_part=part*4,actual_time_s=part*INTERVAL,**compare_prefix(a,native(reference,part*4))))
            state.update(checked_frames=part+1,actual_last_saved_time_s=row['time_s']);publish()
        verify(prepared['inputs']);state['prefix']=prefix
        peak=lambda data:dict(part=int(data['part']),time_s=data['time_s'],tv=data['tv'],center_p_over_q=data['center_p_over_q'],theory_at_actual_time=data['theory_center_p_over_q'])
        window=[r for r in rows if r['tv']>=.005];assert window
        state.update(full_history_center_max=peak(max(rows,key=lambda r:r['center_p_over_q'])),
            full_history_particle_pressure_max_pa=max(r['pressure_max_pa'] for r in rows),
            mandel_window_rule='All saved samples Tv>=.005 through this bounded final time, no smoothing/filtering.',
            mandel_window_center_max=peak(max(window,key=lambda r:r['center_p_over_q'])),
            mandel_window_sampled_theory_max=peak(max(window,key=lambda r:r['theory_center_p_over_q'])),
            mandel_center_peak_at_window_end=max(window,key=lambda r:r['center_p_over_q'])['part']==rows[-1]['part'],
            last_saved_center_pressure_is_rising=rows[-1]['center_p_over_q']>rows[-2]['center_p_over_q'],
            status='peak_window_completed_pending_physical_review',stage='terminal')
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop=subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True);state['owned_stop_exit_code']=stop.returncode;child.wait(timeout=20)
        state.update(status='peak_window_rejected_or_interrupted',stage='terminal',error=repr(error),traceback=traceback.format_exc(),owned_exited=child is None or child.poll() is not None)
    finally:
        if rows:pd.DataFrame(rows).to_csv(SUMMARY,index=False,float_format='%.17g')
        state.update(finished_utc=utc(),wall_seconds=time.perf_counter()-started,artifacts=[bound(SUMMARY)] if SUMMARY.exists() else []);publish()
        exclusive(CHECK,dict(passed=state['status']=='peak_window_completed_pending_physical_review',status=state['status'],run_manifest=bound(RUN),
            sealed_completion=state.get('sealed_completion'),checked_frames=len(rows),prefix_samples=prefix,error=state.get('error'),physical_accepted=False,
            half_window_accepted=False,full_cycle_accepted=False,limits=['One bounded GPU peak window; no full-cycle or independent peak-window half-step acceptance.',
            'All startup samples retained; native initialp/q0 differs from quasistatic theoretical limit1.',
            'Theory is point-center; native observable is the fixed18-ID initial ball. No accuracy-percentage gate is imposed.',
            'Only two exact shared native time-step samples are checked, with dterror_s interval statistic separate; no other field exception.',
            'Old float histories are not isolated double-stress A/B controls. No D,shifting,damping,load or formal-input change.']))
        notify(state)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:run()
    else:prepare()
