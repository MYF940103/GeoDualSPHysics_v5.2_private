"""Extra closed-state and opening-response views; retained full-history plots unchanged."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cryer_start_r1 import TESTS,bound,native,utc
import cryer_preload_probe_r1 as probe
from cryer_preload_offline_r1 import floating_state

TAG='cryer_preload_figs_r1'
SOURCE=TESTS/'figures/cryer_preload_offline_r1_summary.csv'
REVIEW=TESTS/'logs/cryer_preload_review_r1.check.json'
CHECK=TESTS/'logs'/(TAG+'.check.json')
CLOSED=TESTS/'figures'/(TAG+'_closed.png')
OPENING=TESTS/'figures'/(TAG+'_opening.png')


def main():
    assert not CHECK.exists(),'Do not overwrite a completed chart receipt'
    assert CLOSED.exists()==OPENING.exists(),'Incomplete retained chart pair needs separate inspection'
    retained_pngs=CLOSED.exists()
    review=json.loads(REVIEW.read_text(encoding='utf8'))
    assert review['evidence_consistency_passed'] and review['declared_initial_equilibrium_diagnostics_passed']
    table=pd.read_csv(SOURCE,float_precision='round_trip');assert len(table)==69
    closed=table[table.part.between(61,64)];opening=table[table.part.between(64,68)]
    assert len(closed)==4 and len(opening)==5
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'lines.linewidth':1.5})
    blue,orange,ink='#2166ac','#d17b0f','#333333'
    fig,axes=plt.subplots(2,2,figsize=(11.5,7.5));t=closed.time_s.to_numpy()*1000
    panels=[(['pressure_target_rms_pa','total_stress_target_six_rms_pa'],['Pressure target RMS','Total-stress six-component RMS'],'Target errors','Error (Pa)',100.),
        (['speed_max_m_s'],['Maximum native speed'],'Residual motion','Speed (m/s)',1e-5),
        (['isotropic_vector_residual_rms_mm','shell_target_error_rms_mm'],['Fixed-origin isotropic-fit vector RMS','Shell per-initial-radius target RMS'],'Geometric errors','Error (mm)',1e-5)]
    for ax,(fields,labels,title,unit,limit) in zip(axes.flat,panels):
        for field,label,color in zip(fields,labels,[blue,orange]):ax.plot(t,closed[field],color=color,marker='o',label=label)
        ax.axhline(limit,color=ink,ls='--',label='Declared initial-state limit');ax.set_yscale('log')
        ax.set_title(title);ax.set_ylabel(unit)
    ax=axes[1,1]
    ax.plot(t,closed.pressure_mean_pa-probe.P_TARGET,color=blue,marker='o',label='Volume-mean pressure minus reference')
    ax.plot(t,closed.total_mean_compression_pa-probe.Q,color=orange,marker='s',label='Volume-mean total compression minus q')
    ax.axhline(0,color=ink,lw=1);ax.set_title('Mean signed deviations');ax.set_ylabel('Difference (Pa)')
    for ax in axes.flat:
        ax.set_xlabel('Actual saved time (ms)');ax.set_xticks(t);ax.set_xticklabels([f'{v:.3f}' for v in t])
        ax.legend(fontsize=8,loc='best')
    fig.suptitle('Cryer: last four closed saves, before the drainage operation',fontsize=14)
    fig.text(.5,.01,'Part64 at the source event is still pre-opening. Five unchanged criteria pass on all four saved states; not full physical acceptance.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.96))
    if not retained_pngs:fig.savefig(CLOSED,dpi=160)
    plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11.5,7.5));tau=opening.tau_from_drainage_s.to_numpy()*1000
    ax=axes[0,0]
    for field,label,color,style in [('center_pressure_mean_pa','Fixed 18-ID center mean',orange,'-'),('pressure_mean_pa','Whole-material volume mean',blue,'-'),('pressure_max_pa','Native maximum',ink,'--')]:
        ax.plot(tau,opening[field]/1000,color=color,ls=style,marker='o',label=label)
    ax.set_title('Pressure');ax.set_ylabel('Pore pressure (kPa)')
    for ax,field,title,unit in [(axes[0,1],'total_mean_compression_pa','Total stress','Volume-mean compression (kPa)'),
        (axes[1,0],'speed_max_m_s','Motion','Maximum speed (m/s)'),(axes[1,1],'true_surface_pressure_absmax_pa','Active drainage','True-surface absolute pressure maximum (kPa)')]:
        values=opening[field]/1000 if 'kPa' in unit else opening[field]
        ax.plot(tau,values,color=blue,marker='o',label='Actual native saves');ax.set_title(title);ax.set_ylabel(unit)
    for ax in axes.flat:
        ax.set_xlabel('Elapsed from drainage source event (ms)');ax.set_xticks(tau);ax.set_xticklabels([f'{v:.3f}' for v in tau])
        ax.legend(fontsize=8,loc='best')
    fig.suptitle('Cryer: saved opening response, not a Mandel-peak measurement',fontsize=14)
    fig.text(.5,.01,'The zero-time save is pre-opening; the first active save is +0.1220703125 ms. Lines only connect five saved samples, without smoothing.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.96))
    if not retained_pngs:fig.savefig(OPENING,dpi=160)
    plt.close(fig)
    a=floating_state(native(probe.FOLDER,64));r=np.linalg.norm(a[['x','y','z']].to_numpy(),axis=1);center=r<=.0025+1e-12
    compression=a.pressure.to_numpy()-a[probe.SIGMA[:3]].to_numpy().mean(axis=1)
    result=dict(utc=utc(),solver_executed=False,physical_accepted=False,
        source_csv=bound(SOURCE),independent_review=bound(REVIEW),script=bound(__file__),
        sealed_native_completion=bound(probe.COMPLETE),
        retained_existing_pngs_after_metadata_failure=retained_pngs,
        part64_center_total_compression_pa=float(compression[center].mean()),
        part64_all_node_mean_compression_min_pa=float(compression.min()),part64_all_node_mean_compression_max_pa=float(compression.max()),
        artifacts=[bound(CLOSED),bound(OPENING)],
        scope='Additional views of retained same CSV/native state. Full histories remain intact; no new threshold, theory or solver.')
    with CHECK.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(CHECK)


if __name__=='__main__':main()
