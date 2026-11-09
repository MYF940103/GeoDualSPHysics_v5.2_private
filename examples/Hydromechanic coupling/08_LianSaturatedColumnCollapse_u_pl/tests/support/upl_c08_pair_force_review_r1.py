"""Plot the sealed six zero-step whole-neighbor force observations."""
from pathlib import Path
import csv,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];tag='upl_c08_pair_force_review_r1';cp=T/'logs/upl_c08_pair_force_cpu_r1.check.json';r=json.loads(cp.read_text());assert r['passed'] and r['consumed_stats_unchanged'];p=T/'outputs/upl_c08_pair_force_cpu_r1/pairs.csv'
def stat(p):s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
assert stat(p) in r['files'];rows=list(csv.DictReader(p.open()));assert len(rows)==6
png=T/'figures'/(tag+'.png');check=T/'logs'/(tag+'.check.json');assert not png.exists() and not check.exists();fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
for mode,label,color,marker in [('baseline','AS on, AV on','#0072B2','o'),('AS_off','AS off only','#D55E00','s'),('AV_off','AV off only','#009E73','^')]:
 q=[x for x in rows if x['mode']==mode];x=[float(z['tau_s']) for z in q];y=[float(z['rddot_m_s2']) for z in q];ax.plot(x,y,marker=marker,color=color,label=label,lw=1.3)
 for a,b in zip(x,y):ax.annotate(f'{b:+.3f}',(a,b),xytext=(7,6),textcoords='offset points',fontsize=9,color=color)
ax.axhline(0,color='black',lw=.7);ax.set(xlabel='Actual saved time after release [s]',ylabel="Instantaneous separation curvature r'' [m/s?]",title='Fixed material pair 7011/7012: complete-neighbor CPU force');ax.set_xticks([.14,.15]);ax.set_xlim(.139,.1525);ax.legend();ax.grid(alpha=.2);fig.suptitle('Six zero-step evaluations; no trajectory or GPU bit-replay claim',fontsize=10);fig.savefig(png,dpi=180);plt.close(fig)
check.write_text(json.dumps(dict(passed=True,component_check=stat(cp),source_pair_CSV=stat(p),figure=stat(png),observations=6,physical_steps=0,AS_or_AV_changes_not_future_trajectory=True,physical_acceptance=False),indent=2)+'\n',encoding='utf-8');print(png)
