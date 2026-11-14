"""Plot-only revision of the sealed 144-row summary."""
import argparse,csv,itertools,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator,FuncFormatter,MaxNLocator

T=Path(__file__).resolve().parents[1];SOURCE='c08_h18_joint_eta_shadow_r1';TAG='c08_h18_joint_eta_display_r2'
GATE=T/'logs'/(SOURCE+'.check.json');NOTE=T/'notes'/(TAG+'.md');CHECK=T/'logs'/(TAG+'.check.json')
CSV=T/'figures'/(SOURCE+'_metrics.csv');OUT=[T/'figures'/(TAG+'_'+s+'.png')for s in('rates','deltas')]
PARTS=(29,30);FIELDS=('H_hydro_affine','N_normal_quadratic','X_cross_cubic');ORACLES=('real_wall','analytic_ghost')
COHORTS=('all_soil','legal_flat_bed','interior_no_wall');VARIANTS=('pair_C_eta','pair_C_bare','receiver_C_eta','receiver_C_bare')
COLORS=('tab:blue','tab:orange','tab:green','tab:red');NUMBERS=('original_rate_RMS','shadow_rate_RMS','delta_rate_mean','delta_rate_RMS')

def need(x,s):
    if not x:raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):
    with Path(p).open(encoding='utf-8-sig')as f:return json.load(f)
def bind(e):
    s=stat(e['path']);need(s['bytes']==e['bytes']and s['mtime_ns']==e['mtime_ns'],'Bound display source changed: '+e['path']);return s
def sealed(g,p):
    m=[e for e in g['files']if Path(e['path']).resolve()==p.resolve()];need(len(m)==1,'Unique original file seal required: '+str(p));return bind(m[0])
def key(q):return(int(q['part']),q['field'],q['oracle'],q['cohort'],q['variant'])
def load():
    with CSV.open(encoding='utf-8-sig',newline='')as f:rr=list(csv.DictReader(f))
    expected=set(itertools.product(PARTS,FIELDS,ORACLES,COHORTS,VARIANTS));lookup={}
    need(len(rr)==144,'Original compact summary must have 144 rows')
    for q in rr:
        k=key(q);need(k in expected and k not in lookup,'Unexpected/duplicate compact row');n=int(q['material_IDs']);need(n>=0,'Negative cohort size')
        for name in NUMBERS:
            if n:need(math.isfinite(float(q[name])),'Nonfinite plotted value: '+name)
            else:need(q[name]=='','Empty cohort must remain N/A')
        if n:need(float(q['original_rate_RMS'])>=0 and float(q['shadow_rate_RMS'])>=0 and float(q['delta_rate_RMS'])>=0,'Negative RMS')
        lookup[k]=q
    need(set(lookup)==expected,'Complete original group coverage required');return lookup
def number(x,pos):return '0'if x==0 else f'{x:.3g}'
def ordinate(ax,values,linear,signed):
    v=[x for x in values if math.isfinite(x)];need(v,'No visible values for this panel')
    m=max(abs(x)for x in v);limit=1.18*m if m else 1.
    ax.set_ylim(-limit if signed else 0,limit)
    if linear:
        ax.set_yscale('linear');ax.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3));ax.yaxis.set_major_formatter(FuncFormatter(number))
    else:
        ax.set_yscale('symlog',base=10,linthresh=1.,linscale=1.)
        powers=[10.**i for i in range(0,max(1,int(math.ceil(math.log10(max(limit,1.))))+1))]
        ticks=([-x for x in reversed(powers)if x<=limit]if signed else [])+[0.]+[x for x in powers if x<=limit]
        ax.yaxis.set_major_locator(FixedLocator(ticks));ax.yaxis.set_major_formatter(FuncFormatter(number))
    ax.tick_params(axis='y',labelsize=9);ax.grid(axis='y',alpha=.25)
def values(q,name):return math.nan if int(q['material_IDs'])==0 else float(q[name])
def save(fig,p):
    with p.open('xb')as f:fig.savefig(f,format='png',dpi=175)
    plt.close(fig)
