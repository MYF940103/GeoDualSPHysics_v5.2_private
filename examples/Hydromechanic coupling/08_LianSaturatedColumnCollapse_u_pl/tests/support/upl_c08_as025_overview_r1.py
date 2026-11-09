"""Compact view of completed AS025 review; no data transformation or solver."""
import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];tag='upl_c08_as025_overview_r1'
source=T/'figures/upl_c08_as025_review_r2_summary_history.csv';review=T/'logs/upl_c08_as025_review_r2.check.json';png=T/'figures'/(tag+'.png');check=T/'logs'/(tag+'.check.json')
def stat(p):s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
r=json.loads(review.read_text());assert r['passed'] and r['consumed_stats_unchanged'];assert any(e==stat(source) for e in r['files']);assert not png.exists() and not check.exists()
rows=list(csv.DictReader(source.open()));fig,axes=plt.subplots(2,2,figsize=(10,7),sharex=True,layout='constrained')
for g,label,color in [('epsilon0p2_n3',r'$\epsilon=0.20$','#0072B2'),('epsilon0p25_n3',r'$\epsilon=0.25$','#D55E00')]:
 q=[x for x in rows if x['group']==g];assert len(q)==30;t=[float(x['tau_s']) for x in q]
 for ax,key,factor in zip(axes.ravel(),['p_min_Pa','NN_min_over_dp','pairs_lt0p7dp','mean_settlement_from_PRE_mm'],[.001,1.,1.,1.]):ax.plot(t,[float(x[key])*factor for x in q],color=color,label=label,lw=1.6)
for ax,title,ylabel in zip(axes.ravel(),['Saved field minimum pressure','Saved minimum soil spacing','Close pairs at each save','Mean material settlement'],['Pressure [kPa]','Nearest spacing / dp','Unique pairs, r < 0.7 dp','Settlement from PRE [mm]']):ax.set(title=title,ylabel=ylabel,xlabel='Actual time after release [s]',xlim=(0,.30));ax.grid(alpha=.25);ax.legend()
fig.suptitle('C08 psi = 0: AS strength comparison, exponent = 3',fontsize=13);fig.savefig(png,dpi=180);plt.close(fig)
check.write_text(json.dumps(dict(passed=True,source_review=stat(review),source_CSV=stat(source),figure=stat(png),all30_actual_saved_times=True,solver_invocations=0,native_reads=0,physical_acceptance=False),indent=2)+'\n',encoding='utf-8');print(png)
