"""New offline Cryer full-history/theory review; no solver or automatic physical acceptance."""
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[name]='1'
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize_scalar
import cryer_radial_consistency_r1 as theory

TESTS=Path(__file__).resolve().parents[1]; CASE=TESTS.parent; FIG=TESTS/'figures'; LOG=TESTS/'logs'
TAG='cryer_full_review_r1'; NATIVE='cryer_full_native_r1'; TD=2.**-7; Q=10000.; R=.05; DP=.0025
LEGACY_CV=.0027444522857366896
CONTROLS=['cryer_preload_peak_r1','cryer_preload_peak_half_r1','cryer_symc_gpu_peak_r1','cryer_symc_gpu_peak_half_r1']
LABELS=['raw_coarse','raw_half','symC_coarse','symC_half']; COLORS=['#1f77b4','#777777','#d95f02','#16853b']
ARTIFACTS={key:FIG/(TAG+'_'+key+ext) for key,ext in [(x,'.csv') for x in ['history','theory','peaks','profiles','radial_bins','modal_weights','spotchecks']]+[(x,'.png') for x in ['pressure','state','radial']]}
CHECK=LOG/(TAG+'.check.json')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bound(path):
    path=Path(path).resolve()
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha)


def verify(record):
    got=bound(record['path']); assert got['bytes']==record['bytes'] and got['sha256']==record['sha256'].lower(),record['path']


def modal_integrals(ref,cloud,h):
    """One geometry integration, using FIXED native initial-volume weights, not fitted volume."""
    radius=cloud.r0_m.to_numpy(); weight=cloud.weight0.to_numpy(); shell=radius>=R-2*h
    assert shell.any() and abs(weight.sum()-1)<1e-12 and np.all((radius>0)&(radius<=R+1e-12))
    shell_weight=weight[shell]/weight[shell].sum(); meanS=np.zeros(len(ref.xi)); shell_rU=meanS.copy()
    for begin in range(0,len(radius),2048):
        sl=slice(begin,begin+2048); rr=radius[sl]; z=rr[:,None]/R*ref.xi; sinc=np.sinc(z/np.pi)
        small=abs(z)<.02; phi=np.empty_like(z); zz=z[small]**2
        phi[small]=1/3-zz/30+zz**2/840-zz**3/45360+zz**4/3991680
        phi[~small]=(np.sin(z[~small])-z[~small]*np.cos(z[~small]))/z[~small]**3
        meanS += weight[sl]@(sinc-ref.sx)
        local=shell[sl]; sw=weight[sl][local]/weight[shell].sum()
        shell_rU += (sw*rr[local])@(phi[local]+(ref.beta*ref.mean-ref.sx)/3)
    return dict(meanS=meanS,shell_rU=shell_rU,shell=shell,weight=weight,shell_weight=shell_weight,
        shell_mean_r=float(shell_weight@radius[shell]))


def reference_history(ref,tau,integrals):
    tau=np.asarray(tau); positive=tau>0; w=ref.amplitude[:,None]*np.exp(-ref.decay[:,None]*tau[positive]); n=len(tau)
    fields={key:np.full(n,np.nan) for key in ['center18_pressure_pa','true_center_pressure_pa','pressure_mean_pa','total_mean_compression_pa','shell_inward_mean_mm']}
    for key,radius in [('center18_pressure_pa',.0025),('true_center_pressure_pa',0.)]:
        shape=np.sinc(ref.xi*radius/R/np.pi)-ref.sx; fields[key][positive]=Q*(shape@w)
    mean=Q*(integrals['meanS']@w); continuum_mean=Q*(ref.mean@w)
    fields['pressure_mean_pa'][positive]=mean
    fields['total_mean_compression_pa'][positive]=Q+(1-ref.K/ref.H)*mean-ref.K/ref.H*ref.beta*continuum_mean
    fields['shell_inward_mean_mm'][positive]=1000*Q/(3*ref.K)*integrals['shell_mean_r']-1000*Q/ref.H*(integrals['shell_rU']@w)
    zero=tau==0
    for key in ['center18_pressure_pa','true_center_pressure_pa','pressure_mean_pa']:fields[key][zero]=ref.B*Q
    fields['total_mean_compression_pa'][zero]=Q
    fields['shell_inward_mean_mm'][zero]=1000*Q/(3*(ref.K+ref.Mf))*integrals['shell_mean_r']
    return pd.DataFrame(dict(tau_s=tau,legacy_Tv=LEGACY_CV*tau/R**2,finite_theta=ref.cv*tau/R**2,**fields))


