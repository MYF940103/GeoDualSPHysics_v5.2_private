"""Sequential native Cryer full-run summaries; no solver, GPU, queue or inherited full-half claim."""
import os
for _name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ[_name]='1'
import argparse
import ast
import csv
import ctypes
from ctypes import wintypes
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE,TESTS,REPO,READER,READER_SOURCE,utc

TAG='cryer_full_native_r1'; NAME='CaseCryerProblem_PR_symc_nu030'; FOLDER=CASE/(NAME+'_out'); CONFIG=FOLDER/(NAME+'.xml'); ROOTDEF=CASE/(NAME+'_Def.xml')
LOGS=TESTS/'logs'; FIGURES=TESTS/'figures'; CHECK,INPUTS,PROGRESS,INITIAL,EQUILIBRIUM=[LOGS/(TAG+s) for s in ['.check.json','.inputs.json','.progress.json','.initial35.json','.equilibrium.json']]
CSV={k:FIGURES/(TAG+'_'+k+'.csv') for k in ['summary','radial','center','initial_cloud']}; NOTE=TESTS/'notes'/(TAG+'.json')
SIGMA=['sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_yz','sigma_xz']; COLUMNS='time_s saved_step id x y z vx vy vz rho pressure sigma_xx sigma_yy sigma_zz sigma_xy sigma_yz sigma_xz kplastic load_ax load_ay load_az fstype normal_x normal_y normal_z load_available position_double stress_double mass dp h native_count nout has_dterror dterror_s'.split()


def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
    if isinstance(x,np.generic):return clean(x.item())
    return None if isinstance(x,float) and not np.isfinite(x) else x


def seal(path,value):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(clean(value),stream,indent=2,allow_nan=False)


def parameters(path):
    root=ET.parse(path).getroot(); get=lambda k:float((root.find('.//parameter[@key="'+k+'"]') if root.find('.//'+k) is None else root.find('.//'+k)).get('value'))
    E,nu=get('ModulusE'),get('PRvs'); K=E/(3*(1-2*nu)); G=E/(2*(1+nu)); H=K+4*G/3; Mf=get('PoreWaterBulkModulus')/get('Porosity'); g=root.find('.//gravity')
    gravity=np.sqrt(sum(float(np.float32(g.get(k)))**2 for k in 'xyz')); ghyd=float(gravity) if gravity else 9.80665
    return dict(dt=get('DtFixed'),end=get('TimeMax'),TD=get('HydroMechDrainageStartTime'),ramp=get('HydroMechTopLoadRampTime'),Q=get('HydroMechTopLoadQ0'),K=K,Mf=Mf,H=H,
        pore_factor=float(np.float32(get('PoreDtSafety')))*(float(np.float32(get('PoreWaterRho')))*ghyd/(float(np.float32(get('PoreWaterBulkModulus')))/float(np.float32(get('Porosity'))))),source_k=float(np.float32(get('HydraulicConductivity'))),
        legacy_cv=H*get('HydraulicConductivity')/(get('PoreWaterRho')*9.81),finite_cv=H*get('HydraulicConductivity')/(get('PoreWaterRho')*9.80665)/(1+H/Mf))


