"""Offline damping-only peak comparison; preserve all retained solver evidence."""
import importlib.util
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar
from cryer_grad_peak_r1 import TESTS,THEORY,bound,verify,theory_parameters

TAG='cryer_damp_peak_compare_r1'
FIG=TESTS/'figures'
BLUE='#1764a0';GOLD='#a46c16';INK='#343b42';PINK='#a64f79'


def main():
    paths={k:FIG/(TAG+'_'+k+ext) for k,ext in [
        ('pressure','.png'),('response','.png'),('history','.csv'),('theory','.csv')]}
    receipt=TESTS/'logs'/(TAG+'.check.json')
    assert not any(p.exists() for p in [receipt,*paths.values()]),'Never overwrite a retained comparison'
    review_path=TESTS/'logs/cryer_damp_peak_review_r1.check.json'
    review=json.loads(review_path.read_text(encoding='utf8'))
    assert review['evidence_consistency_passed'] and review['original_single_run_safety_passed']
    verify([dict(path=str(review_path.parent/e['path']),sha256=e['sha256']) for e in review['source_links']])
    sources=[__file__,review_path,THEORY,TESTS/'logs/cryer_radial_review_r1.check.json']
    histories=[];starts=[]
    for tag,coef,short in [('cryer_grad_peak_r1',.02,'cryer_gpu_grad_fine_r1'),
                           ('cryer_damp_peak_r1',.00004,'cryer_damp_short_r1')]:
        checkpath=TESTS/'logs'/(tag+'.check.json');check=json.loads(checkpath.read_text(encoding='utf8'))
        assert check['passed'];verify([check['run_manifest'],check['sealed_completion']])
        run=json.loads(open(check['run_manifest']['path'],encoding='utf8').read())
        verify(run['artifacts']+[run['prepared_inputs']]);sources += [checkpath,TESTS/'configs'/(tag+'_Def.xml')]
        hp=FIG/(tag+'_summary.csv');sp=FIG/(short+'_summary.csv');sources += [hp,sp]
        data=pd.read_csv(hp,float_precision='round_trip').sort_values('part');assert len(data)==129
        startup=pd.read_csv(sp,float_precision='round_trip');startup=startup[startup.run.eq(short+'_c')].copy()
        assert len(startup)==5
        data['damping_coefficient']=coef;startup['damping_coefficient']=coef
        histories.append(data);starts.append(startup)
    old,new=histories
    assert np.array_equal(old[['part','time_s','saved_step']],new[['part','time_s','saved_step']])
    assert new.time_s.iloc[-1]==.0625
    config=TESTS/'configs/cryer_damp_peak_r1_Def.xml';meta,point=theory_parameters(config)
    q=meta['q_pa'];cv=meta['cv_m2_s'];R=meta['radius_m'];eta=meta['eta']
    spec=importlib.util.spec_from_file_location('cryer_damping_theory',THEORY)
    theory=importlib.util.module_from_spec(spec);spec.loader.exec_module(theory)
    roots=np.asarray(theory.cryer_roots(eta))
    coeff=eta*(np.sin(roots)-roots)/(.5*eta*roots*np.cos(roots)+(eta-1)*np.sin(roots))
    radial_shape=(np.sinc(roots*.05/np.pi)-np.sinc(roots/np.pi))/(1-np.sinc(roots/np.pi))
    finite=lambda tv:1. if tv<=0 else float((coeff*radial_shape)@np.exp(-roots*roots*tv))
    dense_tv=np.linspace(0,float(new.tv.iloc[-1]),601)
    dense=pd.DataFrame(dict(tv=dense_tv,time_s=dense_tv*R**2/cv,
        ideal_point_theory_p_over_q=[point(t) for t in dense_tv],
        ideal_r005_theory_p_over_q=[finite(t) for t in dense_tv]))
    reference={}
    for label,fn in [('point',point),('r005',finite)]:
        fit=minimize_scalar(lambda t:-fn(t),bounds=(.005,float(new.tv.iloc[-1])),method='bounded',options={'xatol':1e-13})
        assert fit.success
        reference[label]=dict(peak_p_over_q=-float(fit.fun),peak_tv=float(fit.x),peak_time_s=float(fit.x)*R**2/cv)
    metrics={}
    for label,data in [('control',old),('weak',new)]:
        late=data[data.tv.ge(.005)];peak=late.loc[late.center_p_over_q.idxmax()]
        metrics[label]=dict(peak_p_over_q=float(peak.center_p_over_q),sampled_peak_time_s=float(peak.time_s),
            sampled_peak_tv=float(peak.tv),sampled_peak_part=int(peak.part),
            late_point_theory_rmse_pa=float(np.sqrt(np.mean((late.center_p_over_q-late.theory_center_p_over_q)**2)))*q,
            point_peak_deficit_pa=(reference['point']['peak_p_over_q']-float(peak.center_p_over_q))*q,
            point_peak_error_percent=100*(float(peak.center_p_over_q)/reference['point']['peak_p_over_q']-1),
            finite_radius_peak_deficit_pa=(reference['r005']['peak_p_over_q']-float(peak.center_p_over_q))*q,
            center_total_compression_at_peak_pa=float(peak.center_total_mean_compression_pa),
            center_effective_compression_at_peak_pa=float(peak.center_effective_mean_compression_pa),
            outer_radial_displacement_at_peak_mm=float(peak.outer_shell_radial_settlement_mean_mm))
    effectpath=FIG/'cryer_damp_peak_r1_effects.csv';effect=pd.read_csv(effectpath,float_precision='round_trip');sources.append(effectpath)
    assert np.array_equal(effect.time_s,new.time_s)
    combined=pd.concat(histories,ignore_index=True)
    columns=['damping_coefficient','part','time_s','tv','center_p_over_q','center_pressure_mean_pa',
        'center_total_mean_compression_pa','center_effective_mean_compression_pa','total_mean_compression_pa',
        'outer_shell_radial_settlement_mean_mm','center_radial_settlement_mean_mm',
        'center_speed_rms_m_s','outer_shell_speed_rms_m_s','affine_work_over_3qV',
        'radial_force_over_geometric_area_q','true_drained_count','drained_pressure_abs_max_pa']
    combined=combined[columns]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'lines.linewidth':1.6})
    fig,ax=plt.subplots(2,2,figsize=(12,7.6),constrained_layout=True)
    for data,start,coef,color,ls in zip(histories,starts,[.02,.00004],[BLUE,GOLD],['-','--']):
        label=f'xi={coef:g}'
        early=data[data.time_s.le(.002)]
        ax[0,0].plot(1000*early.time_s,early.center_p_over_q,color=color,ls=ls,label=label+' peak-window saves')
        ax[0,0].plot(1000*start.time_s,start.center_pressure_mean_pa/q,'o',ms=4,mfc='white',color=color,label=label+' dense short saves')
        ax[0,1].plot(data.tv,data.center_p_over_q,color=color,ls=ls,label=label+' fixed 18 IDs')
    ax[0,1].plot(dense.tv,dense.ideal_point_theory_p_over_q,ls='--',color=INK,label='Ideal step theory, r=0')
    ax[0,1].plot(dense.tv,dense.ideal_r005_theory_p_over_q,ls=':',color=INK,label='Ideal step theory, r/a=.05')
    delta=q*(new.center_p_over_q.to_numpy()-old.center_p_over_q.to_numpy())
    ax[1,0].plot(new.tv,delta,color=GOLD,label='Weak minus control: center pressure')
    ax[1,0].axhline(0,color=INK,ls=':',lw=1)
    ax[1,1].plot(new.tv,effect.pressure_rms_pa,color=PINK,label='Whole-cloud pressure difference RMS')
    ax[0,0].set(title='Saved startup: two retained sampling cadences',xlabel='Actual saved time (ms)',ylabel='Center p/q',xlim=(0,2),ylim=(0,1.46))
    ax[0,1].set(title='Late peak: zoomed pressure scale',xlabel=r'$T_v$',ylabel='Center p/q',xlim=(.005,float(new.tv.iloc[-1])),ylim=(1.04,1.265))
    ax[1,0].set(title='Damping-option change, not a half-step error',xlabel=r'$T_v$',ylabel='Center pressure change (Pa)')
    ax[1,1].set(title='Damping-option change, not a half-step gate',xlabel=r'$T_v$',ylabel='Pressure difference RMS (Pa)')
    for a in ax.flat:a.legend(fontsize=8,loc='best')
    fig.suptitle('Cryer damping comparison: identical raw load, geometry, dt and actual save times')
    fig.savefig(paths['pressure'],dpi=180);plt.close(fig)
    fig,ax=plt.subplots(2,2,figsize=(12,7.6),constrained_layout=True)
    for data,coef,color,ls in zip(histories,[.02,.00004],[BLUE,GOLD],['-','--']):
        label=f'xi={coef:g}'
        ax[0,0].plot(data.tv,data.center_total_mean_compression_pa/q,color=color,ls=ls,label=label)
        ax[0,1].plot(data.tv,data.outer_shell_radial_settlement_mean_mm,color=color,ls=ls,label=label)
        ax[1,0].plot(data.tv,data.center_speed_rms_m_s,color=color,ls=ls,label=label)
        ax[1,1].plot(data.tv,data.affine_work_over_3qV,color=color,ls=ls,label=label)
    ax[0,0].axhline(1,color=INK,ls=':',lw=1,label='q: load scale, not transient stress truth')
    ax[0,0].set(title='Fixed 18-ID total mean compressive stress',ylabel='Total compression / q')
    ax[0,1].set(title='Fixed outer-support-shell material displacement',ylabel='Mean inward radial displacement (mm)')
    ax[1,0].set(title='Fixed 18-ID RMS speed',ylabel='Speed (m/s)');ax[1,0].set_yscale('symlog',linthresh=1e-5)
    ax[1,1].set(title='Actual load isotropic virial, geometric-volume reference',ylabel=r'$-\sum m\,a_{load}\cdot x/(3qV_{sphere})$')
    for a in ax.flat:a.set(xlabel=r'$T_v$',xlim=(0,float(new.tv.iloc[-1])));a.legend(fontsize=8,loc='best')
    fig.suptitle('Cryer retained native response: different damping, not a new theory acceptance')
    fig.savefig(paths['response'],dpi=180);plt.close(fig)
    combined.to_csv(paths['history'],index=False,float_format='%.17g');dense.to_csv(paths['theory'],index=False,float_format='%.17g')
    metrics['weak_minus_control_sampled_peak_pa']=(metrics['weak']['peak_p_over_q']-metrics['control']['peak_p_over_q'])*q
    metrics['weak_minus_control_sampled_peak_time_s']=metrics['weak']['sampled_peak_time_s']-metrics['control']['sampled_peak_time_s']
    record=dict(analysis_complete=True,physical_accepted=False,half_window_accepted=False,full_cycle_accepted=False,
        inputs=[bound(p) for p in sources],theory_reference=reference,metrics=metrics,
        artifacts=[bound(p) for p in paths.values()],limitations=[
            'Parameter changes, not backend or half errors. Only startup has independent half evidence.',
            'Peaks are saved-grid peaks; cadence=.00048828125s. No sub-cadence peak-time equality claim.',
            'Dense short saves are separate retained same-dt data, not invented intermediate long-run states.',
            'Native initial p=0 differs from ideal quasi-static step limit1; all startup samples retained.',
            'Ideal incompressible-phase theory is not a finite-Kw dynamic truth; r/a=.05 reference shown separately.',
            'Center18 is not a disjoint partition from the interior. Outer shell is fixed initial material membership.',
            'Actual-load virial uses geometric volume, not a force renormalization or uniform transient-stress claim.',
            'No solver, production/formal edits, native time shifts, smoothing or acceptance-threshold changes.'])
    with receipt.open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2,allow_nan=False)
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
