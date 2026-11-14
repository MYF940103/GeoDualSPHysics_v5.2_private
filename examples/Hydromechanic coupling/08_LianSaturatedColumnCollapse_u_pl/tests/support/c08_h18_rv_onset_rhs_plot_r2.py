"""Author-only tick-layout repair of the passed six-panel RHS/AS figure.

Read only bound focus_RHS160 and metrics10; keep all data, units and axis ranges.
Write one new rhs_AS_r2.png/check. No mechanics/soil/component/solver/native rerun.
After root review:
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_rv_onset_rhs_plot_r2.py --execution-authorized
Existing success/partial derived artifacts are protected.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

T=Path(__file__).resolve().parents[1];TAG='c08_h18_rv_onset_rhs_plot_r2'
GATE=T/'logs/c08_h18_rv_onset_review_r1.check.json'
OUT=T/'figures/c08_h18_rv_onset_review_r1_rhs_AS_r2.png'
CHECK=T/'logs'/(TAG+'.check.json')
CHANNELS=('compression','LP','Taylor_pressure','Da','FS_Ace_Lx','chain_pressure','chain_Ace')
ALL_TERMS=CHANNELS+('numeric_residual',);CASES=('original','rv')

def need(ok,message):
    if not ok:raise RuntimeError(message)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def table(name,count,gate,used):
    path=T/'figures'/('c08_h18_rv_onset_review_r1_'+name+'.csv')
    e=[q for q in gate['files'] if Path(q['path']).resolve()==path.resolve()]
    need(len(e)==1 and stat(path)==e[0],'Passed figure data binding differs: '+name);used.append(e[0])
    df=pd.read_csv(path,float_precision='round_trip')
    need(len(df)==count and np.isfinite(df.select_dtypes(include=np.number).to_numpy(dtype=float)).all(),'Complete finite passed plot data required')
    return df

def render(focus,metrics):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm
    from matplotlib.ticker import SymmetricalLogLocator
    colors={'original':'#2166AC','rv':'#D6604D'}
    fig,axes=plt.subplots(3,2,figsize=(15,13),layout='constrained')
    for case in CASES:
        q=focus[focus['case']==case];axes[0,0].scatter(q.base_R_Pa_s,q.candidate_R_Pa_s,s=16,c=colors[case],label=case,alpha=.7)
        seven=q[['delta_'+v for v in CHANNELS]].sum(axis=1);axes[1,0].scatter(seven,q.delta_R_Pa_s,s=16,c=colors[case],alpha=.7)
        axes[1,1].scatter(q.focus_row_index,q.delta_numeric_residual,s=13,c=colors[case],alpha=.8)
        axes[2,0].scatter(q.total_positive_eigen_sum_Pa,q.actual_AS_tensor_nn_Pa,s=17,c=colors[case],alpha=.7)
        z=metrics[metrics['case']==case];axes[2,1].plot(z['part'],z.base_R_RMS,color=colors[case],marker='o',label=case+' bare');axes[2,1].plot(z['part'],z.candidate_R_RMS,color=colors[case],marker='s',ls='--',label=case+' +RV')
    axes[0,0].set(xlabel='Bare full rate [Pa/s]',ylabel='Bare + RV full rate [Pa/s]',title='All160 actual focus rates');axes[0,0].legend()
    axes[1,0].set(xlabel='Sum of seven physical channel deltas [Pa/s]',ylabel='Actual full delta rate [Pa/s]',title='Independent numeric residual is not forced into the seven terms')
    for ax,x,y in ((axes[0,0],focus.base_R_Pa_s,focus.candidate_R_Pa_s),(axes[1,0],focus[['delta_'+v for v in CHANNELS]].sum(axis=1),focus.delta_R_Pa_s)):
        ax.set_xscale('symlog',linthresh=1.);ax.set_yscale('symlog',linthresh=1.);lo=min(float(x.min()),float(y.min()));hi=max(float(x.max()),float(y.max()));ax.plot([lo,hi],[lo,hi],c='.5',ls=':',lw=.8)
    values=focus[['delta_'+v for v in ALL_TERMS]].to_numpy().T;limit=float(np.abs(values).max());need(limit>0,'Nonzero passed RHS range required')
    im=axes[0,1].imshow(values,aspect='auto',interpolation='nearest',cmap='RdBu_r',norm=SymLogNorm(linthresh=1.,vmin=-limit,vmax=limit));axes[0,1].set(yticks=np.arange(8),yticklabels=ALL_TERMS,xlabel='Actual focus row index0..159',title='All7 channel deltas + independent numeric residual')
    fig.colorbar(im,ax=axes[0,1],label='Actual delta term [Pa/s]; full range, symlog1Pa/s')
    axes[1,1].set(xlabel='Actual focus row index',ylabel='Independent delta numeric residual [Pa/s]',title='Observed float/source-order remainder, not a physical source')
    axes[2,0].set(xlabel='Actual float total positive eigenvalue sum [Pa]',ylabel='actual_AS_tensor_nn_Pa [Pa]',title='Original actual AS tensor projection: rho argument=1, no rescaling')
    axes[2,1].set(xlabel='Actual selected part',ylabel='All5000-soil rate RMS [Pa/s]',title='All10 states, original/candidate full rates');axes[2,1].legend(fontsize=8)
    for ax in axes.flat:ax.grid(alpha=.15)
    fig.suptitle('Conditional full-Darcy response on two existing trajectories; no time integration or causal acceptance',fontsize=12)
    # Only this block differs from the passed RHS/AS drawing. Each axis gets
    # its own locator. Some Matplotlib versions round the stride downward, so
    # reduce numticks only when needed to keep <=11 visible major ticks.
    ticks={}
    for label,ax in (('full_rates',axes[0,0]),('delta_rates',axes[1,0])):
        xlim,ylim=ax.get_xlim(),ax.get_ylim()
        for dim,axis,limits in (('x',ax.xaxis,xlim),('y',ax.yaxis,ylim)):
            locator=SymmetricalLogLocator(base=10,linthresh=1.)
            for requested in range(11,1,-1):
                locator.set_params(numticks=requested);positions=locator.tick_values(*limits)
                visible=[float(v) for v in positions if min(limits)<=v<=max(limits)]
                if len(visible)<=11:break
            need(len(visible)<=11,'Tick locator did not reach the requested sparse visible major ticks')
            axis.set_major_locator(locator);ticks[label+'_'+dim]=dict(requested_numticks=requested,visible_major_ticks=visible)
        ax.set_xlim(xlim);ax.set_ylim(ylim)
        ticks[label+'_ranges']=dict(x=list(xlim),y=list(ylim))
    fig.savefig(OUT,dpi=180);plt.close(fig);return ticks

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');need(p.parse_args().execution_authorized,'Author-only until root plot-only admission')
    need(not OUT.exists() and not CHECK.exists(),'Prior complete/partial plot repair protected')
    used=[stat(Path(__file__)),stat(GATE)];result=dict(stage=TAG,passed=False,solver_invocations=0,native_invocations=0,component_invocations=0,soil_rows_read=0,SHA_scans=0,physical_acceptance=False)
    try:
        gate=json.loads(GATE.read_text(encoding='utf-8-sig'));need(gate['passed'] and gate['analysis_complete'] and gate['consumed_stats_unchanged'] and gate['actual_AS_tensor_nn_units']=='Pa' and not gate['AS_tensor_rescaled_or_renamed'],'Passed correctly labelled RHS review required')
        focus=table('focus_RHS',160,gate,used);metrics=table('metrics',10,gate,used);ticks=render(focus,metrics)
        need(all(stat(q['path'])==q for q in used),'Passed plot input changed while rendering')
        result.update(passed=True,source_review=stat(GATE),focus_rows=160,metrics_rows=10,major_tick_formatting_only=True,scatter_axis_ranges_preserved=True,
            visible_ticks=ticks,original_six_panel_data_units_and_range_unchanged=True,old_successful_assets_modified=False,mechanics_regenerated=False,
            visual_QA_pending=True,consumed=used,consumed_stats_unchanged=True,image=stat(OUT))
    except Exception as error:result.update(first_failure=str(error),consumed=used,partial_outputs_preserved=True);raise
    finally:
        with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
