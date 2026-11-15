"""CSV-only view of both saved-wall proxy attempts; never recompute the proxy."""
import argparse
import csv
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

T=Path(__file__).resolve().parents[1]
TAG='c08_h18_hg_wall_proxy_visual_r2'
NOTE=T/'notes'/(TAG+'.md')
SOURCE=T/'figures/c08_h18_hg_wall_saved_proxy_r1_attempts.csv'
ORIGINAL=T/'logs/c08_h18_hg_wall_saved_proxy_r1.check.json'
PNG=T/'figures'/(TAG+'.png')
CHECK=T/'logs'/(TAG+'.check.json')


def need(ok,message):
    if not ok:raise RuntimeError(message)


def stat(path):
    p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args()
    need(args.execution_authorized,'Root review and separate offline authorization required')
    need(not PNG.exists() and not CHECK.exists(),'Existing complete/partial visual outputs protected')
    original=json.loads(ORIGINAL.read_text(encoding='utf-8-sig'))
    need(original['analysis_passed'] and original['analysis_complete'] and original['consumed_stats_unchanged']
         and original['saved_state_proxy'] and not original['actual_unsaved_GPU_C']
         and not original['actual_failure_branch_confirmed'],'Completed saved-state proxy review required')
    refs=[q for q in original['files'] if Path(q['path']).resolve()==SOURCE.resolve()]
    need(len(refs)==1 and stat(SOURCE)==refs[0],'Original sealed attempts CSV changed')
    consumed=[stat(q) for q in (Path(__file__),NOTE,ORIGINAL,SOURCE)]
    result=dict(stage=TAG,passed=False,visual_revision_only=True,proxy_recomputations=0,native_decodes=0,
                solver_invocations=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False,
                actual_unsaved_GPU_C=False,actual_failure_branch_confirmed=False)
    try:
        with SOURCE.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        parts=list(range(89,99));need(len(rows)==20,'Exactly20 original two-attempt rows required')
        keyed={(int(q['part']),int(q['attempt'])):q for q in rows}
        need(len(keyed)==20 and set(keyed)=={(part,attempt) for part in parts for attempt in (0,1)},'Original ten states and both attempts required')
        groups=[[keyed[(part,attempt)] for part in parts] for attempt in (0,1)]
        times=[float(q['actual_tau_s']) for q in groups[0]]
        for a,b in zip(*groups):
            need(a['saved_state_proxy']==b['saved_state_proxy']=='True' and a['actual_unsaved_GPU_C']==b['actual_unsaved_GPU_C']=='False'
                 and float(a['actual_tau_s'])==float(b['actual_tau_s']) and int(a['wall_native_id'])==int(b['wall_native_id'])==894,
                 'Both attempts must refer to the same genuine saved-wall proxy')
        value=lambda group,key:[float(q[key]) for q in group]
        dets=[value(group,'raw_M_det') for group in groups]
        need(all(math.isfinite(x) and x>0 for group in dets for x in group),'Log view requires actual positive finite detM values')
        accepted=[q for q in groups[1] if q['original_geometry_predicate_on_proxy']=='True']
        need(len(accepted)==10,'This revision displays the ten geometry-valid retry1 fits only')
        tfit=[float(q['actual_tau_s']) for q in accepted]
        fig,axes=plt.subplots(2,2,figsize=(13,8.8),layout='constrained')
        for attempt,group in enumerate(groups):
            label='Attempt 0: original G' if attempt==0 else 'Attempt 1: nearest-donor retry G'
            axes[0,0].plot(times,dets[attempt],'o-',ms=4,label=label)
            axes[0,1].plot(times,[int(q['real_soil_donors']) for q in group],'o-',ms=4,label=label)
        axes[0,0].axhline(.001,color='red',ls='--',label='Original geometry limit: 0.001')
        axes[0,0].set(title='Both proxy moment determinants',ylabel='det M',yscale='log')
        axes[0,1].set(title='Both real-soil donor counts',ylabel='Donors [count]')
        axes[0,1].yaxis.set_major_locator(MaxNLocator(integer=True))
        for key,label,style in (('fitted_C_det','Retry 1: det C','o-'),('fitted_C_sym_eig_min','Retry 1: min eig(sym C)','s-'),('fitted_C_sym_eig_max','Retry 1: max eig(sym C)','^-')):
            axes[1,0].plot(tfit,value(accepted,key),style,ms=4,label=label)
        axes[1,0].axhline(0,color='.4',lw=.8)
        axes[1,0].set(title='Retry 1 fit: geometry-valid saved proxies',ylabel='Determinant / symmetric-part eigenvalue')
        ax=axes[1,1];other=ax.twinx()
        a=ax.plot(tfit,value(accepted,'alpha_L1'),'o-',ms=4,color='C0',label='Last geometry-valid proxy (retry 1): sum |alpha|')
        b=other.plot(tfit,[int(q['negative_alpha_count']) for q in accepted],'s--',ms=4,color='C1',label='Last geometry-valid proxy (retry 1): negative count')
        ax.set(title='Last accepted proxy coefficients (retry 1)',ylabel='Sum |alpha|');other.set_ylabel('Negative coefficients [count]');other.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend(a+b,[q.get_label() for q in a+b],fontsize=8,loc='upper right')
        for ax in axes.flat:
            ax.set_xlabel('Actual saved time after release [s]');ax.grid(alpha=.2);ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
        for ax in (axes[0,0],axes[0,1],axes[1,0]):ax.legend(fontsize=8)
        fig.suptitle('Wall 894: both saved-state proxy attempts',fontsize=14)
        fig.supxlabel('Only the existing CSV is redrawn; the 0.001 geometry limit is unchanged.\nThese are saved-state proxies, not the rejected unsaved GPU C or proof of its failure branch.',fontsize=9)
        fig.savefig(PNG,dpi=180);plt.close(fig)
        need(all(stat(q['path'])==q for q in consumed),'Immutable source binding changed')
        result.update(passed=True,consumed_stats_unchanged=True,input_rows=20,attempt0_rows=10,attempt1_rows=10,
                      original_geometry_limit=.001,fitted_metrics_attempt=1,last_accepted_proxy_attempt=1,
                      original_artifacts_changed=False,numerical_proxy_rerun=False,visual_QA_pending=True,figure=stat(PNG))
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    need(result['passed'],result.get('first_failure','Visual revision failed; preserve partial outputs'))


if __name__=='__main__':main()
