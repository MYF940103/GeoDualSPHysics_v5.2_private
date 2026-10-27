"""Offline Cryer peak figures and actual-time tables; never starts a solver."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar
from cryer_grad_peak_r1 import CASE,TESTS,native,bound,verify,theory_parameters

TAG='cryer_peak_compare_r1'
FIG=TESTS/'figures'
BLUE='#1764a0'; GOLD='#a46c16'; INK='#343b42'; PINK='#a64f79'; OLIVE='#6b7638'


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json')
    paths={name:FIG/(TAG+'_'+name+ext) for name,ext in [
        ('pressure','.png'),('response','.png'),('history','.csv'),
        ('startup','.csv'),('theory','.csv'),('old_snapshots','.csv')]}
    assert not receipt.exists(), 'Preserve the completed review'
    preserved=[bound(p) for p in paths.values() if p.exists()]
    checkpath=TESTS/'logs/cryer_grad_peak_r1.check.json'
    check=json.loads(checkpath.read_text(encoding='utf8'));assert check['passed']
    verify([check['run_manifest'],check['sealed_completion']])
    run=json.loads(open(check['run_manifest']['path'],encoding='utf8').read())
    verify(run['artifacts']+[run['prepared_inputs']])
    config=TESTS/'configs/cryer_grad_peak_r1_Def.xml'
    meta,theory=theory_parameters(config)
    q=meta['q_pa'];R=meta['radius_m'];cv=meta['cv_m2_s']
    historypath=TESTS/'figures/cryer_grad_peak_r1_summary.csv'
    finepath=TESTS/'figures/cryer_gpu_grad_fine_r1_summary.csv'
    data=pd.read_csv(historypath,float_precision='round_trip')
    startup=pd.read_csv(finepath,float_precision='round_trip')
    startup=startup[startup.run.eq('cryer_gpu_grad_fine_r1_c')].copy()
    startup['tv']=startup.time_s*cv/R**2
    startup['center_p_over_q']=startup.center_pressure_mean_pa/q
    assert len(data)==129 and len(startup)==5 and data.time_s.iloc[-1]==.0625
    assert np.array_equal(data.tv.to_numpy(),data.time_s.to_numpy()*cv/R**2)
    assert np.allclose([theory(t) for t in data.tv],data.theory_center_p_over_q,rtol=0,atol=3e-15)
    window=data[data.tv.ge(.005)]
    peak=window.loc[window.center_p_over_q.idxmax()]
    optimum=minimize_scalar(lambda t:-theory(t),bounds=(.005,float(data.tv.iloc[-1])),
        method='bounded',options={'xatol':1e-13})
    assert optimum.success
    theory_peak=-float(optimum.fun);theory_tv=float(optimum.x)
    initial=native(TESTS/'outputs/cryer_grad_peak_r1',0)
    ids=np.asarray(run['center_material_ids']);assert len(ids)==18
    oldrows=[];oldinputs=[]
    for part in [49,50]:
        old=native(CASE/'CaseCryerProblem_PR_out',part)
        assert np.array_equal(old.id,initial.id)
        mask=old.id.isin(ids)
        oldrows.append(dict(part=part,time_s=float(old.time_s.iloc[0]),
            saved_step=int(old.saved_step.iloc[0]),tv=float(old.time_s.iloc[0])*cv/R**2,
            center_count=int(mask.sum()),center_p_over_q=float(old.pressure[mask].mean()/q),
            role='Retained peak-neighbour snapshot, not an isolated precision/gradient control'))
        oldinputs.append(bound(CASE/'CaseCryerProblem_PR_out/data'/f'Part_{part:04d}.bi4'))
    old=pd.DataFrame(oldrows);oldpoint=old.loc[old.center_p_over_q.idxmax()]

    # A continuous quasistatic identity evaluated with a discrete pressure average.
    # This is a consistency clue, not a dynamic analytical acceptance criterion.
    state=native(TESTS/'outputs/cryer_grad_peak_r1',int(peak.part))
    center=state.id.isin(ids).to_numpy();weights=(state.mass/state.rho).to_numpy()
    p=state.pressure.to_numpy();effective=-(state.sigma_xx+state.sigma_yy+state.sigma_zz).to_numpy()/3
    total=effective+p;pc=float(p[center].mean());actual=float(total[center].mean())
    E=meta['e'];nu=meta['nu'];K=E/(3*(1-2*nu));G=E/(2*(1+nu));M=K+4*G/3
    pbar=float(np.average(p,weights=weights));predicted=q+4*G/(3*M)*(pc-pbar)
    x=state[['x','y','z']].to_numpy();x0=initial[['x','y','z']].to_numpy()
    r0=np.linalg.norm(x0,axis=1);surface=initial.fstype.isin([2,3]).to_numpy()
    assert surface.sum()==5153 and np.max(abs(r0[surface]-R))<1e-10
    ur=np.sum((x-x0)*x0/r0[:,None],axis=1)
    c_surface=-q+4*G*float(ur[surface].mean())/R
    cd=.02*np.sqrt(E/(state.rho.to_numpy()*state.h.to_numpy()**2))
    f_damp=-state.mass.to_numpy()[:,None]*cd[:,None]*state[['vx','vy','vz']].to_numpy()
    damping_virial=float(-np.sum(x*f_damp)/(3*(4*np.pi*R**3/3)))

    dense_tv=np.linspace(0,float(data.tv.iloc[-1]),601)
    dense=pd.DataFrame(dict(tv=dense_tv,time_s=dense_tv*R**2/cv,
        theory_center_p_over_q=[theory(t) for t in dense_tv]))
    for name,table in [('history',data),('startup',startup),('theory',dense),('old_snapshots',old)]:
        if paths[name].exists():
            assert paths[name].read_bytes()==table.to_csv(index=False,float_format='%.17g').encode('utf8')
        else:table.to_csv(paths[name],index=False,float_format='%.17g')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
        'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'lines.linewidth':1.6})
    fig,axes=plt.subplots(1,2,figsize=(12.4,4.6),constrained_layout=True)
    for ax in axes:
        ax.plot(dense.tv,dense.theory_center_p_over_q,'--',color=INK,label='Point-center theory')
        ax.plot(data.tv,data.center_p_over_q,color=BLUE,label='Current: fixed 18 material IDs')
        ax.set(xlabel=r'$T_v=C_vt/R^2$',ylabel=r'Center pore pressure $p/q$')
    axes[0].plot(startup.tv,startup.center_p_over_q,'o',ms=4,mfc='white',color=BLUE,
        label='Retained same-dt startup saves')
    axes[0].set(title='Saved startup and peak window',xlim=(0,float(data.tv.iloc[-1])),ylim=(0,1.46))
    axes[0].legend(fontsize=9,loc='lower right')
    axes[1].plot(oldpoint.tv,oldpoint.center_p_over_q,'s',ms=6,color=GOLD,label='Old snapshot: same 18 IDs')
    axes[1].plot(peak.tv,peak.center_p_over_q,'o',color=BLUE,ms=5)
    axes[1].plot(theory_tv,theory_peak,'x',color=INK,ms=7)
    axes[1].set(title='Late window: zoomed pressure scale',xlim=(.005,float(data.tv.iloc[-1])),ylim=(1.04,1.265))
    axes[1].legend(fontsize=9,loc='lower right')
    fig.suptitle('Cryer: raw confinement, stress-gradient correction, damping 0.02')
    if not paths['pressure'].exists():fig.savefig(paths['pressure'],dpi=180)
    plt.close(fig)

    fig,axes=plt.subplots(2,2,figsize=(12.4,7.8),constrained_layout=True)
    regions=[('center','Center (18)',BLUE),('interior','Interior (19527)',OLIVE),
        ('outer_shell','Outer support shell (17646)',PINK)]
    for region,label,color in regions:
        axes[0,0].plot(data.tv,data[region+'_pressure_mean_pa']/q,color=color,label=label)
        axes[0,1].plot(data.tv,data[region+'_total_mean_compression_pa']/q,color=color,label=label)
        axes[1,0].plot(data.tv,data[region+'_radial_settlement_mean_mm'],color=color,label=label)
        axes[1,1].plot(data.tv,data[region+'_speed_rms_m_s'],color=color,label=label)
    axes[0,1].plot(data.tv,data.total_mean_compression_pa/q,'--',color=INK,label='Whole cloud')
    axes[0,1].axhline(1,color=INK,ls=':',lw=1,label='Applied q: load reference only')
    axes[0,0].set(title='Material-region mean pressure',ylabel='Mean p/q')
    axes[0,1].set(title='Total mean compressive stress',ylabel='Mean total compression / q')
    axes[1,0].set(title='Mean inward radial material displacement',ylabel='Displacement (mm)')
    axes[1,1].set(title='Material-region RMS speed',ylabel='Speed (m/s)')
    axes[1,1].set_yscale('symlog',linthresh=1e-5)
    for ax in axes.flat:
        ax.set(xlabel=r'$T_v$',xlim=(0,float(data.tv.iloc[-1])))
        ax.legend(fontsize=8,loc='best')
    fig.suptitle('Cryer saved histories: pressure, stress, material motion')
    if not paths['response'].exists():fig.savefig(paths['response'],dpi=180)
    plt.close(fig)
    sources=[bound(p) for p in [__file__,config,checkpath,TESTS/'logs/cryer_grad_peak_review_r1.check.json',
        historypath,finepath,TESTS/'support/cryer_grad_peak_r1.py',CASE/'support/plot_cryer_poisson_sweep.py']]+oldinputs
    metrics=dict(current_peak_p_over_q=float(peak.center_p_over_q),current_peak_time_s=float(peak.time_s),
        current_peak_tv=float(peak.tv),continuous_theory_peak_p_over_q=theory_peak,
        continuous_theory_peak_tv=theory_tv,continuous_theory_peak_time_s=theory_tv*R**2/cv,
        current_peak_deficit_pa=(theory_peak-float(peak.center_p_over_q))*q,
        current_peak_relative_error_percent=100*(float(peak.center_p_over_q)/theory_peak-1),
        current_peak_time_lag_percent=100*(float(peak.tv)/theory_tv-1),
        late_window_rms_error_pa=float(np.sqrt(np.mean((window.center_p_over_q-window.theory_center_p_over_q)**2)))*q,
        retained_old_snapshot=oldpoint.to_dict(),new_minus_old_snapshot_peak_pa=(float(peak.center_p_over_q)-float(oldpoint.center_p_over_q))*q,
        quasistatic_consistency_at_current_peak=dict(pbar_native_volume_weighted_pa=pbar,
            center_total_compression_actual_pa=actual,center_total_compression_predicted_pa=predicted,
            residual_pa=actual-predicted,c_from_surface_pa=c_surface,c_from_pbar_pa=(-3*M*q+4*G*pbar)/(3*K),
            c_from_center_pa=M/K*(pc-actual)-pc,instantaneous_damping_virial_pa=damping_virial),
        same_dt_startup_sample_max_p_over_q=float(startup.center_p_over_q.max()))
    verify(preserved)
    with receipt.open('x',encoding='utf8') as stream:
        json.dump(dict(analysis_complete=True,physical_accepted=False,inputs=sources,metrics=metrics,
            preserved_preexisting_artifacts=preserved,
            artifacts=[bound(p) for p in paths.values()],limitations=[
                'Only a peak window; no new half-window or full-cycle acceptance.',
                'Old snapshots differ in stress precision, gradient option and actual dt, not an isolated A/B.',
                'Center theory is a point, native result a fixed 18-ID finite ball.',
                '129 coarse-cadence saves do not resolve all startup extrema; retained fine-startup saves are shown separately.',
                'Quasistatic stress identity neglects inertia/damping and uses discrete volume quadrature.',
                'Center is a subset of interior, not a third disjoint partition; interior plus outer shell covers all nodes.',
                'Applied q is not a uniform transient total-stress theory; no smoothing or time interpolation.']),stream,indent=2,allow_nan=False)
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