def render(d):
    fig,axes=plt.subplots(3,3,figsize=(15,11));shown=0
    for i,field in enumerate(FIELDS):
        for j,cohort in enumerate(COHORTS):
            ax=axes[i,j];panel=[]
            for color,(part,oracle)in zip(COLORS,itertools.product(PARTS,ORACLES)):
                q=[d[part,field,oracle,cohort,v]for v in VARIANTS];y=[values(z,'shadow_rate_RMS')for z in q];panel+=y;shown+=sum(math.isfinite(x)for x in y)
                ax.plot(range(4),y,'.-',color=color,label=f'P{part} '+('real wall'if oracle=='real_wall'else 'analytic ghost'))
            ax.set_title(field[:1]+' | '+cohort,fontsize=11);ax.set_ylabel('Conditional rate RMS [Pa/s]',fontsize=10);ax.set_xticks(range(4),('pair/eta','pair/bare','recv/eta','recv/bare'),rotation=18,fontsize=9)
            ordinate(ax,panel,i==0,False)
    h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='lower center',bbox_to_anchor=(.5,.035),ncol=4,fontsize=9,frameon=False)
    fig.suptitle('Frozen joint fields: four pressure weights; C/J/FS/Gp/Da/k-chain unchanged\nPlot-only revision: H linear; N/X symlog with explicit numeric ticks',fontsize=12,y=.985)
    fig.text(.5,.013,'Original values/zeros retained. Whole-domain X is not a compatible IBVP. No physical acceptance.',ha='center',fontsize=8.7)
    fig.subplots_adjust(left=.08,right=.985,top=.89,bottom=.16,wspace=.30,hspace=.47);save(fig,OUT[0])
    fig,axes=plt.subplots(3,2,figsize=(14,11));delta_shown=0
    for i,field in enumerate(FIELDS):
        for j,cohort in enumerate(COHORTS[1:]):
            ax=axes[i,j];panel=[]
            for color,v in zip(COLORS[1:],VARIANTS[1:]):
                q=[d[p,field,o,cohort,v]for p in PARTS for o in ORACLES]
                for metric,style,marker,label in(('delta_rate_mean','-','.','signed mean'),('delta_rate_RMS','--','x','RMS')):
                    y=[values(z,metric)for z in q];panel+=y;delta_shown+=sum(math.isfinite(x)for x in y);ax.plot(range(4),y,ls=style,marker=marker,color=color,label=v+' '+label)
            ax.axhline(0,color='.4',lw=.7);ax.set_title(field[:1]+' | '+cohort,fontsize=11);ax.set_ylabel('Variant - original rate [Pa/s]',fontsize=10);ax.set_xticks(range(4),('29 real','29 analytic','30 real','30 analytic'),rotation=15,fontsize=9);ordinate(ax,panel,i==0,True)
    h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc='lower center',bbox_to_anchor=(.5,.035),ncol=2,fontsize=8.5,frameon=False)
    fig.suptitle('Conditional signed and RMS changes on unchanged material-ID cohorts\nH linear; N/X symmetric symlog. Bare/receiver-C curves are offline shadows.',fontsize=12,y=.985)
    fig.text(.5,.013,'Signed means/RMS/zero retained. Units: Pa/s. No CSV, numerical gate or model changes.',ha='center',fontsize=8.5)
    fig.subplots_adjust(left=.09,right=.985,top=.89,bottom=.22,wspace=.25,hspace=.43);save(fig,OUT[1]);return shown,delta_shown
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');need(p.parse_args().execution_authorized,'Root plot-only admission required');need(not CHECK.exists()and all(not p.exists()for p in OUT),'Protect old/new complete or partial plots');consumed=[]
    try:
        g=read(GATE);need(g['passed']and g['analysis_complete']and g['consumed_stats_unchanged']and g['metrics_rows']==144 and g['actual_groups']==12 and not g['physical_acceptance'],'Passed original four-weight summary required')
        consumed=[stat(GATE),stat(__file__),stat(NOTE),sealed(g,CSV)]+[sealed(g,T/'figures'/(SOURCE+'_'+s+'.png'))for s in('rates','deltas')]
        data=load();shown,delta_shown=render(data);[bind(e)for e in consumed]
        result=dict(stage=TAG,passed=True,plot_only=True,analysis_rerun=False,source_metrics_rows=144,source_CSV_reads=1,source_value_transformations=0,plotted_rate_values=shown,plotted_delta_values=delta_shown,physical_acceptance=False,visual_QA_pending=True,solver_invocations=0,reader_invocations=0,component_invocations=0,build_invocations=0,SHA_scans=0,large_per_ID_body_reads=0,old_plots_overwritten=False,consumed=consumed,consumed_stats_unchanged=True,files=[stat(x)for x in OUT])
    except Exception as e:
        result=dict(stage=TAG,passed=False,first_failure=str(e),partial_outputs_preserved=True,plot_only=True,physical_acceptance=False,consumed=consumed);raise
    finally:
        with CHECK.open('x',encoding='utf-8')as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
