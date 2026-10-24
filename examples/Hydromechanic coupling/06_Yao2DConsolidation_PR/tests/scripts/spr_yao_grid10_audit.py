"""Bind revised review, independent saved-dt metadata and endpoint-load plots."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from spr_yao_short import TESTS,bound


def main():
    tag='spr_yao_grid10_r1';prefix=tag+'_review_r2';review=TESTS/'logs'/(prefix+'.check.json')
    result=json.loads(review.read_text());assert result['whole_window_half_passed'] and result['half_samples']==101
    history=pd.read_csv(TESTS/'figures'/(prefix+'_history.csv'),float_precision='round_trip')
    endpoints=pd.read_csv(TESTS/'figures'/(prefix+'_endpoints.csv'),float_precision='round_trip')
    saved=[];evidence=[bound(__file__),bound(review)];colors={'faces_off':'#696969','faces_on':'#2166a5','faces_half':'#b18b2b'}
    for variant,dt in [('faces_off',2e-5),('faces_on',2e-5),('faces_half',1e-5)]:
        path=TESTS/'figures'/(tag+'_'+variant+'_metadata.csv');a=pd.read_csv(path,float_precision='round_trip');evidence.append(bound(path));a=a[a.part.gt(0)]
        assert len(a)==100 and a.has_dterror.eq(1).all() and a.nout.eq(0).all()
        assert a.dterror_s.between(-1e100,0).all() and a.dt_min_s.eq(dt).all() and a.dt_max_s.eq(dt).all()
        saved.append(dict(variant=variant,intervals=100,fixed_dt_s=dt,mechanical_min_limit_s=float(dt-a.dterror_s.max()),pore_limit_s=9.53206462560066e-5,dt_guard_passed=True))
    off=history[history.variant.eq('faces_off')].reset_index(drop=True);on=history[history.variant.eq('faces_on')].reset_index(drop=True)
    assert np.array_equal(off.time_s,on.time_s) and off.force_N_m.equals(on.force_N_m)
    fig,axes=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
    for variant,h in history.groupby('variant'):
        ls='--' if variant=='faces_half' else '-';c=colors[variant]
        positive=h[h.time_s.gt(0)]
        axes[0].step(positive.time_s,positive.loaded_count,where='post',color=c,ls=ls,label=variant)
        axes[1].plot(h.time_s,h.force_N_m-h.ideal_force_N_m,color=c,ls=ls,label=variant)
        e=endpoints[endpoints.variant.eq(variant)&endpoints.id.eq(14874)]
        axes[2].plot(e.time_s,(e.x_m-3)*1e6,color=c,ls=ls,label=variant)
    for ax,title,unit in zip(axes,['Observed loaded particle count','Observed minus ideal 6-m strip resultant','Right endpoint distance from x=3'],['count','N/m','micrometres']):
        ax.set(title=title,xlabel='Actual saved time (s)',ylabel=unit);ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0].set_yticks([59,60,61]);axes[0].set_ylim(58.5,61.5)
    axes[0].set_title('Loaded count after initially zero load')
    axes[2].axhline(0,color='.3',lw=.8)
    fig.suptitle('Existing strict Eulerian strip: both SPR-off and SPR-on endpoints re-enter')
    path=TESTS/'figures'/(prefix+'_load_r3.png');assert not path.exists();fig.savefig(path,dpi=170);plt.close(fig);evidence.append(bound(path))
    active=history[history.time_s.gt(0)];out=TESTS/'logs'/(prefix+'.audit_r3.json');assert not out.exists()
    record=dict(cpu_01s_numerical_admission_passed=True,physical_or_theory_acceptance=False,metadata=saved,
        force_telemetry_off_on_exact_at_all_101_saved_times=True,exact_every_step_force_equality_not_observed=True,
        corrected_r2_interpretation='The unconditional r2 unequal-force flag was too strong: native saved force is equal. Between-frame stage membership was not saved.',
        positive_time_discrete_width_range_m=[float(active.discrete_loaded_width_m.min()),float(active.discrete_loaded_width_m.max())],
        initial_width_quadrature_bias_pct=-100/60,final_width_quadrature_bias_pct=100/60,
        visual_inspection_pending=True,evidence=evidence)
    with out.open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2)
    print(json.dumps({k:v for k,v in record.items() if k!='evidence'},indent=2))


if __name__=='__main__':main()