def paper_center(tau,ref):
    eta=ref.H/(2*ref.G); f=lambda x:(1-eta*x*x/2)*np.sin(x)-x*np.cos(x)
    xi=np.array([brentq(f,j*np.pi+1e-6,(j+1)*np.pi-1e-6,xtol=5e-15,rtol=1e-15) for j in range(360)])
    c=eta*(np.sin(xi)-xi)/(eta*xi*np.cos(xi)/2+(eta-1)*np.sin(xi)); t=np.asarray(tau); out=np.full(len(t),np.nan)
    out[t>0]=Q*(c@np.exp(-xi[:,None]**2*LEGACY_CV*t[t>0]/R**2)); out[t==0]=Q
    return out


def direct_spotchecks(ref,cloud,integrals,tau):
    rows=[]; r=cloud.r0_m.to_numpy(); weights=integrals['weight']; shell=integrals['shell']; sw=integrals['shell_weight']
    fast=reference_history(ref,tau,integrals)
    for i,t in enumerate(tau):
        f=ref.field(r,float(t)); direct=dict(pressure_mean_pa=float(weights@f['p']),
            total_mean_compression_pa=float(weights@(-(f['sr']+2*f['st']-3*f['p'])/3)),
            shell_inward_mean_mm=float(sw@(-1000*r[shell]*f['u_over_r'][shell])))
        for key,value in direct.items():
            difference=float(fast[key].iloc[i]-value); tolerance=1e-10 if key.endswith('_mm') else 1e-7
            assert abs(difference)<=tolerance,('Modal integration arithmetic',key,difference)
            rows.append(dict(tau_s=t,field=key,preintegrated=float(fast[key].iloc[i]),direct_native_geometry=value,difference=difference,arithmetic_tolerance=tolerance,physical_gate=False))
    return pd.DataFrame(rows)


def peak_metrics(history,ref):
    optimum=minimize_scalar(lambda t:-float(ref.field(np.array([.0025]),t)['p'][0]),bounds=(.02,.07),method='bounded',options={'xatol':1e-14})
    assert optimum.success; pt,pp=float(optimum.x),float(-optimum.fun); rows=[]
    for dataset,a in history.groupby('dataset',sort=False):
        a=a.reset_index(drop=True); window=a.legacy_Tv.ge(.005); i=int(a.loc[window,'center_pressure_mean_pa'].idxmax()); row=a.iloc[i]
        assert 0<i<len(a)-1,'Mandel sampled peak must be interior to retained coverage'
        j=int(a.center_pressure_mean_pa.idxmax()); errors=a.center_pressure_mean_pa-a.finite_radius_pressure_pa
        rows.append(dict(dataset=dataset,part=int(row.part),time_s=float(row.time_s),tau_s=float(row.tau_s),pressure_pa=float(row.center_pressure_mean_pa),
            theory_continuous_peak_tau_s=pt,theory_continuous_peak_pressure_pa=pp,amplitude_error_percent=100*(row.center_pressure_mean_pa/pp-1),time_error_percent=100*(row.tau_s/pt-1),
            left_saved_tau_s=float(a.tau_s.iloc[i-1]),right_saved_tau_s=float(a.tau_s.iloc[i+1]),left_spacing_s=float(row.tau_s-a.tau_s.iloc[i-1]),right_spacing_s=float(a.tau_s.iloc[i+1]-row.tau_s),
            theory_at_sampled_peak_pressure_pa=float(row.finite_radius_pressure_pa),error_at_sampled_peak_pa=float(errors.iloc[i]),mandel_rms_error_pa=float(np.sqrt(np.mean(errors[window]**2))),
            endpoint_tau_s=float(a.tau_s.iloc[-1]),endpoint_error_pa=float(errors.iloc[-1]),startup_inclusive_peak_part=int(a.part.iloc[j]),startup_inclusive_peak_pressure_pa=float(a.center_pressure_mean_pa.iloc[j]),
            theory_percentage_threshold_declared=False,physical_acceptance=False))
    return pd.DataFrame(rows)


