"""CSV-only accumulated-plastic-history concentration review; no physical job."""
import argparse
import csv
import datetime
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

T=Path(__file__).resolve().parents[1]
TAG='c08_h18_hg_localization_review_r1'
OLD=T/'logs/c08_h18_wall_c_retry_full3_review_r1.check.json'
DATA=T/'figures/c08_h18_wall_c_retry_full3_review_r1_spatial.csv'
NOTE=T/'notes'/(TAG+'.md')
PARTS=(30,60,120,300)
CASES=('Retained HG0','C-quality retry + cached HG xi0.1')
CAP=.5
OUT={k:T/'figures'/(TAG+s) for k,s in [('summary','_summary.csv'),('lorenz','_lorenz.csv'),('map','_kappa_reference.png'),('metrics','_concentration.png')]}
CHECK=T/'logs'/(TAG+'.check.json')


def need(ok,msg):
    if not ok:raise RuntimeError(msg)


def stat(p):
    p=Path(p);s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)


def bind(ref):
    p=Path(ref['path']);a=stat(p)
    need(all(a[k]==ref[k] for k in ('path','bytes','mtime_ns')),'Consumed stat changed: '+str(p))
    return p


def save_csv(p,rows):
    need(rows,'Empty derived table')
    with p.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def concentration(k):
    total=float(np.sum(k));ss=float(np.dot(k,k));n=len(k)
    return dict(nodes=n,positive_nodes=int(np.count_nonzero(k>0)),kappa_mean=float(np.mean(k)),kappa_max=float(np.max(k)),
        kappa_q95_orderstat_higher=float(np.quantile(k,.95,method='higher')),
        effective_nodes=total*total/ss if ss else None,effective_node_fraction=total*total/(n*ss) if ss else None,
        top10percent_share=float(np.sort(k)[-n//10:].sum()/total) if total else None,
        nodes_gt_0p1=int(np.count_nonzero(k>.1)),nodes_gt_0p5=int(np.count_nonzero(k>.5)),sum_kappa=total)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root full-read and separate one-shot authorization required')
    need(not any(p.exists() for p in [*OUT.values(),CHECK]),'Existing derived outputs/partial evidence are protected')
    old=json.loads(OLD.read_text(encoding='utf-8'))
    need(old['passed'] and old['analysis_complete'] and old['soil_IDs']==5000 and old['selected_parts']==list(PARTS),'Original passed review/schema required')
    refs=[q for q in old['files'] if Path(q['path'])==DATA];need(len(refs)==1,'Original spatial CSV must have one exact sealed output binding')
    bind(refs[0]);consumed=[stat(p) for p in (OLD,DATA,Path(__file__),NOTE)]
    groups={p:[] for p in PARTS}
    with DATA.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            p=int(row['part']);need(p in groups,'Unexpected selected part');groups[p].append(row)
    fields=['actual_time_s','tau_s','completed_step','x_m','z_m','dx_from_PRE_mm','dz_from_PRE_mm','HG0_x_m','HG0_z_m','kappa','HG0_kappa']
    arrays={};reference=None;max_reference_spread=0.;summary=[];lorenz=[];previous={}
    for part,tau_expected in zip(PARTS,old['selected_actual_tau_s']):
        rows=sorted(groups[part],key=lambda q:int(q['native_id']))
        ids=np.array([int(q['native_id']) for q in rows],dtype=np.int64)
        need(ids.tolist()==list(range(2060,7060)),'Every original 5000 soil ID is required exactly once')
        vals={k:np.array([float(q[k]) for q in rows]) for k in fields}
        need(all(np.isfinite(v).all() for v in vals.values()),'Nonfinite original CSV value')
        for key in ('actual_time_s','tau_s','completed_step'):need(np.all(vals[key]==vals[key][0]),'One actual clock/step per part required')
        need(vals['tau_s'][0]==tau_expected,'Selected actual tau differs from sealed original check')
        xref=vals['x_m']-vals['dx_from_PRE_mm']/1000.;zref=vals['z_m']-vals['dz_from_PRE_mm']/1000.
        xy=np.column_stack((xref,zref))
        if reference is None:reference=xy.copy()
        spread=float(np.max(np.abs(xy-reference)));max_reference_spread=max(max_reference_spread,spread)
        bound=32*np.finfo(np.float64).eps*(1+float(np.max(np.abs(reference))))
        need(spread<=bound,'Fixed PRE coordinate reconstruction differs beyond arithmetic screen')
        for ci,case in enumerate(CASES):
            k=vals['HG0_kappa' if ci==0 else 'kappa'];need((k>=0).all(),'Original kappa history must be nonnegative')
            tau=float(vals['tau_s'][0]);time=float(vals['actual_time_s'][0]);step=int(vals['completed_step'][0])
            entry=dict(case=case,kind='accumulated_kappa',part=part,previous_part='',actual_tau_start_s='',actual_tau_end_s=tau,interval_s='',**concentration(k))
            summary.append(entry);arrays[(ci,part)]=(k.copy(),tau,time,step)
            dk=None
            if ci in previous:
                pprev,tprev,kprev=previous[ci];dk=k-kprev;need((dk>=0).all(),'Original selected kappa history decreased; retain failure without masking')
                summary.append(dict(case=case,kind='saved_interval_delta_kappa',part=part,previous_part=pprev,actual_tau_start_s=tprev,actual_tau_end_s=tau,interval_s=tau-tprev,**concentration(dk)))
            previous[ci]=(part,tau,k.copy())
            total=float(k.sum());cum=np.r_[0.,np.cumsum(np.sort(k))]
            for rank in range(0,5001,50):
                lorenz.append(dict(case=case,part=part,tau_s=tau,sorted_material_rank=rank,material_fraction=rank/5000.,cumulative_kappa_share=float(cum[rank]/total) if total else '',all_values_retained_in_original_spatial_csv=True))
    need(sum(len(q[0]) for q in arrays.values())==40000 and len(summary)==14 and len(lorenz)==808,'All exact selected materials/statistics must remain')
    save_csv(OUT['summary'],summary);save_csv(OUT['lorenz'],lorenz)
    plt.rcParams.update({'font.size':10})
    fig,ax=plt.subplots(2,4,figsize=(16,7),sharex=True,sharey=True)
    cmap=plt.get_cmap('viridis').copy();cmap.set_over('crimson');norm=Normalize(vmin=0.,vmax=CAP,clip=False)
    for ci in range(2):
        for col,part in enumerate(PARTS):
            k,tau,_,_=arrays[(ci,part)]
            sc=ax[ci,col].scatter(reference[:,0],reference[:,1],c=k,cmap=cmap,norm=norm,s=3,linewidths=0,rasterized=True)
            ax[ci,col].set_title(f'{CASES[ci]}\nτ={tau:.6f} s; κ>{CAP}: {int(np.count_nonzero(k>CAP))}')
            ax[ci,col].set_aspect('equal');ax[ci,col].set_xlabel('Fixed PRE x [m]')
        ax[ci,0].set_ylabel('Fixed PRE z [m]')
    fig.suptitle('Accumulated plastic history on identical PRE material coordinates',fontsize=14)
    fig.subplots_adjust(left=.055,right=.91,top=.86,bottom=.13,wspace=.12,hspace=.42)
    cax=fig.add_axes([.935,.20,.012,.53]);fig.colorbar(sc,cax=cax,extend='max',label='Native accumulated κ (display range 0–0.5)')
    fig.text(.5,.025,'Crimson marks κ>0.5; all unmodified values remain in the bound original spatial CSV. This is not slip-band thickness or dissipated work.',ha='center',fontsize=10)
    fig.savefig(OUT['map'],dpi=160);plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(11,4.8))
    colors=('#285c9b','#c95b27')
    for ci,case in enumerate(CASES):
        s=[r for r in summary if r['case']==case and r['kind']=='accumulated_kappa']
        ax[0].plot([r['actual_tau_end_s'] for r in s],[r['effective_node_fraction'] for r in s],'-o',c=colors[ci],label=case)
        q=[r for r in lorenz if r['case']==case and r['part']==300]
        ax[1].plot([r['material_fraction'] for r in q],[r['cumulative_kappa_share'] for r in q],c=colors[ci],label=case)
    ax[0].set(xlabel='Actual release-relative time [s]',ylabel='Effective material fraction',title='Accumulated κ participation')
    ax[1].plot([0,1],[0,1],':',c='.5',label='Uniform κ reference')
    ax[1].set(xlabel='Materials sorted by κ: cumulative fraction',ylabel='Cumulative share of κ',title='3 s accumulated κ concentration')
    for a in ax:a.grid(alpha=.25);a.legend(fontsize=8)
    fig.suptitle('Same-material descriptions, not energy or physical accuracy',fontsize=12);fig.tight_layout();fig.savefig(OUT['metrics'],dpi=160);plt.close(fig)
    for q in consumed:bind(q)
    result=dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,visual_QA_pending=True,consumed=consumed,files=[stat(p) for p in OUT.values()],
        soil_IDs=5000,selected_parts=list(PARTS),kappa_scalar_values_analyzed=40000,no_duplicate_node_csv=True,summary_rows=len(summary),lorenz_rows=len(lorenz),
        fixed_PRE_coordinate_max_reconstruction_spread_m=max_reference_spread,coordinate_arithmetic_screen_m=bound,
        display_cap=CAP,display_overrange_not_data_clipping=True,all_raw_kappa_values_retained=True,q95_definition='higher order statistic; no spatial interpolation',
        delta_kappa_is_saved_interval_difference_not_instantaneous_rate=True,intervals_have_different_duration=True,
        concentration_is_bandwidth_or_energy=False,HG0_is_physical_truth=False,HG_C_retry_cached_material_path_confounding=True,
        HG_correctness_or_dissipation_proven=False,solver_invocations=0,native_decodes=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,automatic_next_job=False,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
