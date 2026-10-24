"""Plot the audited native corner fields; no solver or physical changes."""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from spr_yao_short import TESTS, bound


def main():
    tag='spr_yao_10s_r1';figures=TESTS/'figures';logs=TESTS/'logs'
    receipt=logs/(tag+'.corner_r1.json');assert not receipt.exists()
    audit=logs/(tag+'.audit_r1.json');review=json.loads(audit.read_text());assert review['passed']
    evidence=[bound(__file__),bound(audit)]
    sources=[figures/(tag+'_fields_r1.csv'),figures/(tag+'_boundary_r1.csv')]
    for path in sources:
        item=bound(path);assert item in review['outputs'];evidence.append(item)
    field=pd.read_csv(sources[0],float_precision='round_trip')
    corner=field[field.x0_m.le(-8.799999)&field.z0_m.le(1.200001)].copy();assert len(corner)==169
    outputs=[];fig,axes=plt.subplots(3,3,figsize=(12,10),layout='constrained')
    labels=['Pore pressure (kPa)','Material settlement (mm)','Vertical total compression (kPa)']
    for row,variable in enumerate(['pressure','settlement','total_compression']):
        unit='mm' if variable=='settlement' else 'pa';scale=1 if unit=='mm' else 1000
        on=corner[variable+'_'+unit]/scale;change=corner[variable+'_on_off_'+unit]/scale;off=on-change
        for col,values in enumerate((off,on,change)):
            ax=axes[row,col]
            if col<2:
                lo=min(float(off.min()),float(on.min()));hi=max(float(off.max()),float(on.max()))
                kw=dict(cmap='viridis',vmin=lo,vmax=hi)
            else:
                limit=max(float(abs(change).max()),1e-14);kw=dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit))
            dots=ax.scatter(corner.x0_m,corner.z0_m,c=values,s=30,marker='s',linewidths=0,**kw);fig.colorbar(dots,ax=ax,shrink=.85)
            ax.set(title=('SPR off','SPR on','On minus off')[col]+'\n'+labels[row],xlabel='Initial material x (m)',ylabel='Initial material z (m)',aspect='equal',xlim=(-10.05,-8.75),ylim=(-.05,1.25))
    fig.suptitle('Native bottom-left corner at actual t = 10 s\nShared off/on scale per row; no spatial interpolation; HG/NoPen off')
    path=figures/(tag+'_corner_r1.png');assert not path.exists();fig.savefig(path,dpi=150);plt.close(fig);outputs.append(bound(path))
    path=figures/(tag+'_corner_r1.csv');corner.to_csv(path,index=False,mode='x');outputs.append(bound(path))
    history=pd.read_csv(sources[1],float_precision='round_trip');fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for ax,name,title in zip(axes,['bottom_normal_displacement_abs_max_mm','side_normal_displacement_abs_max_mm'],['Bottom material normal displacement','Side material normal displacement']):
        for key,color in [('off','#696969'),('on','#2166a5'),('half','#b18b2b')]:
            a=history[history.key.eq(key)];ax.plot(a.time_s,a[name],marker='o',color=color,ls='--' if key=='half' else '-',label=key)
        ax.set(title=title,xlabel='Actual time (s)',ylabel='Maximum absolute residual (mm)');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Fixed-wall residual at six audited times; not every internal step')
    path=figures/(tag+'_wall_r1.png');assert not path.exists();fig.savefig(path,dpi=150);plt.close(fig);outputs.append(bound(path))
    with receipt.open('x',encoding='utf8') as f:json.dump(dict(passed=True,visual_inspected=False,native_corner_nodes=169,evidence=evidence,outputs=outputs),f,indent=2)
    print('Audited native corner and wall residual figures generated.')


if __name__=='__main__':main()
