"""Readable signed-pressure views of already published CSVs; no resampling or solver."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm
T=Path(__file__).resolve().parents[1];C=T.parent
tag='upl_c08_r5_pressure_fields_r1';png=T/'figures'/(tag+'.png');record=T/'logs'/(tag+'.check.json')
assert not png.exists() and not record.exists(),'Existing pressure views are protected'
def stat(p):
    s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
source=C/'figures/collapse_psi0_r5';history=source/'history.csv'
with history.open(encoding='utf-8',newline='') as f:h=list(csv.DictReader(f))
low=min(float(x['p_min_Pa']) for x in h);high=max(float(x['p_max_Pa']) for x in h)
limit=max(abs(low),abs(high))/1000
norm=SymLogNorm(linthresh=.1,vmin=-limit,vmax=limit,base=10)
files=[history,Path(__file__)];fig,axes=plt.subplots(2,3,figsize=(15,7.5),layout='constrained')
for col,tau in enumerate((.6,1.2,3.0)):
    path=source/('fields_tau_'+str(tau)+'.csv');files.append(path)
    with path.open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==5000 and {int(q['native_id']) for q in rows}==set(range(2060,7060))
    x=np.array([float(q['x_m']) for q in rows]);z=np.array([float(q['z_m']) for q in rows])
    actual={float(q['actual_tau_s']) for q in rows};assert len(actual)==1
    for row,key in enumerate(('PorePress_Pa','NativeExcessPorePress_Pa')):
        values=np.array([float(q[key])/1000 for q in rows]);im=axes[row,col].scatter(x,z,c=values,s=5,cmap='RdBu_r',norm=norm,linewidths=0)
        axes[row,col].set(title=('Total p' if row==0 else 'Native p - fixed material P0')+'; tau=%.9g s'%next(iter(actual)),xlabel='x [m]',ylabel='z [m]',xlim=(0,6),ylim=(0,2.1),aspect='equal');axes[row,col].grid(alpha=.15)
        axes[row,col].text(.02,.02,'Snapshot min/max: %.3f / %.3f kPa'%(values.min(),values.max()),transform=axes[row,col].transAxes,fontsize=8)
fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.8,label='Pressure [kPa], signed log outside +/-0.1 kPa; all-run extremes retained')
fig.suptitle('psi0 r5 diagnostic: shared signed scale, no clipping or smoothing\nFull-run total-p extrema: %.3f / %.3f kPa; native excess is not a uniquely established paper excess reference'%(low/1000,high/1000),fontsize=11)
fig.savefig(png,dpi=180);plt.close(fig)
q=dict(stage=tag,passed=True,physical_acceptance=False,source_CSVs=[stat(p) for p in files],PNG=stat(png),raw_Pa_to_kPa_only=True,symlog_display_threshold_kPa=.1,symmetric_color_bound_kPa=limit,no_clipping_interpolation_or_smoothing=True,no_decoder_or_solver=True,visual_QA_pending=True)
record.write_text(json.dumps(q,indent=2)+'\n',encoding='utf-8');print(record)