def native_frame(reader,part,raw_records,inputs):
    directory=CASE/'CaseCryerProblem_PR_symc_nu030_out/data'; record=raw_records[str((directory/f'Part_{part:04d}.bi4').resolve()).lower()]
    verify(record); inputs.append(record); command=[reader['path'],str(directory),str(part)]
    raw=subprocess.check_output(command,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0))
    a=pd.read_csv(io.BytesIO(raw),dtype='<f8',float_precision='round_trip')
    assert len(a)==37173 and len(a.columns)==35 and np.array_equal(a.id,np.arange(8,37181)) and np.isfinite(a.to_numpy()).all()
    return a,dict(part=part,argv=command,exit_code=0,full_raw_rows_decoded=len(a))


def selected_profiles(check,cloud,history,ref,inputs,raw_records):
    server=history[history.dataset.eq('server')].reset_index(drop=True); window=server.legacy_Tv.ge(.005)
    parts=[int(server.iloc[np.argmin(abs(server.legacy_Tv.to_numpy()-tv))].part) for tv in [.01,.06,.2,.5,1.]]
    parts.append(int(server.loc[server.loc[window,'center_pressure_mean_pa'].idxmax(),'part'])); parts=sorted(set(parts)); assert len(parts)<=8
    reader=check['reader']; verify(reader); verify(check['reader_source']); inputs += [reader,check['reader_source']]
    initial=cloud.set_index('id'); plane=abs(cloud.y0)<=DP/2+1e-12; assert int(plane.sum())==1709
    rows=[]; commands=[]
    for part in parts:
        a,command=native_frame(reader,part,raw_records,inputs); assert np.array_equal(a.id,cloud.id)
        target=server[server.part.eq(part)].iloc[0]; assert a.time_s.eq(target.time_s).all() and a.saved_step.eq(target.saved_step).all()
        a=a.loc[plane.to_numpy()].copy(); b=initial.loc[a.id]; x0=b[['x0','y0','z0']].to_numpy(); r0=b.r0_m.to_numpy(); er0=x0/r0[:,None]; x=a[['x','y','z']].to_numpy(); er=x/np.linalg.norm(x,axis=1)[:,None]
        sigma=np.empty((len(a),3,3)); sigma[:,0,0],sigma[:,1,1],sigma[:,2,2]=a.sigma_xx,a.sigma_yy,a.sigma_zz
        sigma[:,0,1]=sigma[:,1,0]=a.sigma_xy; sigma[:,1,2]=sigma[:,2,1]=a.sigma_yz; sigma[:,0,2]=sigma[:,2,0]=a.sigma_xz
        rr=np.einsum('ni,nij,nj->n',er0,sigma,er0); tt=(np.trace(sigma,axis1=1,axis2=2)-rr)/2; rrnow=np.einsum('ni,nij,nj->n',er,sigma,er)
        f=ref.field(r0,float(target.tau_s)); displacement=np.sum((x-x0)*er0,axis=1)*1000
        frame=pd.DataFrame(dict(part=part,time_s=target.time_s,tau_s=target.tau_s,legacy_Tv=target.legacy_Tv,finite_theta=target.finite_theta,id=a.id.to_numpy(),r0_m=r0,r0_over_a=r0/R,
            pressure_pa=a.pressure.to_numpy(),radial_displacement_mm=displacement,inward_mm=-displacement,effective_sigma_rr_pa=rr,effective_sigma_tt_pa=tt,
            effective_sigma_rr_current_direction_pa=rrnow,total_sigma_rr_pa=rr-a.pressure.to_numpy(),total_sigma_tt_pa=tt-a.pressure.to_numpy(),
            theory_pressure_pa=f['p'],theory_radial_displacement_mm=r0*f['u_over_r']*1000,theory_effective_sigma_rr_pa=f['sr'],theory_effective_sigma_tt_pa=f['st'],theory_total_sigma_rr_pa=f['tr'],theory_total_sigma_tt_pa=f['tt']))
        rows.append(frame); commands.append(dict(command,plane_count=len(frame)))
    verify(reader); return pd.concat(rows,ignore_index=True),parts,commands


