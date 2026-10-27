"""Plot retained preload coarse/half CSVs only; no solver or notifier."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cryer_start_r1 import TESTS,bound,utc
from cryer_gpu_base_r1 import verify

TAG='cryer_preload_half_compare_r1'
PNG=TESTS/'figures'/(TAG+'.png');CHECK=TESTS/'logs'/(TAG+'.check.json')


def main():
    assert not PNG.exists() and not CHECK.exists(),'Never overwrite retained plots'
    paths=[TESTS/'figures'/n for n in ['cryer_preload_offline_r1_summary.csv','cryer_preload_half_r1_summary.csv','cryer_preload_half_r1_half.csv']]
    run_path=TESTS/'logs/cryer_preload_half_r1.run.json';run=json.loads(run_path.read_text(encoding='utf8'))
    assert run['status']=='preload_half_passed_pending_causal_review';verify(run['artifacts'])
    c,h,p=[pd.read_csv(path,float_precision='round_trip') for path in paths]
    assert len(c)==len(h)==len(p)==69 and np.array_equal(c.time_s,h.time_s) and np.array_equal(p.time_s,c.time_s)
    assert p.screen_passed.all() and p.pressure_rms_pa.le(5).all() and p.material_displacement_max_mm.le(.005).all()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'lines.linewidth':1.6})
    blue,orange,ink='#2166ac','#d17b0f','#333333';td=2.**-7
    fig,axes=plt.subplots(2,2,figsize=(12,8));t=c.time_s.to_numpy()*1000
    ax=axes[0,0]
    for a,label,color,style in [(c,'Coarse: dt=2^-21 s',blue,'-'),(h,'Half: dt=2^-22 s',orange,'--')]:
        ax.plot(t,a.center_pressure_mean_pa/1000,color=color,ls=style,label=label)
    ax.axvline(td*1000,color=ink,ls=':',lw=1,label='Drainage source event')
    ax.set_title('Fixed 18-ID material-center pressure');ax.set_ylabel('Pore pressure (kPa)');ax.set_xlabel('Actual saved time (ms)')
    ax=axes[0,1];opening=c.part.ge(64);tau=(c.time_s[opening].to_numpy()-td)*1000
    ax.plot(tau,c.center_pressure_mean_pa[opening]/1000,color=blue,marker='o',label='Coarse')
    ax.plot(tau,h.center_pressure_mean_pa[opening]/1000,color=orange,ls='--',marker='x',label='Half')
    ax.set_xticks(tau);ax.set_xticklabels([f'{v:.3f}' for v in tau])
    ax.set_title('Opening response: five actual saves');ax.set_ylabel('Pore pressure (kPa)');ax.set_xlabel('Elapsed from drainage source event (ms)')
    ax=axes[1,0]
    ax.plot(t,p.pressure_rms_pa,color=blue,label='All-material field pressure RMS difference')
    ax.axhline(5,color=ink,ls='--',label='Original 5-Pa half-step limit');ax.set_ylim(0,5.3)
    ax.set_title('Pressure half-step screen');ax.set_ylabel('RMS difference (Pa)');ax.set_xlabel('Actual matched time (ms)')
    ax=axes[1,1];positive=p.material_displacement_max_mm.gt(0)
    ax.plot(t[positive],p.material_displacement_max_mm[positive],color=blue,label='Maximum native material displacement difference')
    ax.axhline(.005,color=ink,ls='--',label='Original .005-mm half-step limit');ax.set_yscale('log')
    ax.set_title('Displacement half-step screen (log)');ax.set_ylabel('Maximum difference (mm)');ax.set_xlabel('Actual matched time (ms)')
    for ax in axes.flat:ax.legend(fontsize=8,loc='best')
    fig.suptitle('Cryer preload and opening: 69 actual-matched coarse/half saves',fontsize=14)
    fig.text(.5,.012,'Both initial differences are exactly zero (off the displacement log scale). Event-time save is pre-opening. No smoothing or theory-fit time shift.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(PNG,dpi=160);plt.close(fig)
    result=dict(utc=utc(),solver_executed=False,physical_accepted=False,peak_accepted=False,full_cycle_accepted=False,
        source_csvs=[bound(path) for path in paths],source_run=bound(run_path),script=bound(__file__),artifact=bound(PNG),
        paired_samples=69,max_half_pressure_rms_pa=float(p.pressure_rms_pa.max()),
        max_half_displacement_mm=float(p.material_displacement_max_mm.max()),
        max_half_total_stress_rms_pa=float(p.total_stress_six_component_rms_pa.max()),
        pressure_max_part=int(p.loc[p.pressure_rms_pa.idxmax(),'part']),
        note='Short half agreement is not theory accuracy; the opening transient remains in both converged trajectories.')
    with CHECK.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({k:result[k] for k in ['paired_samples','max_half_pressure_rms_pa','max_half_displacement_mm']}))


if __name__=='__main__':main()