def schedule(dt=2.**-20,steps=963370):
    delta=Fraction(12753,14000000); tick=Fraction.from_float(dt); times=[]; grid=[]
    for part in range(1065):
        target=Fraction(part,8192) if part<=64 else Fraction(1,128)+(part-64)*delta; quotient=target/tick
        n=min(steps,(quotient.numerator+quotient.denominator-1)//quotient.denominator); grid.append(n); times.append(n*dt)
    return np.array(grid),np.array(times)


def native(folder,part):
    child=subprocess.Popen([str(READER),str(folder/'data'),str(part)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0))
    try:
        a=pd.read_csv(child.stdout,dtype='<f8',float_precision='round_trip'); code=child.wait(timeout=60); error=child.stderr.read().decode(errors='replace'); assert code==0,(part,code,error)
        assert list(a)==COLUMNS and len(a)==37173 and np.array_equal(a.id,np.arange(8,37181)); return a
    finally:
        child.stdout.close(); child.stderr.close()
        if child.poll() is None:child.terminate(); child.wait(timeout=15) # Only this read-only decoder, never any solver.


def context(a):
    x=a[['x','y','z']].to_numpy(); r=np.linalg.norm(x,axis=1); v=a.mass.to_numpy()/a.rho.to_numpy(); width=float(a.dp.iloc[0])/2; bins=np.floor((r+1e-13)/width).astype(int)
    center=r<=.0025+1e-12; assert center.sum()==18
    return dict(id=a.id.to_numpy(),x=x,r=r,v=v,w=v/v.sum(),fs=a.fstype.to_numpy(),constants=a[['mass','h','dp']].to_numpy(),center=center,
        shell=r>=.05-2*float(a.h.iloc[0]),bins=bins,nb=max(int(bins.max())+1,int(np.floor(.05/width))+1),width=width)


def inspect(a,c,part,p,grid,times):
    t=float(a.time_s.iloc[0]); saved=int(a.saved_step.iloc[0]); issues=[]
    def guard(ok,name):
        if not bool(ok):issues.append(name)
    guard(np.isfinite(a.to_numpy()).all() and a.rho.gt(0).all() and a.nout.eq(0).all() and a.kplastic.eq(0).all(),'finite_elastic_rho_no_excluded')
    guard(a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all() and a.native_count.eq(37181).all(),'double_state_load_telemetry_native_count')
    guard(np.array_equal(a[['mass','h','dp']],c['constants']),'fixed_mass_h_dp'); guard(a.time_s.eq(times[part]).all() and a.saved_step.eq(grid[part]-1 if part else 0).all(),'exact_dyadic_clock_and_ceil_schedule')
    if part:guard(a.has_dterror.eq(1).all() and a.dterror_s.max()<=1e-14,'original_signed_natural_dterror')
    x=a[['x','y','z']].to_numpy(); du=x-c['x']; r=np.linalg.norm(x,axis=1); unit=x/np.where(r>0,r,1)[:,None]; guard(r.max()<=.0525,'radius_limit')
    w=c['w']; mean=lambda v:float(w@np.asarray(v)); rms=lambda v:float(np.sqrt(w@(np.asarray(v)**2))); pressure=a.pressure.to_numpy(); sigma=a[SIGMA].to_numpy(); total=sigma.copy(); total[:,:3]-=pressure[:,None]
    speed=np.linalg.norm(a[['vx','vy','vz']],axis=1); force=a.mass.to_numpy()[:,None]*a[['load_ax','load_ay','load_az']].to_numpy(); torque=np.cross(x,force); radial=-np.sum(force*unit,axis=1); virial=-np.sum(force*x,axis=1)
    surface=a.fstype.isin([2,3]).to_numpy(); guard(surface.any(),'nonempty_true_surface'); drained=float(abs(pressure[surface]).max()) if surface.any() else None
    if t>p['TD']:guard(drained==0.,'post_TD_true_surface_pressure_zero')
    if part:guard(radial.sum()>0 and np.linalg.norm(force,axis=1).max()>0,'nonzero_inward_actual_load')
    dtw=p['pore_factor']*float(a.h.iloc[0])*float(a.h.iloc[0])/p['source_k']; guard(p['dt']<=dtw,'actual_config_native_h_pore_dt'); inward=(c['r']-r)*1000; shell=c['shell']; sw=c['v'][shell]/c['v'][shell].sum(); center=c['center']; cm=c['v'][center]/c['v'][center].sum()
    row=dict(part=part,time_s=t,saved_step=saved,natural_step=saved+1 if part else 0,scheduled_step=int(grid[part]),clock_error_s=t-times[part],tau_from_drainage_s=t-p['TD'],legacy_Tv=p['legacy_cv']*(t-p['TD'])/.05**2,finite_storage_theta=p['finite_cv']*(t-p['TD'])/.05**2,
        native_soil_count=len(a),native_safety_passed=not issues,safety_issues=';'.join(issues),drainage_active=t>p['TD'],true_surface_count=int(surface.sum()),changed_fstype_count=int(np.count_nonzero(a.fstype.to_numpy()!=c['fs'])),true_surface_pressure_absmax_pa=drained,
        center_fixed_material_count=int(center.sum()),center_pressure_mean_pa=float(pressure[center].mean()),center_pressure_volume_mean_pa=float(cm@pressure[center]),pressure_mean_pa=mean(pressure),pressure_rms_pa=rms(pressure),pressure_min_pa=float(pressure.min()),pressure_max_pa=float(pressure.max()),
        total_mean_compression_pa=-mean(total[:,:3].mean(axis=1)),effective_mean_compression_pa=-mean(sigma[:,:3].mean(axis=1)),rho_mean_kg_m3=mean(a.rho),rho_min_kg_m3=float(a.rho.min()),rho_max_kg_m3=float(a.rho.max()),
        shell_inward_mean_mm=float(sw@inward[shell]),shell_inward_rms_mm=float(np.sqrt(sw@(inward[shell]**2))),material_inward_mean_mm=mean(inward),speed_max_m_s=float(speed.max()),speed_volume_rms_m_s=rms(speed),
        actual_radial_force_N=float(radial.sum()),net_force_norm_N=float(np.linalg.norm(force.sum(axis=0))),torque_norm_N_m=float(np.linalg.norm(torque.sum(axis=0))),virial_N_m=float(virial.sum()),
        load_virial_over_3qVnative=float(virial.sum()/(3*p['Q']*(a.mass/a.rho).sum())),load_virial_over_3qVgeometric=float(virial.sum()/(3*p['Q']*(4*np.pi*.05**3/3))),
        saved_radius_min_m=float(r.min()),saved_radius_max_m=float(r.max()),native_current_volume_m3=float((a.mass/a.rho).sum()),native_reference_volume_m3=float(c['v'].sum()),dterror_s=float(a.dterror_s.max()),pore_diffusion_dt_s=dtw,fixed_to_pore_dt_ratio=p['dt']/dtw,source_clock_q_reference_pa=p['Q']*min(max(t-p['dt'],0)/p['ramp'],1))
    for i,key in enumerate(SIGMA):row['effective_'+key+'_mean_pa']=mean(sigma[:,i]); row['effective_'+key+'_rms_pa']=rms(sigma[:,i]); row['total_'+key+'_mean_pa']=mean(total[:,i]); row['total_'+key+'_rms_pa']=rms(total[:,i])
    for i,k in enumerate('xyz'):row['net_force_'+k+'_N']=float(force[:,i].sum()); row['torque_'+k+'_N_m']=float(torque[:,i].sum())
    for key in ['pressure_target_rms_pa','total_stress_target_six_rms_pa','isotropic_vector_residual_rms_mm','shell_target_error_rms_mm']:row[key]=None
    if part in [61,62,63,64]:
        target=p['Q']*p['Mf']/(p['K']+p['Mf']); strain=-p['Q']/(3*(p['K']+p['Mf'])); residual=total.copy(); residual[:,:3]+=p['Q']; beta=float(np.sum(c['v']*np.sum(c['x']*du,axis=1))/np.sum(c['v']*c['r']**2))
        row.update(pressure_target_rms_pa=rms(pressure-target),total_stress_target_six_rms_pa=float(np.sqrt(w@np.mean(residual**2,axis=1))),isotropic_vector_residual_rms_mm=1000*rms(np.linalg.norm(du-beta*c['x'],axis=1)),shell_target_error_rms_mm=float(np.sqrt(sw@((inward+strain*c['r']*1000)[shell]**2))))
    sr=np.sum(sigma[:,:3]*unit**2,axis=1)+2*(sigma[:,3]*unit[:,0]*unit[:,1]+sigma[:,4]*unit[:,1]*unit[:,2]+sigma[:,5]*unit[:,0]*unit[:,2]); st=(sigma[:,:3].sum(axis=1)-sr)/2
    return row,dict(pressure=pressure,inward=inward,radial_material_inward=-np.sum(du*c['x']/np.where(c['r']>0,c['r'],1)[:,None],axis=1)*1000,speed=speed,rho=a.rho.to_numpy(),effective_sigma_rr=sr,effective_sigma_tt=st,total_sigma_rr=sr-pressure,total_sigma_tt=st-pressure,force=force,torque=torque,radial=radial,virial=virial),issues


def radial_rows(c,values,row):
    b,n,v=c['bins'],c['nb'],c['v']; counts=np.bincount(b,minlength=n); volume=np.bincount(b,weights=v,minlength=n)
    def stats(x):
        mean=np.divide(np.bincount(b,weights=v*x,minlength=n),volume,out=np.full(n,np.nan),where=volume>0); square=np.divide(np.bincount(b,weights=v*x*x,minlength=n),volume,out=np.full(n,np.nan),where=volume>0)
        lo=np.full(n,np.inf); hi=np.full(n,-np.inf); np.minimum.at(lo,b,x); np.maximum.at(hi,b,x); lo[counts==0]=np.nan; hi[counts==0]=np.nan
        return dict(mean=mean,rms=np.sqrt(square),std=np.sqrt(np.maximum(square-mean*mean,0)),min=lo,max=hi)
    fields={name:(stats(values[name]),unit) for name,unit in [('pressure','pa'),('inward','mm'),('radial_material_inward','mm'),('speed','m_s'),('rho','kg_m3'),('effective_sigma_rr','pa'),('effective_sigma_tt','pa'),('total_sigma_rr','pa'),('total_sigma_tt','pa')]}; geometry=stats(c['r'])
    for j in range(n):
        r=dict(part=row['part'],time_s=row['time_s'],saved_step=row['saved_step'],natural_step=row['natural_step'],r0_bin=j,r0_bin_lo_m=j*c['width'],r0_bin_hi_m=(j+1)*c['width'],count=int(counts[j]),volume0_m3=float(volume[j]),initial_volume_weight_sum=float(volume[j]/v.sum()),r0_mean_m=geometry['mean'][j],r0_min_m=geometry['min'][j],r0_max_m=geometry['max'][j])
        for name,(d,unit) in fields.items():r.update({name+'_'+key+'_'+unit:value[j] for key,value in d.items()})
        mask=b==j; r.update(radial_force_sum_N=float(values['radial'][mask].sum()),load_force_norm_sum_N=float(np.linalg.norm(values['force'][mask],axis=1).sum()),virial_N_m=float(values['virial'][mask].sum()))
        for i,k in enumerate('xyz'):r['net_force_'+k+'_N']=float(values['force'][mask,i].sum()); r['torque_'+k+'_N_m']=float(values['torque'][mask,i].sum())
        yield r


def run():
    assert not any(path.exists() for path in [CHECK,INPUTS,PROGRESS,INITIAL,EQUILIBRIUM]+list(CSV.values())),'Fresh analysis only; never overwrite or restart old evidence'
    if os.name=='nt':
        kernel=ctypes.WinDLL('kernel32',use_last_error=True); kernel.GetCurrentProcess.restype=wintypes.HANDLE
        kernel.SetPriorityClass.argtypes=[wintypes.HANDLE,wintypes.DWORD]; kernel.SetPriorityClass.restype=wintypes.BOOL
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000):raise ctypes.WinError(ctypes.get_last_error())
    p=parameters(CONFIG); assert p['dt']==2.**-20 and p['TD']==2.**-7 and p['ramp']==2.**-8 and p['end']==963370*p['dt']; grid,times=schedule(p['dt']); started=time.perf_counter(); last=0.; records={}; stamps={}; state=dict(status='hashing_inputs',pid=os.getpid(),utc=utc(),hashed_files=0,checked_frames=0)
    def progress(force=False):
        nonlocal last
        if force or time.perf_counter()-last>=1:
            state.update(utc=utc(),wall_seconds=time.perf_counter()-started); temp=PROGRESS.with_suffix('.tmp'); seal(temp,state); os.replace(temp,PROGRESS); last=time.perf_counter()
    def freeze(path):
        path=Path(path).resolve(); key=str(path).lower()
        if key not in records:
            before=path.stat(); digest=hashlib.sha256(); state['current_input']=str(path)
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block); progress()
            after=path.stat(); assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns); stamps[key]=(after.st_size,after.st_mtime_ns); records[key]=dict(path=str(path),bytes=after.st_size,sha256=digest.hexdigest()); state['hashed_files']=len(records)
        return records[key]
    command="Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*'} | Select-Object Name,ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    active=subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).strip(); state['active_solvers_observed_only']=active; progress(True)
    old=[TESTS/'outputs'/name for name in ['cryer_preload_probe_r1','cryer_preload_half_r1']]; metadata=[Path(__file__),NOTE,CONFIG,ROOTDEF,READER,READER_SOURCE]+[TESTS/'support'/name for name in ['cryer_start_r1.py','cryer_preload_peak_r1.py','cryer_preload_probe_r1.py','cryer_radial_consistency_r1.py']]+[REPO/'src/source'/name for name in ['JSphGpu.cpp','JSphCpu.cpp']]
    for path in metadata+sorted(x for x in FOLDER.rglob('*') if x.is_file())+[x for folder in old for x in (folder/'data').iterdir() if x.name in ['Part_0000.bi4','Part_Head.ibi4','PartInfo.ibi4']]:freeze(path)
    text=(FOLDER/'Run.out').read_text(errors='replace'); assert 'Finished execution (code=0)' in text and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==963370
    assert sorted(int(x.stem.split('_')[-1]) for x in (FOLDER/'data').glob('Part_*.bi4'))==list(range(1065)); c=None; closed=[]; errors=[]; comparisons=[]; writers={}; streams={k:path.open('x',encoding='utf8',newline='') for k,path in CSV.items()}
    def emit(kind,rows):
        for row in rows:
            if kind not in writers:writers[kind]=csv.DictWriter(streams[kind],fieldnames=list(row)); writers[kind].writeheader()
            writers[kind].writerow(row)
    try:
        state['status']='reading_native_sequentially'; progress(True)
        for part in range(1065):
            a=native(FOLDER,part)
            if part==0:
                c=context(a); cloud=pd.DataFrame(dict(id=c['id'],x0=c['x'][:,0],y0=c['x'][:,1],z0=c['x'][:,2],r0_m=c['r'],mass0=a.mass,rho0=a.rho,volume0_m3=c['v'],weight0=c['w'],surface0=np.isin(c['fs'],[2,3]),fstype0=c['fs'],center18=c['center'],shell_bin=c['bins'])); cloud.to_csv(streams['initial_cloud'],index=False,float_format='%.17g'); del cloud
                for folder in old:
                    b=native(folder,0); bad=a.to_numpy(dtype='<f8').view('<u8')!=b.to_numpy(dtype='<f8').view('<u8'); comparisons.append(dict(folder=str(folder),part=0,all35_equal=not bad.any(),different_fields=[dict(field=key,count=int(bad[:,i].sum())) for i,key in enumerate(COLUMNS) if bad[:,i].any()],prefix_claimed=False)); del b,bad
            row,values,issues=inspect(a,c,part,p,grid,times); emit('summary',[row]); emit('radial',radial_rows(c,values,row)); selected=a.loc[c['center']].copy(); selected['part']=part; selected['r0_m']=c['r'][c['center']]; selected['inward_mm']=values['inward'][c['center']]; emit('center',selected.to_dict('records'))
            if part in [61,62,63,64]:closed.append(row)
            if issues:errors.append(dict(part=part,time_s=row['time_s'],guards=issues))
            state.update(checked_frames=part+1,last_part=part,actual_last_saved_time_s=row['time_s']); progress(); del a,values,selected
    except BaseException as failure:state.update(error=repr(failure),traceback=traceback.format_exc())
    finally:
        for stream in streams.values():stream.close()
    limits=dict(pressure_target_rms_pa=100.,total_stress_target_six_rms_pa=100.,speed_max_m_s=1e-5,isotropic_vector_residual_rms_mm=1e-5,shell_target_error_rms_mm=1e-5)
    eq=dict(limits=limits,samples=[dict(part=r['part'],time_s=r['time_s'],metrics={k:r[k] for k in limits},passed=all(r[k]<=v for k,v in limits.items())) for r in closed],post_drain_uniform_target_gate=False); eq['initial_equilibrium_diagnostics_passed']=len(closed)==4 and all(x['passed'] for x in eq['samples']); seal(EQUILIBRIUM,eq); seal(INITIAL,dict(samples=comparisons,initial35_passed=len(comparisons)==2 and all(x['all35_equal'] for x in comparisons),full_half_validation=False,prefix_claimed=False))
    unchanged=all((Path(r['path']).stat().st_size,Path(r['path']).stat().st_mtime_ns)==stamps[key] for key,r in records.items()); seal(INPUTS,dict(inputs=list(records.values()),parameters=p,root_Def_dt_comparison_only=parameters(ROOTDEF)['dt'],all_input_stats_unchanged=unchanged,hash_passes_per_file=1,solver_program_attribution_proven=False))
    state.update(status='completed' if state['checked_frames']==1065 and 'error' not in state else 'analysis_failed_no_solver_rerun',finished_utc=utc()); progress(True)
    from cryer_start_r1 import bound
    complete=state['status']=='completed' and unchanged; initial_ok=len(comparisons)==2 and all(x['all35_equal'] for x in comparisons); passed=complete and not errors and initial_ok
    seal(CHECK,dict(passed=passed,analysis_checks_passed=complete,native_safety_passed=complete and not errors,initial35_passed=initial_ok,initial_equilibrium_diagnostics_passed=eq['initial_equilibrium_diagnostics_passed'],checked_frames=state['checked_frames'],errors=errors,error=state.get('error'),reader=records[str(READER.resolve()).lower()],reader_program=records[str(READER.resolve()).lower()],reader_source=records[str(READER_SOURCE.resolve()).lower()],solver_program=None,solver_program_attribution_proven=False,center_fixed_material_ids=c['id'][c['center']].astype(int).tolist() if c is not None else [],inputs_manifest=bound(INPUTS),artifacts=[bound(x) for x in list(CSV.values())+[INITIAL,EQUILIBRIUM,PROGRESS]],full_half_validation=False,physical_acceptance=False,solver_started=False,gpu_used=False,queue_used=False))
    return dict(check=str(CHECK),passed=passed,checked_frames=state['checked_frames'])


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); n,t=schedule(); assert len(n)==1065 and len(COLUMNS)==35 and np.array_equal(n[:65],np.arange(65)*128) and n[-1]==963370 and np.all(np.diff(n)>0) and np.array_equal(t,n*2.**-20)
    for j in range(65,1065):assert Fraction(int(n[j]-1),1048576)<Fraction(1,128)+(j-64)*Fraction(12753,14000000)<=Fraction(int(n[j]),1048576)
    return dict(passed=True,files_written=False,native_reader_started=False,source_data_read=False,solver_started=False,hashing_executed=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(); modes.add_argument('--selftest',action='store_true'); modes.add_argument('--run',action='store_true'); args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.run:
        result=run(); print(json.dumps(result)); raise SystemExit(0 if result['passed'] else 1)
    else:parser.print_help()