def plots(history,reference,peaks,profiles,conditional):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.25})
    def line(ax,column,x='tau_s',scale=1):
        for dataset,a in history.groupby('dataset',sort=False):
            color='black' if dataset=='server' else COLORS[LABELS.index(dataset)]
            ax.plot(a[x]*(1000 if x=='tau_s' else 1),a[column]/scale,color=color,lw=1.4 if dataset=='server' else .8,label=dataset)
    def finish(fig,axes,key,title):
        for ax in axes.flat:ax.legend(fontsize=7)
        fig.suptitle(title+'\n'+conditional,fontsize=11); fig.savefig(ARTIFACTS[key],dpi=180); plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(14,10),constrained_layout=True)
    for i,ax in enumerate(axes.flat):
        x='legacy_Tv' if i in [0,3] else 'tau_s'; line(ax,'center_pressure_mean_pa',x)
        xx=reference[x]*(1000 if x=='tau_s' else 1); ax.plot(xx,reference.center18_pressure_pa,'--',color='#b2182b',label='Finite Kw, fixed r0/a=.05')
        ax.plot(xx,reference.paper_incompressible_r0_pressure_pa,':',color='#6a51a3',label='Paper incompressible r=0, g=9.81')
        ax.set(xlabel='Legacy Tv (g=9.81 definition)' if x=='legacy_Tv' else 'tau=t-tD [ms]',ylabel='Fixed18 mean p [Pa]')
    axes[0,0].set_title('Complete saved history; old controls stop at their coverage')
    axes[0,1].set(title='Unfiltered loading/opening startup',xlim=(-8,6)); axes[1,0].set(title='Mandel window peak: no time/pressure fit',xlim=(20,70))
    peak=peaks[peaks.dataset.eq('server')].iloc[0]; axes[1,0].scatter([1000*peak.tau_s],[peak.pressure_pa],color='black',marker='o',s=30,label='Server sampled peak')
    axes[1,0].scatter([1000*peak.theory_continuous_peak_tau_s],[peak.theory_continuous_peak_pressure_pa],color='#b2182b',marker='*',s=60,label='Analytical continuous peak')
    axes[1,1].set(title='Late decay; symlog preserves nonpositive native p',xlim=(.2,1.01)); axes[1,1].set_yscale('symlog',linthresh=1)
    finish(fig,axes,'pressure','Cryer server dt=2^-20 versus retained dt=2^-21/22; no inherited half convergence')
    fig,axes=plt.subplots(2,3,figsize=(16,9),constrained_layout=True)
    for i,key in enumerate(['pressure_mean_pa','total_mean_compression_pa','shell_inward_mean_mm','speed_max_m_s','actual_radial_force_N','load_virial_over_3qVnative']):
        line(axes.flat[i],key,'legacy_Tv'); axes.flat[i].set(xlabel='Actual legacy Tv',ylabel=key)
        if key in reference:axes.flat[i].plot(reference.legacy_Tv,reference[key],'--',color='#b2182b',label='Theory: same initial native weights')
    axes.flat[3].set_yscale('symlog',linthresh=1e-6)
    finish(fig,axes,'state','Native volume-weighted state/load; continuum/native volume are not interchangeable')
    fig,axes=plt.subplots(2,2,figsize=(14,10),constrained_layout=True); colors=plt.get_cmap('turbo')(np.linspace(.05,.95,profiles.part.nunique()))
    for (part,a),color in zip(profiles.groupby('part',sort=True),colors):
        a=a.sort_values('r0_m'); label=f'part{part}: actual Tv={a.legacy_Tv.iloc[0]:.5g}, tau={a.tau_s.iloc[0]:.5g}s'
        for ax,key,scale in zip(axes.flat,['pressure_pa','radial_displacement_mm','effective_sigma_rr_pa','effective_sigma_tt_pa'],[1000,1,1000,1000]):
            ax.scatter(a.r0_over_a,a[key]/scale,s=3,alpha=.25,color=color,label=label); ax.plot(a.r0_over_a,a['theory_'+key]/scale,color=color,lw=.9)
    for ax,title in zip(axes.flat,['p [kPa]','u_r [mm], outward positive','Effective sigma_rr [kPa], tension positive','Effective sigma_tt [kPa], tension positive']):ax.set(xlabel='Fixed initial material r0/a',ylabel=title)
    finish(fig,axes,'radial','All1709 fixed initial material-plane points; lines=finite-Kw theory, no smoothing or clipping')


