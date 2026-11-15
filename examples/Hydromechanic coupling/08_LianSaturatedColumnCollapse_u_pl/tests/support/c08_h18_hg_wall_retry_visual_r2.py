"""CSV-only redrawing of the sealed independent wall-retry counterfactual."""
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
TAG='c08_h18_hg_wall_retry_visual_r2'
NOTE=T/'notes'/(TAG+'.md')
ORIGINAL=T/'logs/c08_h18_hg_wall_retry_candidate_r1.check.json'
ATTEMPTS=T/'figures/c08_h18_hg_wall_retry_candidate_r1_attempts.csv'
DONORS=T/'figures/c08_h18_hg_wall_retry_candidate_r1_donors.csv'
PNG=T/'figures'/(TAG+'.png')
CHECK=T/'logs'/(TAG+'.check.json')


def need(ok,message):
    if not ok:raise RuntimeError(message)


def stat(path):
    p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)


def readcsv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args()
    need(args.execution_authorized,'Separate root offline execution authorization required')
    need(not PNG.exists() and not CHECK.exists(),'Existing complete/partial visual outputs protected')
    original=json.loads(ORIGINAL.read_text(encoding='utf-8-sig'))
    need(original['analysis_passed'] and original['analysis_complete'] and original['consumed_stats_unchanged']
         and not original['physical_repair_selected'] and not original['actual_GPU_M_C_registers'],
         'Completed independent counterfactual review required')
    for path in (ATTEMPTS,DONORS):
        refs=[q for q in original['files'] if Path(q['path']).resolve()==path.resolve()]
        need(len(refs)==1 and stat(path)==refs[0],'Original sealed CSV changed: '+path.name)
    consumed=[stat(q) for q in (Path(__file__),NOTE,ORIGINAL,ATTEMPTS,DONORS)]
    result=dict(stage=TAG,passed=False,visual_revision_only=True,independent_CPU_counterfactual=True,
                matrix_or_coefficient_recomputations=0,native_decodes=0,solver_invocations=0,
                GPU_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,
                physical_acceptance=False,physical_repair_selected=False,actual_GPU_M_C_registers=False,
                original_solver_still_failed=True)
    try:
        rows=readcsv(ATTEMPTS);donors=readcsv(DONORS)
        keyed={(q['method'],int(q['attempt'])):q for q in rows}
        expected={('Original source',0),('Counterfactual retry',0),('Counterfactual retry',1)}
        need(len(rows)==3 and set(keyed)==expected,'Exactly the three original attempt rows required')
        selected=[keyed[('Original source',0)],keyed[('Counterfactual retry',1)]]
        values={key:[float(q[key]) for q in selected] for key in
                ('independent_C_det','independent_C_sym_eig_min','alpha_L1')}
        need(all(math.isfinite(v) for pair in values.values() for v in pair),'Nonfinite plotted metric')
        counts=[int(q['negative_alpha_count']) for q in selected]
        donorcounts=[int(q['consumed_fluid_donors']) for q in selected]
        for q,count,donorcount in zip(selected,counts,donorcounts):
            group=[d for d in donors if d['method']==q['method'] and int(d['attempt'])==int(q['attempt'])]
            need(len(group)==donorcount and sum(float(d['independent_alpha'])<0 for d in group)==count,
                 'Sealed donor CSV count differs from attempt CSV')
        labels=['Original source\nattempt 0 (17 donors)','Counterfactual retry\nattempt 1 (24 donors)']
        need(donorcounts==[17,24] and counts==[13,18],'This visual revision is bound to the reviewed packet')
        fig,axes=plt.subplots(1,2,figsize=(11.8,6.4))
        fig.subplots_adjust(left=.08,right=.92,bottom=.29,top=.79,wspace=.45)
        x=[0,1];width=.30
        a=axes[0].bar([v-width/2 for v in x],values['independent_C_det'],width,color='#2474ad',label='det C')
        b=axes[0].bar([v+width/2 for v in x],values['independent_C_sym_eig_min'],width,color='#6e4797',label='min eig(sym C)')
        axes[0].axhline(0,color='.25',lw=.9,ls='--')
        axes[0].set(title='Fitted matrix: independent recomputation',ylabel='Dimensionless determinant / eigenvalue',ylim=(-.28,2.55))
        for bars in (a,b):axes[0].bar_label(bars,fmt='%.4g',padding=5,fontsize=10)
        ax=axes[1];other=ax.twinx()
        c=ax.bar([v-width/2 for v in x],values['alpha_L1'],width,color='#2474ad',label='Sum |alpha| (left axis)')
        d=other.bar([v+width/2 for v in x],counts,width,color='#d97818',label='Negative alpha count (right axis)')
        ax.set(title='Coefficient magnitude and negative count',ylabel='Sum |alpha| [dimensionless]',ylim=(0,7.1))
        other.set(ylabel='Negative coefficients [count]',ylim=(0,22))
        other.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.bar_label(c,fmt='%.4g',padding=5,fontsize=10)
        other.bar_label(d,fmt='%d',padding=5,fontsize=10)
        for axis in axes:
            axis.set_xticks(x,labels);axis.grid(axis='y',alpha=.2);axis.set_axisbelow(True)
        axes[0].legend(handles=[a,b],loc='upper left',framealpha=1,fontsize=9)
        fig.legend(handles=[c,d],loc='lower center',bbox_to_anchor=(.5,.145),ncol=2,framealpha=1,fontsize=10)
        fig.suptitle('Wall 894: independent nearest-donor retry counterfactual',fontsize=15,y=.96)
        fig.text(.5,.88,'Negative coefficient count increases 13 to 18; sum |alpha| decreases 5.727 to 2.315.',ha='center',fontsize=11)
        fig.text(.5,.055,'Existing sealed CSVs only; no matrix or coefficient calculation is repeated.\n'
                 'Independent CPU counterfactual on the actual captured packet; not GPU registers, a selected physical repair, or solver success.',
                 ha='center',va='center',fontsize=9)
        fig.savefig(PNG,dpi=180);plt.close(fig)
        need(all(stat(q['path'])==q for q in consumed),'Immutable consumed artifact changed')
        result.update(passed=True,consumed_stats_unchanged=True,input_attempt_rows=3,input_donor_rows=len(donors),
                      selected_attempts=[dict(method=q['method'],attempt=int(q['attempt'])) for q in selected],
                      plotted_values=values,donor_counts=donorcounts,negative_alpha_counts=counts,
                      negative_count_increases=True,legend_outside_twin_axes=True,
                      original_artifacts_changed=False,visual_QA_pending=True,figure=stat(PNG))
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    need(result['passed'],result.get('first_failure','Visual revision failed; preserve partial outputs'))


if __name__=='__main__':main()
