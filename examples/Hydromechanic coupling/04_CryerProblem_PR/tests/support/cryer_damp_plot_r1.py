"""Plot retained short damping controls; never execute a solver or overwrite evidence."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from cryer_start_r1 import TESTS, bound
from cryer_gpu_base_r1 import verify

tag='cryer_damp_plot_r1'
figure=TESTS/'figures'/(tag+'.png')
table=TESTS/'figures'/(tag+'.csv')
receipt=TESTS/'logs'/(tag+'.check.json')
assert not any(p.exists() for p in [figure,table,receipt])
review_path=TESTS/'logs/cryer_damp_short_review_r1.check.json'
review=json.loads(review_path.read_text(encoding='utf8'))
assert review['evidence_consistency_passed'] and review['original_independent_half_screen_passed']
verify([dict(path=str(review_path.parent/p['path']),sha256=p['sha256']) for p in review['source_links']])
old=TESTS/'figures/cryer_gpu_grad_fine_r1_summary.csv'
new=TESTS/'figures/cryer_damp_short_r1_summary.csv'
effect=TESTS/'figures/cryer_damp_short_r1_effects.csv'
half=TESTS/'figures/cryer_damp_short_r1_half.csv'
frames=[]
for path,coef in [(old,.02),(new,.00004)]:
    data=pd.read_csv(path,float_precision='round_trip')
    assert len(data)==10
    data['damping_coefficient']=coef
    data['step_kind']=data.run.str[-1]
    frames.append(data)
history=pd.concat(frames,ignore_index=True)
effects=pd.read_csv(effect,float_precision='round_trip')
halves=pd.read_csv(half,float_precision='round_trip')
assert len(effects)==10 and len(halves)==5 and halves.screen_passed.all()
plt.rcParams.update({'font.size':10})
fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
colors={.02:'#1769a0',.00004:'#aa5c00'}
for (coef,step),data in history.groupby(['damping_coefficient','step_kind']):
    data=data.sort_values('part');t=1000*data.time_s
    options=dict(color=colors[coef],linestyle='-' if step=='c' else '--',
                 marker='o' if step=='c' else 'x',markersize=4,label=f'xi={coef:g}, {step}')
    axes[0,0].plot(t,data.center_pressure_mean_pa/10000,**options)
    axes[0,1].plot(t,data.center_radial_settlement_mm,**options)
for step,data in effects.groupby(effects.run.str[-1]):
    axes[1,0].plot(1000*data.time_s,data.pressure_rms_pa,marker='o' if step=='c' else 'x',
                   linestyle='-' if step=='c' else '--',label=f'{step}: xi=.00004 vs .02')
axes[1,1].plot(1000*halves.time_s,halves.pressure_rms_pa,color='#1769a0',marker='o',label='Independent coarse/half RMS')
axes[1,1].axhline(5,color='#555555',linestyle='--',label='Original 5-Pa half-step limit')
axes[0,0].set(title='Fixed 18-ID center pressure',ylabel='p / q')
axes[0,1].set(title='Fixed 18-ID inward radial displacement',ylabel='Displacement (mm)')
axes[1,0].set(title='Physical damping-option change, NOT a half error',ylabel='Whole-cloud pressure difference RMS (Pa)')
axes[1,1].set(title='Independent half-step check, xi=.00004 only',ylabel='Whole-cloud pressure difference RMS (Pa)',ylim=(0,5.5))
for ax in axes.flat:
    ax.set_xlabel('Actual saved time (ms)');ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('Cryer: damping-only startup comparison; five saves, not peak-window acceptance',fontsize=13)
history.to_csv(table,index=False,float_format='%.17g')
fig.savefig(figure,dpi=180);plt.close(fig)
record=dict(analysis_complete=True,physical_accepted=False,peak_window_admitted=False,
    inputs=[bound(p) for p in [__file__,review_path,old,new,effect,half]],
    artifacts=[bound(figure),bound(table)],
    limits=['Five native samples per run, no theory or late-peak accuracy claim.',
            'Option-change RMS and independent half RMS are different quantities, shown on separate panels.',
            'Native p(0)=0 and all startup samples retained; no smoothing or shifted times.'])
with receipt.open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2,allow_nan=False)
print(figure)