def review():
    assert not CHECK.exists() and not any(p.exists() for p in ARTIFACTS.values()),'Fresh offline artifacts only; preserve all prior files'
    priority=False
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True); kernel.GetCurrentProcess.restype=wintypes.HANDLE
        kernel.SetPriorityClass.argtypes=[wintypes.HANDLE,wintypes.DWORD]; kernel.SetPriorityClass.restype=wintypes.BOOL
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000):raise ctypes.WinError(ctypes.get_last_error())
        priority=True
    nativecheck=LOG/(NATIVE+'.check.json'); check=read(nativecheck)
    assert all(check[k] for k in ['passed','analysis_checks_passed','native_safety_passed','initial35_passed']) and not check['physical_acceptance'] and not check['full_half_validation']
    assert check['solver_program_attribution_proven'] is False; verify(check['inputs_manifest']); inputs=[bound(__file__),bound(TESTS/'notes'/(TAG+'.json')),bound(nativecheck),check['inputs_manifest']]
    artifacts={Path(r['path']).name:r for r in check['artifacts']}
    for record in artifacts.values():verify(record)
    inputs += list(artifacts.values())
    raw_records={str(Path(r['path']).resolve()).lower():r for r in read(check['inputs_manifest']['path'])['inputs']}
    def adopted(name):
        record=artifacts[NATIVE+'_'+name]; return pd.read_csv(record['path'],float_precision='round_trip')
    summary,cloud,center,bins=[adopted(n) for n in ['summary.csv','initial_cloud.csv','center.csv','radial.csv']]
    assert len(summary)==1065 and np.array_equal(summary.part,np.arange(1065)) and np.all(np.diff(summary.time_s)>0)
    assert len(cloud)==37173 and np.array_equal(cloud.id,np.arange(8,37181)) and len(center)==18*1065
    assert center.groupby('part').size().eq(18).all() and np.array_equal(center.groupby('part').time_s.first(),summary.time_s)
    mask=cloud.center18.astype(bool); assert mask.sum()==18 and np.max(abs(cloud.r0_m[mask]-.0025))<=1e-16
    assert all(set(a.id)==set(cloud.id[mask]) for _,a in center.groupby('part'))
    eq=artifacts[NATIVE+'.equilibrium.json']; verify(eq)
    equilibrium=bool(check['initial_equilibrium_diagnostics_passed']); conditional='Closed61-64 five diagnostics passed; quasi-static reference remains conditional' if equilibrium else 'CLOSED INITIAL EQUILIBRIUM FAILED: reference shown for diagnosis only, not realized-initial-value truth'
    verify(check['reader']); verify(check['reader_source']); initial,initial_command=native_frame(check['reader'],0,raw_records,inputs)
    assert initial.time_s.eq(0).all() and np.array_equal(initial[['x','y','z']],cloud[['x0','y0','z0']]) and np.array_equal(initial.mass,cloud.mass0) and np.array_equal(initial.rho,cloud.rho0)
    native_h=float(initial.h.iloc[0]); del initial
    ref=theory.Reference(); selftests=theory.selftest(ref); integrals=modal_integrals(ref,cloud,native_h); tau=summary.time_s.to_numpy()-TD
    reference=reference_history(ref,tau,integrals); reference['paper_incompressible_r0_pressure_pa']=paper_center(tau,ref)
    server=summary.copy(); server['dataset']='server'; server['tau_s']=tau; server['legacy_Tv']=LEGACY_CV*tau/R**2; server['finite_theta']=ref.cv*tau/R**2; server['finite_radius_pressure_pa']=reference.center18_pressure_pa
    history=[server]; oldreview=LOG/'cryer_symc_gpu_peak_half_review_r1.check.json'; old=read(oldreview); inputs.append(bound(oldreview)); assert old['analysis_checks_passed']
    oldrecords={str(Path(r['path']).resolve()).lower():r for r in old['sources']}
    for tag,label in zip(CONTROLS,LABELS):
        path=FIG/(tag+'_summary.csv'); record=oldrecords[str(path.resolve()).lower()]; verify(record); inputs.append(record); a=pd.read_csv(path,float_precision='round_trip'); assert len(a)==577
        a['dataset']=label; a['tau_s']=a.time_s-TD; a['legacy_Tv']=LEGACY_CV*a.tau_s/R**2; a['finite_theta']=ref.cv*a.tau_s/R**2
        a['finite_radius_pressure_pa']=reference_history(ref,a.tau_s.to_numpy(),integrals).center18_pressure_pa; history.append(a)
    history=pd.concat(history,ignore_index=True); peaks=peak_metrics(history,ref); profiles,parts,reader_commands=selected_profiles(check,cloud,history,ref,inputs,raw_records); reader_commands.insert(0,initial_command)
    peak_tau=float(peaks.loc[peaks.dataset.eq('server'),'tau_s'].iloc[0]); positive=reference.tau_s.gt(0)
    spot_times=np.unique([float(reference.loc[positive].iloc[0].tau_s),peak_tau,float(reference.tau_s.iloc[-1])]); spot=direct_spotchecks(ref,cloud,integrals,spot_times)
    modes=pd.DataFrame(dict(mode=np.arange(1,len(ref.xi)+1),xi=ref.xi,amplitude=ref.amplitude,continuum_mean_shape=ref.mean,native_mean_shape=integrals['meanS'],shell_rU=integrals['shell_rU']))
    tables=dict(history=history,theory=reference,peaks=peaks,profiles=profiles,radial_bins=bins[bins.part.isin(parts)],modal_weights=modes,spotchecks=spot)
    for key,a in tables.items():
        with ARTIFACTS[key].open('x',encoding='utf8',newline='') as stream:a.to_csv(stream,index=False,float_format='%.17g')
    plots(history,reference,peaks,profiles,conditional)
    sources=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(CASE.parent)})
    inputs += [bound(p) for p in sources]; unique={r['path']:r for r in inputs}
    for record in unique.values():verify(record)
    result=dict(passed=True,analysis_checks_passed=True,native_safety_adopted=True,initial_equilibrium_diagnostics_passed=equilibrium,reference_condition=conditional,reference_selftest=selftests,
        inputs=list(unique.values()),artifacts=[bound(p) for p in ARTIFACTS.values()],native_complete_hashes_adopted_from=check['inputs_manifest'],raw_full_catalog_rehashed=False,
        reader_commands=reader_commands,additional_native_frames_decoded=len(reader_commands),selected_profile_parts=parts,plane_points_per_frame=1709,initial_native_h_m=native_h,
        peaks=peaks.to_dict('records'),solver_program_attribution_proven=False,server_dt_s=2.**-20,retained_dt_s=[2.**-21,2.**-22],no_inherited_half_or_prefix=True,
        peak_neighbours='Adjacent observed save times/sampling resolution, NOT a confidence interval for the unknown continuous native peak.',
        reference_scope='Finite Kw,alpha1,small-strain quasistatic constant-q sphere after equilibrated closed ramp/hold; no fitted R,time,pressure or volume. Native initial geometry weights and shell r0 targets, continuum pbar separately retained.',
        limitations=['Inertia,damping,artificial viscosity,surface layers and particle quadrature are not exact continuum theory.','Global startup and declared legacyTv>=.005 Mandel peak remain separate; no native interpolation/filtering.','Paper incompressible point-center curve is separately labeled,not finite-Kw fixed18 truth.','Server executable SHA remains unproven; current local executable hash cannot repair historical attribution.','No predeclared physical peak-percentage threshold was found; no automatic physical acceptance.'],
        below_normal_priority_set=priority,blas_thread_environment={n:os.environ[n] for n in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']},physical_acceptance=False,full_cycle_acceptance=False,formal_acceptance=False,solver_started=False)
    with CHECK.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(check=str(CHECK),analysis_checks_passed=True,physical_acceptance=False)))


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); ref=theory.Reference(); outcome=theory.selftest(ref)
    radius=np.linspace(.0025,R,48); cloud=pd.DataFrame(dict(r0_m=radius,weight0=np.repeat(1/48,48)))
    integrals=modal_integrals(ref,cloud,.0045); spot=direct_spotchecks(ref,cloud,integrals,np.array([.001,.042,.9])); assert len(spot)==9
    t=np.array([-TD,0.,.042]); h=reference_history(ref,t,integrals); assert np.isnan(h.center18_pressure_pa.iloc[0]) and h.center18_pressure_pa.iloc[1]==ref.B*Q
    assert len(ARTIFACTS)==10 and max(abs(spot.difference))<1e-7
    return dict(passed=True,reference_selftest=outcome,files_written=False,real_native_data_read=False,child_programs_started=False,solver_started=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); mode=parser.add_mutually_exclusive_group(); mode.add_argument('--selftest',action='store_true'); mode.add_argument('--review',action='store_true'); args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.review:review()
    else:parser.print_help()
