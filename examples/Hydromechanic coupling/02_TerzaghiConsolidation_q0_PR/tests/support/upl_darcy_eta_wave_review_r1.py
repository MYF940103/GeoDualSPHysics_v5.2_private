"""Offline, unfitted continuous weak-wave comparison of the closed Darcy-Eta A/B."""
import csv,json,os
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
from scipy.linalg import expm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];BASE='upl_darcy_eta_wave_r1';TAG='upl_darcy_eta_wave_review_r1'
K=89478488.;G=134217728.;KW=67108864.;N0=.25;RHO=2048.;WATER=1000.;KH=float(np.float32(.0001));GAMMA=WATER*9.80665
LX=.125;AMPLITUDE=1./512.;M=K+4*G/3;B=KW/N0;D=B*KH/GAMMA;WAVE=2*np.pi/LX;CU=np.sqrt((M+B)/RHO)
PSTAR=B*AMPLITUDE/CU;USTAR=AMPLITUDE/(CU*WAVE);SSTAR=M*AMPLITUDE/CU;END=2.**-15;DT=2.**-24
FIELDS=('x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s','p_Pa','p0_Pa','J','theta_s_inv','sigma_xx_Pa','sigma_xy_Pa','sigma_xz_Pa','sigma_yy_Pa','sigma_yz_Pa','sigma_zz_Pa','kappa','FSType','FSNormal_x','FSNormal_y','FSNormal_z','PosDiv','loadAx_m_s2','loadAy_m_s2','loadAz_m_s2','native_rhop_kg_m3')
def need(ok,message):
    if not ok:raise RuntimeError(message)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def verify(entries):
    for e in entries:need(stat(e['path'])==e,'Closed input stat changed: '+e['path'])
