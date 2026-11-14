"""Repair derived figure layout only, reusing the completed r1 numerical review."""
from pathlib import Path
import argparse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import c08_h18_wend_matrix_r1 as m

T,L=m.T,m.L
TAG='c08_h18_rvisc_plot_r2'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true')
    m.need(p.parse_args().execution_authorized,'Root offline layout review required')
    check=L/(TAG+'.check.json');out=T/'figures'/TAG
    m.need(not check.exists() and not out.exists(),'Existing figures/checks protected')
    source=L/'c08_h18_rvisc_force_review_r1.check.json';review=m.read(source)
    m.need(review['passed'] and review['consumed_stats_unchanged'],'Completed numerical review required')
    entries=review['files'];m.verify(entries)
    summary=next(q for q in entries if Path(q['path']).name=='summary.csv')
    pairs=next(q for q in entries if Path(q['path']).name=='pairs.csv')
    original=m.read(L/'c08_h18_rvisc_force_r1.check.json')
    soil=next(q for q in original['files'] if Path(q['path']).name=='soil.csv');m.bind(soil)
    before=[m.stat(Path(__file__)),m.stat(source),summary,pairs,soil]
    result=pd.read_csv(summary['path'],float_precision='round_trip').sort_values('part')
    pair=pd.read_csv(pairs['path'],float_precision='round_trip').sort_values(['part','ID_i'])
    data=pd.read_csv(soil['path'],float_precision='round_trip')
    m.need(len(result)==2 and len(pair)==4 and len(data)==10000,'Bound r1 coverage differs')
    out.mkdir();plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.22})
    fig,axes=plt.subplots(2,2,figsize=(13,8),constrained_layout=True)
    x=np.arange(2);labels=[f"P{int(r.part)}, tau={r.tau_s:.6f}s" for r in result.itertuples()]
    for ax,col,title in ((axes[0,0],'R_RMS','Pressure-rate RMS'),(axes[0,1],'max_abs_R','Maximum absolute pressure rate')):
        ax.bar(x-.18,result['baseline_'+col]/1e6,.36,label='Original')
        ax.bar(x+.18,result['candidate_'+col]/1e6,.36,label='Residual viscosity 0.1')
        ax.set(title=title,ylabel='MPa/s');ax.set_xticks(x,labels);ax.legend(fontsize=8)
    ax=axes[1,0];other=ax.twinx()
    ax.bar(x-.17,result.recomputed_work,.32,color='tab:blue')
    other.bar(x+.17,result.recomputed_pressure_term,.32,color='tab:orange')
    ax.set_xticks(x,labels);ax.set_ylabel('Added mechanical power [W/m]',color='tab:blue')
    other.set_ylabel('Conditional sum(w p deltaR) [W/m]',color='tab:orange');other.grid(False)
    ax.set_title('Separate conditional terms; no total-energy claim')
    ax=axes[1,1];j=np.arange(4)
    ax.bar(j-.18,pair.base_rddot,.36,label='Original');ax.bar(j+.18,pair.candidate_rddot,.36,label='Candidate')
    ax.set_xticks(j,[f'P{r.part}\n{r.ID_i}/{r.ID_j}' for r in pair.itertuples()])
    ax.set(title='Fixed material pairs at unchanged rdot',ylabel='rddot [m/s2]');ax.legend(fontsize=8,loc='upper left')
    fig.suptitle('C08 H1.8 residual-force/Darcy response: frozen states, no integration or physical acceptance')
    fig.savefig(out/'summary.png',dpi=170);plt.close(fig)
    lo=float(data.dt_delta_R_Pa.min());hi=float(data.dt_delta_R_Pa.max())
    fig=plt.figure(figsize=(12,4.8));grid=fig.add_gridspec(1,3,width_ratios=(1,1,.035),wspace=.2)
    axs=[fig.add_subplot(grid[0,i]) for i in range(2)];cax=fig.add_subplot(grid[0,2])
    for ax,part in zip(axs,(38,76)):
        d=data[data.part==part]
        image=ax.scatter(d.x_m,d.z_m,c=d.dt_delta_R_Pa,cmap='RdBu_r',norm=Normalize(lo,hi),s=5,linewidths=0)
        ax.set(title=f'P{part}, tau={d.tau_s.iloc[0]:.6f}s',xlabel='x [m]',ylabel='z [m]',aspect='equal')
        ax.set_xlim(float(data.x_m.min())-.05,float(data.x_m.max())+.05)
        ax.set_ylim(float(data.z_m.min())-.05,float(data.z_m.max())+.05)
    fig.colorbar(image,cax=cax,label='5 us * deltaR [Pa]\n(conditional; not updated pressure)')
    fig.suptitle(f'All5000 soil IDs per state; common full linear range [{lo:.6g}, {hi:.6g}] Pa')
    fig.subplots_adjust(left=.055,right=.91,bottom=.16,top=.82)
    fig.savefig(out/'space.png',dpi=180);plt.close(fig);m.verify(before)
    m.save(check,dict(stage=TAG,passed=True,consumed=before,files=[m.stat(out/q) for q in ('summary.png','space.png')],
        matching_CSVs=[summary,pairs],original_soil=soil,layout_only=True,numerical_reanalysis=False,
        original_r1_figures_preserved=True,physical_steps=0,force_calls=0,SHA_scans=0,physical_acceptance=False))

if __name__=='__main__':main()
