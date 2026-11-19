"""Plot the paired times from a completed cryer_dt_gpu run."""
import csv
import sys
from pathlib import Path
from statistics import median

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

tests=Path(__file__).resolve().parents[1]
tag=sys.argv[1] if len(sys.argv)>1 else 'cryer_dt_gpu_r1'
target=tests/'figures'/(tag+'.png')
if target.exists():
    raise FileExistsError(target)
with (tests/'outputs'/tag/'timings.csv').open() as file:
    rows=list(csv.DictReader(file))
fig,axes=plt.subplots(1,2,figsize=(8.8,3.65),constrained_layout=True)
states=(('native_part_65','Native frame 65'),('p3_b64_round3_Jhalf','P3 step 64, half J'))
metrics=(('kernel_us_per_eval','CUDA event · kernels'),('transaction_us_per_eval','Host clock · kernels, copies and checks'))
for ax,(metric,title) in zip(axes,metrics):
    for i,(state,name) in enumerate(states):
        center=3*i
        groups={}
        for row in rows:
            if row['sample']==state:
                groups.setdefault(int(row['paired_group']),{})[row['path']]=float(row[metric])
        points=[[group[key] for key in ('old','fused')] for group in groups.values()]
        for pair in points:
            ax.plot([center,center+1],pair,color='#a6b6c1',lw=1,alpha=.66)
        for k,color in enumerate(('#27475a','#0b7969')):
            values=[pair[k] for pair in points]
            ax.scatter([center+k]*len(values),values,color=color,s=13,alpha=.72,zorder=3)
            ax.plot([center+k-.15,center+k+.15],[median(values)]*2,color='#172832',lw=2.4,zorder=4)
        ax.text(center+.5,-.20,name,transform=ax.get_xaxis_transform(),ha='center',fontsize=9)
    ax.set_xticks([0,1,3,4],['Old','Fused','Old','Fused'])
    ax.set_xlim(-.45,4.45)
    ax.set_ylim(bottom=0)
    ax.set_title(title,fontsize=11,loc='left',fontweight='bold')
    ax.set_ylabel('Microseconds per scale evaluation')
    ax.grid(axis='y',alpha=.19)
    ax.spines[['top','right']].set_visible(False)
fig.savefig(target,dpi=160)