def table(p):
    with Path(p).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(p,rows):
    with Path(p).open('x',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def save(p,value):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def load(kind,consumed):
    checkpath=T/'logs'/(BASE+'_'+kind+'.check.json');check=read(checkpath)
    need(check['passed'] and check['coupled_integrated'] and check['half_performed'] is False,'Closed actual coarse run required')
    verify([check['actual_run'],check['build'],check['completion'],*check['files']]);call=read(check['actual_run']['path']);build=read(check['build']['path'])
    need(build['passed'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['invocation_failure'] is None,'Actual owned build/run failure')
    need(call['program']==build['programs'][kind],'Run program differs from its closed build');verify([call['program'],build['private_source']])
    cpp=T/'support'/(BASE+'.cpp');source=[e for e in build['consumed'] if Path(e['path'])==cpp];need(len(source)==1,'Compiled helper author binding missing');verify(source)
    consumed += [stat(checkpath),check['actual_run'],check['build'],check['completion'],*check['files'],call['program'],build['private_source'],*source]
    folder=T/'outputs'/(BASE+'_'+kind);done=read(folder/'complete.json')
    need(done['passed'] and done['actual_ComputeStep_Sym'] and not done['smoke'] and done['Nx']==32 and done['native_ids']==512 and done['steps']==512 and done['samples']==257 and done['actual_end_s']==END,'Native completion/window changed')
    need(done['darcy_bare']==(kind=='candidate') and done['global_eta2']>0 and done['darcy_eta2']==(0. if kind=='candidate' else done['global_eta2']),'Denominator labels changed')
    p=folder/'physical.bin';header=np.fromfile(p,dtype='<u4',count=3);need(tuple(map(int,header))==(512,26,257),'Physical binary header changed')
    dtype=np.dtype([('time','<f8'),('state','<f8',(512,26))]);need(p.stat().st_size==12+257*dtype.itemsize,'Physical binary length changed');a=np.fromfile(p,dtype=dtype,offset=12)
    need(np.isfinite(a['time']).all() and np.isfinite(a['state']).all() and a['time'][0]==0 and a['time'][-1]==END and np.all(np.diff(a['time'])>0),'Invalid native actual clocks/fields')
    modes=table(folder/'modes.csv');policy=table(folder/'endpoint_policy.csv');need(len(modes)==257 and len(policy)==512,'Original mode/policy coverage changed')
    need(np.array_equal(a['time'],[float(x['time_s']) for x in modes]) and np.array_equal([int(x['step']) for x in modes],np.arange(257)*2),'Binary/mode actual clocks differ')
    q=lambda name:np.array([float(x[name]) for x in policy]);need(all(np.isfinite(q(name)).all() for name in policy[0]),'Nonfinite endpoint policy')
    need(np.array_equal(q('step'),np.arange(1,513)) and np.all(q('used_dt_s')==DT) and np.array_equal(q('time_s')[1::2],a['time'][1:]),'Actual512-step endpoint clock differs')
    # Retain the original single-run budgets; no new A/B physical-equivalence gate.
    need(np.all(q('used_dt_s')<=q('complete_bound_s')) and np.all(q('min_RH_margin')>0) and np.max(q('energy_ratio'))<=1.1,'Original endpoint guard failed')
    need(np.max(abs(q('cumulative_fixed_error_s')))<=1e-14,'Original signed FixedDt budget failed')
    need(done['max_energy_ratio']<=1.1 and done['max_coupled_CFL']<=.01 and done['max_Ddt_h2']<=.01 and done['max_discrete_pressure_RMS_Pa']<=1 and done['max_discrete_v_RMS_normalized']<=1e-3 and done['max_discrete_u_RMS_normalized']<=1e-3,'Original completion budget failed')
    return dict(kind=kind,a=a,modes=modes,policy=policy,done=done,elapsed_s=call['elapsed_s'])
def reference(times):
    # x=[u,v,sigma_xx,p]. Acceleration is eliminated algebraically in row4.
    # p'=-B*k*v-D*k^2*p+D*rhow*k*v', v'=k*(p-sigma_xx)/rho.
    physical=np.array([[0,1,0,0],[0,0,-WAVE/RHO,WAVE/RHO],[0,M*WAVE,0,0],[0,-B*WAVE,-D*WATER*WAVE**2/RHO,-D*WAVE**2*(1-WATER/RHO)]],dtype=float)
    scales=np.array([USTAR,AMPLITUDE,SSTAR,PSTAR]);scaled=physical*scales[None,:]/scales[:,None];initial=np.array([0,1,0,0.])
    values=np.array([(expm(scaled*float(t))@initial)*scales for t in times])
    # Small-strain plane-strain energy, divided by analytic initial kinetic energy.
    energy=(RHO*values[:,1]**2+values[:,2]**2/M+N0*values[:,3]**2/KW)/(RHO*AMPLITUDE**2)
    return values,energy,dict(matrix_physical=physical.tolist(),matrix_scaled=scaled.tolist(),scales=scales.tolist(),end_scaled_matrix_norm2=float(np.linalg.norm(scaled*float(times[-1]),2)),end_scaled_exponential_condition2=float(np.linalg.cond(expm(scaled*float(times[-1])))))
def main():
    check=T/'logs'/(TAG+'.review.json');png=T/'figures'/(TAG+'.png');csvpath=T/'figures'/(TAG+'.csv');fieldpath=T/'figures'/(TAG+'_fields.csv');note=T/'notes'/(TAG+'.md')
    need(not any(p.exists() for p in (check,png,csvpath,fieldpath,note)),'Fresh offline artifacts required');proof=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,SHA_scans=0);consumed=[stat(__file__)]
    try:
        runs=[load(k,consumed) for k in ('baseline','candidate')];base,candidate=runs
        need(np.array_equal(base['a']['time'],candidate['a']['time']),'A/B actual clocks differ');need(np.array_equal(base['a']['state'][0].view('<u8'),candidate['a']['state'][0].view('<u8')),'Initial26-field bits differ');need(base['done']['global_eta2']==candidate['done']['global_eta2'],'Global Eta2 changed')
        initial=base['a']['state'][0];ix=initial[:,0]/(LX/32)-.5;iz=initial[:,2]/(LX/32)-.5
        need(np.all(initial[:,1]==0) and np.array_equal(ix,np.rint(ix)) and np.array_equal(iz,np.rint(iz)) and np.all((ix>=0)&(ix<32)&(iz>=0)&(iz<16)) and len(np.unique(ix+32*iz))==512,'Initial ordered-ID lattice is incomplete')
        time=base['a']['time'];ref,energy_ref,conditioning=reference(time);sn=np.sin(WAVE*initial[:,0]);cs=np.cos(WAVE*initial[:,0]);rows=[];fields=[];summary={};series={}
        for run in runs:
            a=run['a']['state'];kind=run['kind'];u=a[:,:,:3]-initial[None,:,:3];vel=a[:,:,3:6]
            errors=dict(p_RMS_Pa=np.sqrt(np.mean((a[:,:,6]-ref[:,3,None]*cs)**2,axis=1)),u_XYZ_RMS_m=np.sqrt(np.mean((u[:,:,0]-ref[:,0,None]*sn)**2+u[:,:,1]**2+u[:,:,2]**2,axis=1)),v_XYZ_RMS_m_s=np.sqrt(np.mean((vel[:,:,0]-ref[:,1,None]*sn)**2+vel[:,:,1]**2+vel[:,:,2]**2,axis=1)),sigma_xx_RMS_Pa=np.sqrt(np.mean((a[:,:,10]-ref[:,2,None]*cs)**2,axis=1)))
            modal=np.column_stack((2*np.mean(u[:,:,0]*sn,axis=1),2*np.mean(vel[:,:,0]*sn,axis=1),2*np.mean(a[:,:,10]*cs,axis=1),2*np.mean(a[:,:,6]*cs,axis=1)));cpp=np.array([[float(x[k]) for k in ('u_continuum','v_continuum','sigma_continuum','p_continuum')] for x in run['modes']]);actual_energy=np.array([float(x['energy_ratio']) for x in run['modes']]);signed=np.array([float(x['cumulative_fixed_error_s']) for x in run['policy']]);series[kind]=dict(modal=modal,errors=errors,energy=actual_energy)
            for j,t in enumerate(time):
                row=dict(kind=kind,part=j,actual_time_s=float(t),native_IDs=512,continuum_u_m=float(ref[j,0]),continuum_v_m_s=float(ref[j,1]),continuum_sigma_xx_Pa=float(ref[j,2]),continuum_p_Pa=float(ref[j,3]),actual_u_sine_m=float(modal[j,0]),actual_v_sine_m_s=float(modal[j,1]),actual_sigma_xx_cosine_Pa=float(modal[j,2]),actual_p_cosine_Pa=float(modal[j,3]),cpp_continuum_u_m=float(cpp[j,0]),cpp_continuum_v_m_s=float(cpp[j,1]),cpp_continuum_sigma_xx_Pa=float(cpp[j,2]),cpp_continuum_p_Pa=float(cpp[j,3]),**{k:float(v[j]) for k,v in errors.items()},p_RMS_over_Pstar=float(errors['p_RMS_Pa'][j]/PSTAR),u_RMS_over_Ustar=float(errors['u_XYZ_RMS_m'][j]/USTAR),v_RMS_over_A=float(errors['v_XYZ_RMS_m_s'][j]/AMPLITUDE),sigma_xx_RMS_over_Sstar=float(errors['sigma_xx_RMS_Pa'][j]/SSTAR),actual_energy_ratio=float(actual_energy[j]),continuous_linear_energy_ratio=float(energy_ref[j]),signed_fixed_error_s=None if not j else float(signed[2*j-1]));rows.append(row)
            cpp_error=np.max(abs(cpp-ref),axis=0);summary[kind]=dict(actual_Debug_elapsed_s=run['elapsed_s'],completion=run['done'],maximum_field_errors={k:float(np.max(v)) for k,v in errors.items()},maximum_p_RMS_over_Pstar=float(np.max(errors['p_RMS_Pa'])/PSTAR),maximum_u_RMS_over_Ustar=float(np.max(errors['u_XYZ_RMS_m'])/USTAR),maximum_v_RMS_over_A=float(np.max(errors['v_XYZ_RMS_m_s'])/AMPLITUDE),maximum_sigma_xx_RMS_over_Sstar=float(np.max(errors['sigma_xx_RMS_Pa'])/SSTAR),endpoint_modal_u_v_sigma_p=modal[-1].tolist(),endpoint_pressure_amplitude_relative_error=float(abs(modal[-1,3]-ref[-1,3])/abs(ref[-1,3])),cpp_continuum_vs_expm_max_abs=dict(zip(('u_m','v_m_s','sigma_xx_Pa','p_Pa'),map(float,cpp_error))),cpp_pressure_field_error_vs_independent_max_abs=float(np.max(abs(np.array([float(x['p_continuum_RMS_over_Pstar']) for x in run['modes']])-errors['p_RMS_Pa']/PSTAR))),signed_fixed_error_min_s=float(np.min(signed)),signed_fixed_error_max_s=float(np.max(signed)),original_single_run_guards_passed=True)
        for j,t in enumerate(time):
            delta=candidate['a']['state'][j]-base['a']['state'][j];different=candidate['a']['state'][j].view('<u8')!=base['a']['state'][j].view('<u8')
            for col,name in enumerate(FIELDS):fields.append(dict(part=j,actual_time_s=float(t),field=name,A_B_difference_is_descriptive=True,RMS=float(np.sqrt(np.mean(delta[:,col]**2))),max_abs=float(np.max(abs(delta[:,col]))),different_double_scalar_bitpatterns=int(np.count_nonzero(different[:,col]))))
        write(csvpath,rows);write(fieldpath,fields);old=summary['baseline']['maximum_field_errors']['p_RMS_Pa'];new=summary['candidate']['maximum_field_errors']['p_RMS_Pa'];change=100*(new/old-1)
        verdict='Eta0 candidate pressure error is higher' if summary['candidate']['endpoint_pressure_amplitude_relative_error']>summary['baseline']['endpoint_pressure_amplitude_relative_error'] else 'Eta0 candidate pressure error did not increase'
        fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained');us=time*1e6
        axes[0,0].plot(us,ref[:,3]/PSTAR,'k--',label='unfitted continuous expm');axes[0,1].plot(us,ref[:,0]/USTAR,'k--',label='unfitted continuous expm');axes[1,1].plot(us,energy_ref,'k--',label='continuous linear energy')
        for kind in ('baseline','candidate'):
            q=series[kind];label='baseline (r2+Eta2)' if kind=='baseline' else 'candidate (r2)';axes[0,0].plot(us,q['modal'][:,3]/PSTAR,label=label);axes[0,1].plot(us,q['modal'][:,0]/USTAR,label=label);axes[1,0].plot(us,q['errors']['p_RMS_Pa'],label=label);axes[1,1].plot(us,q['energy'],label=label)
        for ax,title,ylabel in zip(axes.flat,('Pressure cosine mode','Displacement sine mode','All512-ID pressure field error','Energy'),('p cosine / Pstar','u sine / Ustar','pressure RMS (Pa)','E / initial E')):ax.set(title=title,xlabel='actual time (microseconds)',ylabel=ylabel);ax.grid(alpha=.25);ax.legend(fontsize=8)
        fig.suptitle('Darcy denominator A/B | independent continuous4x4 exponential\n'+verdict+'; production unchanged',fontsize=11);fig.savefig(png,dpi=160);plt.close(fig)
        text=f'''# Closed Darcy-Eta weak-wave review\n\nAll257 actual times and all512 ordered IDs are compared; initial26-field bits match. The independent reference uses scipy.linalg.expm on a dimensionlessly scaled4x4 continuous system with the declared material constants, k=2pi/.125 and initial[0,1/512,0,0]. No discrete ell/Kr/Ks, fitted amplitude, clock substitution or parameter fit enters it. Pstar={PSTAR:.17g}Pa, Ustar={USTAR:.17g}m, Sstar={SSTAR:.17g}Pa. Initial velocity float quantization and the nonlinear current-J/current-C solver remain real differences from this linear continuous reference.\n\nMaximum all-ID pressure RMS error: baseline{old:.12g}Pa, candidate{new:.12g}Pa; candidate change{change:+.8g}%. Endpoint pressure-amplitude relative errors: {summary['baseline']['endpoint_pressure_amplitude_relative_error']:.12g}/{summary['candidate']['endpoint_pressure_amplitude_relative_error']:.12g}. This verdict concerns pressure only: sigma_xx can improve slightly while other fields worsen; no uniform coupled accuracy gain is claimed. Individual p/u/v/sigma errors and CPP-continuum/expm differences are retained in the JSON/CSV whether candidate improves or worsens. Small errors against each helper's own discrete symbol are not continuous accuracy.\n\nAll original single-run finite/ledger/periodic/energy1.1/step/CFL/diffusion/discrete-reference and absolute signed FixedDt1e-14s guards remain in force. Signed FixedDt is not a temporal-reference error metric. A/B field differences are descriptive; there is no5Pa equivalence threshold. Actual Debug elapsed times are not a speed benchmark. Production denominator is retained by root decision; this analysis makes no production edit.\n\nScope: XZ-periodic regular small-strain constant-k Wendland only, no FS/wall/variable-k/strong-disorder or collapse admission. No solver/decoder/build is invoked. PNG visual QA remains pending until inspected separately.\n'''
        with note.open('x',encoding='utf-8') as f:f.write(text)
        verify(consumed);proof.update(passed=True,summary=summary,reference=dict(K=K,G=G,Kw=KW,n0=N0,rho0=RHO,rhow=WATER,hydraulic_k_float32=KH,gamma=GAMMA,M=M,B=B,D=D,k=WAVE,Lx=LX,A=AMPLITUDE,Pstar=PSTAR,Ustar=USTAR,Sstar=SSTAR,initial_u_v_sigma_p=[0,AMPLITUDE,0,0],endpoint=ref[-1].tolist(),conditioning=conditioning,unfitted=True),samples=257,native_IDs=512,initial26_different_bitpatterns=0,maximum_actual_time_gap_s=0.,pressure_continuum_RMS_change_percent=change,production_denominator_retained=True,no_new_A_B_physical_gate=True,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(png),stat(csvpath),stat(fieldpath),stat(note)])
    except Exception as e:proof['first_failure']=str(e)
    save(check,proof);print(json.dumps({k:v for k,v in proof.items() if k not in ('consumed','files')},indent=2));need(proof['passed'],'Offline review failed; preserve partial evidence')
if __name__=='__main__':main()
